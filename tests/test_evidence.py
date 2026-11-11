"""Tests de scripts/evidence.py y scripts/mutation_report.py, y de la evidencia de mutación."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

from scripts import evidence as ev
from scripts import mutation_report as mr

REPO = Path(__file__).resolve().parents[1]


def _git(cwd: Path, *a: str) -> None:
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo_tmp(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.txt").write_text("a\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "base")
    return tmp_path


# --- manifiesto ------------------------------------------------------------------------
@pytest.mark.req("REQ-NFR-014")
def test_manifiesto_y_verificacion(repo_tmp: Path) -> None:
    d = repo_tmp / "docs" / "evidence" / "FASE-9"
    d.mkdir(parents=True)
    (d / "uno.txt").write_text("1\n")
    (d / "sub").mkdir()
    (d / "sub" / "dos.txt").write_text("2\n")
    ev.write_manifest(d, repo_tmp)
    texto = (d / "MANIFEST.sha256").read_text()
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_tmp, capture_output=True, text=True
    ).stdout.strip()
    assert f"# commit: {commit}" in texto
    assert hashlib.sha256(b"1\n").hexdigest() + "  uno.txt" in texto
    assert "  sub/dos.txt" in texto
    assert ev.verify_manifest(d) == []


@pytest.mark.req("REQ-NFR-014")
def test_manipulacion_detectada(repo_tmp: Path) -> None:
    d = repo_tmp / "ev"
    d.mkdir()
    (d / "uno.txt").write_text("1\n")
    ev.write_manifest(d, repo_tmp)
    (d / "uno.txt").write_text("2\n")
    assert ev.verify_manifest(d) == ["modificado: uno.txt"]
    (d / "nuevo.txt").write_text("x\n")
    assert "no listado: nuevo.txt" in ev.verify_manifest(d)
    (d / "uno.txt").unlink()
    assert "falta: uno.txt" in ev.verify_manifest(d)


@pytest.mark.req("REQ-NFR-014")
def test_arbol_sucio_se_declara(repo_tmp: Path) -> None:
    d = repo_tmp / "ev"
    d.mkdir()
    (repo_tmp / "a.txt").write_text("cambiado\n")
    ev.write_manifest(d, repo_tmp)
    assert "# árbol de trabajo limpio: no" in (d / "MANIFEST.sha256").read_text()


@pytest.mark.req("REQ-NFR-014")
def test_verificar_sin_manifiesto_falla(tmp_path: Path) -> None:
    assert ev.verify_manifest(tmp_path) == ["no existe MANIFEST.sha256"]


@pytest.mark.req("REQ-NFR-014")
def test_capturar_comando_guarda_salida_y_codigo(repo_tmp: Path) -> None:
    out = repo_tmp / "salida.txt"
    argv = [sys.executable, "-c", "print('hola'); raise SystemExit(3)"]
    rc = ev.capture(argv, out, repo_tmp)
    assert rc == 3
    texto = out.read_text()
    assert "raise SystemExit(3)" in texto.splitlines()[1]
    assert "hola" in texto
    assert texto.rstrip().endswith("exit=3")
    assert "# commit:" in texto.splitlines()[0]


@pytest.mark.req("REQ-NFR-014")
def test_cli_verify(repo_tmp: Path) -> None:
    d = repo_tmp / "ev"
    d.mkdir()
    (d / "x.txt").write_text("x\n")
    ev.write_manifest(d, repo_tmp)
    assert ev.main(["--verify", str(d)]) == 0
    (d / "x.txt").write_text("y\n")
    assert ev.main(["--verify", str(d)]) == 1


# --- informe de mutación ----------------------------------------------------------------
@pytest.mark.req("REQ-NFR-018")
def test_informe_de_mutacion(tmp_path: Path) -> None:
    src = tmp_path / "scripts" / "m.py"
    src.parent.mkdir()
    src.write_text("x = 1\n")
    meta = tmp_path / "mutants" / "scripts" / "m.py.meta"
    meta.parent.mkdir(parents=True)
    codes = {"a": 1, "b": 1, "c": 1, "d": 0, "e": None, "f": 36}
    meta.write_text(json.dumps({"exit_code_by_key": codes}))
    (tmp_path / "tests" / "guardrails").mkdir(parents=True)
    (tmp_path / "tests" / "guardrails" / "t.py").write_text("x\n")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.mutmut]\npytest_add_cli_args_test_selection = ["tests/guardrails/"]\n'
    )
    rep = mr.report(tmp_path, "scripts/m.py")
    assert rep["killed"] == 3
    assert rep["survived"] == 1
    assert rep["other"] == 1
    assert rep["total"] == 5  # sin contar los no ejecutados
    assert rep["score"] == pytest.approx(0.6)
    assert rep["survivors"] == ["d"]
    assert rep["sha256"] == hashlib.sha256(b"x = 1\n").hexdigest()
    assert rep["tests_sha256"] == mr.tests_digest(tmp_path)
    (tmp_path / "tests" / "guardrails" / "t.py").write_text("y\n")
    assert rep["tests_sha256"] != mr.tests_digest(tmp_path)


@pytest.mark.req("REQ-NFR-018")
def test_informe_sin_meta_falla(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        mr.report(tmp_path, "scripts/no.py")


# --- la evidencia de mutación corresponde al código actual y supera el umbral ------------
def _umbrales() -> dict[str, Any]:
    data = tomllib.loads((REPO / "pyproject.toml").read_text())
    return dict(data["tool"]["atalaya"])


def evidencia_mutacion_problemas(repo: Path, fase: str) -> list[str]:
    cfg = _umbrales()
    path = repo / "docs" / "evidence" / fase / "mutacion.json"
    if not path.exists():
        return [f"no existe {path.relative_to(repo)}"]
    data = json.loads(path.read_text())
    problemas = []
    for rel in cfg["mutation_critical"]:
        entrada = data.get(rel)
        if entrada is None:
            problemas.append(f"{rel}: sin evidencia de mutación")
            continue
        actual = hashlib.sha256((repo / rel).read_bytes()).hexdigest()
        if entrada["sha256"] != actual:
            problemas.append(f"{rel}: evidencia obsoleta (el código cambió; ejecuta make mutation)")
        if entrada.get("tests_sha256") != mr.tests_digest(repo):
            problemas.append(f"{rel}: los tests cambiaron desde la última mutación (make mutation)")
        if entrada.get("inputs_sha256") != mr.inputs_digest(repo, cfg["mutation_critical"]):
            problemas.append(f"{rel}: inputs de mutación obsoletos (make mutation)")
        if entrada["score"] < float(cfg["mutation_threshold"]):
            problemas.append(f"{rel}: puntuación {entrada['score']:.3f} < umbral")
        if not mr.valid_report(entrada, float(cfg["mutation_threshold"])):
            problemas.append(f"{rel}: informe de mutación incompleto o inconsistente")
    return problemas


@pytest.mark.req("REQ-NFR-018")
def test_evidencia_de_mutacion_vigente(repo: Path) -> None:
    assert evidencia_mutacion_problemas(repo, "FASE-0") == []

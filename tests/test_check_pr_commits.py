"""Higiene de historia: la CI rechaza PR con commits WIP o «sin verificar»."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts import check_pr_commits as cpc

pytestmark = pytest.mark.req("REQ-NFR-014")

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_pr_commits.py"


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


def repo_con_commits(tmp_path: Path, asuntos: list[str]) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "test")
    git(tmp_path, "config", "core.hooksPath", "/dev/null")
    git(tmp_path, "commit", "-q", "--allow-empty", "-m", "base")
    git(tmp_path, "branch", "base")
    for asunto in asuntos:
        git(tmp_path, "commit", "-q", "--allow-empty", "-m", asunto)
    return tmp_path


def comprobar(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "--range", "base..HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "asunto",
    [
        "wip: guardar trabajo",
        "WIP(phase1): contratos",
        "feat: algo [Wip]",
        "docs: registro (sin verificar)",
        "fix: SIN VERIFICAR todavía",
    ],
)
def test_asuntos_prohibidos_se_detectan(asunto: str) -> None:
    assert cpc.offending(["feat: limpio", asunto]) == [asunto]


@pytest.mark.parametrize(
    "asunto",
    [
        "wip(piloto): iteración 4",
        "fix: sin verificar, falta CI",
        "docs: registro [sin verificar]",
    ],
)
def test_marcas_reales_de_la_historia_se_detectan(asunto: str) -> None:
    assert cpc.offending([asunto]) == [asunto]


def test_asuntos_limpios_pasan() -> None:
    limpios = ["feat(sim): red y relojes [REQ-FUN-004]", "docs: verificado con make check"]
    assert cpc.offending(limpios) == []


@pytest.mark.parametrize(
    "asunto",
    [
        # Mencionar la regla no es marcar el commit (el propio commit que la introduce).
        "ci: rechazar PR con commits provisionales o sin verificar en su rango",
        "feat(ui): gesto swipe en el mapa",
        "docs: wiping de caché explicado",
    ],
)
def test_menciones_no_son_marcas(asunto: str) -> None:
    assert cpc.offending([asunto]) == []


@pytest.mark.subproceso
def test_rango_con_commit_wip_falla(tmp_path: Path) -> None:
    proc = comprobar(repo_con_commits(tmp_path, ["feat: limpio", "wip: a medias (sin verificar)"]))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "wip: a medias (sin verificar)" in proc.stdout
    assert "feat: limpio" not in proc.stdout


@pytest.mark.subproceso
def test_rango_limpio_pasa(tmp_path: Path) -> None:
    proc = comprobar(repo_con_commits(tmp_path, ["feat: limpio", "docs: registro verificado"]))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK (2 commits)" in proc.stdout


@pytest.mark.subproceso
def test_rango_inexistente_falla_cerrado(tmp_path: Path) -> None:
    repo_con_commits(tmp_path, [])
    proc = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "--range", "noexiste..HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2


def test_main_en_proceso(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_con_commits(tmp_path, ["WIP final"])
    monkeypatch.chdir(tmp_path)
    assert cpc.main(["--range", "base..HEAD"]) == 1
    assert cpc.main(["--range", "noexiste..HEAD"]) == 2
    git(tmp_path, "commit", "-q", "--amend", "--allow-empty", "-m", "feat: limpio")
    assert cpc.main(["--range", "base..HEAD"]) == 0


@pytest.mark.req("REQ-SEC-012")
def test_ci_ejecuta_el_control_solo_en_pull_request(repo: Path) -> None:
    ci = (repo / ".github/workflows/ci.yml").read_text()
    idx = ci.index("scripts/check_pr_commits.py")
    paso = ci[ci.rindex("- name:", 0, idx) : idx]
    assert "if: github.event_name == 'pull_request'" in paso
    assert "origin/${BASE_REF}..HEAD" in ci[idx : idx + 80]

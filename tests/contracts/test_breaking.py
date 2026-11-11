"""Comprueba la compatibilidad Protobuf contra una referencia Git archivada."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "proto_breaking.sh"


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def repo_with_baseline(tmp_path: Path, *, contracts: bool = True) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    scripts = repo / "scripts"
    scripts.mkdir()
    shutil.copy2(SCRIPT, scripts / SCRIPT.name)
    shutil.copy2(ROOT / "buf.yaml", repo / "buf.yaml")
    if contracts:
        for source in (ROOT / "proto").rglob("*.proto"):
            target = repo / "proto" / source.relative_to(ROOT / "proto")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    else:
        (repo / "README.md").write_text("sin contratos\n", encoding="utf-8")
    git(repo, "add", "buf.yaml", "proto" if contracts else "README.md")
    git(
        repo,
        "-c",
        "user.name=Atalaya Tests",
        "-c",
        "user.email=tests@example.invalid",
        "commit",
        "-qm",
        "baseline",
    )
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repo


def breaking(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(repo / "scripts" / SCRIPT.name), *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.req("REQ-FUN-002")
def test_contratos_sin_cambios_son_compatibles(tmp_path: Path) -> None:
    repo = repo_with_baseline(tmp_path)

    assert breaking(repo).returncode == 0  # REF por defecto: origin/main.
    assert breaking(repo, "HEAD").returncode == 0


@pytest.mark.req("REQ-FUN-002")
def test_sin_proto_en_ref_informa_ausencia_de_linea_base(tmp_path: Path) -> None:
    repo = repo_with_baseline(tmp_path, contracts=False)

    result = breaking(repo)

    assert result.returncode == 0
    assert "sin línea base" in result.stdout


@pytest.mark.req("REQ-FUN-002")
def test_ref_invalida_falla_en_lugar_de_omitir_comprobacion(tmp_path: Path) -> None:
    repo = repo_with_baseline(tmp_path)

    result = breaking(repo, "ref-inexistente")

    assert result.returncode != 0
    assert "referencia inválida" in result.stderr


@pytest.mark.req("REQ-FUN-002")
def test_renumerar_detection_y_borrar_campo_track_son_dos_violaciones(tmp_path: Path) -> None:
    repo = repo_with_baseline(tmp_path)
    detection = repo / "proto" / "atalaya" / "v1" / "detection.proto"
    original = detection.read_text(encoding="utf-8")
    field = "optional string detection_id = 1 ["
    assert original.count(field) == 1
    detection.write_text(original.replace(field, "optional string detection_id = 101 ["))

    track = repo / "proto" / "atalaya" / "v1" / "track.proto"
    original = track.read_text(encoding="utf-8")
    removed = (
        "  PositionCovariance state_covariance = 4 "
        "[(atalaya.v1.sensitivity) = OPERATOR, (atalaya.v1.required) = true];\n"
    )
    assert original.count(removed) == 1
    track.write_text(original.replace(removed, ""), encoding="utf-8")

    result = breaking(repo, "HEAD")
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert 'field "1" with name "detection_id" on message "Detection" was deleted' in output
    assert 'field "4" with name "state_covariance" on message "Track" was deleted' in output


@pytest.mark.req("REQ-FUN-002")
def test_campo_nuevo_es_compatible(tmp_path: Path) -> None:
    repo = repo_with_baseline(tmp_path)
    track = repo / "proto" / "atalaya" / "v1" / "track.proto"
    original = track.read_text(encoding="utf-8")
    anchor = (
        "  TimeQuality time_quality = 10 "
        "[(atalaya.v1.sensitivity) = OPERATOR, (atalaya.v1.required) = true];\n"
    )
    assert original.count(anchor) == 1
    added = "  optional string breaking_probe = 11 [(atalaya.v1.sensitivity) = OPERATOR];\n"
    track.write_text(original.replace(anchor, anchor + added), encoding="utf-8")

    assert breaking(repo, "HEAD").returncode == 0

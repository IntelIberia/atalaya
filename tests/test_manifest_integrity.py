"""Regresiones de integridad del paquete de evidencias (T0.9)."""

from pathlib import Path

import pytest

from scripts import evidence


@pytest.mark.req("REQ-NFR-014")
def test_nested_manifest_is_verified(tmp_path: Path) -> None:
    nested = tmp_path / "sub" / evidence.MANIFEST
    nested.parent.mkdir()
    nested.write_text("original\n")
    evidence.write_manifest(tmp_path)
    nested.write_text("alterado\n")
    assert "modificado: sub/MANIFEST.sha256" in evidence.verify_manifest(tmp_path)


@pytest.mark.req("REQ-NFR-014")
def test_duplicate_manifest_entry_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("original")
    manifest = evidence.write_manifest(tmp_path)
    entry = manifest.read_text().splitlines()[-1]
    manifest.write_text(manifest.read_text() + entry + "\n")
    assert evidence.main(["--verify", str(tmp_path)]) == 1


@pytest.mark.req("REQ-NFR-014")
@pytest.mark.parametrize("line", ["broken", "not-a-hash  a.txt", "0" * 64 + "  ../a.txt"])
def test_malformed_manifest_fails_cleanly(tmp_path: Path, line: str) -> None:
    (tmp_path / evidence.MANIFEST).write_text(line + "\n")
    assert evidence.main(["--verify", str(tmp_path)]) == 1


@pytest.mark.req("REQ-NFR-014", "REQ-SEC-005")
def test_phase_evidence_requires_integration_report() -> None:
    command = evidence.closing_commands("0")["trazabilidad.txt"]
    assert command.count("--junit") == 2
    assert "reports/junit-integracion.xml" in command

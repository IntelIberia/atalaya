"""La generación de evidencias no puede alterar un paquete ya cerrado."""

from pathlib import Path

import pytest

from scripts import evidence


@pytest.mark.req("REQ-NFR-014")
@pytest.mark.parametrize("via", ["fase", "manifest", "manifest_child"])
def test_cli_rechaza_reescritura_de_fase_cerrada(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, via: str
) -> None:
    registry = tmp_path / "docs" / "requirements" / "FASES-CERRADAS.txt"
    registry.parent.mkdir(parents=True)
    registry.write_text("# cerrado\n-1\n0\n", encoding="utf-8")
    directory = tmp_path / "docs" / "evidence" / "FASE-0"
    directory.mkdir(parents=True)
    manifest = directory / "MANIFEST.sha256"
    manifest.write_text("evidencia congelada\n", encoding="utf-8")
    monkeypatch.setattr(evidence, "ROOT", tmp_path)

    child = directory / "relevo-2026-11-10"
    child.mkdir()
    arguments = (
        ["--fase", "0"]
        if via == "fase"
        else ["--manifest", str(child if via == "manifest_child" else directory)]
    )
    assert evidence.main(arguments) == 1
    assert manifest.read_text(encoding="utf-8") == "evidencia congelada\n"
    assert not (child / "MANIFEST.sha256").exists()


@pytest.mark.req("REQ-NFR-014")
def test_cli_rechaza_ruta_en_numero_de_fase() -> None:
    with pytest.raises(SystemExit):
        evidence.main(["--fase", "0/../FASE-1"])

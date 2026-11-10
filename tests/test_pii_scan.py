"""Detector de datos personales en logs y salidas (REQ-PRIV-003)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import pii_scan as ps

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.req("REQ-PRIV-003")
@pytest.mark.parametrize(
    ("texto", "tipo"),
    [
        ("contacto: ana.garcia@correo.es", "email"),
        ("tel +34 612 345 678", "telefono"),
        ("llamar al 612345678", "telefono"),
        ("DNI 12345678Z", "dni"),
        ("NIE X1234567L", "nie"),
        ("IBAN ES91 2100 0418 4502 0005 1332", "iban"),
        ("cliente desde 83.45.120.7", "ipv4_publica"),
    ],
    ids=lambda v: "muestra",  # sin datos (aunque sintéticos) en los nombres del JUnit
)
def test_detecta(texto: str, tipo: str) -> None:
    assert tipo in {h.kind for h in ps.scan_text(texto)}


@pytest.mark.req("REQ-PRIV-003")
@pytest.mark.parametrize(
    "texto",
    [
        "noreply@anthropic.com",  # direcciones técnicas permitidas
        "123456789+IntelIberia@users.noreply.github.com",
        "t@example.invalid",
        "escucha en 127.0.0.1:1883 y 10.0.0.5",
        "commit 4039896a96e77040910406b09a9d6b7be05c8bcb",
        "versión 2.0.22 · 1.75.0",
        "DNI 12345678A",  # letra de control incorrecta: no es un DNI válido
        "hackrf -f 915000000 (915 MHz)",  # frecuencia, no teléfono
    ],
    ids=lambda v: "muestra",
)
def test_no_falsos_positivos(texto: str) -> None:
    assert ps.scan_text(texto) == []


@pytest.mark.req("REQ-PRIV-003")
def test_evidencias_y_logs_sin_datos_personales() -> None:
    rutas = [REPO / "docs" / "evidence", REPO / "reports"]
    hallazgos = [h for r in rutas if r.exists() for h in ps.scan_tree(r)]
    assert hallazgos == []


@pytest.mark.req("REQ-PRIV-003")
def test_scan_tree_detecta(tmp_path: Path) -> None:
    (tmp_path / "log.json").write_text('{"msg": "alta de pepe@dominio.com"}\n')
    hits = ps.scan_tree(tmp_path)
    assert [(h.kind, h.line) for h in hits] == [("email", 1)]


@pytest.mark.req("REQ-PRIV-003")
def test_relevo_telefono_terminado_en_ceros() -> None:
    assert {h.kind for h in ps.scan_text('{"telefono":"+34 612 340 000"}')} == {"telefono"}


@pytest.mark.req("REQ-PRIV-003")
def test_relevo_noreply_dentro_de_nombre_personal() -> None:
    assert {h.kind for h in ps.scan_text('{"email":"ana.noreply@correo.es"}')} == {"email"}

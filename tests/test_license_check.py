"""Tests de scripts/license_check.py (G-12, REQ-LEG-016)."""

from __future__ import annotations

import pytest

from scripts import license_check as lc


@pytest.mark.req("REQ-LEG-016")
@pytest.mark.parametrize(
    ("texto", "bloqueada"),
    [
        ("GPL-3.0-or-later", True),
        ("AGPL-3.0-only", True),
        ("License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)", True),
        ("License :: OSI Approved :: GNU Affero General Public License v3", True),
        ("LGPL-2.1-or-later", False),
        ("License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)", False),
        ("MIT", False),
        ("Apache-2.0", False),
        ("MPL-2.0", False),
        ("BSD-3-Clause", False),
    ],
)
def test_clasificacion(texto: str, bloqueada: bool) -> None:
    assert lc.is_strong_copyleft(texto) is bloqueada


@pytest.mark.req("REQ-LEG-016")
def test_nombres_de_requirements() -> None:
    texto = (
        "# comentario\nfoo==1.0 \\\n    --hash=sha256:abc\n-e .\n"
        "Bar_Baz==2.0 ; python_version >= '3.12'\n"
    )
    assert lc.parse_requirements(texto) == ["foo", "bar-baz"]


@pytest.mark.req("REQ-LEG-016")
def test_dependencia_gpl_de_ejecucion_bloquea() -> None:
    licencias = {"limpia": "MIT", "copyleft": "GPL-2.0-or-later"}
    bloqueadas = lc.evaluate(["limpia", "copyleft"], licencias.__getitem__)
    assert bloqueadas == [("copyleft", "GPL-2.0-or-later")]


@pytest.mark.req("REQ-LEG-016")
def test_licencia_desconocida_bloquea() -> None:
    assert lc.evaluate(["rara"], lambda _n: "") == [("rara", "(desconocida)")]


@pytest.mark.req("REQ-LEG-016")
def test_licencia_de_paquete_instalado() -> None:
    assert "MIT" in lc.license_of("pyyaml")


@pytest.mark.req("REQ-LEG-016")
def test_paquete_no_instalado() -> None:
    assert lc.license_of("paquete-que-no-existe-xyz") == lc.NOT_INSTALLED

"""Configuración común de pytest para Atalaya."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def repo() -> Path:
    """Raíz del repositorio."""
    return REPO


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Copia los IDs de @pytest.mark.req a las propiedades del JUnit XML (trazabilidad).

    Fallo cerrado: si algún test recogido (antes de deseleccionar con -m o -k) no lleva un
    marcador `req` con al menos un ID, la recogida falla y no se ejecuta nada.
    """
    sin_req: list[str] = []
    for item in items:
        ids = [rid for marker in item.iter_markers(name="req") for rid in marker.args]
        if not ids:
            sin_req.append(item.nodeid)
        for rid in ids:
            item.user_properties.append(("req", rid))
    if sin_req:
        lista = "\n  ".join(sin_req)
        raise pytest.UsageError(
            f"trazabilidad: {len(sin_req)} test(s) sin marcador req "
            f'(añade @pytest.mark.req("REQ-…") o pytestmark):\n  {lista}'
        )


@pytest.fixture(autouse=True)
def _git_aislado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Los repos temporales de los tests no heredan la configuración global de git."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

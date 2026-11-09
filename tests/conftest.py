"""Configuración común de pytest para Atalaya."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def repo() -> Path:
    """Raíz del repositorio."""
    return REPO


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Copia los IDs de @pytest.mark.req a las propiedades del JUnit XML (trazabilidad)."""
    for item in items:
        for marker in item.iter_markers(name="req"):
            for rid in marker.args:
                item.user_properties.append(("req", rid))


@pytest.fixture(autouse=True)
def _git_aislado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Los repos temporales de los tests no heredan la configuración global de git."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

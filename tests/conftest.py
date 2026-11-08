"""Configuración común de pytest para Atalaya."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def repo() -> Path:
    """Raíz del repositorio."""
    return REPO

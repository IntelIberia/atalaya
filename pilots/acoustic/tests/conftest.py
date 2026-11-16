"""Configuración común de los tests del piloto acústico (proyecto uv aparte, ADR 0016)."""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    # Trazabilidad del hito 2: los tests nuevos citan sus requisitos (p. ej. REQ-FUN-027).
    config.addinivalue_line("markers", "req(*ids): requisitos que cubre el test")

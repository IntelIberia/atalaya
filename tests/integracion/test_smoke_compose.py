"""Integración con el stack de compose en marcha (REQ-SEC-005): cada servicio funciona con
credenciales y rechaza el acceso sin ellas. Se ejecuta con `make up && make smoke`; queda
fuera de `make test` (marcador `integracion`) porque necesita Docker y el stack arrancado."""

from __future__ import annotations

import pytest

from scripts import smoke_compose

pytestmark = pytest.mark.integracion


@pytest.mark.req("REQ-SEC-005", "REQ-NFR-015")
def test_stack_rechaza_accesos_sin_credenciales() -> None:
    assert smoke_compose.main() == 0

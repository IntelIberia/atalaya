"""Integración con el stack de compose en marcha (REQ-SEC-005): cada servicio funciona con
credenciales y rechaza el acceso sin ellas. Se ejecuta con `make up && make smoke`; queda
fuera de `make test` (marcador `integracion`) porque necesita Docker y el stack arrancado."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from scripts import integration_evidence, smoke_compose

pytestmark = pytest.mark.integracion


@pytest.mark.req("REQ-SEC-005", "REQ-NFR-015")
def test_stack_rechaza_accesos_sin_credenciales(
    record_property: Callable[[str, object], None],
) -> None:
    record_property("integration_source_sha256", integration_evidence.source_digest())
    assert smoke_compose.main() == 0

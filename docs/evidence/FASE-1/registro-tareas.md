# Registro de tareas — FASE 1

| Fecha | Commit | Tarea | Comando de verificación | Resultado real | Prueba negativa | Estado |
|---|---|---|---|---|---|---|
| 2026-11-10 | pendiente | T1.0 precondiciones, P0 y ADR 0009–0013 | `make regress`; `uv run --frozen pytest -q tests/test_documentos.py`; `python3 -I scripts/check_spec.py` | P0 y D-1–D-8 anotados; FASE 0 cerrada con tag; B-07b distingue no conformidad SAPIENT verificada de pruebas locales | Clon temporal sin `fase-0-cerrada`: precondición `test -n "$(git tag -l fase-0-cerrada)"` exit 1; test documental cubre estructura de ADR | OK |
| 2026-11-10 | pendiente | T1.1 dependencias y entorno | `uv sync --frozen`; `uv run --frozen python -m grpc_tools.protoc --version`; `uv run --frozen python -m scripts.license_check`; `make doctor`; `make check` | Dependencias instaladas y evaluadas; `libprotoc 35.1`; licencias preliminares OK; Makefile/doctor incorporan el compilador. En curso: actualizar evidencia FASE 0 invalidada por los nuevos inputs | Tests existentes `test_license_check.py`: GPL/AGPL de ejecución y licencia desconocida bloquean | EN CURSO |

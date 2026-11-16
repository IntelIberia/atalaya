# Registro de tareas — HITO 2

| Fecha | Commit | Tarea | Comando de verificación | Resultado real | Prueba negativa | Estado |
|---|---|---|---|---|---|---|
| 2026-11-16 | (este commit) | T0.1 extra `live` (REQ-NFR-015, REQ-NFR-016, REQ-LEG-016) | `uv lock`; `uv sync --extra live --frozen`; `uv run --frozen --extra live python -c "import onnxruntime, sounddevice; ..."`; `du -sk .venv`; `uv run --frozen pytest -q tests/live/test_live_deps.py` | onnxruntime 1.23.2 y sounddevice 0.5.6 (PortAudio V19.7.0-devel) importan en el Mac Intel (macOS 15.8.3, x86_64); `.venv` 257 412 kB → 388 120 kB (+128 MB ≤ 300 MB); licencias MIT/BSD/Apache-2.0 registradas en el anexo T0.1 del ADR 0017; 3 tests en verde. (a) base con la iteración 5 (`98455be` no es antecesor de `fc11581`) queda fuera de este bloque | `uv tree --extra live --frozen \| grep -ci tensorflow` → 0; el test rechaza versiones no exactas o TensorFlow en el extra | OK |

# Registro de tareas — HITO 2

Cada fila recoge la verificación **real** ejecutada antes del commit de la tarea (comandos en
`pilots/acoustic/`). El commit de cada tarea es el que lleva su ID al principio del asunto
(`git log --oneline --grep '^H2.N'`); el propio commit no puede contener su hash.

| Fecha | Commit | Tarea | Comando de verificación | Resultado real | Prueba negativa | Estado |
|---|---|---|---|---|---|---|
| 2026-11-16 | `H2.1` | H2.1 Normalización de canal compartida (`acoustic_pilot/channel_norm.py`) | `uv run --frozen pytest -q tests/test_channel_norm.py` | 19 passed: tono de 1 kHz tras 48/44,1 → 16 kHz con error ≤ 1 Hz; banda 100 Hz–7,5 kHz dentro de ±1 dB (−0,49 dB a 100 Hz) y −58,9 dB a 30 Hz; −20/+6 dB dan la misma ventana (≤ 1e-3); salida finita, determinista y con pico ≤ 0,99; PCEN realza un clic sobre ruido estacionario; módulo autocontenido (numpy, scipy, stdlib) | 11 025, 8 000, 0 y −16 000 Hz → `ValueError`; NaN/±inf → `ValueError`; silencio digital y −120 dBFS sin ganancia; −70 dBFS limitado a +30 dB | OK |

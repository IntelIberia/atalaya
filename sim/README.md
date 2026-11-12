# sim

Simulador y gemelo digital, reproducible por semilla.

## Escenarios (T1.9, REQ-FUN-005)

- `scenarios/<nombre>.yaml`: entorno, emplazamientos, amenazas, aeronaves tripuladas y fallos;
  valida contra `schemas/scenario.schema.json` (`additionalProperties: false` en todo objeto).
- `scenarios/<nombre>.nodes.geo.json`: GeoJSON con el centro de cada emplazamiento y los nodos;
  valida contra `schemas/nodes.geo.schema.json`.
- Carga: `sim.scenario.load_scenario(Path(...))`; los errores (`ScenarioError`) llevan la ruta del dato.

Privacidad geográfica: los centros son **ficticios** (D-8), sobre mar abierto, redondeados a 0,01°;
nodos, rutas, objetivos y `launch_point` son desplazamientos locales en metros. `launch_point`
equivale al origen probable y se declara `FCSE_ONLY`. Las aeronaves tripuladas usan identificadores
sintéticos con prefijo `SIM`.

## Núcleo y reproducibilidad (T1.10, REQ-FUN-003)

- `engine.py`: cola de eventos ordenada por `(tiempo_ns, orden de programación)`; tiempo entero en
  nanosegundos; cada `Envelope` lleva una secuencia global y se serializa de forma determinista.
- `rng.py`: un `random.Random` por componente con subsemilla
  `sha256("atalaya-sim-v1" ‖ 0 ‖ semilla ‖ 0 ‖ componente)`; prohibidos el `random` global,
  `hash()`, el reloj del sistema y `uuid4` (lo comprueba un análisis estático en los tests).
- `geo.py`: WGS84 ↔ ECEF ↔ ENU local; `clock.py`: época simulada fija (2026-01-01T00:00:00Z).
- CLI: `uv run python -m sim run --scenario sim/scenarios/X.yaml [--seed N] [--duration S] --out F.pb.zst`
  y `uv run python -m sim hash F.pb.zst`; ambos imprimen `stream_sha256` (flujo sin comprimir,
  `varint(longitud) ‖ Envelope`) y `file_sha256` (zstd nivel 10).
- Por ahora solo se emite el latido `NodeStatus` de cada nodo cada 30 s simulados (datos
  sintéticos); trayectorias, sensores, red, fallos, replay con cabecera y MQTT llegan en T1.11–T1.16.

## Trayectorias (T1.11, REQ-FUN-004)

- `classes.py`: cinemática C1-C8 (crucero, máxima, aceleración y tasa de giro), cada valor con su
  procedencia; **hoy todos NO VERIFICADO** (estimaciones; C6/C7 declarados, no medidos). C9 no vuela.
- `trajectory.py`: `Trajectory(clase, puntos_de_paso, velocidad)` con tramos rectos y giros
  coordinados (radio `max(v/ω, 2v²/a)`), altitud con `smoothstep` y, solo en C1-C2, arranque y
  parada en reposo y vuelo estacionario (`hover_s`). Rutas imposibles → `ValueError` con la clase y
  el límite. `state(t)` da posición, velocidad y aceleración ENU.

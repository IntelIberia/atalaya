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

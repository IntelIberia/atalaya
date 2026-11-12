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
  `varint(longitud) ‖ Envelope`) y `file_sha256` (fichero de replay completo). Desde T1.15
  `run` escribe el replay versionado e incluye todos los sensores (ver «Replay»).
- La red de T1.13 y MQTT se integran en T1.16 (construcción, sin publicación), T1.7b y T1.17.

## Trayectorias (T1.11, REQ-FUN-004)

- `classes.py`: cinemática C1-C8 (crucero, máxima, aceleración y tasa de giro), cada valor con su
  procedencia; **hoy todos NO VERIFICADO** (estimaciones; C6/C7 declarados, no medidos). C9 no vuela.
- `trajectory.py`: `Trajectory(clase, puntos_de_paso, velocidad)` con tramos rectos y giros
  coordinados (radio `max(v/ω, 2v²/a)`), altitud con `smoothstep` y, solo en C1-C2, arranque y
  parada en reposo y vuelo estacionario (`hover_s`). Rutas imposibles → `ValueError` con la clase y
  el límite. `state(t)` da posición, velocidad y aceleración ENU.

## Propagación acústica y detección (T1.12, REQ-FUN-004, REQ-FUN-062)

- `acoustics.py`: divergencia esférica (−20·log10 r), absorción atmosférica con la formulación de
  ISO 9613-1 (ecuaciones tomadas de dos fuentes públicas secundarias y contrastadas con una tabla
  publicada; texto original de la norma **NO VERIFICADO**), velocidad del sonido según la
  temperatura, corrección por viento a favor/en contra y ruido de viento sumado al fondo por bandas
  (modelo de viento **NO VERIFICADO**). Sin viento, el nivel decrece estrictamente con la distancia.
- `sensors/acoustic.py`: SNR por banda → probabilidad de detección logística → `Detection` con
  `class_scores` de una matriz de confusión configurable, `detection_confidence`, `time_quality` y
  rumbo con su incertidumbre; toda `Detection` pasa `validate()`. Espectros de fuente por clase y
  matriz por defecto **NO VERIFICADO**. `acoustic_components(escenario)` da un componente del motor
  por nodo acústico (se pasa con `extra_components`; desde T1.15 lo incluye `python -m sim run`).
- **Sin audio en ningún punto:** solo niveles por banda, SNR y puntuaciones.

## Red, relojes y fallos (T1.13, REQ-FUN-004)

- `network.py`: `transmit_scenario(escenario, envelopes, semilla)` aplica por nodo latencia
  lognormal, pérdidas, duplicados (copia idéntica, mismo `detection_id`) y desorden, y devuelve las
  entregas por instante de llegada. Valores por defecto (20 ms, σ 0,5) **NO VERIFICADO**.
- `clock.py`: deriva lineal en ppm (`drift_offset_ms`) y σ del reloj con o sin PPS.
- `faults.py`: `node_down`, `link_down`, `pps_invalid`, `clock_drift`, `latency`, `packet_loss`,
  `duplicate`, `reorder`; las magnitudes imposibles se rechazan al cargar el escenario. El latido
  `NodeStatus` y el sensor acústico respetan nodo caído, PPS perdido y deriva (solo sin PPS).
- La CLI `python -m sim run` aún escribe el flujo emitido, sin red; la red se aplicará en el
  extremo a extremo (T1.16–T1.17); el replay de T1.15 graba lo emitido.

## Remote ID y ADS-B (T1.14, REQ-FUN-004, REQ-LEG-007, REQ-LEG-001)

- **Solo datos en memoria:** mensajes Protobuf internos como los que entregaría un receptor tras
  decodificar. Ni tramas, ni radio, ni Wi-Fi, ni Bluetooth; un test estático comprueba que `sim/`
  no importa bibliotecas de ese tipo.
- `sensors/remote_id.py`: por amenaza con Remote ID (`compliant` o `forged`, norma EN 4709-002 o
  ASTM F3411) un componente que cada segundo registra la verdad terreno (`Engine.ground_truth`,
  nunca en `Envelope`) y entrega `Detection.remote_id` a los receptores en alcance y en servicio.
  Conforme: posición real + ruido gaussiano truncado (σ 3 m, ±4σ: error ≤ 20,8 m). Falsificado:
  desplazamiento de 400 m con giros ≥ 90° cada 5 mensajes (saltos imposibles, posición
  incompatible con la acústica); la `Detection` tiene la misma forma que la conforme y solo
  `GroundTruth.is_forged` lo sabe. `uas_id`, `operator_id` y `operator_location` son sintéticos
  (`SIM-…`) y `FCSE_ONLY`; `self_id_description` (texto libre) no se rellena.
- `sensors/adsb.py`: aeronaves C8 con indicativos sintéticos `SIM…` (el sensor rechaza cualquier
  otro), posición con ruido (σ 10 m) y covarianza.
- Valores por defecto (ruido, alcances 3 km y 60 km, confianzas) **NO VERIFICADO**. Los componentes
  se pasan con `extra_components`; desde T1.15 `python -m sim run` los incluye vía `sim.replay`.

## Replay `.pb.zst` (T1.15, REQ-FUN-006, REQ-FUN-003)

- `atalaya_contracts.envelope_io`: magia `ATLYRPLY`, versión de formato (2 B, hoy 1), SHA-256 del
  contenido sin comprimir y una trama zstd de nivel 10 con suma de comprobación. Contenido:
  registros `tipo ‖ varint(longitud) ‖ mensaje` (1 = `Envelope`, 2 = `GroundTruth`), en orden.
- Lectura todo o nada: magia, versión, trama (truncada, corrupta o con datos sobrantes), hash y
  cada registro se comprueban antes de devolver nada; cualquier fallo es `ReplayFormatError` con el
  desplazamiento (en el fichero o en el contenido descomprimido).
- `sim/replay.py`: `record()` (escenario con latido, acústica, Remote ID y ADS-B), `write()`,
  `read()`/`decode()` y `stream_sha256()`. CLI: `python -m sim replay --in F.pb.zst` (exit 2 si el
  fichero no es válido). `--mqtt` existe desde T1.16 y sale con exit 3 (publicación cerrada hasta T1.7b).

## Salida MQTT (T1.16, sin publicación)

- `mqtt_out.py`: `topic_for()` (`atalaya/v1/<site>/<node>/{detection,node_status}`, solo sitios
  autorizados y segmentos `[a-z0-9-]`), `build_message()` (valida, redacta a `OPERATOR`, serializa
  de forma determinista; QoS 1) y `make_client()` (paho-mqtt, MQTT 5, sin conectar). Solo
  `Detection` y `NodeStatus` son publicables; `Evidence`, `Sighting` y el resto se rechazan.
- `MqttCredentials.from_env()`: `MQTT_SIM_USER`/`MQTT_SIM_PASSWORD` del entorno (`.env` de
  `make bootstrap`); sin valores por defecto; contraseña de ≥ 32 caracteres; nunca en `repr`.
- `MqttPublisher.publish()` **deniega siempre** (`PublicationDenied`) sin crear el transporte ni
  registrar el payload. No hay parámetro, variable de entorno ni método para abrir la puerta: la
  sustituye T1.7b con autenticación, ACL y autorización por rol y recurso.
- Broker: cuentas de administración, simulador e ingesta con ACL por topic y sitio
  (`infra/compose/mosquitto/acl.tmpl`).

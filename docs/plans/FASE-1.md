# Plan FASE 1 — Contratos de datos, SAPIENT, simulador y gemelo digital

Versión 3 · 2026-11-10 · Estado: **APROBADO por el usuario (P0), 2026-11-10**: «Si, continua». Decisiones D-1 a D-8 resueltas en esta versión.

## 1. Objetivo
Fijar los **contratos de datos** de Atalaya en Protobuf (`proto/atalaya/v1`), con la sensibilidad `PUBLIC` / `OPERATOR` / `FCSE_ONLY` declarada **en cada campo** y la incertidumbre obligatoria en toda estimación, y construir un **simulador reproducible por semilla** (gemelo digital) que produzca detecciones, estado de nodos, Remote ID y ADS-B realistas para los cuatro escenarios, con salida por MQTT y ficheros de replay `.pb.zst`. Sin hardware ni drones, el simulador es la base de verificación de las fases 8 a 10.

Para SAPIENT, los `.proto` oficiales de BSI Flex 335 v2.0 **son públicos** (Dstl, `github.com/dstl/SAPIENT-Proto-Files`, Apache-2.0). Hoy `third_party/sapient/` solo tiene un README, así que se **vendorizan sin modificar**, fijados a un commit exacto con el SHA-256 de cada fichero y su licencia, y los bindings se **generan** desde ellos: los mensajes SAPIENT **nunca** se escriben a mano. Encima se construye la versión inicial de `sapient-gateway` (puerto hexagonal, filtro de sensibilidad y mapeo básico), con tests de round-trip y de mapeo. El **harness oficial de Dstl solo funciona en Windows** con PostgreSQL 12: en el Mac Intel queda **bloqueado (B-07b) y NO VERIFICADO**.

## 2. Requisitos que cubre
MUST con Fase 1 en `REQUIREMENTS.md`:
- **Contratos:** REQ-FUN-002, REQ-FUN-062 (esquema), REQ-PRIV-001 (esquema), REQ-LEG-007.
- **Simulador y replay:** REQ-FUN-003, REQ-FUN-004, REQ-FUN-005, REQ-FUN-006.
- **Ingesta:** REQ-FUN-001.
- **SAPIENT:** REQ-FUN-054 (versión inicial: `.proto` vendorizados, bindings generados, round-trip y mapeo). Su criterio de aceptación es que **pase el harness**, que no se puede ejecutar en el Mac: queda como **B-07b** y ningún test lleva su marcador, para que la trazabilidad no lo dé por cumplido.
- **Transversales «0→»:** REQ-NFR-014, REQ-NFR-015, REQ-NFR-016, REQ-LEG-001, REQ-LEG-016, REQ-SEC-005, REQ-SEC-015, REQ-SEC-016, REQ-PRIV-003, REQ-PRIV-006.

Preparan (sin cerrarlos) REQ-FUN-031, REQ-FUN-036, REQ-FUN-048, REQ-FUN-061, REQ-NFR-005 y REQ-NFR-021: el simulador genera sus casos de prueba (Remote ID falsificado, PPS inválido, nodo caído, duplicados y desorden).

## 3. Hallazgos de la exploración (2026-11-08)

| Hallazgo | Efecto |
|---|---|
| **Hallazgo histórico (2026-11-08):** la FASE 0 estaba abierta y faltaba T0.13 | **Estado actual (2026-11-10):** FASE 0 cerrada por P6; commit de cierre `02fa431`, etiqueta `fase-0-cerrada`. Se conserva la fecha del hallazgo como evidencia histórica. Los ADR de esta fase empiezan en **0008** |
| `proto/atalaya/v1/` y `third_party/sapient/` solo tienen un README; `services/sapient-gateway` y `services/ingest`, también | Todo se crea desde cero |
| Guardarraíl `pilot-public` (`scripts/guardrails.py`): en `.proto`, `.json`, `.yaml` y `.yml`, **toda línea** con `pilot_*` u `operator_*` debe contener `\bFCSE_ONLY\b` | (1) El campo y su opción `[(atalaya.v1.sensitivity) = FCSE_ONLY]` van **en la misma línea**. (2) Los valores serán `PUBLIC`, `OPERATOR`, `FCSE_ONLY`; D-1 aprobó una excepción de `ENUM_VALUE_PREFIX` limitada a `options.proto`. (3) Ningún campo que no sea `FCSE_ONLY` se llamará `operator_*`; para el revisor SOC se usa `reviewer_*`. (4) YAML de escenario usa `launch_point`, no claves `pilot_*`/`operator_*` |
| Guardarraíl `offensive-term` en código (`.py`, `.proto`, `.yaml`, `.json`…): la lista blanca del ADR 0005 solo admite tres identificadores defensivos | El Remote ID falsificado se nombra `forged` en código (`is_forged`, `forged_remote_id`); no se añaden entradas a la lista blanca en esta fase |
| `.geojson` **no** está entre las extensiones que analiza el guardarraíl | La geometría de nodos se guarda como GeoJSON con extensión `.json` (`*.nodes.geo.json`), que sí se analiza. No hace falta tocar el guardarraíl |
| `scripts/check_spec.py` analiza solo SPEC, REQUIREMENTS, plan maestro de pruebas, RIESGOS y la entrevista | Este plan no entra en su análisis; aun así se ha redactado sin menciones sensibles nuevas |
| `scripts/traceability.py` toma la **primera** fase de la columna (REQ-FUN-054 → 1) y admite un MUST sin tests si su fila tiene **B** | Ningún test de esta fase lleva `@req("REQ-FUN-054")`: su criterio es el harness, y un round-trip en verde lo marcaría como cumplido sin estarlo |
| `traceability.py` lee **un solo** JUnit (`reports/junit.xml` de `make test`) | El test de integración MQTT de REQ-FUN-001 necesita el broker; si queda fuera de `make test`, el requisito sale como HUECO. Prohibido usar `skip` → T1.16 añade varios JUnit y decisión **D-5** |
| Herramientas: buf 1.75.0 instalado; **sin `protoc`** ni `mosquitto_pub`; uv 0.11.7; Docker 29.0.1; RAM 8 GB; disco **23 GB libres** | La generación de Python usa el `protoc` que trae el wheel `grpcio-tools` (sin Homebrew: la fórmula `protobuf` 36.2 de Homebrew no muestra bottle para Intel y habría que compilarla) |
| **buf y los worktrees:** la entrada `.git#branch=…` de `buf breaking` espera un directorio `.git`; en un worktree `.git` es un fichero (la documentación de entradas no menciona worktrees: NO VERIFICADO) | `buf breaking` contra un directorio extraído con `git archive` o contra una imagen `buf build -o base.binpb` (sintaxis documentada en buf.build/docs/reference/inputs) |
| buf v2 (`buf.build/docs/configuration/v2/buf-yaml`): `version: v2`, `modules[].path`, `lint.use/except/ignore_only`, `enum_zero_value_suffix` (por defecto `_UNSPECIFIED`); lint por defecto `STANDARD`, breaking por defecto `FILE` | Verificado en la documentación oficial |
| CI: el flujo `ci.yml` ya descarga buf 1.75.0 y comprueba su SHA-256 antes de `make check` | La integración de `buf lint` en `make lint` queda cubierta por el binario ya fijado; no se añade una acción ni otra dependencia de CI |
| **SAPIENT (verificado en la web, 2026-11-08, y confirmado por el coordinador):** Dstl publica en `github.com/dstl/SAPIENT-Proto-Files` un directorio `bsi_flex_335_v2_0/` con 16 `.proto` (`sapient_message`, `detection_report`, `status_report`, `registration`, `registration_ack`, `alert`, `alert_ack`, `task`, `task_ack`, `location`, `velocity`…), más `proto_options.proto` en la raíz, con licencia **Apache-2.0** (`LICENCE.txt`, «Crown owned Copyright 2023»). La página de gov.uk lo enlaza como definición legible por máquina del ICD. Apache-2.0 es compatible con un producto propietario si se conservan la licencia y los avisos | **SAPIENT no está bloqueado:** T1.8 los vendoriza. NO VERIFICADO: qué `.proto` importa cada uno (¿`proto_options.proto`?), si hay fichero `NOTICE` y si coinciden byte a byte con la descarga de BSI |
| **Hallazgo histórico (2026-11-08):** harness Dstl reportado como solo Windows, .NET 6 y PostgreSQL 12 | B-07b se registra en SPEC §9. La ejecución y conformidad permanecen NO VERIFICADAS en este entorno hasta intentar/verificar el procedimiento documentado; el bloqueo se retira solo con evidencia del harness oficial |
| Los `.proto` de SAPIENT incluyen `task.proto` (tareas para sensores y efectores, según el nombre del estándar; contenido NO VERIFICADO) | Riesgo legal: el gateway solo actuará como nodo de sensor y de fusión y **nunca** construirá tareas para efectores (R-34). Si `sapient_message.proto` importa `task.proto`, se generan sus bindings (no se puede generar un mensaje sin sus importaciones), pero un test impide usarlos |
| **Remote ID en la UE:** la norma armonizada es **EN 4709-002:2023** (Decisión de Ejecución (UE) 2024/2103, en apoyo del Reglamento Delegado (UE) 2019/945; verificado en EUR-Lex y AENOR). ASTM F3411 es la norma estadounidense y no aparece en el Reglamento 2019/945 (según el coordinador; no lo he comprobado en el texto del Reglamento) | La referencia legal del proyecto es EN 4709-002. El simulador genera observaciones de ambos formatos (campo `standard`), con EN 4709-002 por defecto |

**Versiones verificadas en PyPI el 2026-11-10 y fijadas en `uv.lock` en T1.1** (los wheels disponibles se comprobaron con `uv sync` en macOS x86_64):

| Paquete | Versión | Licencia | Wheel Mac Intel | Uso |
|---|---|---|---|---|
| `protobuf` | 7.36.2 (17-09-2026) | BSD-3-Clause | `abi3 universal2` | Ejecución |
| `grpcio-tools` (+ `grpcio`) | 1.85.1 (30-10-2026); `protoc` reporta 35.1 | Apache-2.0 | `cp312 macOS 11 universal2` | Desarrollo: `protoc` empaquetado |
| `types-protobuf` | 7.35.1.20260906 | Apache-2.0 | puro | Desarrollo (mypy) |
| `zstandard` | 0.25.0 (14-09-2025) | BSD-3-Clause | `cp312 x86_64` | Ejecución (`.pb.zst`; `compression.zstd` de la biblioteca estándar es de Python 3.14 y el proyecto usa 3.12) |
| `paho-mqtt` | 2.2.0 (04-11-2026) | EPL-2.0 OR BSD-3-Clause | puro | Ejecución (MQTT 5: `CallbackAPIVersion.VERSION2`, `MQTTv5`) |
| `jsonschema` (+ `rpds-py`, `referencing`, `attrs`) | 4.26.0; `rpds-py` 2026.9.1 | MIT | `rpds-py` `cp312 x86_64` | Ejecución (validación de escenarios) |
| `types-jsonschema` | 4.26.0.20261006 | Apache-2.0 | puro | Desarrollo (mypy) |
| `hypothesis` | 6.170.15 (ya en `uv.lock`) | MPL-2.0 | sí | Desarrollo |

No verificadas todavía en el código instalado (se comprueban en T1.1 o en su tarea antes de usarlas): `SerializeToString(deterministic=True)`, `FieldOptions.Extensions[...]` y `HasExtension` en protobuf 7.x; `--pyi_out` y la ruta de los `.proto` estándar dentro de `grpc_tools`; el ajuste `derandomize` de hypothesis.

## 4. Diseño propuesto (resumen para revisar en el STOP)

### 4.1 Contratos `atalaya.v1`
- `options.proto`: `enum Sensitivity` y dos opciones de campo `extend google.protobuf.FieldOptions { Sensitivity sensitivity = 50001; bool required = 50002; }` (rango 50000-99999 reservado para uso interno de cada organización según `descriptor.proto`).
- **Sensibilidad efectiva** de un campo anidado = la **más restrictiva** de su ruta (`Detection.remote_id.operator_location.lat` es `FCSE_ONLY` porque lo es `operator_location`). Los tipos comunes (`GeoPoint`, `PositionCovariance`…) declaran `PUBLIC` y es el campo contenedor el que restringe.
- `common.proto`: `GeoPoint`, `PositionCovariance` (ENU, m², 6 términos), `ErrorEllipse` (semiejes, orientación y nivel de confianza), `ClassScore` (clase y probabilidad), `TimeQuality` (PPS válido, desfase estimado e incertidumbre del reloj).
- Mensajes: `Detection` (con `oneof` de observación: acústica, Remote ID, ADS-B, presencia RF, humana), `Track`, `Prediction`, `Alert`, `NodeStatus`, `CoverageStatus`, `Sighting`, `Evidence`, `SignatureClass` (C1-C9) y `Envelope` (secuencia, tiempo y `oneof` con los nueve; es lo que viaja por MQTT y en los replays).
- Paquete aparte `atalaya.sim.v1`: `GroundTruth` (verdad del simulador: posición real, clase, `is_forged`, `launch_point` `FCSE_ONLY`). Nunca lo consume la plataforma, solo las métricas.
- Sin campos de país ni de actor en ningún mensaje automático (REQ-LEG-008 se diseña en la FASE 9 como mensaje aparte de analista).

**Propuesta inicial de sensibilidad** (la tabla completa campo a campo la genera un script en T1.3 y es el objeto del STOP):

| Campo | Propuesta | Motivo |
|---|---|---|
| `RemoteIdObservation.operator_id`, `operator_location`, `uas_id`, `self_id_description` | `FCSE_ONLY` | Identifican o sitúan al operador (REQ-LEG-007). `uas_id` y el texto libre: decisión D-6 |
| `Prediction.origin_heatmap` | `FCSE_ONLY` | Origen probable (REQ-LEG-007) |
| `GroundTruth.launch_point` | `FCSE_ONLY` | Equivale al origen |
| Posición, covarianza y clase de `Detection`, `Track` y `Prediction` | `OPERATOR` | Uso operativo |
| `Sighting.observer_position`, `Sighting.description`, actores de la cadena de custodia de `Evidence` | `OPERATOR` (propuesta) | Datos del vigilante; decisión D-6 |
| `NodeStatus`, `CoverageStatus` | `OPERATOR` | La ubicación de los nodos es sensible para la seguridad del emplazamiento |
| `SignatureClass` (catálogo C1-C9) | `PUBLIC` | Taxonomía sin datos personales |

**Incertidumbre obligatoria (REQ-FUN-062)**, marcada con `(atalaya.v1.required) = true` y comprobada por `atalaya_contracts.validate()`:
- `Detection`: `class_scores` (al menos uno, probabilidades en [0, 1] que suman ≤ 1), `detection_confidence`, `time_quality`; si lleva rumbo, su incertidumbre; si lleva posición, su covarianza o elipse.
- `Track`: `state_covariance` (simétrica y semidefinida positiva) y `class_probabilities` (suman 1 ± 1e-6).
- `Prediction`: covarianza en cada horizonte (5, 10 y 30 s) y `destination_probabilities` (suman 1 ± 1e-6).

### 4.2 Código Python
- Código generado (`*_pb2.py` y `*_pb2.pyi` con `--pyi_out`) en `proto/gen/python/`, **versionado** (el clon limpio no necesita generar) y con test de deriva (regenerar = lo versionado). Excluido de ruff; mypy usa los `.pyi`.
- Biblioteca `proto/python/atalaya_contracts/`: `sensitivity` (sensibilidad efectiva, campos sin declarar), `validate`, `redact(msg, clearance)` y `envelope_io` (flujo delimitado por longitud y comprimido con zstd).
- `pythonpath` de pytest y `mypy_path`: `proto/gen/python`, `proto/python`, `services/sapient-gateway` y la raíz.
- `redact` y `validate` pasan a `coverage_critical` y `mutation_critical` (control de acceso; umbrales del ADR 0006, que suben, no bajan).

### 4.3 Simulador (`sim/`, solo biblioteca estándar más protobuf, zstandard y paho-mqtt)
- Paquete `sim` con: `scenario` (YAML + JSON Schema), `geo` (WGS84 ↔ ENU local), `classes` (cinemática C1-C9 con fuente por clase), `trajectory`, `acoustics`, `sensors/` (acústico, Remote ID, ADS-B), `clock`, `network`, `faults`, `engine` (cola de eventos ordenada por `(tiempo, secuencia)`), `replay` y `mqtt_out`.
- **Reproducibilidad:** un `random.Random` por componente, con semilla derivada de `sha256(semilla_global, nombre_del_componente)`; nada de `hash()`, `set` sin ordenar, reloj del sistema ni `uuid4` (los identificadores salen de la semilla); serialización determinista. Las salidas físicas se redondean a una resolución fija antes de serializar, para no depender del último bit de `libm`.
- **Física simplificada y declarada como tal:** divergencia esférica (−20·log10(r/r0)); absorción atmosférica según la formulación de ISO 9613-1 (la norma es de pago: los coeficientes se toman de una fuente pública citada en el código y los valores de referencia del test se marcan NO VERIFICADO si no se pueden contrastar); velocidad del sonido según la temperatura; viento como corrección del nivel a favor o en contra y como ruido de fondo añadido; fondo por bandas por escenario. **El simulador no genera audio**: trabaja con niveles por banda, SNR y probabilidad de detección.
- **Remote ID:** observaciones en formato **EN 4709-002** (referencia legal en la UE, por defecto) o ASTM F3411 (campo `standard` de `RemoteIdObservation`), como mensajes ya recibidos y decodificados.
- **Remote ID falsificado:** se simula solo como **datos de entrada** que el sistema tendrá que señalar (posiciones con saltos imposibles o incoherentes con la acústica), dentro de mensajes Protobuf internos. El simulador no produce tramas de radio ni contiene código para hacerlo.
- **ADS-B:** aeronaves tripuladas (C8) con identificadores sintéticos (prefijo `SIM`), nunca matrículas reales.
- **Fallos:** nodo caído (deja de enviar `NodeStatus` cada 30 s), PPS inválido, deriva de reloj (ppm), latencia lognormal, pérdidas, duplicados y desorden.
- CLI: `uv run python -m sim run --scenario … --seed … --duration … --out ….pb.zst [--mqtt]`, `python -m sim replay --in … [--mqtt]` y `python -m sim hash …`.
- Topics MQTT 5: `atalaya/v1/<site>/<node>/detection` y `…/node_status`, QoS 1, carga `Envelope`.

### 4.4 Escenarios
`sim/scenarios/{prision_ceuta,puerto_ceuta,aerodromo,frontera_8km}.yaml` y su geometría en `*.nodes.geo.json`. El **centro se redondea a 0,01° (~1 km)** y la disposición de los nodos es **sintética** (no reproduce perímetros reales). Cada escenario incluye: entorno (temperatura, humedad, viento, fondo), nodos (acústico tipo Android sin PPS, nodo con PPS, receptor de Remote ID y ADS-B), objetivos del emplazamiento (para la FASE 9), amenazas (clase, ruta, comportamiento de Remote ID: ninguno, conforme o falsificado), aeronaves tripuladas y fallos programados. `frontera_8km` tiene dos emplazamientos para probar después el traspaso de pistas.

## 5. Tareas

Orden estricto. Cada tarea: TDD (primero el test que falla), verificación y prueba negativa registradas en `docs/evidence/FASE-1/registro-tareas.md` y un commit con los IDs de requisito. **Un FALLO bloquea la tarea siguiente.** Todos los tests llevan `@pytest.mark.req(...)`. `make check` debe seguir por debajo de ~60 s: lo pesado (escenarios completos, integración MQTT, mutación) va en objetivos aparte.

### T1.0 — Precondiciones y ADR de la fase
- **Qué:** comprobar que la FASE 0 está cerrada; registrar P0 y decisiones D-1 a D-8. ADR 0008 ya existe y no se reutiliza. Crear ADR 0009 (dependencias y generación: `grpcio-tools` como `protoc`, código generado versionado, módulos críticos), 0010 (sensibilidad efectiva y excepción de `ENUM_VALUE_PREFIX` en `options.proto`), 0011 (SAPIENT: fuentes oficiales Dstl fijadas por commit/hash, harness de conformidad bloqueado/no verificado, gateway solo como nodo de sensor/fusión y sin uso de tareas a efectores), 0012 (criterio de REQ-FUN-006 en esta fase) y 0013 (integración MQTT solo local, sin añadir consumo de CI). Incorporar B-07b a SPEC §9 sin presentar la conformidad como verificada.
- **Requisitos:** REQ-NFR-016, REQ-LEG-001, REQ-LEG-016
- **Verificación:** `test -n "$(git tag -l 'fase-0-cerrada')" && grep -qx '0' docs/requirements/FASES-CERRADAS.txt && make regress && uv run pytest tests/test_documentos.py -q`
- **Resultado esperado:** la etiqueta existe; `make regress` da «fase -1 OK» y «fase 0 OK»; los tests documentales validan los nuevos ADR (Estado, Contexto, Decisión, Consecuencias).
- **Prueba negativa:** en una copia sin la etiqueta `fase-0-cerrada`, `test -n "$(git tag -l 'fase-0-cerrada')"` falla y la precondición se detiene; en una copia, un ADR nuevo sin «Consecuencias» hace fallar el test de documentos.

### T1.1 — Dependencias y entorno
- **Qué:** añadir las versiones registradas en la tabla (§3) como runtime (`protobuf`, `zstandard`, `paho-mqtt`, `jsonschema`) y desarrollo (`grpcio-tools`, `types-protobuf`, `types-jsonschema`) en `pyproject.toml` y `uv.lock`. Confirmar instalación desde wheels para el Mac Intel y licencias. Registrar `libprotoc 35.1`. `make doctor` comprueba también `python -m grpc_tools.protoc --version`. Configurar `pythonpath` de pytest y `mypy_path` cuando se incorporen los bindings en T1.5.
- **Requisitos:** REQ-NFR-015, REQ-LEG-016, REQ-NFR-016
- **Verificación:** `uv sync --frozen && uv run --frozen python -m grpc_tools.protoc --version && uv run --frozen python -m scripts.license_check && make doctor && make check`
- **Resultado esperado:** todo con exit 0; `license_check` sin dependencias runtime con copyleft fuerte (paho-mqtt tiene opción BSD-3-Clause en su doble licencia); `libprotoc 35.1` y los hashes de los wheels quedan en lock/evidencia.
- **Prueba negativa:** el test de G-12 inyecta una dependencia runtime GPL y `license_check` la bloquea; `uv sync --frozen` con un `pyproject.toml` alterado y sin regenerar el lock falla.

### T1.2 — `buf`, opciones de sensibilidad y meta-test «todo campo declara sensibilidad»
- **Qué:** `buf.yaml` v2 en la raíz (`modules: [{path: proto}]`, lint `STANDARD`, breaking `FILE`), `proto/atalaya/v1/options.proto` y `common.proto`. Generar sus bindings iniciales para exponer las extensiones del descriptor. `atalaya_contracts.sensitivity.undeclared_fields(file_descriptors)` recorre los mensajes de `atalaya.v1` y `atalaya.sim.v1` presentes (incluidos anidados y campos de `oneof`) y devuelve rutas sin la opción o con `SENSITIVITY_UNSPECIFIED`. `buf lint` entra en `make lint`; el test de deriva para el conjunto completo se añade en T1.5.
- **Requisitos:** REQ-FUN-002, REQ-PRIV-001
- **Verificación:** `buf lint && uv run pytest tests/contracts/test_sensitivity_declared.py -v`
- **Resultado esperado:** `buf lint` sin avisos; los descriptores de los mensajes presentes en `common.proto` devuelven lista vacía; todo campo marcado `(required)=true` tiene presencia explícita en proto3.
- **Prueba negativa:** copiar el descriptor generado de `common.proto`, borrar la opción de un campo o asignarle `SENSITIVITY_UNSPECIFIED` → el test nombra la ruta completa y falla; un mensaje anidado sin opción también se detecta. En una copia temporal, un enum sin prefijo en otro `.proto` debe fallar `buf lint`, confirmando que la excepción se limita a `options.proto`.

### T1.3 — Los nueve mensajes, `Envelope`, `GroundTruth` y tabla de sensibilidad
- **Qué:** `detection.proto`, `track.proto`, `prediction.proto`, `alert.proto`, `node_status.proto`, `coverage_status.proto`, `sighting.proto`, `evidence.proto`, `signature_class.proto`, `envelope.proto` y `proto/atalaya/sim/v1/ground_truth.proto`. Lista **cerrada** de rutas que deben ser `FCSE_ONLY` (§4.1) en `scripts/contract_policy.py`. `scripts/sensitivity_table.py` genera `docs/contracts/SENSIBILIDAD.md` (mensaje, campo, tipo, sensibilidad declarada, sensibilidad efectiva y si es obligatorio) desde los descriptores.
- **Requisitos:** REQ-FUN-002, REQ-LEG-007, REQ-PRIV-001
- **Verificación:** `buf lint && uv run pytest tests/contracts -v && uv run python -m scripts.sensitivity_table --check && make guard`
- **Resultado esperado:** los 9 mensajes más `Envelope` y `GroundTruth` existen; 0 campos sin sensibilidad; todas las rutas de la lista cerrada con sensibilidad efectiva `FCSE_ONLY`; todo campo cuyo nombre empieza por `pilot_` u `operator_` es `FCSE_ONLY`; `--check` confirma que `SENSIBILIDAD.md` coincide con lo generado; `make guard` en verde.
- **Prueba negativa:** en una copia, bajar `operator_location` a `OPERATOR` → fallan el test de rutas `FCSE_ONLY` **y** el guardarraíl (`pilot-public`, exit 2); añadir un campo `operator_note` sin `FCSE_ONLY` → exit 2 de `scripts/guardrails.py --paths`; editar a mano `SENSIBILIDAD.md` → `--check` sale con 1.

### T1.4 — Incertidumbre obligatoria (REQ-FUN-062)
- **Qué:** `atalaya_contracts.validate(msg)` comprueba los campos `(required) = true` y las reglas semánticas del §4.1 (probabilidades, sumas, covarianza simétrica y semidefinida positiva, nivel de confianza de la elipse en (0, 1)). Devuelve la lista de errores con la ruta del campo.
- **Requisitos:** REQ-FUN-062
- **Verificación:** `uv run pytest tests/contracts/test_uncertainty.py -v`
- **Resultado esperado:** ≥ 15 tests en verde; un `Detection`, un `Track` y un `Prediction` completos validan sin errores; test de propiedades (`hypothesis`): toda covarianza construida como `A·Aᵀ` valida.
- **Prueba negativa:** `Detection` sin `class_scores`, `Track` sin `state_covariance`, `Prediction` sin covarianza en el horizonte de 10 s, probabilidades de destino que suman 0,9, covarianza con un autovalor negativo y rumbo sin incertidumbre → cada uno rechazado con su ruta exacta.

### T1.5 — Generación de código Python, deriva y round-trip
- **Qué:** `make proto` = `buf lint` + `python -m grpc_tools.protoc --python_out --pyi_out` sobre `proto/` → `proto/gen/python/`. Test de deriva: regenera en un directorio temporal y compara byte a byte con lo versionado. Round-trip con `hypothesis` de los 11 mensajes: `parse(serialize(m)) == m` y serialización determinista estable.
- **Requisitos:** REQ-FUN-002, REQ-NFR-014
- **Verificación:** `make proto && git diff --exit-code proto/gen && uv run pytest tests/contracts/test_codegen_drift.py tests/contracts/test_roundtrip.py -v && uv run mypy --strict scripts tests proto/python`
- **Resultado esperado:** sin diferencias en `proto/gen`; round-trip en verde con ≥ 200 ejemplos por mensaje; mypy estricto sin errores.
- **Prueba negativa:** cambiar un `.proto` sin regenerar → el test de deriva falla nombrando el fichero; un mensaje con un byte truncado → `DecodeError` (no se acepta en silencio).

### T1.6 — `buf breaking`
- **Qué:** `scripts/proto_breaking.sh [REF]` (por defecto `origin/main`; desde la FASE 2, la etiqueta `fase-1-cerrada`): extrae `buf.yaml` y `proto/` de `REF` con `git archive` a un directorio temporal y ejecuta `buf breaking proto --against <dir>`. Si `REF` no tiene `.proto`, lo dice («sin línea base») y sale con 0. `make proto-breaking` y paso en la CI con buf instalado por `bufbuild/buf-action` (fijada por SHA).
- **Requisitos:** REQ-FUN-002
- **Verificación:** `scripts/proto_breaking.sh "$(git log --diff-filter=A --format=%H -- proto/atalaya/v1/detection.proto | tail -1)"`
- **Resultado esperado:** exit 0 contra el primer commit de los contratos (solo hay cambios compatibles o ninguno).
- **Prueba negativa:** `tests/contracts/test_breaking.py` (requiere buf; está en el `doctor`) copia `proto/` a un temporal, cambia el número de `Detection.detection_id` y borra un campo de `Track` → `buf breaking` sale con ≠ 0 y nombra las dos reglas incumplidas; añadir un campo nuevo → exit 0.

### T1.7 — Filtro de sensibilidad `redact` y logs sin datos personales
- **Qué:** `redact(msg, clearance)` devuelve una copia sin ningún campo cuya sensibilidad efectiva supere `clearance` (recursivo, con `repeated`, `oneof` y mapas). Es la base de REQ-PRIV-001 para APIs, SAPIENT y logs. Logger JSON del simulador y de la ingesta que solo registra mensajes ya filtrados a `OPERATOR`.
- **Requisitos:** REQ-PRIV-001, REQ-LEG-007, REQ-PRIV-003
- **Verificación:** `uv run pytest tests/contracts/test_redact.py tests/sim/test_logs.py -v` y `make mutation FASE=1` (incluye `redact` y `validate`)
- **Resultado esperado:** test generativo (`hypothesis`) sobre los 11 mensajes con valores centinela únicos en cada campo `FCSE_ONLY`: con `clearance=OPERATOR` y `PUBLIC`, **cero** centinelas en los bytes serializados ni en los logs; con `FCSE_ONLY`, el mensaje queda intacto; mutación ≥ 80 % (ADR 0006); cobertura de ramas ≥ 90 %.
- **Prueba negativa:** una versión de `redact` que ignora los campos anidados (inyectada en el propio test) deja escapar el centinela de `operator_location` y el test lo detecta; `clearance=SENSITIVITY_UNSPECIFIED` → error (fallo cerrado), nunca «todo visible».

### T1.8 — SAPIENT: vendorizar los `.proto` oficiales y generar los bindings
- **Qué:**
  - Copiar **sin modificar** `bsi_flex_335_v2_0/*.proto` de `github.com/dstl/SAPIENT-Proto-Files` (y `proto_options.proto` si alguno lo importa) en `third_party/sapient/bsi_flex_335_v2_0/`, fijados a un **commit exacto**. La descarga se hace con `git clone` en un directorio vacío del scratchpad, sin ejecutar nada de su contenido.
  - Junto a ellos: `LICENCE.txt` original (y `NOTICE` si existe), `SHA256SUMS` (un hash por fichero) y `SOURCE.md` (URL, commit, fecha de descarga, licencia Apache-2.0, aviso «Crown owned Copyright 2023», versión BSI Flex 335 v2.0 y la advertencia de que no se ha comparado con la descarga de BSI).
  - Generación con el mismo `protoc` de T1.5 en `proto/gen/python/` (con su propio paquete, sin mezclarse con `atalaya.v1`) y test de deriva. Los `.proto` de terceros **no** pasan por `buf lint` (su estilo no es nuestro), pero sí por los guardarraíles: si alguno salta por contenido del estándar, **se para** y se propone un ADR (no se excluye `third_party/` en silencio).
  - Test «sin SAPIENT a mano»: falla si algún `.proto` fuera de `third_party/sapient/` declara el paquete de SAPIENT, o si algún `.py` fuera del código generado define clases o diccionarios con nombres de mensajes SAPIENT (`SapientMessage`, `DetectionReport`, `StatusReport`, `Registration`, `RegistrationAck`, `Task`, `TaskAck`…).
  - Revisión de los subagentes `sapient-conformance` y `legal-guardrail-reviewer` antes del commit.
- **Requisitos:** REQ-LEG-016 (licencia registrada), REQ-NFR-016 (preparan REQ-FUN-054, que no se marca)
- **Verificación:** `(cd third_party/sapient/bsi_flex_335_v2_0 && shasum -a 256 -c ../SHA256SUMS) && make proto && git diff --exit-code proto/gen && uv run pytest tests/sapient/test_vendor.py tests/sapient/test_no_handwritten.py -v && make guard`
- **Resultado esperado:** los hashes de los 16 ficheros (17 con `proto_options.proto`) coinciden con `SHA256SUMS` y con el commit de `SOURCE.md`; bindings generados sin diferencias; `make guard` en verde.
- **Prueba negativa:** alterar un byte de un `.proto` vendorizado → `shasum -c` falla y el test de vendorización también; un fixture temporal con un `.proto` que declara el paquete SAPIENT fuera de `third_party/` o un `.py` con `class DetectionReport` → el test «sin SAPIENT a mano» falla nombrando el fichero.

### T1.8b — `sapient-gateway` inicial: round-trip y mapeo básico
- **Qué:**
  - Paquete `sapient_gateway` en `services/sapient-gateway/`, hexagonal: puerto `SapientCodec` y adaptador que usa **solo** los bindings generados en T1.8.
  - Papel de **nodo de sensor (Edge Node) y de fusión**, solo en salida de información: registro, informe de estado (`NodeStatus` → `StatusReport`) e informe de detección (`Detection`/`Track` → `DetectionReport`), siempre **después** de `redact(…, OPERATOR)`.
  - Tabla de mapeo de campos en `docs/contracts/SAPIENT-MAPEO.md`, con los campos SAPIENT que no tienen equivalente y los de Atalaya que no salen. Los nombres de campo SAPIENT se confirman en los `.proto` vendorizados antes de escribir el mapeo (hoy NO VERIFICADOS). El mapeo completo de la taxonomía SAPIENT a C1-C9 es de la FASE 11.
  - Test legal: el gateway no construye ni envía mensajes de tarea (`task.proto`) ni nada dirigido a efectores; recibir una tarea → se rechaza y se registra.
  - Ningún test lleva `@req("REQ-FUN-054")`: su criterio es el harness (B-07b). La trazabilidad lo mostrará como **BLOQUEADO (B)**, y la evidencia dirá qué se ha probado (round-trip y mapeo) y qué no (harness).
- **Requisitos:** REQ-PRIV-001, REQ-LEG-001, REQ-LEG-007 (preparan REQ-FUN-054, que no se marca)
- **Verificación:** `uv run pytest tests/sapient -v && make trace`
- **Resultado esperado:** round-trip (`hypothesis`) de los mensajes SAPIENT que usa el gateway; mapeo `Detection` → `DetectionReport` → valores de vuelta con posición, tiempo y confianza dentro de la tolerancia documentada; `TRAZABILIDAD.md` con REQ-FUN-054 como «BLOQUEADO (B)», no «OK». **Harness de Dstl: NO VERIFICADO** (solo Windows con PostgreSQL 12).
- **Prueba negativa:** un `Track` con centinelas en todos sus campos `FCSE_ONLY` → ningún centinela en los bytes SAPIENT serializados; un `Detection` sin `class_scores` → el gateway lo rechaza antes de mapear; un mensaje de tarea entrante → rechazado y registrado, nunca ejecutado; un import de los tipos de tarea dentro de `sapient_gateway` (fixture) → el test legal falla.

### T1.9 — Esquema de escenario y los cuatro escenarios
- **Qué:** `sim/schemas/scenario.schema.json` (JSON Schema, `additionalProperties: false`), `sim/scenario.py` (carga y validación) y los cuatro escenarios con su GeoJSON (§4.4). Test de privacidad geográfica: ninguna coordenada de un escenario tiene más resolución que la permitida para el centro, y los nodos se definen como desplazamientos locales en metros.
- **Requisitos:** REQ-FUN-005
- **Verificación:** `uv run pytest tests/sim/test_scenarios.py -v && make guard`
- **Resultado esperado:** los 4 YAML y sus 4 GeoJSON validan; cada escenario tiene ≥ 1 amenaza de cada tipo de Remote ID (ninguno, conforme, falsificado) entre los cuatro, ≥ 1 aeronave ADS-B y ≥ 1 fallo programado; `make guard` en verde.
- **Prueba negativa:** YAML con una clave desconocida, con una clase `C10`, sin `seed_policy` o con un centro con 6 decimales → rechazado con la ruta del error; un YAML con la clave `pilot_lat` sin `FCSE_ONLY` → exit 2 del guardarraíl.

### T1.10 — Núcleo del simulador y reproducibilidad
- **Qué:** `sim/engine.py` (cola de eventos determinista), `sim/rng.py` (subsemillas por componente), `sim/geo.py` y `sim/clock.py`. CLI `python -m sim run|hash`.
- **Requisitos:** REQ-FUN-003
- **Verificación:** `uv run pytest tests/sim/test_determinism.py -v`
- **Resultado esperado:** el mismo escenario con la misma semilla, en dos procesos distintos y con `PYTHONHASHSEED` distinto, produce el mismo SHA-256 del flujo sin comprimir y del `.pb.zst`; `geo`: ida y vuelta WGS84 → ENU → WGS84 con error < 1 mm a 10 km (test de propiedades).
- **Prueba negativa:** semilla distinta → hash distinto; un componente que usa `random` global (inyectado en un test) rompe la igualdad entre procesos y el test lo detecta.

### T1.11 — Trayectorias C1-C7 (y C8 para ADS-B)
- **Qué:** `sim/classes.py` con, por clase, velocidad de crucero y máxima, aceleración y tasa de giro, **cada valor con su fuente o marcado NO VERIFICADO** (los rangos del MEGAPROMPT para C6/C7 son declarados, no medidos); `sim/trajectory.py` (rutas por puntos de paso, vuelo estacionario para multirrotores, giros coordinados).
- **Requisitos:** REQ-FUN-004
- **Verificación:** `uv run pytest tests/sim/test_trajectory.py -v`
- **Resultado esperado:** un test por clase; propiedades (`hypothesis`): la velocidad y la aceleración nunca superan el máximo de la clase; la trayectoria pasa por los puntos de paso con tolerancia; solo C1-C2 admiten vuelo estacionario.
- **Prueba negativa:** pedir una ruta imposible para la clase (C6 con giro de 90° en 1 s, C1 a 60 m/s) → `ValueError` con la clase y el límite; una clase sin fuente ni marca NO VERIFICADO → el test de catálogo falla.

### T1.12 — Propagación acústica y modelo de detección
- **Qué:** `sim/acoustics.py` (divergencia esférica, absorción por frecuencia, velocidad del sonido, viento, fondo por bandas) y `sim/sensors/acoustic.py` (SNR por banda → probabilidad de detección → `Detection` con `class_scores` a partir de una matriz de confusión configurable, siempre con su incertidumbre). Sin audio en ningún punto.
- **Requisitos:** REQ-FUN-004, REQ-FUN-062
- **Verificación:** `uv run pytest tests/sim/test_acoustics.py -v`
- **Resultado esperado:** test de propiedades exigido por REQ-FUN-004: **sin viento, el nivel recibido decrece estrictamente con la distancia**; −6,0 ± 0,1 dB por duplicación de distancia sin absorción; la absorción crece con la frecuencia en el rango de bandas usado; el viento a favor da más nivel que en contra a igual distancia; valores de absorción frente a una tabla de referencia citada (o NO VERIFICADO si no hay fuente pública contrastable); toda `Detection` generada pasa `validate()`.
- **Prueba negativa:** distancia ≤ 0, humedad fuera de [0, 100] % o frecuencia ≤ 0 → `ValueError`; un fondo de ruido mayor que la señal da probabilidad de detección por debajo del umbral configurado.

### T1.13 — Red, relojes y fallos de nodo
- **Qué:** `sim/network.py` (latencia lognormal, pérdidas, duplicados y desorden configurables), deriva de reloj en ppm y PPS válido o inválido en `sim/clock.py`, `sim/faults.py` (nodo caído, PPS perdido, enlace perdido) y `NodeStatus` cada 30 s de tiempo simulado.
- **Requisitos:** REQ-FUN-004
- **Verificación:** `uv run pytest tests/sim/test_network_faults.py -v`
- **Resultado esperado:** un test por fenómeno: tasa de pérdida empírica dentro del IC al 99 % de la configurada con 10.000 mensajes; desfase de reloj lineal con la deriva; un nodo caído deja de publicar `NodeStatus` desde el instante del fallo; un nodo sin PPS publica `pps_valid=false` y su `TimeQuality` lo refleja; con duplicados activados, cada duplicado conserva el mismo `detection_id`.
- **Prueba negativa:** probabilidad de pérdida > 1, latencia negativa o deriva no finita → rechazadas al cargar el escenario; con fallos desactivados, cero huecos en la secuencia de `NodeStatus`.

### T1.14 — Remote ID (también falsificado) y ADS-B
- **Qué:** `sim/sensors/remote_id.py`: los drones con Remote ID conforme generan observaciones con su posición (más ruido) y la ubicación del operador (`FCSE_ONLY`); los casos `forged` generan datos incoherentes (saltos imposibles, posición incompatible con la acústica), y solo `GroundTruth.is_forged` lo sabe. `sim/sensors/adsb.py`: aeronaves C8 con identificadores sintéticos.
- **Requisitos:** REQ-FUN-004, REQ-LEG-007, REQ-LEG-001
- **Verificación:** `uv run pytest tests/sim/test_remote_id_adsb.py -v && make guard`
- **Resultado esperado:** en los casos conformes, la posición declarada queda a < 30 m de la real (ruido configurado); en los `forged`, al menos un salto supera la velocidad máxima de la clase o la distancia a la posición real supera el umbral configurado; los campos de operador salen siempre marcados `FCSE_ONLY` y desaparecen con `redact(…, OPERATOR)`; ADS-B solo con identificadores `SIM…`.
- **Prueba negativa:** la `Detection` de un caso `forged` no contiene ningún campo que revele que es falsificado (el test busca `is_forged` y equivalentes en el mensaje serializado: cero); un test estático confirma que `sim/` no importa bibliotecas de radio, Wi-Fi ni Bluetooth.

### T1.15 — Replay `.pb.zst`
- **Qué:** `sim/replay.py` y `atalaya_contracts.envelope_io`: escritura y lectura de `Envelope` delimitados por longitud y comprimidos con zstd (nivel fijo), con cabecera de versión del formato y hash del contenido.
- **Requisitos:** REQ-FUN-006, REQ-FUN-003
- **Verificación:** `uv run pytest tests/sim/test_replay.py -v`
- **Resultado esperado:** propiedad (`hypothesis`): escribir y leer cualquier secuencia de `Envelope` devuelve la misma secuencia; el replay de un escenario reproduce los mismos `Envelope` y la misma verdad terreno, en el mismo orden.
- **Prueba negativa:** fichero truncado, un byte alterado o una versión de formato desconocida → error explícito con el desplazamiento del fallo, nunca una secuencia parcial en silencio.

### T1.16 — Salida MQTT, ingesta mínima y trazabilidad de la integración
- **Qué:** `sim/mqtt_out.py` (paho-mqtt, MQTT 5, QoS 1, credenciales de `.env` leídas por el propio script, como `scripts/smoke_compose.py`); `services/ingest`: se suscribe a `atalaya/v1/+/+/detection`, decodifica, valida (`validate`), elimina duplicados por `detection_id` y entrega a un puerto `DetectionSink` (adaptador en memoria; el de NATS llega en la FASE 9). Tests de integración con marcador `integracion`, **fuera** de `make check`, en `make integration` (necesita `make up`), con JUnit propio. `scripts/traceability.py` acepta varios JUnit (`--junit` repetible, con tests propios y mutación por ser código crítico). Según D-5, trabajo de CI con solo Mosquitto.
- **Requisitos:** REQ-FUN-001, REQ-SEC-005, REQ-PRIV-003
- **Verificación:** `make up && make integration && make trace`
- **Resultado esperado:** el simulador publica N = 1.000 detecciones (con un 5 % de duplicados y desorden activados) y la ingesta registra **exactamente 1.000** `detection_id` únicos, 0 pérdidas y 0 duplicados; `TRAZABILIDAD.md` muestra REQ-FUN-001 en verde con el JUnit de integración.
- **Prueba negativa:** una carga que no es un `Envelope` válido y una `Detection` sin `class_scores` → rechazadas y contadas en `rejected_total`, sin tumbar la ingesta; conexión con contraseña errónea → rechazada por Mosquitto; `traceability.py` con un JUnit de integración que tiene el test en rojo → HUECO y exit 1.

### T1.17 — Escenarios de extremo a extremo y equivalencia vivo/replay
- **Qué:** `make sim-scenarios`: los 4 escenarios con semilla fija durante 600 s simulados, dos veces cada uno; guarda los SHA-256 en `docs/evidence/FASE-1/sim-hashes.txt`. Equivalencia: la secuencia recibida por MQTT en directo es idéntica a la de reproducir el `.pb.zst` por MQTT. Mide el tiempo de cada ejecución en el Mac.
- **Requisitos:** REQ-FUN-005, REQ-FUN-006, REQ-FUN-003, REQ-NFR-015
- **Verificación:** `make sim-scenarios && make up && uv run pytest -m integracion tests/integration/test_live_vs_replay.py -v`
- **Resultado esperado:** 4 escenarios × 2 ejecuciones con hashes idénticos por pareja; secuencia de `Envelope` (y de pistas de verdad terreno) idéntica entre directo y replay; cada escenario en < 2 min en el Mac Intel (objetivo propuesto, NO VERIFICADO hasta medirlo).
- **Prueba negativa:** reproducir un replay con un `Envelope` borrado → la comparación falla e indica el primer número de secuencia distinto.

### T1.18 — Modelo de amenazas, DPIA, ENS y riesgos
- **Qué:** `docs/threat-model/v1.md` (STRIDE de MQTT, ingesta, replays y contratos: detecciones falsas, replays manipulados, fuga de campos `FCSE_ONLY`, Remote ID falsificado como entrada); `docs/dpia/v1.md` (la tabla de sensibilidad, datos solo sintéticos en esta fase, base para la retención de `FCSE_ONLY`); `docs/ens/v1.md`; `RIESGOS.md` con R-30 a R-35 (§6).
- **Requisitos:** REQ-SEC-015, REQ-SEC-016, REQ-PRIV-006
- **Verificación:** `uv run pytest tests/test_documentos.py -q && python3 -I scripts/check_spec.py`
- **Resultado esperado:** documentos con sus secciones obligatorias (las 6 categorías STRIDE; base jurídica por tratamiento); `check_spec` OK (las líneas sensibles nuevas de RIESGOS.md se proponen con `--propose` y las revisa el usuario; no se añaden solas).
- **Prueba negativa:** en una copia, quitar «Repudio» del STRIDE v1 → el test falla; una línea sensible nueva en RIESGOS.md sin revisar → `check_spec` sale con 1.

### T1.19 — Cierre de fase
- **Qué:** P2-P5: `make check`, `make integration`, `make sim-scenarios`, `make mutation FASE=1`, `make regress` (con `scripts/regress.d/fase1.sh` nuevo: lint de buf, deriva de código generado, round-trip, determinismo, sensibilidad, hashes de `third_party/sapient/`, `proto_breaking.sh fase-1-cerrada` a partir de la FASE 2), `scripts/verify_clean_clone.sh`; subagentes `independent-reviewer`, `test-auditor`, `security-reviewer`, `legal-guardrail-reviewer`, `privacy-reviewer` y `sapient-conformance`, sin contexto; `make evidence FASE=1` y `CIERRE.md`. El STOP presenta `docs/contracts/SENSIBILIDAD.md`.
- **Requisitos:** todos los de §2
- **Verificación:** los comandos de P2-P4, con su salida en el paquete, y `(cd docs/evidence/FASE-1 && shasum -a 256 -c MANIFEST.sha256)`
- **Resultado esperado:** todo en verde; `TRAZABILIDAD.md` sin huecos MUST de las fases -1, 0 y 1, salvo REQ-FUN-054 como BLOQUEADO (B); `make check` < 60 s.
- **Prueba negativa:** la de cada puerta; además, el revisor independiente intenta un commit con un campo `operator_*` sin `FCSE_ONLY` y debe bloquearse.

## 6. Riesgos de la fase

| ID | Riesgo | Mitigación |
|---|---|---|
| R-24 (actualizado) | Los `.proto` ya no faltan (Dstl, Apache-2.0), pero el harness solo funciona en Windows (B-07b, nuevo) y la copia de GitHub no se ha comparado con la descarga de BSI | Vendorización con commit y hashes (T1.8); conformidad con el harness NO VERIFICADA hasta tener Windows; REQ-FUN-054 sin marcador de test |
| R-30 (nuevo) | Determinismo frágil: `libm`, versiones de `zstandard` o `protobuf` y orden de iteración cambian el hash entre Mac y la CI (Linux) | Redondeo antes de serializar; versiones fijadas; la igualdad se exige en la misma plataforma y los hashes de referencia se guardan por plataforma |
| R-31 (nuevo) | Desaparecen los wheels para macOS x86_64 (como pasó con libcst 1.9) | Versiones fijadas en `uv.lock`; comprobación en `make doctor`; deuda técnica si hay que fijar por debajo |
| R-32 (nuevo) | El simulador da una falsa sensación de capacidad real | Física simplificada y declarada; cada parámetro con fuente o NO VERIFICADO; nada de cifras de alcance sacadas del simulador sin la campaña de la FASE 7 |
| R-33 (nuevo) | El guardarraíl de esquemas trabaja por línea: un formateador que parta las opciones o un `.geojson` sin analizar dejarían pasar un campo sensible | Opción en la misma línea, `.json` para GeoJSON y, como barrera real, los tests sobre descriptores (T1.2, T1.3, T1.7) |
| R-34 (nuevo) | Legal: el estándar SAPIENT incluye tareas para efectores | El gateway solo actúa como nodo de sensor y de fusión (ADR 0011) y un test impide referenciar tipos de tareas a efectores; revisión legal antes de vendorizar |
| R-35 (nuevo) | Integración MQTT: RAM (8 GB), tiempo de `make check` y minutos de CI | Integración fuera de `make check`; solo Mosquitto cuando basta; trabajo de CI opcional (D-5) |
| R-28 | Disco: 23 GB libres | Código generado pequeño; los replays de evidencia se limitan a los 4 escenarios de 600 s |

## 7. Decisiones que necesita el usuario

1. **P0 aprobado (2026-11-10):** FASE 0 cerrada; este plan aprobado para iniciar la FASE 1.
2. **D-2 SAPIENT aprobada:** copiar sin cambios la fuente oficial `dstl/SAPIENT-Proto-Files`, fijada por commit y hashes, conservando licencias/avisos. Generar tipos importados si son necesarios, pero el gateway no construye ni ejecuta tareas a efectores. El harness permanece bloqueado y NO VERIFICADO (B-07b).
3. **D-1 aprobada:** valores `PUBLIC`, `OPERATOR`, `FCSE_ONLY`; excepción de `ENUM_VALUE_PREFIX` únicamente en `options.proto`.
4. **D-4 aprobado:** replay idéntico significa la misma secuencia de eventos del simulador y de pistas de verdad terreno; la equivalencia con el tracker se verificará en FASE 9.
5. **D-5 aprobada:** pruebas de integración MQTT se ejecutan localmente y quedan en el paquete de evidencias; no se añaden minutos de CI en esta fase.
6. **D-6 aprobada:** `uas_id`, `self_id_description` y datos de operador Remote ID son `FCSE_ONLY`; posición y texto de avistamiento y actores de cadena de custodia se etiquetan `OPERATOR`, estos últimos solo con identificador seudónimo. La redacción de texto y límites de acceso se prueban antes de salida.
7. **D-7 aprobada:** se autorizan las dependencias propuestas por familia; versiones exactas solo se fijan tras verificar vigencia, licencia, mantenimiento y wheel para Mac Intel.
8. **D-8 aprobada:** escenarios con coordenadas totalmente ficticias, sin reproducir perímetros ni ubicaciones reales; la proyección/geometría se documentará.

## 8. Estimación
**3-4 semanas** de trabajo efectivo (21 tareas: T1.0 a T1.19 más T1.8b), dentro del rango de 2-4 semanas de SPEC §8. SAPIENT (T1.8 y T1.8b) supone unos 3-4 días de ese total. Coste: **0 €** (dependencias y `.proto` de licencia libre; Docker local; minutos de CI dentro de lo gratuito, NO VERIFICADO el consumo extra de D-5).

## 9. Fuentes consultadas (2026-11-08)
- buf: buf.build/docs/configuration/v2/buf-yaml, buf.build/docs/breaking/quickstart, buf.build/docs/reference/inputs; github.com/bufbuild/buf-action.
- PyPI (API JSON): protobuf, grpcio-tools, grpcio, types-protobuf, zstandard, paho-mqtt, jsonschema, rpds-py, hypothesis.
- SAPIENT: gov.uk/government/publications/sapient-interface-control-document; github.com/dstl/SAPIENT-Proto-Files (y su `LICENCE.txt`); github.com/dstl/BSI-Flex-335-v2-Test-Harness; github.com/dstl/SAPIENT-Middleware-and-Test-Harness (archivado el 29-08-2024).
- Remote ID en la UE: eur-lex.europa.eu/eli/dec_impl/2024/2103/oj (Decisión de Ejecución (UE) 2024/2103, norma armonizada EN 4709-002:2023); tienda.aenor.com (UNE-EN 4709-002:2023).

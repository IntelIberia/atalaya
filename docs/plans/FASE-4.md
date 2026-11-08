# Plan FASE 4 — Biblioteca de firmas y datos

Versión 1 · 2026-11-08 · Estado: **pendiente de aprobación (STOP de plan, puerta P0)**

## 1. Objetivo
Al cerrar la fase quedará demostrado, con evidencia ejecutable y a 0 €, que:
- cada fichero de datos del repositorio tiene **licencia, procedencia y hash** registrados, y que **nada no comercial, sin licencia verificada, de conflictos (OSINT) ni sensible de emplazamiento** puede entrar en un pipeline de producción ni subir a la nube (puerta G-13);
- existe una **biblioteca de firmas C1-C9** en `ml/signatures/` en la que cada entrada lleva fuente, licencia, distancia, condiciones, calidad y confianza, con los huecos declarados en lugar de rellenados;
- hay un **generador de síntesis física C6/C7** reproducible por semilla, cuya frecuencia fundamental coincide con RPM × palas / 60 y cuyas salidas llevan `synthetic=true`;
- existe **`evals/frozen/v1`**, congelado con SHA-256 y dividido por sesión y emplazamiento, con confusores;
- hay un **análisis de fugas** reproducible (duplicados exactos, huella acústica y mismo vuelo o sesión entre particiones);
- hay un **protocolo y una herramienta de grabación** (sesión autorizada, consentimiento, VAD de voz, metadatos e importación del registro de vuelo), probados sobre una sesión sintética;
- `docs/DATOS-HUECOS.md` dice qué falta, cómo se cubrirá y qué alianzas se proponen.

Base de la fase: `docs/data-cards/INVESTIGACION-LICENCIAS.md` (investigación del 2026-11-08).

## 2. Requisitos que cubre
- **MUST:** REQ-FUN-023, REQ-FUN-024, REQ-FUN-025, REQ-LEG-006, REQ-LEG-009, REQ-LEG-014, REQ-PRIV-009.
- **SHOULD:** REQ-FUN-026.
- **Transversales de todas las fases:** REQ-NFR-014 (reproducibilidad), REQ-NFR-016 (0 €), REQ-LEG-016 (licencias de dependencias), REQ-PRIV-006 (DPIA actualizada).
- **Prepara** REQ-NFR-020 (FASE 5): cada clase queda marcada con el origen de sus datos (real, equivalente, sintético o sin datos).

## 3. Hallazgos de la exploración (2026-11-08)

| Hallazgo | Efecto |
|---|---|
| **Al-Emadi prohíbe cualquier uso con fines de seguridad o defensa**, comercial o no, incluida la detección y el seguimiento de drones con esos fines | Excluido del proyecto, también para investigación. Nuevo riesgo R-33 |
| **DADS contiene Al-Emadi y no guarda la fuente de cada fichero**; además mezcla 5 fuentes NC y tiene un solo split | **DADS no se descarga** (decisión D2). Su análisis de fugas se sustituye por el análisis de los datasets que sí se ingieren y por pruebas con fugas sintéticas inyectadas. Las partes con licencia comercial se bajan de su fuente original |
| Hay datos con licencia comercial para C1 y confusores: Salford (CC BY 4.0), DroneAudioSet `drone-only` (MIT), Yi et al. (CC BY 4.0), Svanström (CC0-1.0), ESC-10 (CC BY) | Base de producción de la v1. Dominio sesgado (cámara anecoica, micrófonos a bordo, interiores): se documenta en las data cards (R-35) |
| **NASA sUAS Flyover: dos aviones RC de gasolina (pistón), tres multirrotores, RTK y meteorología**, pero **sin licencia declarada** | Fuente real de equivalentes de C6 y de prueba real de la importación del registro de vuelo. Entra como **solo investigación** hasta confirmación escrita de la NASA (D3) |
| **Disco: 24 GB libres** (`df -h /`), por debajo de los ~30 GB de la SPEC; RF (40-299 GB), Tegler (19 GB) y visión no caben | Presupuesto de datos de la fase: **≤ 8 GB** con subconjuntos y descarga secuencial con limpieza (§4, T4.6-T4.7). RF, visión y Tegler, solo registrados |
| Ninguna fase posterior a la -1 está cerrada (`FASES-CERRADAS.txt`); el enum `SignatureClass` de la FASE 1 aún no existe | La FASE 4 empieza tras cerrar la 0. Si la FASE 1 no ha cerrado, la taxonomía C1-C9 vive en `ml/signatures/taxonomy.py` con un test que la comparará con el `.proto` cuando exista |
| `docs/plans/` lo analiza `check_spec.py`; `.yaml`, `.json` y `.py` los analiza el guardarraíl de código; el audio solo puede ir a git en `tests/fixtures/sinteticos/` | Ningún audio real va a git: todo por DVC. Los tests generan audio sintético en `tmp_path` |
| `.claude/settings.json` deniega `Edit(/evals/frozen/**)` y `ml.md` prohíbe tocar `evals/frozen/` | La creación única de `evals/frozen/v1` la hace un script, con aprobación expresa del usuario (D6); después, un test garantiza la inmutabilidad |
| La CI de GitHub no tiene acceso al remoto local de DVC | Los tests de `make check` y de CI usan datos sintéticos. Las verificaciones con datos reales van en `make data-check` (local) y su salida se guarda en el paquete de evidencias |
| ADR libres a partir del **0009**; riesgos a partir del **R-33** | Numeración del plan |

### Distribución prevista de los datos (≤ 8 GB)

| Dataset | Licencia | Qué se guarda | Tamaño | Uso |
|---|---|---|---|---|
| DroneNoise Database (Salford) | CC BY 4.0 | Completo | 0,74 GB | C1, producción |
| Svanström et al. 2021 | CC0-1.0 | Completo (el vídeo se conserva para la FASE 9) | 0,31 GB | C1, C8 y fondo, producción |
| ESC-10 (dentro de ESC-50) | CC BY | Solo ESC-10, sin estornudo ni llanto; el resto de ESC-50 se borra tras extraerlo | ~0,15 GB | C8 (helicóptero) y C9, producción |
| DroneAudioSet `drone-only` | MIT | Subconjunto de ~1,5 GB (parquets elegidos por dron y acelerador, con semilla) | ~1,5 GB | C1, producción |
| Yi et al. (KAIST) | CC BY 4.0 | Un TAR (dron A), solo estado sin fallo | ~2,5 GB (temporal), ~1 GB final | C1, producción |
| NASA sUAS Flyover | No declarada | Completo | 1,69 GB | C1, C2 y equivalente de C6; **solo investigación** hasta D3 |
| **Total** | | | **≈ 5,4-6 GB** | |

## 4. Tareas

Orden estricto. Cada tarea: TDD (primero el test que falla), verificación y prueba negativa registradas en `docs/evidence/FASE-4/registro-tareas.md` y un commit con los IDs. **Un FALLO bloquea la tarea siguiente.** Todos los tests llevan `@pytest.mark.req(...)`. `make check` debe seguir por debajo de ~60 s: lo pesado va a `make data-check`.

### T4.1 — Decisiones de base y dependencias (ADR 0009 y 0010)
- **Qué:**
  - **ADR 0009 — Datos de terceros:** clases de licencia (`commercial_ok`, `research_only`, `excluded`, `unknown`), regla `production_allowed` (solo `commercial_ok` con licencia verificada), etiquetas `osint_conflict`, `site_sensitive`, `synthetic` y `personal_data`, exclusión de Al-Emadi y DADS, y política de `evals/frozen/v1` (D6).
  - **ADR 0010 — Dependencias de datos y audio:** DVC, numpy, scipy, soundfile, pyarrow, h5py y un VAD con licencia permisiva (candidatos: `webrtcvad-wheels`, MIT, o Silero VAD, MIT, con onnxruntime). Antes de fijarlas: comprobar que hay ruedas x86_64 para macOS (problema conocido con `libcst`) y la licencia con `scripts/license_check.py`. Todas en el grupo de desarrollo o de datos, nunca en un componente distribuido sin revisar.
  - Estructura: `ml/__init__.py`, `ml/datasets/`, `ml/signatures/`, `ml/recording/` como paquete importable; tests en `tests/ml/`.
- **Requisitos:** REQ-LEG-009, REQ-LEG-016, REQ-NFR-016
- **Verificación:** `uv sync --frozen && uv run python -m scripts.license_check && uv run pytest tests/test_documentos.py tests/ml/test_estructura_ml.py -v`
- **Resultado esperado:** ningún bloqueo de licencia; los ADR 0009 y 0010 con Estado, Contexto, Decisión y Consecuencias; el test de estructura encuentra los paquetes de `ml/`.
- **Prueba negativa:** en una copia, añadir una dependencia GPL al grupo de ejecución → `license_check` sale con 1 nombrándola; quitar «Consecuencias» del ADR 0009 → el test de documentos falla.

### T4.2 — DVC con remoto local (0 €) y medida de disco
- **Qué:** `dvc init`; `cache.type = reflink,hardlink,copy` (APFS admite reflink; **NO VERIFICADO** que DVC lo use en este Mac: se mide); remoto local en el directorio que decida el usuario (D5; por defecto `~/atalaya-dvc-remote`, fuera del repo). `make data-pull` y `make data-push`. `scripts/regress.d/fase4.sh`: si el remoto existe, `dvc pull` y verificación completa; si no (CI, clon limpio), verificación solo de los manifiestos y aviso **NO VERIFICADO** explícito.
- **Requisitos:** REQ-NFR-014, REQ-NFR-016
- **Verificación:** `uv run dvc doctor && uv run pytest tests/ml/test_dvc_setup.py -v && scripts/measure_dvc_disk.sh`
- **Resultado esperado:** DVC configurado con el remoto local; el script añade un fichero sintético de 500 MB y muestra el consumo real de disco del caché y del remoto (cifra registrada en la evidencia). Si el remoto duplica los datos en el mismo disco, se informa y se aplica D5.
- **Prueba negativa:** `git add` de un `.wav` en `ml/datasets/` → el guardarraíl lo bloquea (exit 2); `dvc push` con el remoto inexistente → error explícito, nunca éxito silencioso.

### T4.3 — Registro de licencias y puerta de producción (G-13)
- **Qué:**
  - `ml/datasets/registry.yaml`: una entrada por dataset de `INVESTIGACION-LICENCIAS.md` (incluidos los excluidos y los no ingeridos) con `id`, URL de la fuente, SPDX o texto, clase de licencia, `verified_at`, URL de evidencia, `production_allowed`, `osint_conflict`, `personal_data` y notas.
  - `ml/datasets/gate.py`: `assert_production_allowed(manifest)` rechaza cualquier fichero cuyo dataset no sea `commercial_ok` verificado, o que lleve `osint_conflict` o `synthetic` sin la marca de uso permitido; `assert_cloud_upload_allowed(manifest)` rechaza `site_sensitive` (REQ-PRIV-009) y todo lo no público.
  - CLI: `uv run python -m ml.datasets.gate --production <manifest>` y `--cloud <manifest>`.
- **Requisitos:** REQ-LEG-009, REQ-LEG-014, REQ-PRIV-009
- **Verificación:** `uv run pytest tests/ml/test_gate.py tests/ml/test_registry.py -v`
- **Resultado esperado:** ≥ 15 tests en verde; el registro valida contra su esquema y tiene las 28 entradas de la investigación (ESC-10 aparte de ESC-50); Al-Emadi y DADS figuran como `excluded`.
- **Prueba negativa:** manifiestos de prueba con (a) un fichero UrbanSound8K (NC), (b) uno NASA (`unknown`), (c) uno con `osint_conflict: true`, (d) uno `site_sensitive` hacia la nube y (e) un dataset que no está en el registro → todos rechazados con exit 1 y el motivo; un manifiesto solo con Salford → exit 0.

### T4.4 — Herramienta de intake y data cards
- **Qué:** `ml/datasets/intake.py` implementa la skill `dataset-intake`: descarga desde la URL del registro a un directorio nuevo y vacío, archiva `LICENSE-fuente.txt` (texto, URL y fecha), genera `MANIFEST.sha256` por fichero, registra versión y fecha de descarga, hace `dvc add`, lanza `scripts/pii_scan.py` sobre los metadatos de texto y crea la data card `docs/data-cards/<id>.md` desde una plantilla (licencia, procedencia, distribución de clases, sesiones y emplazamientos, datos personales, limitaciones y muestra revisada con semilla). Se niega a ingerir un dataset `excluded` o que no esté en el registro. Los ficheros descargados se tratan como no confiables (lectura con `python -I`, nada se ejecuta desde ellos).
- **Requisitos:** REQ-LEG-009, REQ-FUN-023
- **Verificación:** `uv run pytest tests/ml/test_intake.py tests/ml/test_data_cards.py -v`
- **Resultado esperado:** intake de un dataset sintético local (servido desde `tmp_path`) de punta a punta: manifiesto correcto, `.dvc` creado y data card con todas las secciones obligatorias.
- **Prueba negativa:** intake de `al-emadi` o `dads` → rechazado; un fichero alterado tras la descarga → el manifiesto no verifica; una data card sin la sección «Licencia» o «Limitaciones» → el test falla.

### T4.5 — Análisis de fugas
- **Qué:** `ml/datasets/leakage.py`:
  - **duplicados exactos:** SHA-256 del fichero y del PCM decodificado y normalizado (detecta el mismo audio en otro formato);
  - **casi duplicados por huella acústica:** huella propia de picos espectrales (sin dependencias GPL) más similitud coseno de un log-mel resumido, con umbral fijado con datos sintéticos;
  - **mismo vuelo o sesión:** continuidad entre el final de un clip y el inicio de otro, y agrupación por metadatos (`session_id`, `site_id`, fecha, nombre de fichero);
  - informe JSON y Markdown; exit 1 si hay fugas entre particiones.
- **Requisitos:** REQ-FUN-025, REQ-LEG-009
- **Verificación:** `uv run pytest tests/ml/test_leakage.py -v`
- **Resultado esperado:** sobre un corpus sintético con fugas inyectadas (copia exacta, recodificación, cambio de ganancia de 6 dB, recorte de 0,5 s y clips consecutivos de un mismo «vuelo» en particiones distintas): **recall de fugas = 100 %** en los casos inyectados y **0 falsos positivos** en 200 clips independientes; tiempo < 10 s.
- **Prueba negativa:** dos clips distintos con el mismo ruido de fondo pero distinto tono no se marcan como duplicados; una partición con un clip duplicado → exit 1 nombrando ambos ficheros.

### T4.6 — Intake del lote 1 (licencia comercial, pequeño)
- **Qué:** intake de **DroneNoise Database (Salford)**, **Svanström et al.** y **ESC-10** (desde ESC-50; se conserva el fichero `LICENSE` de atribución por clip, se excluyen estornudo y llanto y se borra el resto tras extraer). Data card de cada uno. Revisión manual de una muestra aleatoria de 20 clips por dataset (semilla registrada) para confirmar la etiqueta y la ausencia de voz.
- **Requisitos:** REQ-LEG-009, REQ-FUN-023
- **Verificación:** `make data-check DATASETS="salford-dronenoise svanstrom-2021 esc10"`
- **Resultado esperado:** los tres manifiestos verifican; la puerta de producción los acepta; la distribución de clases está en cada data card; el análisis de fugas entre los tres sale limpio o con las fugas documentadas; uso de disco ≤ 1,3 GB.
- **Prueba negativa:** la puerta rechaza ESC-50 completo (NC) si se intenta registrar; el intake falla si la licencia archivada no coincide con la del registro.

### T4.7 — Intake del lote 2 (subconjuntos) y de la NASA
- **Qué:** **DroneAudioSet `drone-only`** (subconjunto de ~1,5 GB elegido con semilla; nunca `drone-with-source` ni `source-only`, que tienen voz y material de terceros), **Yi et al.** (dron A, estado sin fallo; se borra el resto tras extraer) y, si el usuario aprueba D3, **NASA sUAS Flyover** como `research_only`, convirtiendo los `.mat` a WAV con la posición RTK alineada por UTC. Descarga **secuencial**: una por una, con `df` antes y después.
- **Requisitos:** REQ-LEG-009, REQ-FUN-023
- **Verificación:** `make data-check DATASETS="droneaudioset-droneonly yi-kaist-2023 nasa-suas-flyover"`
- **Resultado esperado:** manifiestos verificados; NASA marcada `production_allowed: false`; disco total de datos ≤ 8 GB y ≥ 12 GB libres al terminar; análisis de fugas entre todos los datasets ingeridos registrado.
- **Prueba negativa:** la puerta de producción rechaza cualquier fichero NASA; un intento de ingerir `drone-with-source` falla porque no está en el registro como permitido.

### T4.8 — Registro de los datasets no ingeridos
- **Qué:** data card corta para cada dataset que **no** se descarga en esta fase (DADS, Al-Emadi, UrbanSound8K, TUT 2017, DREGON, SPCup19, DNC, AUDROK, arXiv 2509.04715, Tegler, DroneRF, CardRF, CageDroneRF, RFUAV, Anti-UAV, Anti-UAV410, DUT Anti-UAV, CST Anti-UAV, MMAUD, DIAT-μSAT y SIPRI): licencia, motivo de no ingesta, fase en la que se reconsidera y qué falta (carta a autores, disco). Actualización de SPEC §7 y §11 y de RIESGOS (R-03 y R-33 a R-37) con lo verificado.
- **Requisitos:** REQ-LEG-009
- **Verificación:** `uv run pytest tests/ml/test_data_cards.py -v && python3 -I scripts/check_spec.py`
- **Resultado esperado:** una data card por cada entrada del registro (28); cada una enlaza la URL de la fuente y su fecha de verificación; check_spec en verde (las líneas sensibles nuevas se revisan a mano antes de añadirlas a la lista blanca).
- **Prueba negativa:** una entrada del registro sin data card, o una data card sin URL de fuente → el test falla.

### T4.9 — Esquema de la biblioteca de firmas
- **Qué:** `ml/signatures/schema.json` y `ml/signatures/validate.py`. Campos obligatorios de cada entrada: `id`, `class` (C1-C9), `model` y `model_confidence` (opcionales, juntos), `dataset_id`, `license_class`, `production_allowed`, `synthetic`, `osint_conflict`, `audio_sha256`, `session_id`, `site_id`, `distance_m` (número o `null` con `distance_reason` obligatorio: «desconocida», «estimada»…), `height_m`, `conditions` (viento, temperatura, humedad, entorno), `microphone`, `sample_rate_hz`, `quality` (SNR estimado y nota), `label_confidence`, `provenance_url` y `recorded_at`. No hay ningún campo de país ni de actor. C4 no admite entradas de audio propias (se infiere por fusión).
- **Requisitos:** REQ-FUN-023
- **Verificación:** `uv run pytest tests/ml/test_signature_schema.py -v`
- **Resultado esperado:** ≥ 12 tests en verde; una entrada completa valida.
- **Prueba negativa:** una entrada sin `license_class`, sin `distance_m` y sin `distance_reason`, con `class: C10`, con `model` sin confianza, con un campo `country` o una entrada de audio de clase C4 → rechazada con el campo culpable.

### T4.10 — Biblioteca de firmas C1-C9
- **Qué:** `ml/signatures/build.py` genera `ml/signatures/catalog.jsonl` (solo metadatos y hashes; el audio sigue en DVC) desde los datasets ingeridos, con características ligeras calculadas en el Mac (frecuencia fundamental y armónicos estimados, bandas de energía, SNR) y `ml/signatures/clases/C1.md` … `C9.md` con el resumen por clase y el origen de los datos (real, equivalente, sintético o **sin datos**). Mapeo previsto: C1 (Salford, DroneAudioSet, Yi, Svanström, NASA Phantom 2), C2 (NASA Hex Flyer, investigación), C3 y C5 (**sin datos con licencia**), C4 (solo fusión), C6 (equivalente NASA, investigación, y sintético), C7 (sintético), C8 (helicópteros de Svanström y ESC-10), C9 (fondos de Svanström y ESC-10).
- **Requisitos:** REQ-FUN-023
- **Verificación:** `make data-check STEP=signatures && uv run pytest tests/ml/test_catalog.py -v`
- **Resultado esperado:** el 100 % de las entradas pasa el validador de T4.9; las 9 clases tienen ficha y cada una declara su origen; los recuentos por clase se generan por script.
- **Prueba negativa:** un catálogo con una entrada cuyo `audio_sha256` no está en ningún manifiesto → el test falla; una ficha de clase sin la declaración de origen → falla.

### T4.11 — Generador de síntesis física C6/C7
- **Qué:** `ml/signatures/synth.py`, reproducible por semilla:
  - **C6 (pistón):** paso de pala = RPM × palas / 60 con armónicos y modulación; frecuencia de encendido del motor (RPM / 60 × cilindros / 2 en cuatro tiempos);
  - **C7 (reactor o turbina):** tonos ligados al régimen del eje más ruido de banda ancha;
  - **propagación:** divergencia esférica, absorción atmosférica según ISO 9613-1 (temperatura, humedad, presión), reflexión en el suelo y Doppler opcionales, y ruido de fondo;
  - parámetros genéricos por familia con rangos marcados **NO VERIFICADO** y su fuente; ningún modelo concreto;
  - metadatos `synthetic=true`, `generator_version` y `seed`. Si se aprueba D3, se compara la estructura armónica del sintético de pistón con los aviones de gasolina de la NASA (análisis, no métrica de detección).
- **Requisitos:** REQ-FUN-024
- **Verificación:** `uv run pytest tests/ml/test_synth.py -v`
- **Resultado esperado:** para RPM y palas en una rejilla con `hypothesis`, el pico fundamental medido por FFT coincide con RPM × palas / 60 con un error ≤ 1 % o ≤ 1 Hz; la atenuación a 1 km coincide con la fórmula ISO 9613-1 calculada de forma independiente con un error ≤ 0,5 dB; misma semilla ⇒ mismo hash; todas las salidas con `synthetic=true`.
- **Prueba negativa:** RPM ≤ 0 o palas < 1 → error; la puerta de producción rechaza el uso de sintéticos como métrica de detección real; una salida sin `synthetic=true` → el validador la rechaza.

### T4.12 — `evals/frozen/v1`
- **Qué:** `ml/eval/freeze.py` crea, una sola vez y con aprobación expresa (D6), `evals/frozen/v1/` con dos pistas separadas:
  - **`production/`:** solo ficheros `production_allowed`, por clase, con confusores (C8 y C9);
  - **`research/`:** NASA (equivalentes de C6) y sintéticos de C6/C7 marcados, que **nunca** se usan para afirmar rendimiento comercial.
  
  División **por sesión y emplazamiento** (nunca por clip), con semilla registrada; el análisis de fugas de T4.5 entre `evals/frozen/v1` y el resto de datos debe salir limpio. Audio en DVC; en git, `MANIFEST.sha256`, `FROZEN.lock` (hash del manifiesto) y `README.md` con la composición. «Confusores locales» de Ceuta: **no existen a 0 €** sin grabaciones; v1 usa sustitutos genéricos (olas, lluvia, motor) y lo declara. `scripts/check_frozen.py` recalcula los hashes antes de cualquier evaluación.
- **Requisitos:** REQ-FUN-025, REQ-LEG-009
- **Verificación:** `uv run python scripts/check_frozen.py evals/frozen/v1 && uv run pytest tests/ml/test_frozen.py -v`
- **Resultado esperado:** hashes coincidentes; cero fugas entre `v1` y los datos de entrenamiento; ninguna sesión aparece en dos particiones; recuento por clase en el README, con C3, C4 y C5 declaradas **sin datos**.
- **Prueba negativa:** en una copia temporal, cambiar un byte de un fichero de `v1` → `check_frozen.py` sale con 1 nombrándolo; un fichero NASA en `production/` → el test falla; volver a ejecutar `freeze.py` sobre `v1` existente → se niega.

### T4.13 — Protocolo de grabación propia y DPIA
- **Qué:** `docs/runbooks/protocolo-grabacion.md`: sesión autorizada y registrada (quién, dónde, cuándo y permiso del lugar), consentimiento informado de las personas presentes, **VAD de voz** obligatorio, metadatos (distancia, altura, viento, temperatura, humedad, micrófono, emplazamiento, clase y modelo), dron propio o prestado con registro de vuelo, divisiones por sesión y emplazamiento, retención y borrado. En Ceuta rige la zona LER12 (ADR 0008): grabaciones fuera o con autorización. Actualización de `docs/dpia/` con el tratamiento «grabación para entrenamiento» y su base jurídica.
- **Requisitos:** REQ-LEG-006, REQ-PRIV-006
- **Verificación:** `uv run pytest tests/test_documentos.py -v -k "protocolo or dpia"`
- **Resultado esperado:** el protocolo tiene las secciones obligatorias (autorización, consentimiento, VAD, metadatos, registro de vuelo, retención); la DPIA tiene el nuevo tratamiento con base jurídica.
- **Prueba negativa:** en una copia, quitar la sección de consentimiento → el test falla.

### T4.14 — Herramienta de grabación
- **Qué:** `ml/recording/`:
  - `session.py`: una grabación solo empieza con una sesión autorizada abierta (fichero firmado con hash, fechas de validez y emplazamiento) y un registro de consentimiento asociado; si no, error y nada se escribe;
  - `vad.py`: los segmentos con voz (más un margen) se eliminan **antes** de escribir nada; un segmento dudoso se elimina;
  - `flightlog.py`: importa formatos abiertos (CSV con columnas documentadas, GPX, PX4 ULog si se aprueba la dependencia y el formato NED-RTK de la NASA) y etiqueta cada ventana con la distancia 3D al micrófono por interpolación en UTC; los formatos propietarios cifrados no se leen;
  - metadatos obligatorios por grabación y etiqueta `site_sensitive` cuando el emplazamiento es de cliente.
  
  El audio de prueba lo genera el test: sesión sintética con dron simulado (trayectoria conocida, propagación de la FASE 1 o de T4.11) y voz sintética por formantes generada en `tmp_path`, sin voces reales.
- **Requisitos:** REQ-FUN-026, REQ-LEG-006, REQ-PRIV-009
- **Verificación:** `uv run pytest tests/ml/test_recording.py -v` y, si D3 está aprobada, `make data-check STEP=flightlog-nasa`
- **Resultado esperado:** en la sesión sintética, la distancia etiquetada coincide con la verdadera con un error ≤ 1 m (≤ 0,5 % a más de 200 m); ≥ 95 % de las ventanas con voz sintética eliminadas y 0 ventanas con voz escritas por encima del umbral; cada grabación con todos sus metadatos. Con la NASA: distancia RTK reproducida para un vuelo real.
- **Prueba negativa:** grabar sin sesión → error; con la sesión caducada o de otro emplazamiento → error; sin consentimiento → error; un registro de vuelo con saltos de tiempo o sin UTC → rechazado; un fichero `site_sensitive` → `gate --cloud` lo rechaza.

### T4.15 — `docs/DATOS-HUECOS.md` y alianzas
- **Qué:** por clase, qué falta (C3 y C5 sin datos con licencia; C2 escaso; C4 solo fusión; C6 y C7 sin datos reales públicos; fondos locales de 50-100 h por emplazamiento), cómo se cubrirá (equivalentes legales: avionetas y ultraligeros en aeródromos, aeromodelos de gasolina en clubes, motoparapentes; FPV propio o prestado; síntesis marcada) y qué alianzas se proponen: Zvook (arXiv 2608.14287 confirma un corpus de más de 300.000 clips), Sky Fortress y Brave1 vía Ministerio de Defensa o DIANA, INTA, Universidad de Lund (Tegler), Universidad de Salford, Universidad Militar de Tecnología de Varsovia (Sensors 2025), Fraunhofer IVI (AUDROK) y KAIST. Plantillas de carta a autores para las licencias pendientes (NASA, Lund, RFUAV, Fraunhofer, Anti-UAV, DUT y arXiv 2509.04715), que envía el usuario.
- **Requisitos:** REQ-FUN-023 (huecos de la biblioteca), REQ-NFR-016
- **Verificación:** `uv run pytest tests/test_documentos.py -v -k huecos && python3 -I scripts/check_spec.py`
- **Resultado esperado:** las 9 clases aparecen con su estado; cada alianza tiene vía de contacto y qué se pide; ninguna afirmación externa sin fuente o sin la marca NO VERIFICADO.
- **Prueba negativa:** en una copia, quitar una clase del documento → el test falla.

### T4.16 — Cierre de fase
- **Qué:** puertas P2-P5 (`make check`, `make regress`, `make data-check` completo, `scripts/verify_clean_clone.sh`); subagentes `independent-reviewer`, `test-auditor`, `ml-eval-reviewer`, `legal-guardrail-reviewer` y `privacy-reviewer`, sin contexto de la implementación; `make evidence FASE=4` y `CIERRE.md`. Revisión manual de las muestras de datos documentada con semilla.
- **Requisitos:** todos los de §2
- **Verificación:** `make check && make regress && make data-check && scripts/verify_clean_clone.sh && make evidence FASE=4 && (cd docs/evidence/FASE-4 && shasum -a 256 -c MANIFEST.sha256)`
- **Resultado esperado:** todo con exit 0; `TRAZABILIDAD.md` sin huecos MUST de la FASE 4; en el clon limpio sin remoto, la verificación de datos aparece como NO VERIFICADO explícito, nunca como OK.
- **Prueba negativa:** la ya incluida en cada puerta; además, borrar un fichero del caché DVC → `make data-check` falla nombrándolo.

## 5. Riesgos de la fase

| ID | Riesgo | Mitigación |
|---|---|---|
| R-03 (se materializa) | Licencias incompatibles: la mayoría de los datasets de audio de la tabla son NC, sin licencia o con conflicto | Registro y puerta G-13; base de producción solo con CC0, CC BY y MIT verificados; cartas a autores |
| R-33 (nuevo) | Licencias que prohíben usos de seguridad (Al-Emadi) y agregados que las arrastran sin poder filtrarlas (DADS y sus copias en Hugging Face) | Exclusión total; el intake rechaza agregados sin fuente por fichero; huella acústica para detectar clips de Al-Emadi que lleguen por otra vía |
| R-34 (nuevo) | Disco insuficiente (24 GB libres) para datos, caché DVC y remoto | Presupuesto ≤ 8 GB; descarga secuencial con limpieza; medida del reflink (T4.2); remoto en disco externo (D5) |
| R-35 (nuevo) | Sesgo de dominio de los datos comerciales (cámara anecoica, micrófonos a bordo, interiores, sin viento de Ceuta) | Data cards con limitaciones; fondos reales en cuanto haya sesiones autorizadas; la FASE 5 reporta por dominio |
| R-36 (nuevo) | Los sintéticos C6/C7 o los equivalentes se confunden con rendimiento real | `synthetic=true`; pista `research/` separada; REQ-NFR-020 en la FASE 5; la puerta rechaza sintéticos como métrica real |
| R-37 (nuevo) | El VAD no detecta toda la voz y quedan datos personales en una grabación | Umbral conservador y eliminación de lo dudoso; revisión manual de una muestra; DPIA; ninguna grabación real en esta fase sin D7 |
| R-17 | La IA da por buena una licencia que no lo es | Investigación con URL y fecha; revisión del usuario en el STOP; cartas a autores para todo lo dudoso |

## 6. Estimación
**3-5 semanas de trabajo efectivo** (16 tareas), en línea con la SPEC §8. Coste: **0 €**. Descargas: ≈ 6 GB (≈ 8 GB de pico con temporales). Las grabaciones propias no entran en la estimación: dependen de D7 y, para drones, del hito v1+. Las tareas más inciertas son T4.2 (comportamiento real de DVC con reflink), T4.5 (umbral de la huella acústica) y T4.14 (VAD sobre voz sintética frente a voz real).

## 7. Decisiones que necesita el usuario
1. **D1 — Aprobar este plan** (P0) y `INVESTIGACION-LICENCIAS.md`.
2. **D2 — Excluir Al-Emadi y DADS por completo** (recomendado), en lugar de pedir permiso a la autora (que, según su licencia, no cubriría usos de defensa). Consecuencia: el análisis de fugas del MEGAPROMPT sobre DADS se sustituye por el de los datasets ingeridos y fugas inyectadas.
3. **D3 — NASA sUAS Flyover:** ingerirla como **solo investigación** mientras se pide confirmación escrita de su licencia (recomendado), o no ingerirla.
4. **D4 — Enviar las cartas a autores** (NASA, Lund, RFUAV, Fraunhofer IVI, Anti-UAV, DUT y arXiv 2509.04715). Claude Code las redacta; las envía el usuario.
5. **D5 — Ubicación del remoto DVC:** disco externo (recomendado si lo hay) o directorio en el mismo disco tras medir el consumo real en T4.2.
6. **D6 — Autorizar la creación única de `evals/frozen/v1`** (ruta protegida) con dos pistas: `production/` (solo datos con licencia comercial) y `research/` (NASA y sintéticos, nunca para afirmaciones comerciales).
7. **D7 — Grabaciones de fondo con el Android:** no grabar nada real en esta fase (recomendado; la herramienta se prueba con sesiones sintéticas), o autorizar sesiones de fondo sin personas tras actualizar la DPIA.
8. **D8 — Dependencias nuevas** del ADR 0010 (DVC, numpy, scipy, soundfile, pyarrow, h5py y un VAD) tras comprobar sus licencias.
9. **D9 — SIPRI:** no usarlo en el producto sin licencia (recomendado); como mucho, una consulta manual puntual para priorizar clases, si el usuario la considera uso justo.

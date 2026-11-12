# Plan FASE 4 — Biblioteca de firmas y datos

Versión 2.1 · 2026-11-10 · Estado: **pendiente de aprobación (STOP de plan, puerta P0)**

## 1. Objetivo
Al cerrar la fase quedará demostrado, con evidencia ejecutable y a 0 €, que:
- cada fichero de datos del repositorio tiene **licencia, procedencia y hash** registrados, y que **nada no comercial, sin licencia verificada, de conflictos (OSINT) ni sensible de emplazamiento** puede entrar en un pipeline de producción ni subir a la nube (puerta G-13);
- existe una **biblioteca de firmas C1-C9** en `ml/signatures/` en la que cada entrada lleva fuente, licencia, distancia, condiciones, calidad y confianza, con los huecos declarados en lugar de rellenados;
- hay un **generador de síntesis física C6/C7** reproducible por semilla, cuya frecuencia fundamental coincide con RPM × palas / 60 y cuyas salidas llevan `synthetic=true`;
- existe **`evals/frozen/v1`**, congelado con SHA-256 y dividido por sesión y emplazamiento, con confusores;
- hay un **análisis de fugas** reproducible (duplicados exactos, huella acústica y mismo vuelo o sesión entre particiones);
- hay un **protocolo y una herramienta de grabación** (sesión autorizada, consentimiento, VAD de voz, metadatos e importación del registro de vuelo), probados sobre una sesión sintética;
- `docs/DATOS-HUECOS.md` dice qué falta, cómo se cubrirá y qué alianzas se proponen.

Base documental: `docs/data-cards/INVESTIGACION-LICENCIAS.md`, investigación histórica del 2026-11-08. Sus estados de licencia, tamaños y disponibilidad son **NO VERIFICADOS a fecha de este plan** y no autorizan descarga, ingesta ni uso. La licencia aplicable de cada fuente se volverá a comprobar y archivar desde la fuente original antes de cualquier intake (T4.4); hasta entonces `production_allowed: false`.

## 2. Requisitos que cubre
- **MUST:** REQ-FUN-023, REQ-FUN-024, REQ-FUN-025, REQ-LEG-006, REQ-LEG-009, REQ-LEG-014, REQ-PRIV-009.
- **SHOULD:** REQ-FUN-026.
- **Transversales de todas las fases:** REQ-NFR-014 (reproducibilidad), REQ-NFR-016 (0 €), REQ-LEG-016 (licencias de dependencias), REQ-PRIV-006 (DPIA actualizada).
- **Prepara** REQ-NFR-020 (FASE 5): cada clase queda marcada con el origen de sus datos (real, equivalente, sintético o sin datos).

## 3. Hallazgos de la exploración (2026-11-08)

| Hallazgo | Efecto |
|---|---|
| La investigación de 2026-11-08 registra restricciones de Al-Emadi para usos de seguridad o defensa; DADS contiene Al-Emadi y no guarda la fuente de cada fichero | Se aplica la decisión vigente del propietario: ambos quedan **bloqueados por licencia y sin ingesta**; se pueden citar resultados publicados y siguen previstas cartas a autores. Sin permiso escrito, el estado no cambia. Nuevo riesgo provisional R-55 |
| La investigación del 2026-11-08 reportó candidatos con licencias comerciales para C1 y confusores: Salford, DroneAudioSet `drone-only`, Yi et al., Svanström y ESC-10 | Solo candidatos para revalidación; no habilitan producción hasta completar el intake. El dominio observado es sesgado (cámara anecoica, micrófonos a bordo, interiores) y se documentará en data cards (R-57) |
| La investigación del 2026-11-08 registró que NASA sUAS Flyover no declara licencia y contiene aviones RC de pistón, multirrotores, RTK y meteorología | Solo podría servir como investigación y equivalente de C6 si se aprueba D3 y se verifican y archivan sus términos/licencia y cualquier permiso escrito exigible; la investigación histórica no autoriza su ingesta |
| Medición histórica del 2026-11-08: 24 GB libres (`df -h /`); RF, Tegler y visión exceden el presupuesto de esa medición | El límite de ≤ 8 GB es provisional. Volver a medir disco antes de cualquier adquisición; RF, visión y Tegler solo se registran en esta fase |
| `docs/plans/` lo analiza `check_spec.py`; `.yaml`, `.json` y `.py` los analiza el guardarraíl de código; el audio solo puede ir a git en `tests/fixtures/sinteticos/` | Ningún audio real va a git: todo por DVC. Los tests generan audio sintético en `tmp_path` |
| `evals/frozen/` es una ruta protegida | La creación única de `evals/frozen/v1` requiere aprobación expresa pendiente (D6); después, un test garantiza la inmutabilidad. No se crea ni modifica el conjunto antes de esa aprobación |
| La CI de GitHub no tiene acceso al remoto local de DVC | Los tests de `make check` y de CI usan datos sintéticos. Las verificaciones con datos reales van en `make data-check` (local) y su salida se guarda en el paquete de evidencias |
| El registro actual contiene ADR hasta 0013; T1.8 de FASE 1 tiene una propuesta de ADR 0014 pendiente de STOP/decisión del usuario y FASE 2 revisará la numeración al resolverla. Los riesgos de FASE 1–3 tienen rangos provisionales | Los números de ADR de FASE 4 quedan pendientes: al iniciar T4.1 se revisarán `docs/adr/` y las reservas aprobadas, y se asignarán dos números libres consecutivos tras resolver las propuestas pendientes. No asumir que 0014 o 0015 están reservados. Los IDs de riesgos de FASE 4 se proponen como R-55–R-59 y se cotejan con el registro global y los rangos de FASE 1–3 antes del cierre. |

### 3.1 Estado y dependencias con las FASES 0–3 (2026-11-10)

- **FASE 0:** cerrada por P6 el 2026-11-10; `fase-0-cerrada` figura en el registro de fases cerradas.
- **FASE 1:** P0 aprobado para la versión 3 el 2026-11-10; T1.0–T1.6 constan como OK en el registro de tareas, pero la fase sigue abierta y no aparece cerrada en `docs/requirements/FASES-CERRADAS.txt`. El contrato actual define `SignatureClassCode` C1–C9 en `proto/atalaya/v1/signature_class.proto` en la raíz del proyecto. T4.9–T4.10 deben alinearse con ese contrato; no crear una taxonomía paralela. T4.14 puede usar la propagación del simulador de FASE 1 o la de T4.11.
- **FASES 2 y 3:** sus planes están en worktrees separados y siguen pendientes de P0; ninguna figura cerrada. La FASE 2 no es una dependencia técnica directa de la biblioteca de firmas. La FASE 3 consume la taxonomía/contratos de FASE 1 y prevé usar `dataset-intake` para fuentes reales; coordinar su política de licencias y la actualización compartida de la DPIA (REQ-PRIV-006), sin considerar verificada una fuente por aparecer en otro plan.
- **Puertas de ejecución:** este plan sigue pendiente de su propio P0 (D1). Además, por la secuencia del proyecto, la implementación de FASE 4 espera el P6 y cierre de todas las fases anteriores (FASES 0–3), con sus etiquetas y registros de cierre, aunque una tarea no tenga dependencia técnica directa. P0 de FASE 4 no sustituye esos P6. Mientras las fases anteriores terminan, en paralelo solo se permite revisar este plan, sus dependencias y las decisiones de P0; no se adelantan los entregables documentales de las tareas de FASE 4. No se ejecuta código, `dvc init`, pruebas técnicas, instalaciones ni descargas/intake de datos. Los artefactos protegidos, la congelación de evaluación y cualquier grabación conservan además sus puertas específicas.

### Distribución prevista de los datos (≤ 8 GB; estimación histórica, sujeta a revalidación y decisiones pendientes)

| Dataset | Licencia | Qué se guarda | Tamaño | Uso |
|---|---|---|---|---|
| DroneNoise Database (Salford) | CC BY 4.0 (según investigación histórica) | Completo | 0,74 GB (estimación histórica) | C1, candidato a producción tras revalidación e intake |
| Svanström et al. 2021 | CC0-1.0 (según investigación histórica) | Completo (el vídeo se conserva para la FASE 9) | 0,31 GB (estimación histórica) | C1, C8 y fondo, candidato a producción tras revalidación e intake |
| ESC-10 (dentro de ESC-50) | CC BY (según investigación histórica) | Solo ESC-10, sin estornudo ni llanto; el resto de ESC-50 se borra tras extraerlo | ~0,15 GB (estimación histórica) | C8 (helicóptero) y C9, candidato a producción tras revalidación e intake |
| DroneAudioSet `drone-only` | MIT (según investigación histórica) | Subconjunto de ~1,5 GB (parquets elegidos por dron y acelerador, con semilla) | ~1,5 GB (estimación histórica) | C1, candidato a producción tras revalidación e intake |
| Yi et al. (KAIST) | CC BY 4.0 (según investigación histórica) | Un TAR (dron A), solo estado sin fallo | ~2,5 GB temporal / ~1 GB final (estimación histórica) | C1, candidato a producción tras revalidación e intake |
| NASA sUAS Flyover | No declarada según investigación histórica | Completo | 1,69 GB (estimación histórica) | C1, C2 y equivalente de C6; solo investigación si se aprueba D3 y se verifican/archivan los términos y cualquier permiso escrito exigible |
| **Total estimado** | | | **≈ 5,4-6 GB si se aprueba y admite NASA; menor si D3 se rechaza o no se verifican sus términos** | |

## 4. Tareas

Orden estricto. Cada tarea: TDD (primero el test que falla), verificación y prueba negativa registradas en `docs/evidence/FASE-4/registro-tareas.md` y un commit con los IDs. **Un FALLO bloquea la tarea siguiente.** Todos los tests llevan `@pytest.mark.req(...)`. `make check` debe seguir por debajo de ~60 s: lo pesado va a `make data-check`.

### T4.1 — Decisiones de base y dependencias (dos ADR; numeración pendiente)
- **Qué:**
  - **ADR — Datos de terceros:** clases de licencia (`commercial_ok`, `research_only`, `excluded`, `unknown`), regla `production_allowed` (solo `commercial_ok` con licencia verificada), etiquetas `osint_conflict`, `site_sensitive`, `synthetic` y `personal_data`, y estado de ingesta separado. Para DADS y Al-Emadi se registra `blocked_by_license`/sin ingesta conforme a la decisión vigente; un permiso escrito no cambia automáticamente el estado hasta completar el intake. También fija la política de `evals/frozen/v1` (D6).
  - **ADR — Dependencias de datos y audio:** DVC, numpy, scipy, soundfile, pyarrow, h5py y un VAD con licencia permisiva (candidatos: `webrtcvad-wheels`, MIT, o Silero VAD, MIT, con onnxruntime). Antes de fijarlas: comprobar que hay ruedas x86_64 para macOS (problema conocido con `libcst`) y la licencia con `scripts/license_check.py`. Todas en el grupo de desarrollo o de datos, nunca en un componente distribuido sin revisar. Los dos números se asignan consecutivamente al ejecutar T4.1, tras consultar el registro real y las reservas de ADR de fases anteriores; no se fijan en este borrador.
  - Estructura: `ml/__init__.py`, `ml/datasets/`, `ml/signatures/`, `ml/recording/` como paquete importable; tests en `tests/ml/`.
- **Requisitos:** REQ-LEG-009, REQ-LEG-016, REQ-NFR-016
- **Verificación:** `uv sync --frozen && uv run python -m scripts.license_check && uv run pytest tests/test_documentos.py tests/ml/test_estructura_ml.py -v`
- **Resultado esperado:** ningún bloqueo de licencia; los dos ADR con Estado, Contexto, Decisión y Consecuencias y números consecutivos libres; el test de estructura encuentra los paquetes de `ml/`.
- **Prueba negativa:** en una copia, añadir una dependencia GPL al grupo de ejecución → `license_check` sale con 1 nombrándola; quitar «Consecuencias» del primer ADR de T4.1 → el test de documentos falla.

### T4.2 — DVC con remoto local (0 €) y medida de disco
- **Qué:** `dvc init`; `cache.type = reflink,hardlink,copy` (APFS admite reflink; **NO VERIFICADO** que DVC lo use en este Mac: se mide); remoto local en el directorio que decida el usuario (D5; por defecto `~/atalaya-dvc-remote`, fuera del repo). `make data-pull` y `make data-push`. `scripts/regress.d/fase4.sh`: si el remoto existe, `dvc pull` y verificación completa; si no (CI, clon limpio), verificación solo de los manifiestos y aviso **NO VERIFICADO** explícito.
- **Requisitos:** REQ-NFR-014, REQ-NFR-016
- **Verificación:** `uv run dvc doctor && uv run pytest tests/ml/test_dvc_setup.py -v && scripts/measure_dvc_disk.sh`
- **Resultado esperado:** DVC configurado con el remoto local; el script añade un fichero sintético de 500 MB y muestra el consumo real de disco del caché y del remoto (cifra registrada en la evidencia). Si el remoto duplica los datos en el mismo disco, se informa y se aplica D5.
- **Prueba negativa:** `git add` de un `.wav` en `ml/datasets/` → el guardarraíl lo bloquea (exit 2); `dvc push` con el remoto inexistente → error explícito, nunca éxito silencioso.

### T4.3 — Registro de licencias y puerta de producción (G-13)
- **Qué:**
  - `ml/datasets/registry.yaml`: una entrada por dataset de `INVESTIGACION-LICENCIAS.md` (incluidos los bloqueados y no ingeridos) con `id`, URL de la fuente, SPDX o texto, clase de licencia, estado de ingesta, `verified_at`, URL de evidencia, `production_allowed`, `osint_conflict`, `personal_data` y notas. La investigación del 2026-11-08 se conserva como antecedente histórico; `verified_at` solo se rellena tras comprobar y archivar la fuente original en esta fase.
  - `ml/datasets/gate.py`: `assert_production_allowed(manifest)` rechaza cualquier fichero cuyo dataset no sea `commercial_ok` verificado, o que lleve `osint_conflict` o `synthetic` sin la marca de uso permitido; `assert_cloud_upload_allowed(manifest)` rechaza `site_sensitive` (REQ-PRIV-009) y todo lo no público.
  - CLI: `uv run python -m ml.datasets.gate --production <manifest>` y `--cloud <manifest>`.
- **Requisitos:** REQ-LEG-009, REQ-LEG-014, REQ-PRIV-009
- **Verificación:** `uv run pytest tests/ml/test_gate.py tests/ml/test_registry.py -v`
- **Resultado esperado:** ≥ 15 tests en verde; el registro valida contra su esquema y tiene las 28 entradas de la investigación (ESC-10 aparte de ESC-50); DADS y Al-Emadi figuran `blocked_by_license`, sin ingesta y con `production_allowed: false`. Se pueden citar resultados publicados y preparar cartas a autores; sin permiso escrito no cambia su estado.
- **Prueba negativa:** manifiestos de prueba con (a) un fichero UrbanSound8K (NC), (b) uno NASA (`unknown`), (c) uno con `osint_conflict: true`, (d) uno `site_sensitive` hacia la nube y (e) un dataset que no está en el registro → todos rechazados con exit 1 y el motivo; un manifiesto solo con Salford → exit 0.

### T4.4 — Herramienta de intake y data cards
- **Qué:** `ml/datasets/intake.py` implementa la skill `dataset-intake`: descarga desde la URL del registro a un directorio nuevo y vacío, archiva `LICENSE-fuente.txt` (texto, URL y fecha), genera `MANIFEST.sha256` por fichero, registra versión y fecha de descarga, hace `dvc add`, lanza `scripts/pii_scan.py` sobre los metadatos de texto y crea la data card `docs/data-cards/<id>.md` desde una plantilla (licencia, procedencia, distribución de clases, sesiones y emplazamientos, datos personales, limitaciones y muestra revisada con semilla). Se niega a ingerir un dataset no autorizado para intake, `blocked_by_license`, `excluded` o que no esté en el registro. Los ficheros descargados se tratan como no confiables (lectura con `python -I`, nada se ejecuta desde ellos).
- **Requisitos:** REQ-LEG-009, REQ-FUN-023
- **Verificación:** `uv run pytest tests/ml/test_intake.py tests/ml/test_data_cards.py -v`
- **Resultado esperado:** intake de un dataset sintético local (servido desde `tmp_path`) de punta a punta: manifiesto correcto, `.dvc` creado y data card con todas las secciones obligatorias.
- **Prueba negativa:** intake de `al-emadi` o `dads` → rechazado mientras su estado sea `blocked_by_license`; un fichero alterado tras la descarga → el manifiesto no verifica; una data card sin la sección «Licencia» o «Limitaciones» → el test falla.

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
- **Qué:** **DroneAudioSet `drone-only`** (subconjunto de ~1,5 GB elegido con semilla; nunca `drone-with-source` ni `source-only`, que tienen voz y material de terceros) y **Yi et al.** (dron A, estado sin fallo; se borra el resto tras extraer). Añadir **NASA sUAS Flyover** como `research_only` solo si el usuario aprueba D3 y, antes de descargar o ingerirla, se verifican y archivan sus términos/licencia y cualquier permiso escrito exigible; si no se cumplen esas condiciones, se omite. Al incorporarla, convertir los `.mat` a WAV con la posición RTK alineada por UTC. Descarga **secuencial**: una por una, con `df` antes y después.
- **Requisitos:** REQ-LEG-009, REQ-FUN-023
- **Verificación:** `make data-check DATASETS="droneaudioset-droneonly yi-kaist-2023"`; añadir `nasa-suas-flyover` solo si D3 está aprobada y sus términos/permiso están verificados y archivados.
- **Resultado esperado:** manifiestos verificados; si se ingiere NASA bajo esas condiciones, marcada `production_allowed: false`; disco total de datos ≤ 8 GB y ≥ 12 GB libres al terminar; análisis de fugas entre todos los datasets ingeridos registrado.
- **Prueba negativa:** la puerta de producción rechaza cualquier fichero NASA; un intento de ingerir `drone-with-source` falla porque no está en el registro como permitido.

### T4.8 — Registro de los datasets no ingeridos
- **Qué:** data card corta para cada dataset que **no** se descarga en esta fase (DADS, Al-Emadi, UrbanSound8K, TUT 2017, DREGON, SPCup19, DNC, AUDROK, arXiv 2509.04715, Tegler, DroneRF, CardRF, CageDroneRF, RFUAV, Anti-UAV, Anti-UAV410, DUT Anti-UAV, CST Anti-UAV, MMAUD, DIAT-μSAT y SIPRI): licencia, motivo de no ingesta, fase en la que se reconsidera y qué falta (carta a autores, disco). Actualización de SPEC §7 y §11 y de RIESGOS (R-03 y R-55 a R-59) con lo verificado.
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
- **Qué:** `ml/signatures/build.py` genera `ml/signatures/catalog.jsonl` (solo metadatos y hashes; el audio sigue en DVC) desde los datasets ingeridos, con características ligeras calculadas en el Mac (frecuencia fundamental y armónicos estimados, bandas de energía, SNR) y `ml/signatures/clases/C1.md` … `C9.md` con el resumen por clase y el origen de los datos (real, equivalente, sintético o **sin datos**). Mapeo previsto: C1 (Salford, DroneAudioSet, Yi, Svanström y, solo si D3 y las condiciones de T4.7 se cumplen, NASA Phantom 2), C2 (NASA Hex Flyer, investigación y solo bajo las mismas condiciones), C3 y C5 (**sin datos con licencia**), C4 (solo fusión), C6 (equivalente NASA solo bajo esas condiciones, y sintético), C7 (sintético), C8 (helicópteros de Svanström y ESC-10), C9 (fondos de Svanström y ESC-10).
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
  - metadatos `synthetic=true`, `generator_version` y `seed`. Solo si D3 está aprobada y se han verificado/archivado los términos y permisos exigibles, se compara la estructura armónica del sintético de pistón con los aviones de gasolina de la NASA (análisis, no métrica de detección).
- **Requisitos:** REQ-FUN-024
- **Verificación:** `uv run pytest tests/ml/test_synth.py -v`
- **Resultado esperado:** para RPM y palas en una rejilla con `hypothesis`, el pico fundamental medido por FFT coincide con RPM × palas / 60 con un error ≤ 1 % o ≤ 1 Hz; la atenuación a 1 km coincide con la fórmula ISO 9613-1 calculada de forma independiente con un error ≤ 0,5 dB; misma semilla ⇒ mismo hash; todas las salidas con `synthetic=true`.
- **Prueba negativa:** RPM ≤ 0 o palas < 1 → error; la puerta de producción rechaza el uso de sintéticos como métrica de detección real; una salida sin `synthetic=true` → el validador la rechaza.

### T4.12 — `evals/frozen/v1` *(D6 pendiente; no crear antes de aprobación expresa)*
- **Qué:** cuando D6 se apruebe, `ml/eval/freeze.py` crea una sola vez `evals/frozen/v1/` con dos pistas separadas:
  - **`production/`:** solo ficheros `production_allowed`, por clase, con confusores (C8 y C9);
  - **`research/`:** sintéticos de C6/C7 marcados y, solo si D3 fue aprobada y los términos/licencia y cualquier permiso escrito exigible fueron verificados y archivados antes del intake, NASA como equivalente de C6. Si NASA no supera esas condiciones, no se descarga ni se incluye. Esta pista **nunca** se usa para afirmar rendimiento comercial.
  
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
  - `flightlog.py`: importa formatos abiertos (CSV con columnas documentadas, GPX, PX4 ULog si se aprueba la dependencia y el formato NED-RTK de la NASA); solo procesa datos NASA si D3 y las condiciones de verificación/permiso de T4.7 se cumplen. Etiqueta cada ventana con la distancia 3D al micrófono por interpolación en UTC; los formatos propietarios cifrados no se leen;
  - metadatos obligatorios por grabación y etiqueta `site_sensitive` cuando el emplazamiento es de cliente.
  
  El audio de prueba lo genera el test: sesión sintética con dron simulado (trayectoria conocida, propagación de la FASE 1 o de T4.11) y voz sintética por formantes generada en `tmp_path`, sin voces reales.
- **Requisitos:** REQ-FUN-026, REQ-LEG-006, REQ-PRIV-009
- **Verificación:** `uv run pytest tests/ml/test_recording.py -v`; ejecutar `make data-check STEP=flightlog-nasa` solo si D3 está aprobada y se han verificado/archivado los términos y permisos exigibles.
- **Resultado esperado:** en la sesión sintética, la distancia etiquetada coincide con la verdadera con un error ≤ 1 m (≤ 0,5 % a más de 200 m); ≥ 95 % de las ventanas con voz sintética eliminadas y 0 ventanas con voz escritas por encima del umbral; cada grabación con todos sus metadatos. Si NASA cumple las condiciones de intake, su distancia RTK se reproduce para un vuelo real.
- **Prueba negativa:** grabar sin sesión → error; con la sesión caducada o de otro emplazamiento → error; sin consentimiento → error; un registro de vuelo con saltos de tiempo o sin UTC → rechazado; un fichero `site_sensitive` → `gate --cloud` lo rechaza.

### T4.15 — `docs/DATOS-HUECOS.md` y alianzas
- **Qué:** por clase, qué falta (C3 y C5 sin datos con licencia; C2 escaso; C4 solo fusión; C6 y C7 sin datos reales públicos; fondos locales de 50-100 h por emplazamiento), cómo se cubrirá (equivalentes legales: avionetas y ultraligeros en aeródromos, aeromodelos de gasolina en clubes, motoparapentes; FPV propio o prestado; síntesis marcada) y qué alianzas se proponen: Zvook (arXiv 2608.14287 confirma un corpus de más de 300.000 clips), Sky Fortress y Brave1 vía Ministerio de Defensa o DIANA, INTA, Universidad de Lund (Tegler), Universidad de Salford, Universidad Militar de Tecnología de Varsovia (Sensors 2025), Fraunhofer IVI (AUDROK) y KAIST. Mantener las cartas a los autores de DADS y Al-Emadi previstas por la decisión vigente; preparar además plantillas para licencias pendientes (NASA, Lund, RFUAV, Fraunhofer, Anti-UAV, DUT y arXiv 2509.04715). El usuario decide y envía las cartas.
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
| R-55 (provisional) | Restricciones de licencia de Al-Emadi y falta de procedencia por fichero en DADS y sus copias | Estado `blocked_by_license`, no ingesta ni producción sin permiso escrito; citar resultados publicados y mantener las cartas a autores. El intake bloquea ambos mientras no cambie el estado; la detección de contaminación se limita a fuentes con procedencia verificable |
| R-56 (provisional) | Disco insuficiente (24 GB libres) para datos, caché DVC y remoto | Presupuesto ≤ 8 GB; descarga secuencial con limpieza; medida del reflink (T4.2); remoto en disco externo (D5) |
| R-57 (provisional) | Sesgo de dominio de los datos comerciales (cámara anecoica, micrófonos a bordo, interiores, sin viento de Ceuta) | Data cards con limitaciones; fondos reales en cuanto haya sesiones autorizadas; la FASE 5 reporta por dominio |
| R-58 (provisional) | Los sintéticos C6/C7 o los equivalentes se confunden con rendimiento real | `synthetic=true`; pista `research/` separada; REQ-NFR-020 en la FASE 5; la puerta rechaza sintéticos como métrica real |
| R-59 (provisional) | El VAD no detecta toda la voz y quedan datos personales en una grabación | Umbral conservador y eliminación de lo dudoso; revisión manual de una muestra; DPIA; ninguna grabación real en esta fase sin D7 |
| R-17 | La IA da por buena una licencia que no lo es | Investigación con URL y fecha; revisión del usuario en el STOP; cartas a autores para todo lo dudoso |

Los IDs R-55–R-59 son provisionales. No colisionan con los IDs actuales del registro global (R-01–R-33) ni con los rangos planificados para FASE 1 (R-34–R-39), FASE 2 (R-40–R-46) y FASE 3 (R-47–R-54). Se validarán otra vez su unicidad y su incorporación al registro global antes del cierre de FASE 4; este borrador no modifica dicho registro.

## 6. Estimación
**3-5 semanas de trabajo efectivo** (16 tareas), en línea con la SPEC §8. Coste: **0 €**. Descargas: hasta ≈ 6 GB (≈ 8 GB de pico con temporales) si se aprueba e ingiere NASA; menos si D3 se rechaza o no se verifican sus términos. Las grabaciones propias no entran en la estimación: dependen de D7 y, para drones, del hito v1+. Las tareas más inciertas son T4.2 (comportamiento real de DVC con reflink), T4.5 (umbral de la huella acústica) y T4.14 (VAD sobre voz sintética frente a voz real).

## 7. Decisiones que necesita el usuario
1. **D1 — Aprobar este plan (P0) — PENDIENTE.** `INVESTIGACION-LICENCIAS.md` es un antecedente histórico, no una verificación vigente ni una autorización de uso.
2. **D2 — Aplicar la decisión ya registrada en `DECISIONES-USUARIO.md`.** No se aprueba la exclusión total: DADS y Al-Emadi quedan registrados como `blocked_by_license`, sin descarga ni ingesta; se pueden citar resultados publicados y siguen previstas cartas a autores. Sin permiso escrito, su estado no cambia. Si llega permiso, se reevalúa por `dataset-intake`; no implica autorización automática de ingesta o producción.
3. **D3 — NASA sUAS Flyover: PENDIENTE.** Autorizar su ingesta como solo investigación únicamente después de verificar y archivar sus términos/licencia y cualquier permiso escrito exigible, o no ingerirla. No descargarla mientras esos requisitos estén pendientes; la investigación histórica no cuenta como permiso.
4. **D4 — Cartas a autores: PENDIENTE.** Se mantienen las cartas a los autores de DADS y Al-Emadi previstas por la decisión vigente, además de las cartas de licencia propuestas para NASA, Lund, RFUAV, Fraunhofer IVI, Anti-UAV, DUT y arXiv 2509.04715. El usuario decide y las envía; no se enviará ninguna carta desde esta fase.
5. **D5 — Ubicación del remoto DVC: PENDIENTE.** Disco externo o directorio en el mismo disco, sujeto a medir consumo y espacio disponible en T4.2.
6. **D6 — Autorizar la creación única de `evals/frozen/v1`: PENDIENTE.** Ruta protegida con dos pistas: `production/` (solo datos con licencia comercial verificada) y `research/` (sintéticos y NASA solo si D3 se aprueba y sus términos/licencia y cualquier permiso escrito exigible están verificados y archivados; nunca para afirmaciones comerciales). Si NASA no cumple esas condiciones, `research/` contiene solo sintéticos. No crear ni modificar el conjunto antes de la aprobación expresa.
7. **D7 — Grabaciones de fondo con el Android: PENDIENTE.** Recomendación: no grabar datos reales en esta fase y probar la herramienta con sesiones sintéticas; cualquier autorización requiere actualizar la DPIA.
8. **D8 — Dependencias nuevas: PENDIENTE.** DVC, numpy, scipy, soundfile, pyarrow, h5py y un VAD, después de comprobar licencias y disponibilidad de ruedas Mac Intel.
9. **D9 — SIPRI: PENDIENTE.** No usarlo en el producto sin licencia. El posible uso manual puntual para priorizar clases queda sin decidir; no ingerir ni incorporar datos de SIPRI mientras tanto.

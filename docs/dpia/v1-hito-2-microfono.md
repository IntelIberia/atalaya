# Evaluación de impacto (DPIA) v1 — Hito 2: micrófono del Mac en una vivienda

Fecha: 2026-11-16 · Versión: 1 (borrador) · Estado: **pendiente de aprobación del usuario**.
Tarea: H2.P4 del plan `docs/plans/HITO-2.md` (condición P4 de la revisión legal y de privacidad del
ADR 0017). Amplía la DPIA v0 (`docs/dpia/v0.md`) con el tratamiento T-07 de su registro de
actividades. Requisitos: REQ-PRIV-006, REQ-PRIV-007, REQ-LEG-005, REQ-PRIV-002, REQ-PRIV-003,
REQ-PRIV-010. REQ-LEG-006 (grabación en sesión autorizada) no aplica: en este tratamiento no hay
grabación ni modo de grabación (`test_no_recording_mode_exists`).

> **Esto no es asesoramiento jurídico.** Lo ha redactado Claude Code como borrador técnico. El
> proyecto no tiene asesoría (riesgo R-12, bloqueo B-01 de `docs/SPEC.md`): la revisión por un
> profesional del RGPD es **recomendable** antes de dar por buena la valoración de la base jurídica
> y de la excepción doméstica. Lo que no está comprobado con un test o un comando se marca
> **NO VERIFICADO**.

**Bloqueo vigente.** Mientras este documento no esté aprobado por el usuario, y mientras sigan
pendientes H2.P3 (punto de entrada de sesión) y H2.P5 (puesta a cero de la ventana con voz), **no
se abre el micrófono real** (ADR 0017, sección «Revisión legal y de privacidad»).

## 1. Descripción del tratamiento

| Elemento | Descripción |
|---|---|
| Responsable | El usuario, persona física, en su vivienda en España. Proyecto propio, sin clientes, una sola persona (R-16) |
| Encargados | Ninguno. No interviene ningún servicio externo: el sonido no sale del Mac (ni a Colab, ni a la nube, ni a la red) |
| Medio | Micrófono integrado del Mac Intel del usuario (macOS 15.8.3), proceso Python del piloto `pilots/acoustic/` (subpaquete `live`), aislado del producto (H2-R11) |
| Qué se capta | Sonido ambiente de la habitación donde está el Mac durante una sesión de prueba |
| Flujo | Captura de entrada (`sounddevice.InputStream`, solo entrada) → remuestreo a 16 kHz → búfer circular en memoria de 64 000 muestras (4 s, 256 kB) → ventanas de 0,96 s con salto de 0,48 s → YAMNet (ONNX en CPU) → **puerta de voz** (diseño; H2.9 y H2.P5 pendientes de implementar, §7): si la puntuación de voz es ≥ 0,30, la ventana se descarta antes del clasificador y su región del búfer y su copia se ponen a cero → regresión logística → probabilidad de dron → lógica de alerta |
| Qué sale del proceso | Solo escalares hacia una página local en `127.0.0.1` (estado, probabilidad con 2 decimales, hora, latencia, contadores). Las ventanas con voz no muestran puntuación |
| Qué se guarda | Ninguna muestra, embedding ni espectro. **Opcional** (solo con `--export`, decisión D-5): un resumen JSON de la sesión en `docs/evidence/hito-2/` con, por ventana **sin voz**, hora relativa, probabilidad, estado y etiqueta del operador; las ventanas VOZ solo como recuento agregado por sesión y tipo de tramo; por sesión, latencias y contadores (§6) |
| Duración | Sesiones que el usuario inicia y para a mano (decisión D-9). La sesión de medida de H2.14 dura unas 2 h; el resto, pruebas cortas |
| Frecuencia | Puntual, durante el hito 2. No es una escucha continua ni permanente |

## 2. Finalidad
Prueba técnica del detector acústico: comprobar si distingue el sonido de drones, reproducido por
un altavoz a partir de vídeos, del ruido normal de la casa, y medir sus falsas alarmas. No hay otra
finalidad: no se identifica a personas, no se escuchan conversaciones, no se reconoce a hablantes,
no se vigila la vivienda y nada se usa para entrenar modelos (ADR 0017; los vídeos reproducidos
nunca entran en entrenamiento, REQ-LEG-009).

## 3. Categorías de interesados y de datos

| Interesados | Cómo pueden verse afectados | Probabilidad de presencia |
|---|---|---|
| El usuario (responsable) | Su voz y los sonidos de su actividad en la habitación | Segura |
| Convivientes | Su voz, si hablan cerca del Mac durante la sesión | Media (depende de la franja horaria) |
| Visitas | Igual que los convivientes | Baja (no se hacen sesiones con visitas, §9) |
| Personal del hogar (limpieza, cuidados, reparaciones) | Igual que los convivientes, con una relación de dependencia frente al usuario | Baja (nunca sesiones con personal del hogar presente, §9) |
| Vecinos | Voces que atraviesan paredes o patios | Baja; nivel bajo y poco inteligible con el micrófono de un portátil (NO VERIFICADO) |
| Transeúntes | Voces de la calle por una ventana abierta | Baja; ventanas cerradas durante la sesión (§9) |

Datos: la **voz** de una persona identificable puede ser dato personal (RGPD art. 4.1), y también
lo que se dice. Por prudencia se trata como dato personal aunque solo exista unas décimas de
segundo en memoria: la captación, la consulta y la supresión ya son «tratamiento» (art. 4.2).
**No hay categorías especiales** (art. 9): la voz no se procesa para identificar a nadie (no hay
reconocimiento de hablante; YAMNet solo da la probabilidad de la clase «voz»). Que el contenido de
una conversación pudiera revelar datos de salud, ideología u otros datos sensibles es el motivo de
la puerta de voz y del descarte inmediato.

El resumen opcional no contiene voz ni rasgos del sonido. Un estado VOZ por ventana indicaría
**cuándo** se habló cerca del micrófono (no quién ni qué), y ese patrón temporal podría
considerarse dato personal de la casa (NO VERIFICADO). Por eso el resumen que se confirma en Git
**no lleva ventanas VOZ**: solo su recuento agregado por sesión y tipo de tramo, con hora relativa
a la sesión (§6).

## 4. Base jurídica (valoración razonada, no definitiva)

### 4.1 ¿Aplica la excepción doméstica (RGPD art. 2.2.c)?
El RGPD no se aplica al tratamiento hecho por una persona física «en el ejercicio de actividades
exclusivamente personales o domésticas». El considerando 18 la limita a lo que no tiene «conexión
alguna con una actividad profesional o comercial». Argumentos:

- **A favor:** lo hace una persona física, en su casa, con su propio equipo, sin publicar ni
  ceder nada y sin conservar el sonido.
- **En contra:**
  1. Atalaya se concibe como un producto con licencia propietaria y clientes potenciales (FCSE,
     prisiones, puertos; `docs/RIESGOS.md` R-13). La prueba forma parte del desarrollo de ese
     producto: hay conexión con una actividad profesional o comercial futura.
  2. El Tribunal de Justicia de la UE interpreta la excepción de forma estricta (asunto C-212/13,
     Ryneš, 2014: una cámara doméstica que abarca en parte la vía pública no queda cubierta). Si el
     micrófono capta a vecinos o transeúntes, el razonamiento sería análogo (NO VERIFICADO: la
     sentencia trata de vídeo, no de sonido).

**Conclusión provisional:** la excepción doméstica es **dudosa** y no debe tomarse como base. Se
trabaja como si el RGPD y la LOPDGDD se aplicaran. Si un profesional confirmara que la excepción
aplica, las medidas de este documento se mantendrían igualmente como buena práctica.

### 4.2 Base propuesta: interés legítimo (art. 6.1.f) con ponderación
- **Interés legítimo del responsable:** desarrollar y validar técnicamente un producto (el
  detector acústico de Atalaya), una finalidad lícita. El efecto sobre las personas presentes no
  es nulo: se valora en la ponderación y en los riesgos R-DL-1 a R-DL-3 del §8.
- **Necesidad:** el canal real altavoz → micrófono no se puede medir sin un micrófono abierto en
  una sala (la alternativa 4 del ADR 0017, inyectar ficheros, no mide ese canal). Ver §5.
- **Ponderación con los derechos de los interesados:**
  - a favor del tratamiento: nada se conserva; la voz se descarta antes del clasificador; no hay
    identificación ni escucha humana; todo es local; sesiones cortas, iniciadas y paradas por el
    usuario; los convivientes están informados y pueden oponerse con efecto inmediato;
  - en contra: la vivienda es el espacio de mayor expectativa de intimidad (Constitución Española,
    art. 18); quien está en casa no espera un micrófono abierto con fines técnicos; hay riesgos
    residuales fuera del control del código (§8).
  - **Resultado provisional:** el interés legítimo prevalece **solo** si se cumplen todas las
    medidas organizativas del §9 (en especial el aviso previo y la ausencia de objeción de los
    convivientes). Sin ellas, la ponderación no se sostiene.

### 4.3 Consentimiento informado de los convivientes
El consentimiento (art. 6.1.a) no sirve como base general: no puede obtenerse de visitas
imprevistas, vecinos ni transeúntes, y su retirada obligaría a cortar igualmente. Se propone como
**garantía adicional**, no como base: antes de cada sesión, cada conviviente adulto que vaya a
estar en casa recibe el aviso del §9 y manifiesta que no se opone; si alguien se opone, la sesión
no se hace mientras esa persona esté presente. La oposición puede expresarse **en privado y sin
dar explicaciones**, y no tiene consecuencia alguna para quien la expresa (§9). Menores: no hay
sesiones mientras haya menores en casa salvo aviso previo a sus representantes legales sin
oposición, y **nunca** en la habitación donde esté un menor (NO VERIFICADO si conviven menores:
lo indica el usuario).

### 4.4 Otras normas a tener en cuenta (NO VERIFICADO, para el profesional)
- Captar conversaciones ajenas sin conocimiento de los interlocutores puede tener relevancia penal
  (Código Penal, art. 197) además de la civil (Ley Orgánica 1/1982, intimidad). El diseño evita
  conservar o escuchar nada, pero la valoración corresponde a un profesional.
- LOPDGDD art. 89.3 (prohibición de sistemas de grabación de sonidos en el lugar de trabajo salvo
  riesgos relevantes): si en la vivienda trabaja personal del hogar, la vivienda es su lugar de
  trabajo. Por eso la regla del §9 es no hacer nunca sesiones con personal del hogar presente.
  Si esa regla basta es una pregunta para el profesional.
- Información a los interesados (§10): si la primera capa (aviso y cartel) es suficiente para
  convivientes y visitas, y cómo cumplir el art. 13 con vecinos y transeúntes, son preguntas para
  el profesional.
- La obligatoriedad formal de la DPIA para este tratamiento concreto (art. 35.3 y la lista de la
  AEPD del art. 35.4) no está comprobada. Se hace igualmente porque el proyecto la exige en cada
  fase (REQ-PRIV-006).

## 5. Necesidad y proporcionalidad
| Pregunta | Respuesta |
|---|---|
| ¿Hay una alternativa sin micrófono? | Para el entrenamiento y la evaluación en Colab, sí (datos con licencia, sin micrófono). Para medir el canal altavoz → micrófono en una sala real, no (ADR 0017, opciones 3 y 4 descartadas) |
| ¿Se capta lo mínimo? | Un solo canal, el micrófono integrado; ventanas de 0,96 s; búfer de 4 s que se sobrescribe; sin almacenamiento |
| ¿Se reduce el tiempo? | Sesiones a demanda; el micrófono solo está abierto mientras corre el proceso de la sesión |
| ¿Se reduce el alcance? | Una habitación, ventanas cerradas, sin visitas; el Mac lejos de zonas comunes ocupadas |
| ¿Se reduce la sensibilidad? | Puerta de voz: lo que parece voz se descarta antes de clasificar y se pone a cero |
| ¿Es proporcionado el resultado? | Una prueba técnica de unas horas frente a un riesgo bajo y acotado, si se cumplen §7 y §9 (valoración provisional) |

## 6. Minimización y retención

| Dato | Dónde vive | Retención |
|---|---|---|
| Muestras de sonido (búfer circular) | Memoria del proceso | **Cero**: se sobrescriben a los 4 s; `wipe()` las pone a cero al parar y ante SIGINT/SIGTERM |
| Ventana con voz | Memoria del proceso | **Cero**: se descarta antes del clasificador; su región del búfer y su copia se ponen a cero (H2.9 + H2.P5, **pendientes**) |
| Embeddings y salidas de YAMNet | Memoria del proceso | **Cero**: variables locales de cada ventana; nunca a la página, al log ni a fichero |
| Escalares de la página | Memoria del proceso y del navegador | Lo que dura la sesión; la página no guarda nada (cabecera `no-store`) |
| Resumen de sesión (opcional, `--export`) | `docs/evidence/hito-2/resumen-*.json` en el repositorio privado (D-5) | **Propuesta para aprobar (opción a):** se confirma en Git como evidencia del hito y se conserva en el repositorio privado mientras exista, sin ventanas VOZ (solo su recuento agregado), solo hora relativa, sin voz ni identidad. Ver la limitación de Git abajo |

Contenido del resumen (H2.13, **pendiente de implementar**; esquema NO VERIFICADO hasta su test):
por ventana **sin voz**, hora **relativa** al inicio de la sesión, probabilidad (≤ 1 escalar por
ventana de 0,48 s, REQ-PRIV-010), estado y etiqueta del operador; por sesión, latencias y
contadores, entre ellos el número de ventanas VOZ por tipo de tramo (lo que necesita la métrica
«ventanas descartadas por voz» de la sección 4.1 del plan). Ninguna ventana VOZ individual, muestra,
embedding, nombre, ubicación ni hora absoluta por ventana. Condición para H2.13: el esquema del
resumen debe declarar la sensibilidad de **cada campo** como `OPERATOR` (como `EVENT_SCHEMA` de la
página, P8), y un campo sin sensibilidad declarada o con otro nivel hace fallar su test.

**Limitación de Git:** lo que se confirma en el repositorio queda en su historia; borrarlo exige
reescribirla, y la historia de `main` no se reescribe (CLAUDE.md). Hay que decidir **antes** de la
primera exportación:

- **(a) Recomendada:** confirmar los resúmenes en Git, como ya aprobó el usuario en D-5, con la
  minimización adicional de arriba (sin ventanas VOZ, solo hora relativa, sin voz ni identidad), y
  aceptar su conservación en el repositorio privado mientras exista. Es coherente con D-5 y con la
  verificación de H2.14, que recalcula las métricas desde `docs/evidence/hito-2/resumen-*.json`.
- **(b) Alternativa:** guardar los resúmenes fuera de Git, borrarlos al cerrar el hito y confirmar
  solo las métricas agregadas con su SHA-256. Minimiza más, pero exigiría **modificar D-5** y la
  verificación de H2.14 (el recálculo independiente dejaría de ser reproducible desde el
  repositorio).

Cualquiera de las dos es decisión del usuario.

## 7. Medidas técnicas y su comprobación
Comandos en `pilots/acoustic/` (`uv run --frozen pytest -q …`). Resultados en
`docs/evidence/hito-2/registro-tareas.md`.

| Medida | Prueba | Estado |
|---|---|---|
| Ninguna escritura a disco (capa estática, AST) | `tests/live/test_no_disk.py::test_live_package_has_no_static_violations`, `test_static_layer_catches_injected_wav_writer`, `test_static_layer_catches_injected_np_save`, `test_static_layer_catches_each_forbidden_pattern`, `test_static_layer_catches_evasions` | Verificado (H2.8, P1) |
| Gancho de auditoría durante una sesión simulada de 120 s, con la página | `test_no_disk.py::test_full_simulated_session_writes_nothing`, `test_dynamic_layer_blocks_injected_wav_writer`, `test_dynamic_layer_blocks_injected_np_save`, `test_dynamic_layer_blocks_other_disk_writes`, `test_dynamic_layer_blocks_process_native_and_db_escapes`, `test_dynamic_layer_blocks_non_local_connections` | Verificado (H2.8, H2.12, P1) con origen sintético; **con el micrófono real, NO VERIFICADO** |
| Vigilancia del temporal y del HOME reales | `test_no_disk.py::test_default_watch_roots_are_the_real_tmp_and_home`, `test_real_tmp_snapshot_detects_a_new_wav` | Verificado (P7) con límites: solo mira ficheros con extensión sensible (sonido, arrays, pickle, bases de datos, volcados) o con nombre `core.*`, hasta profundidad 2 en el temporal y el HOME reales y profundidad 1 en `/cores` |
| Sin modo de grabación | `test_no_disk.py::test_no_recording_mode_exists` | Verificado (H2.8) |
| Sin volcados de memoria (`RLIMIT_CORE = 0`) | `test_no_disk.py::test_core_dumps_disabled_in_a_fresh_process` | Verificado (H2.8) |
| Borrado del búfer ante señales y al parar | `test_no_disk.py::test_real_signal_with_lock_held_wipes_and_exits`, `test_stop_handler_only_marks_and_restores_handlers`; `tests/live/test_ring.py::test_wipe_zeroes_every_sample_and_resets_positions`; `tests/live/test_capture.py::test_engine_stop_wipes_buffer_and_stops_source` | Verificado (H2.7, H2.8, P2) |
| Búfer de tamaño fijo | `test_ring.py::test_memory_constant_over_ten_simulated_minutes` | Verificado (H2.7) |
| Solo entrada de sonido | `test_capture.py::test_sounddevice_source_opens_only_a_mono_input_stream`, `test_live_code_never_references_output_or_duplex_streams` | Verificado con un módulo falso (H2.7); el micrófono real no se ha abierto |
| Umbral de voz 0,30 no relajable por el artefacto | `tests/live/test_artifact.py::test_speech_threshold_must_equal_pilot_constant`, `test_speech_indices_must_cover_canonical_yamnet_speech`, `test_threshold_comes_from_pilot_speech_gate` | Verificado (L1) |
| Ventanas VOZ sin puntuación ni efecto en la alerta | `tests/live/test_alert.py::test_speech_windows_do_not_count_and_hide_score`, `test_speech_during_alert_keeps_it_active_without_score` | Verificado (H2.11) |
| **Puerta de voz en directo: descarte y puesta a cero** de la región del búfer y de la copia (`window.samples.fill(0)`) | Parcial: `CaptureEngine.zero_window` y `RingBuffer.zero_range` ya existen y están probados (`tests/live/test_capture.py::test_engine_zero_window_clears_that_region`, `tests/live/test_ring.py::test_zero_range_clears_only_that_region`, `test_zero_range_ignores_already_overwritten_samples`). Falta `tests/live/test_speech_gate_live.py` (aún no existe) | Borrado de la región del búfer: verificado. **Integración en la puerta de voz en directo y `fill(0)` de la copia: PENDIENTES (H2.9 + H2.P5), NO VERIFICADO. Bloquea la primera captura** |
| **Punto de entrada de sesión** en el orden `disable_core_dumps()` → `WriteAudit(block=True)` → `stop_on_signals()` → `try/finally` | test en subproceso con SIGTERM (aún no existe) | **PENDIENTE (H2.P3), NO VERIFICADO. Bloquea la primera captura** |
| Página solo en `127.0.0.1`, CSP, `Host`, token, sin CORS, sin logs, solo escalares | `tests/live/test_server.py::test_bind_is_loopback_only`, `test_non_loopback_bind_is_rejected`, `test_wrong_host_header_is_forbidden`, `test_foreign_origin_is_forbidden`, `test_cors_preflight_is_refused`, `test_events_stream_only_scalars`, `test_board_rejects_non_scalar_or_unknown_fields`, `test_requests_are_not_logged`, `test_every_event_field_declares_operator_sensitivity` | Verificado (H2.12, P8) |
| Resumen solo con escalares, esquema cerrado, sin ventanas VOZ individuales y con sensibilidad `OPERATOR` declarada por campo | `tests/live/test_export.py` (aún no existe) | **PENDIENTE (H2.13), NO VERIFICADO**; sin él no se usa `--export` |
| Aislamiento del piloto respecto del producto | `tests/live/test_isolation.py` | Verificado (H2-R11) |
| Swap cifrada | `sysctl vm.swapusage` → `(encrypted)` | Verificado el 2026-11-16 (P6 y de nuevo al redactar esta DPIA) |
| Disco cifrado | `fdesetup status` → `FileVault is On.` | Verificado el 2026-11-16 al redactar esta DPIA |

## 8. Riesgos residuales
Escala de `docs/RIESGOS.md`: probabilidad (P) e impacto (I) de 1 a 5. Valoración de Claude Code,
NO VERIFICADA por un tercero.

| ID | Riesgo residual | P | I | P×I | Medidas y comentario |
|---|---|---|---|---|---|
| D2-1 | Código nativo (onnxruntime, PortAudio, CoreAudio) escribe datos del proceso fuera de la vista del gancho de Python | 1 | 3 | 3 | Dependencias fijadas y con licencia leída (ADR 0017, anexo T0.1); comprobación tras la sesión de que no hay ficheros de sonido nuevos (H2.14); disco cifrado |
| D2-2 | `coreaudiod` u otro proceso con permiso de micrófono capta a la vez (otra app, dictado, asistente de voz) | 2 | 3 | 6 | Revisar antes de la sesión Ajustes del Sistema → Privacidad y seguridad → Micrófono y cerrar las apps que no hagan falta; fuera del control del código (NO VERIFICADO qué hace cada app) |
| D2-3 | Informes de fallo de macOS (ReportCrash) con memoria del proceso pese a `RLIMIT_CORE = 0` | 1 | 3 | 3 | Desactivar «Compartir análisis» con Apple y con desarrolladores (NO VERIFICADO su estado actual); tras un fallo, revisar `~/Library/Logs/DiagnosticReports` y borrar los informes del proceso de la sesión. El búfer es de 4 s |
| D2-4 | Copias transitorias en memoria (copias de NumPy, remuestreo, entradas de ONNX, recolector de basura) que no se ponen a cero | 3 | 1 | 3 | Viven en el proceso y desaparecen al terminar; no salen del proceso. No se puede garantizar su puesta a cero desde Python (NO VERIFICADO cuántas hay) |
| D2-5 | Paginación de la memoria a la swap | 2 | 1 | 2 | Swap cifrada y FileVault activo (verificado); búfer de 256 kB |
| D2-6 | La puerta de voz deja pasar voz (falso negativo de YAMNet: susurros, voz lejana, voz con música) | 3 | 1 | 3 | Lo que pasa solo produce un escalar de probabilidad de dron; nada se conserva ni se escucha. Tasa de falsos negativos de la puerta en esta sala NO VERIFICADA |
| D2-7 | Captar a un conviviente, visita, menor o persona del personal del hogar no avisados | 2 | 3 | 6 | Aviso previo, sin visitas ni personal del hogar, sin menores en la habitación, sesión en una habitación, el usuario presente y con la parada a mano (§9) |
| D2-8 | Que la exportación del resumen incluya algo más que escalares por un error | 1 | 2 | 2 | H2.13 con esquema cerrado y prueba negativa (pendiente); sin H2.13 en verde no se usa `--export` |

**Riesgos para los derechos y libertades** (no técnicos; los mitigan sobre todo las medidas del §9):

| ID | Riesgo | P | I | P×I | Mitigación |
|---|---|---|---|---|---|
| R-DL-1 | Efecto disuasorio o sensación de vigilancia en la vivienda: los convivientes hablan menos o se sienten observados en su casa (Constitución Española, art. 18) | 3 | 2 | 6 | Sesiones cortas, anunciadas y con fin conocido; indicador naranja y cartel visibles; nunca sesiones desatendidas ni de fondo; derecho a pedir que no haya sesión sin dar razones (§9.1, §9.5) |
| R-DL-2 | Asimetría de poder: un conviviente que depende del usuario (económicamente, por edad o por cuidados) no se atreve a oponerse | 2 | 3 | 6 | La oposición puede expresarse en privado y sin explicaciones, y no tiene consecuencias; ante la duda sobre si alguien está cómodo, no hay sesión; nunca con personal del hogar presente (§4.3, §9.1, §9.9) |
| R-DL-3 | Desviación de finalidad: usar el micrófono o la página para algo distinto de la prueba técnica (por ejemplo, saber cuándo hay gente hablando en casa) | 1 | 4 | 4 | Finalidad única declarada (§2); sin ventanas VOZ individuales en el resumen (§6); sin escucha, sin conservación y sin modo de grabación (§7); compromiso expreso del usuario (§9.8, §12) |

Criterio propio de esta DPIA (`docs/RIESGOS.md` usa la misma escala pero no fija un umbral de
«alto»): se considera alto un riesgo con P×I ≥ 15. Con ese criterio, ningún riesgo residual queda
en nivel alto con las medidas aplicadas; los más altos (D2-2, D2-7, R-DL-1 y R-DL-2, con 6)
dependen de medidas organizativas que solo puede cumplir el usuario.

## 9. Medidas organizativas (las cumple el usuario)
1. **Aviso a convivientes** antes de cada sesión, de palabra o por escrito. Texto propuesto:
   «Voy a hacer una prueba técnica con el micrófono del portátil durante unas horas, en
   [habitación]. No se graba nada: el sonido se analiza al momento y se borra, y si detecta voz la
   descarta. Solo busca el sonido de drones de unos vídeos. Si te molesta, dímelo y paro o lo dejo
   para cuando no estés. Puedes decírmelo en privado y no tienes que darme ninguna razón.» Si
   alguien se opone, no hay sesión mientras esté presente, y la oposición no tiene consecuencias.
2. **Franja horaria** en la que haya el menor número de personas en casa, y nunca de noche, con
   visitas ni con personal del hogar presente.
3. **Cartel o aviso verbal** junto al Mac: «Micrófono en prueba técnica, sin grabación».
4. **Indicador del micrófono de macOS** (punto naranja en la barra de menús) visible durante toda la
   sesión; si aparece sin una sesión en marcha, se investiga.
5. **El usuario inicia y para la sesión** y está presente durante toda ella; nunca sesiones
   desatendidas, programadas ni de fondo (D-9).
6. **Ventanas cerradas** y el Mac lejos de paredes medianeras, para no captar a vecinos ni a la calle.
7. **Antes de la sesión:** revisar las apps con permiso de micrófono (D2-2) y el estado de
   «Compartir análisis» (D2-3). **Después:** comprobar que no hay ficheros de sonido nuevos (H2.14).
8. No reproducir ni hablar de contenidos privados durante la sesión, y **no usarla para ninguna otra
   finalidad** (ni para saber si hay alguien hablando en casa, R-DL-3).
9. **Nunca sesiones con personal del hogar presente** (limpieza, cuidados, reparaciones), por la
   relación de dependencia y porque la vivienda es su lugar de trabajo (LOPDGDD art. 89.3, §4.4).
10. **Menores:** no hay sesiones mientras haya menores en casa salvo aviso previo a sus
    representantes legales sin oposición, y nunca en la habitación donde esté un menor.

## 10. Derechos de los interesados y cómo se ejercen
- **Información (art. 13):** el micrófono capta los datos **directamente** de los interesados, así
  que aplica el art. 13 y no la excepción por esfuerzo desproporcionado del art. 14.5.b. Se propone
  información **por capas**, con el criterio de las Directrices 3/2019 del CEPD para dispositivos
  de captación: primera capa, el aviso verbal del §9.1 y el cartel del §9.3 (quién, para qué, que
  no se graba y cómo oponerse); segunda capa, esta DPIA o un resumen de una página a disposición de
  quien lo pida. Para vecinos y transeúntes no hay forma práctica de informar: la garantía real es
  **evitar captarlos** (ventanas cerradas, Mac lejos de medianeras, §9.6). Si eso basta es una
  pregunta para el profesional (§4.4; NO VERIFICADO).
- **Oposición (art. 21):** cualquier conviviente puede pedir de palabra que se pare: el usuario
  detiene la sesión en el acto (Ctrl+C, que borra el búfer, o cierre del proceso).
- **Acceso, rectificación, supresión, limitación y portabilidad (arts. 15–20):** no se conserva
  sonido ni dato que identifique a nadie, así que no hay nada que entregar, corregir ni borrar; el
  responsable no está obligado a conservar datos para poder identificar al interesado (art. 11).
  Si se exporta el resumen, se puede consultar entero y borrar del disco a petición (en Git, ver la
  limitación del §6).
- **Ejercicio:** directamente ante el usuario, en persona, en la vivienda. Plazo de respuesta: en el
  acto para la oposición; un mes como máximo para lo demás (art. 12.3).
- **Reclamación:** ante la Agencia Española de Protección de Datos (AEPD).

## 11. Registro de actividades (art. 30) — ficha T-07
| Campo | Contenido |
|---|---|
| Tratamiento | T-07 Prueba técnica del detector acústico con el micrófono del Mac en la vivienda del usuario (hito 2) |
| Responsable | El usuario (persona física); sin encargados |
| Finalidad | Prueba técnica del detector (§2) |
| Interesados | Usuario, convivientes, visitas, personal del hogar, vecinos y transeúntes cuya voz pueda captarse (§3) |
| Datos | Sonido ambiente con posible voz, solo en memoria y descartado; resumen opcional con escalares |
| Base jurídica | RGPD art. 6.1.f (interés legítimo con ponderación, §4.2), excepción doméstica dudosa (§4.1), aviso y no oposición de convivientes como garantía (§4.3) — pendiente de asesoría |
| Destinatarios y transferencias | Ninguno; nada sale del Mac |
| Retención | Sonido: cero. Resumen sin ventanas VOZ individuales: opción (a) en el repositorio privado, coherente con D-5, o (b) fuera de Git, según apruebe el usuario (§6) |
| Medidas | §7 y §9 |

La fila T-07 está también en el registro de `docs/dpia/v0.md`.

## 12. Conclusión y lo que debe aprobar el usuario
Valoración provisional de Claude Code (no jurídica): con las medidas técnicas del §7 **completas**
(incluidas H2.P3, H2.P5/H2.9 y, si hay exportación, H2.13) y las organizativas del §9, el riesgo
residual para los interesados es **bajo** y el tratamiento parece proporcionado a una prueba
técnica de unas horas. No es necesaria la consulta previa a la AEPD (art. 36), que solo procede si
el riesgo residual fuera alto (valoración NO VERIFICADA por un profesional).

Para levantar la condición P4, el usuario debe aprobar de forma expresa (y quedará registrado en
`docs/requirements/DECISIONES-USUARIO.md` **cuando lo apruebe**, no antes):

1. Esta DPIA v1 y la fila T-07 del registro de actividades.
2. La base jurídica propuesta: interés legítimo (art. 6.1.f), sin apoyarse en la excepción doméstica,
   y sabiendo que no hay revisión de un profesional (R-12).
3. El compromiso de cumplir las medidas organizativas del §9 en cada sesión (aviso y no oposición
   de convivientes, que pueden expresar en privado y sin explicaciones; franja horaria; cartel;
   indicador; ventanas cerradas; presencia y parada; nunca con personal del hogar presente; reglas
   para menores; ninguna otra finalidad).
4. La retención del resumen: opción (a), recomendada y coherente con D-5 y H2.14, en Git y en el
   repositorio privado mientras exista, sin ventanas VOZ individuales y solo con hora relativa; o
   (b) fuera de Git, borrado al cerrar el hito, que exigiría modificar D-5 y H2.14.
5. La aceptación de los riesgos residuales D2-1 a D2-8 y R-DL-1 a R-DL-3.
6. Que la primera captura real sigue bloqueada hasta que H2.P3 y H2.P5 (con H2.9) estén en verde.

Recomendación adicional: pedir una revisión a un profesional del RGPD (colegio de abogados, clínica
jurídica universitaria; ver B-01) antes de cualquier uso fuera de la vivienda o con terceros.

## 13. Revisión pendiente
- Revisión `privacy-reviewer` sin hallazgos abiertos: **pendiente** (verificación de H2.P4 en el
  plan); NO VERIFICADO.
- Aprobación del usuario: **pendiente**.

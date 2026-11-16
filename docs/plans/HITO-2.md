# Plan HITO 2 — Demo local en directo de un nodo acústico con el micrófono del Mac

Versión 1 · 2026-11-16 · Estado: **pendiente de aprobación (STOP de plan, puerta P0)**.
No es el P0 de FASE 4 ni de FASE 5, no adelanta ningún cierre y no integra nada en el producto.
Decisión de arquitectura asociada: `docs/adr/0017-hito-2-microfono-local-en-directo.md` (propuesto).

## 1. Objetivo
Demostrar en el Mac del usuario, en directo y **solo en local**, que un detector acústico ligero
escucha con el micrófono integrado el sonido de drones que el usuario reproduce por un altavoz
(vídeos), distingue ese sonido del ruido normal de su casa y muestra la alerta en una página de
`localhost`, con estas garantías:

- el sonido vive **solo en memoria** (búfer circular), se infiere por ventanas y se descarta; ninguna
  muestra ni embedding llega a un fichero, a un log, a la página ni a la red, y eso se **comprueba**
  con tests, no solo se promete;
- el modelo se entrena en Colab (ADR 0016) y llega al Mac como un **artefacto pequeño** (pesos de la
  regresión, calibración, configuración y hashes) que se verifica antes de cargarlo;
- el entrenamiento ataca el **atajo de dominio** de la iteración 5 (normalización y aumento de canal,
  mezclas cruzadas entre fuentes, rasgo armónico de hélices) y se juzga con leave-one-source-out
  (LOSO) como métrica principal;
- todo resultado se etiqueta **«reproducción en sala, no vuelo real»** y lo que no se puede medir se
  marca **NO VERIFICADO**.

Al cerrar el hito habrá: código probado en `pilots/acoustic/` (subpaquete `live`), un artefacto de
modelo con hash, evidencias en `docs/evidence/hito-2/` (métricas de Colab recalculadas por script,
métricas del protocolo en sala generadas por script) y la comparación con la línea base de la
iteración 5 en el mismo protocolo.

## 2. Requisitos que cubre
Parcialmente, en un carril aislado (no cierran el requisito en el producto):

| ID | Prioridad | Cómo lo toca este hito |
|---|---|---|
| REQ-PRIV-002 | MUST | El sonido no llega nunca a un fichero: análisis estático + gancho de auditoría de `open` (H2.8) |
| REQ-LEG-005 | MUST | Inferencia local y descarte inmediato; de la página solo salen estado, puntuación y hora (H2.7–H2.12) |
| REQ-LEG-006 | MUST | No hay sesión de grabación: no se abre ningún modo de grabación (H2.8, prueba negativa) |
| REQ-PRIV-010 | MUST | Resumen de sesión con ≤ 1 escalar por ventana de 0,48 s, sin embeddings (H2.13) |
| REQ-PRIV-003 | MUST | Logs sin datos personales ni contenido de sonido (H2.8, H2.13) |
| REQ-PRIV-006 | MUST | DPIA actualizada con el tratamiento del hito (H2.15) |
| REQ-NFR-015 | MUST | La demo corre en el Mac Intel sin GPU (T0.1, H2.10) |
| REQ-NFR-016 | MUST | 0 € (sección 6) |
| REQ-LEG-009 | MUST | Solo datos con licencia verificada en Colab; los vídeos reproducidos nunca entran en entrenamiento |
| REQ-LEG-016 | MUST | Licencias de las dependencias nuevas leídas y registradas (T0.1) |
| REQ-FUN-027 | MUST | Inferencia por ventanas con probabilidad y estado (sin publicación MQTT en este hito) |
| REQ-FUN-057 | MUST | Antecedente del demostrador v1 con Mac en vez de Android y página local en vez del dashboard; **no** lo cierra |

## 3. Hallazgos de la exploración
| Hallazgo | Efecto |
|---|---|
| Iteración 5 (rama `piloto/iteracion-5`, PR #12 **abierta**, cifras transcritas a mano): dentro de fuentes vistas recall ARIS 0,91 con precisión 0,985; en LOSO recall ARIS ≈ 0,002–0,010 y FPR FSD50K hasta 0,52; PR-AUC LOSO 0,71–0,79 | Atajo de dominio: el modelo aprende canal/micrófono de cada dataset. Un micrófono de portátil frente a un altavoz es una fuente nueva → sin tratamiento de canal la demo fallaría. LOSO pasa a ser la métrica principal |
| Los módulos que este plan reutiliza (`augment`, `windows`, `calibration`, `experiment`, `predictions`, `recompute_metrics.py`) solo existen en `piloto/iteracion-5`, no en `main` | Prerrequisito: fusionar PR #12 o basar la implementación en esa rama (decisión D-2) |
| ADR 0016 y el plan del piloto prohíben el micrófono | El micrófono en el Mac necesita ADR propio (0017, propuesto) y aprobación expresa |
| `speech_gate.py` usa umbral 0,30 sobre la puntuación de voz de YAMNet | Se reutiliza en directo como puerta de voz; mismo umbral, sin cambio de umbral → sin ADR adicional |
| Mac Intel, 8 GB de RAM, ~9,8 GB de disco libres, sin datasets descargados | Solo inferencia: YAMNet en ONNX (~15 MB, NO VERIFICADO) + regresión logística. TensorFlow local solo como respaldo (cientos de MB) |
| MEGAPROMPT `<computo>` admite «inferencia ONNX en CPU» y «clasificadores ligeros sobre embeddings congelados» en el Mac | Diseño coherente con la especificación |
| SPEC §3.1 y REQ-FUN-057 piden «datasets con licencia compatible reproducidos por un altavoz» | Los vídeos de YouTube sirven para una **demo informal**; para cifras con verdad terreno conviene reproducir también clips con licencia (decisión D-3) |
| YAMNet (TF Hub) enmarca parches de 0,96 s con salto de 0,48 s; el número exacto de muestras que produce un único parche (15 360 frente a ~15 600) está **NO VERIFICADO** | H2.7 lo fija por test contra la salida real del modelo ONNX |
| `check_spec.py` revisa línea a línea los planes buscando términos sensibles | El plan y el ADR se redactan sin términos que requieran revisión legal; `make check` lo confirma |

## 4. Tareas
Orden estricto. TDD; verificación y prueba negativa registradas en
`docs/evidence/hito-2/registro-tareas.md`; un commit por tarea con los IDs. **Un FALLO bloquea la
tarea siguiente.** Salvo que se diga otra cosa, los comandos se ejecutan en `pilots/acoustic/`.
Todos los tests nuevos llevan `@pytest.mark.req(...)` con los IDs de la tarea.

### T0.1 — Prerrequisitos y viabilidad de dependencias (sin código del hito)
- **Qué:** (a) base de código con la iteración 5 (D-2); (b) ADR 0017 aceptado; (c) extra opcional
  `live` en `pilots/acoustic/pyproject.toml` con `sounddevice` y `onnxruntime` en versiones exactas
  con rueda x86_64 para macOS y Python 3.12; licencias leídas en la fuente y anotadas en el ADR;
  (d) huella en disco medida.
- **Requisitos:** REQ-NFR-015, REQ-NFR-016, REQ-LEG-016
- **Verificación:** `git merge-base --is-ancestor 98455be HEAD && grep -q "Estado: aceptado" ../../docs/adr/0017-*.md && uv sync --extra live --frozen && uv run python -c "import onnxruntime, sounddevice; print(onnxruntime.__version__, sounddevice.__version__)" && du -sh .venv`
- **Resultado esperado:** las cuatro órdenes salen con 0; versiones impresas; incremento del entorno
  ≤ 300 MB; ninguna licencia AGPL/GPL.
- **Prueba negativa:** `uv tree --extra live | grep -ci tensorflow` devuelve 0 (el extra `live` no
  arrastra TensorFlow). Si no hay rueda de `onnxruntime`, la tarea queda en FALLO y se aplica el
  respaldo del ADR (TensorFlow 2.16.2) con nueva aprobación.

### H2.1 — Normalización de canal compartida (Colab y Mac)
- **Qué:** `acoustic_pilot/channel_norm.py`: mono, remuestreo a 16 kHz con `resample_poly`
  (48 000 → 16 000 y 44 100 → 16 000), paso banda 100–7 500 Hz (Butterworth en SOS), normalización
  de sonoridad por ventana a un RMS objetivo con límite de ganancia, y PCEN sobre el mel para la rama
  armónica. **El mismo código** se incrusta en el cuaderno y se importa en el Mac.
- **Requisitos:** REQ-FUN-027
- **Verificación:** `uv run pytest tests/test_channel_norm.py -q`
- **Resultado esperado:** todos en verde; un tono de 1 kHz conserva su frecuencia tras remuestrear
  (error ≤ 1 Hz); ganancia a 100 Hz–7,5 kHz dentro de ±1 dB y ≥ 20 dB de atenuación a 30 Hz;
  salida finita y determinista; dos señales que solo difieren en ganancia (−20/+6 dB) dan la misma
  ventana normalizada (error ≤ 1e-3).
- **Prueba negativa:** una frecuencia de muestreo no admitida (p. ej. 11 025 Hz) o una entrada con
  NaN se rechazan con `ValueError`; una ventana de silencio digital no se amplifica (ganancia limitada).

### H2.2 — Aumento de canal (solo Colab, en entrenamiento)
- **Qué:** `acoustic_pilot/channel_augment.py`, con semilla: EQ aleatoria (3–5 filtros de pico y
  estantería, ±12 dB), respuesta de micrófono aleatoria (corte bajo 80–300 Hz, alto 6–8 kHz,
  pendiente aleatoria), **respuesta de altavoz pequeño** (corte bajo 150–400 Hz, resonancias),
  reverberación con respuesta al impulso sintética (ruido con caída exponencial, RT60 0,2–0,8 s; sin
  datasets de RIR, que necesitarían intake), códec (μ-law de 8 bits y recorte de banda; códecs con
  pérdidas mediante `ffmpeg` de Colab solo si su licencia y su versión se registran, NO VERIFICADO)
  y ruido de fondo de baja amplitud. Las salidas se marcan `synthetic=true`.
- **Requisitos:** REQ-LEG-009
- **Verificación:** `uv run pytest tests/test_channel_augment.py -q`
- **Resultado esperado:** en verde; misma semilla → salida idéntica; longitud conservada; pico
  ≤ 0,99; EQ con todas las ganancias a 0 dB = identidad (error ≤ 1e-6); RT60 estimado de la RIR
  sintética dentro de ±20 % del pedido.
- **Prueba negativa:** RT60 ≤ 0, ganancias fuera de rango o frecuencia ≠ 16 kHz → `ValueError`; un
  test comprueba que ninguna ventana aumentada entra en validación ni test (fallo cerrado).

### H2.3 — Mezclas cruzadas entre fuentes
- **Qué:** ampliar `augment.plan_mixes` con `plan_cross_mixes`: el dron de la fuente A se mezcla con
  fondo de una fuente B ≠ A (SNR −10…+20 dB), de modo que el canal deje de delatar la clase; en cada
  pliegue LOSO solo entran mezclas cuyas dos fuentes están en entrenamiento.
- **Requisitos:** REQ-LEG-009
- **Verificación:** `uv run pytest tests/test_cross_mixes.py tests/test_leakage_balance_augment.py -q`
- **Resultado esperado:** en verde; el 100 % de las mezclas cruzadas tienen fuente de dron ≠ fuente
  de fondo; el plan es determinista con semilla.
- **Prueba negativa:** una mezcla que use la fuente retenida del pliegue se rechaza; una mezcla con
  ambas partes de la misma fuente no aparece en `plan_cross_mixes`.

### H2.4 — Rasgo armónico de hélices
- **Qué:** `acoustic_pilot/harmonic.py`: sobre la ventana normalizada y su mel con PCEN, estima la
  fundamental del paso de palas (50–1 000 Hz, suma de armónicos), armonicidad, número de armónicos
  detectados, estabilidad de la fundamental entre ventanas y modulación de amplitud. Vector de ~8
  rasgos que se concatena al embedding YAMNet (1 024 + 8) para la regresión logística.
- **Requisitos:** REQ-FUN-027
- **Verificación:** `uv run pytest tests/test_harmonic.py -q`
- **Resultado esperado:** en verde; peine sintético con f0 = 180 Hz y 8 armónicos → f0 estimada
  ±3 Hz y armonicidad ≥ 0,8; ruido blanco → armonicidad ≤ 0,2; el peine filtrado por la respuesta
  de altavoz pequeño de H2.2 (sin fundamental) sigue dando f0 ±5 Hz.
- **Prueba negativa:** ruido rosa y un tono puro aislado no se clasifican como «armónico de hélice»
  (≥ 3 armónicos exigidos); entrada vacía o no finita → `ValueError`.

### H2.5 — Iteración 6 en Colab y exportación del artefacto
- **Qué:** `build_colab.py` genera el cuaderno de la iteración 6 con H2.1–H2.4 incrustados. Mismas
  fuentes con licencia verificada que la iteración 5 (Svanström, ESC-10, FSD50K, ITU ARIS); ninguna
  fuente nueva sin `/dataset-intake`. Evalúa **LOSO como métrica principal** y CV por grupos como
  secundaria, frente a la iteración 5 (línea base). Convierte YAMNet a ONNX con `tf2onnx` y comprueba
  la equivalencia de embeddings y de la puntuación de voz. Exporta: `modelo_hito2.json` (coeficientes,
  intercepto, Platt, umbrales, configuración de normalización y de rasgos, índices de clases de voz,
  **vectores dorados**: 3 entradas sintéticas generadas por semilla con su salida esperada),
  `yamnet.onnx`, `predicciones.csv` y `SHA256SUMS`. Las métricas se recalculan con
  `recompute_metrics.py` desde el CSV exportado (cierra el pendiente del ADR 0016).
- **Requisitos:** REQ-LEG-009, REQ-NFR-016
- **Verificación:** local `uv run pytest tests/test_notebook_iter6.py -q`; tras ejecutar en Colab,
  `uv run python recompute_metrics.py --record modelo_hito2.json predicciones.csv > ../../docs/evidence/hito-2/metricas-colab.txt`
- **Resultado esperado:** cuaderno regenerable con hash estable; en Colab, diferencia máxima de
  embeddings TF frente a ONNX ≤ 1e-4 en ≥ 50 clips; tablas LOSO con IC 95 % y comparación con la
  iteración 5; `modelo_hito2.json` ≤ 200 kB. **Criterio de avance** (propuesta, decisión D-6):
  PR-AUC LOSO en ITU ARIS ≥ 0,85 y recall LOSO ARIS ≥ 0,50 con FPR LOSO FSD50K ≤ 0,10. Si no se
  alcanza, la demo puede seguir pero rotulada «modelo que no generaliza» y no se compara al alza.
  **Enmienda aceptada (ADR 0018, aprobada por el usuario el 2026-11-16):** D-6 depende de la prevalencia de ARIS
  (0,83: PR-AUC ≈ 0,83 por azar) y se sustituiría por el criterio C-LOSO, más exigente: por cada
  fuente de dron retenida con ≥ 2 fuentes de dron entrenando, ROC-AUC ≥ 0,85 y recall ≥ 0,50 con
  el umbral fijado sin verla; FPR ≤ 0,10 en los negativos de cada fuente retenida. El cuaderno y
  `recompute_metrics.py --criterio c-loso` informan de ambos criterios.
- **Prueba negativa:** el cuaderno se niega a exportar si la equivalencia ONNX supera 1e-4, si hay
  casi duplicados entre particiones o si aparece una fuente no aprobada (DADS, Al-Emadi…);
  `recompute_metrics.py` falla si el hash del CSV no coincide con el registrado.

### H2.6 — Cargador verificado del artefacto en el Mac
- **Qué:** `acoustic_pilot/live/artifact.py`: lee `modelo_hito2.json` (solo JSON, nunca pickle),
  valida el esquema y las dimensiones, comprueba el SHA-256 del JSON y del ONNX contra los hashes
  fijados en el repo (`pilots/acoustic/live/MODEL_HASHES`), y solo entonces crea la sesión ONNX.
  Los ficheros del modelo viven fuera de Git (D-8).
- **Requisitos:** REQ-FUN-027, REQ-NFR-015
- **Verificación:** `uv run pytest tests/live/test_artifact.py -q`
- **Resultado esperado:** en verde; carga en ≤ 5 s y memoria residente del proceso ≤ 400 MB tras la
  carga (medido; NO VERIFICADO hasta T0.1).
- **Prueba negativa:** un byte alterado en el JSON o en el ONNX, una dimensión de coeficientes
  distinta de la del embedding, un campo desconocido o un fichero `.pkl` → rechazo con error explícito
  y sin cargar nada.

### H2.7 — Captura en memoria con búfer circular y ventanas de 0,96 s a 16 kHz
- **Qué:** `acoustic_pilot/live/ring.py`: búfer circular `float32` preasignado (p. ej. 4 s a
  16 kHz = 64 000 muestras, 256 kB) con escritura que sobrescribe, lectura de ventanas de 0,96 s
  (número exacto de muestras fijado por test contra YAMNet ONNX: 15 360 o 15 600) con salto de
  0,48 s, contador de desbordes y `wipe()` que pone el búfer a cero. `live/capture.py`: adaptador
  sobre `sounddevice.InputStream` (frecuencia nativa del dispositivo, remuestreo con H2.1) con una
  interfaz `Source` que en tests se sustituye por `FakeSource` (señales sintéticas). Solo entrada:
  no se abre ningún flujo de salida de sonido.
- **Requisitos:** REQ-LEG-005, REQ-PRIV-002, REQ-FUN-027
- **Verificación:** `uv run pytest tests/live/test_ring.py tests/live/test_capture.py -q`
- **Resultado esperado:** en verde; tras 10 vueltas completas el búfer conserva solo las últimas
  64 000 muestras; ventanas solapadas al 50 % y alineadas; con 48 kHz de entrada la ventana tiene la
  longitud exacta; tras `wipe()` todas las muestras son 0; la memoria del búfer no crece en 10 min
  simulados.
- **Prueba negativa:** pedir una ventana mayor que la capacidad → `ValueError`; si el consumidor se
  retrasa, se cuentan desbordes y el estado pasa a DEGRADADO (nunca se encolan muestras sin límite);
  un test verifica que el código no crea `OutputStream` ni `Stream` dúplex.

### H2.8 — Garantía comprobable: ninguna muestra llega a disco
- **Qué:** tres capas de prueba sobre `acoustic_pilot/live/`:
  (a) **estática** (AST): prohibidas las importaciones `wave`, `soundfile`, `scipy.io.wavfile`,
  `pickle`, `shelve`, `audioread`, y las llamadas `numpy.save/savez/tofile/memmap`, `open` en modo
  `w/a/x/+` fuera del único exportador permitido de H2.13, y el registro de arrays en logs;
  (b) **dinámica**: `sys.addaudithook` registra los eventos `open` con escritura, `os.rename`,
  `os.remove`, `shutil.*` y `socket.connect` a destinos que no sean `127.0.0.1` durante una sesión
  completa de 120 s con `FakeSource`, página incluida; además se comparan instantáneas del directorio
  temporal y de un `HOME` aislado antes y después;
  (c) **proceso**: `RLIMIT_CORE = 0` al arrancar (sin volcados de memoria), `wipe()` del búfer al
  parar y al recibir SIGINT/SIGTERM.
- **Requisitos:** REQ-PRIV-002, REQ-LEG-005, REQ-LEG-006, REQ-PRIV-003
- **Verificación:** `uv run pytest tests/live/test_no_disk.py -q`
- **Resultado esperado:** en verde; 0 aperturas en escritura durante la sesión (con `--export`
  desactivado); 0 ficheros nuevos en las instantáneas; `RLIMIT_CORE` = 0 comprobado.
- **Prueba negativa:** un módulo de prueba que escribe la ventana en un `.wav` (fixture inyectada
  solo en el test) hace **fallar** las capas (a) y (b); otro que hace `np.save` del búfer también;
  ambas fixtures se ejecutan en cada `pytest` para demostrar que la red atrapa el fallo.
- **Riesgo residual declarado:** la memoria del proceso puede paginarse a la swap del sistema; no se
  puede impedir desde Python sin privilegios. Se documenta; la swap de este Mac está cifrada
  (`sysctl vm.swapusage` → `encrypted`, comprobado el 2026-11-16, revisión P6).

### H2.P3 — Punto de entrada de sesión endurecido (condición de la revisión, BLOQUEANTE)
- **Qué:** un único punto de entrada de la sesión en directo con este orden: `disable_core_dumps()`
  → `WriteAudit(block=True)` → `stop_on_signals()` → `try/finally` con `engine.stop()`. Además,
  `scan_package` se amplía a los módulos de `acoustic_pilot` que importe la sesión.
- **Requisitos:** REQ-PRIV-002, REQ-LEG-005, REQ-LEG-006
- **Verificación:** test en subproceso que arranca la sesión con origen sintético, recibe SIGTERM y
  comprueba que el búfer se borra, que la salida es 143, que `RLIMIT_CORE` vale 0 y que no hay
  eventos de auditoría.
- **Prueba negativa:** con el orden alterado (gancho después de abrir la captura) o con un módulo
  de `acoustic_pilot` que escriba a disco, el test falla.
- **Bloquea:** la primera captura real con el micrófono (H2.14 y cualquier prueba manual).

### H2.P4 — DPIA y registro de actividades (condición de la revisión, BLOQUEANTE)
- **Qué:** actualizar la DPIA (`docs/dpia/`) y el registro de actividades de tratamiento con el
  micrófono en una vivienda, la ausencia de conservación, la puerta de voz, el aviso a los
  convivientes y los riesgos residuales del ADR 0017. Se adelanta parte de H2.15.
- **Requisitos:** REQ-PRIV-006 (RGPD art. 35)
- **Verificación:** revisión `privacy-reviewer` sin hallazgos abiertos; `make check` en verde.
- **Prueba negativa:** sin la DPIA actualizada, la primera captura real no se hace (STOP).
- **Bloquea:** la primera captura real con el micrófono.

### H2.P5 — Borrado de la ventana descartada por voz (condición de la revisión, BLOQUEANTE)
- **Qué:** en H2.9, al descartar una ventana con voz, además de borrar su región del búfer
  (`zero_window`), se pone a cero la copia entregada al consumidor (`window.samples.fill(0)`).
- **Requisitos:** REQ-LEG-005, REQ-PRIV-010
- **Verificación:** `uv run pytest tests/live/test_speech_gate_live.py -q`; la ventana descartada
  y su región del búfer quedan a cero.
- **Prueba negativa:** si se omite el `fill(0)`, el test que inspecciona la copia falla.
- **Bloquea:** la primera captura real con el micrófono.

### H2.9 — Puerta de voz en directo
- **Qué:** con la salida de 521 clases de YAMNet de cada ventana, si la puntuación máxima de las
  clases de voz (índices exportados en el artefacto) ≥ 0,30 (`SPEECH_EXCLUSION_THRESHOLD`), la
  ventana se descarta **antes** del clasificador de dron, se pone a cero su región del búfer y el
  estado muestra «VOZ: ventana descartada», sin puntuación de dron ni otro dato.
- **Requisitos:** REQ-LEG-005, REQ-PRIV-010, REQ-PRIV-003
- **Verificación:** `uv run pytest tests/live/test_speech_gate_live.py -q`
- **Resultado esperado:** en verde; con salidas de YAMNet simuladas, el 100 % de las ventanas con voz
  ≥ 0,30 se descartan y no aparecen en la página, el log ni el resumen; las demás siguen el flujo.
- **Prueba negativa:** una ventana con voz 0,31 y dron 0,99 **no** produce alerta ni puntuación
  visible; cambiar el umbral fuera del artefacto (constante local) hace fallar el test de coherencia.

### H2.10 — Inferencia y rasgos en directo
- **Qué:** `live/pipeline.py`: ventana → H2.1 → YAMNet ONNX (embedding + clases) → H2.9 → H2.4 →
  regresión → Platt → probabilidad. Un único hilo de inferencia; la captura no se bloquea.
- **Requisitos:** REQ-FUN-027, REQ-NFR-015
- **Verificación:** `uv run pytest tests/live/test_pipeline.py -q && uv run python -m acoustic_pilot.live.bench --model <ruta> --seconds 60`
- **Resultado esperado:** los **vectores dorados** del artefacto se reproducen en el Mac con error
  ≤ 1e-4 (prueba de que la normalización y los rasgos son los mismos que en Colab); latencia por
  ventana p50/p95 medida e impresa (objetivo p95 ≤ 250 ms; NO VERIFICADO hasta medir), CPU media
  ≤ 60 % de un núcleo y memoria residente ≤ 500 MB.
- **Prueba negativa:** alterar un parámetro de normalización o el orden de los rasgos rompe los
  vectores dorados y el test falla; un artefacto con otro hash de ONNX no arranca (H2.6).

### H2.11 — Lógica de alerta con persistencia e histéresis
- **Qué:** `live/alert.py`, máquina de estados pura (sin E/S): ESCUCHANDO → POSIBLE → ALERTA →
  ESCUCHANDO, más VOZ y DEGRADADO (sin entrada > 2 s, desbordes, saturación > 1 % de muestras).
  Propuesta inicial (se fija con los datos de validación de Colab y queda en el artefacto, no en el
  código): ALERTA si ≥ 3 de las últimas 5 ventanas superan `θ_on` (≈ 2,4 s de persistencia); fin si
  4 ventanas seguidas quedan por debajo de `θ_off < θ_on`; periodo refractario de 5 s entre alertas;
  las ventanas VOZ no cuentan ni a favor ni en contra.
- **Requisitos:** REQ-FUN-027
- **Verificación:** `uv run pytest tests/live/test_alert.py -q`
- **Resultado esperado:** en verde, incluidas propiedades con secuencias aleatorias (semilla fija):
  un pico aislado nunca alerta; 3 de 5 sí; una señal que oscila alrededor de `θ_on` produce como
  máximo una transición por periodo refractario; DEGRADADO se activa a los 2 s sin entrada.
- **Prueba negativa:** `θ_off ≥ θ_on` o `k > n` en la configuración → rechazo al cargar; una secuencia
  de ventanas VOZ con dron alto no produce ALERTA.

### H2.12 — Página local de alertas
- **Qué:** `live/server.py` con `http.server.ThreadingHTTPServer` de la biblioteca estándar, enlazado
  solo a `127.0.0.1`; `/` sirve una página estática sin recursos externos; `/events` con
  Server-Sent Events (estado, probabilidad redondeada a 2 decimales, hora, latencia, contadores);
  botones del operador para etiquetar el tramo («reproduzco dron», «ruido de casa», «silencio»,
  «fin»), protegidos por un token por sesión. Rótulo fijo «Reproducción en sala, no vuelo real».
  Cabeceras: CSP restrictiva, `X-Content-Type-Options`, sin caché.
- **Requisitos:** REQ-LEG-005, REQ-PRIV-010, REQ-PRIV-003
- **Verificación:** `uv run pytest tests/live/test_server.py -q` y comprobación manual con
  `webapp-testing` (captura de pantalla de la página en ALERTA con `FakeSource`).
- **Resultado esperado:** en verde; el esquema de cada evento solo tiene escalares (ningún array);
  la página funciona sin red; la captura queda en la evidencia.
- **Prueba negativa:** arrancar con `--host 0.0.0.0` o cualquier dirección no local → error y salida
  ≠ 0; petición con cabecera `Host` distinta de `127.0.0.1`/`localhost` → 403; POST de etiqueta sin
  token → 403.

### H2.13 — Ejecución, resumen de sesión y métricas por script
- **Qué:** `uv run python -m acoustic_pilot.live --model <ruta> [--export resumen.json]`. Solo con
  `--export` (decisión D-5) se escribe al terminar un JSON con, por ventana, hora relativa,
  probabilidad, estado y etiqueta del operador; y por sesión, latencias y contadores. Nada de muestras
  ni embeddings. `live_metrics.py` calcula desde ese JSON las métricas de la sección 4.1 con IC 95 %
  (Wilson para proporciones, Poisson exacto para alarmas por hora); `live_metrics_check.py`, escrito
  aparte y sin importar el anterior ni `acoustic_pilot`, las recalcula.
- **Requisitos:** REQ-PRIV-010, REQ-PRIV-003, REQ-LEG-005
- **Verificación:** `uv run pytest tests/live/test_export.py tests/live/test_live_metrics.py -q`
- **Resultado esperado:** en verde; las dos implementaciones coinciden en todas las cifras de una
  sesión sintética; el resumen tiene ≤ 1 valor numérico de señal por ventana de 0,48 s.
- **Prueba negativa:** un resumen con un campo fuera del esquema, una lista de floats dentro de un
  registro o una ruta de exportación fuera del directorio indicado → rechazo sin escribir nada.

### H2.14 — Protocolo de prueba en sala con el usuario (demostración)
- **Qué:** sesión guiada (sección 4.1), con el modelo de la iteración 5 (línea base, exportado con
  el mismo formato) y el de la iteración 6, en orden aleatorio por bloque. Sin grabar nada.
- **Requisitos:** REQ-FUN-057 (antecedente), REQ-LEG-005, REQ-PRIV-002
- **Verificación:** `uv run python live_metrics.py docs/evidence/hito-2/resumen-*.json && uv run python live_metrics_check.py docs/evidence/hito-2/resumen-*.json`
- **Resultado esperado:** tabla de la sección 4.1 para ambos modelos con IC 95 %, fecha y commit;
  `ls` del directorio de trabajo sin ficheros de sonido nuevos (`find ~ -newer <marca> -name '*.wav' -o -name '*.flac' ...` → 0).
- **Prueba negativa:** con el micrófono desconectado o el permiso denegado, la página muestra
  DEGRADADO en ≤ 2 s y no se genera ninguna alerta.

### H2.15 — Privacidad, revisiones y cierre del hito
- **Qué:** nota del tratamiento del hito en `docs/dpia/` (micrófono en vivienda, sin conservación,
  puerta de voz, informar a convivientes); revisiones sin contexto `independent-reviewer`,
  `privacy-reviewer`, `legal-guardrail-reviewer`, `security-reviewer` (página local) y
  `ml-eval-reviewer` (LOSO e interpretación de las cifras); `make check` y tests del piloto.
- **Requisitos:** REQ-PRIV-006, REQ-LEG-017
- **Verificación:** `make check && (cd pilots/acoustic && uv run pytest -q && uv run ruff check . && uv run ruff format --check .)`
- **Resultado esperado:** todo en verde; hallazgos de los revisores corregidos o justificados por
  escrito; `docs/evidence/hito-2/CIERRE.md` con evidencias y `SHA256SUMS`.
- **Prueba negativa:** un hallazgo de privacidad o legal sin resolver bloquea el cierre (STOP).

### 4.1 Protocolo de prueba con el usuario y métricas
**Montaje:** micrófono integrado del Mac; los vídeos se reproducen preferiblemente desde **otro**
dispositivo (móvil, tele, altavoz) a 1–3 m para no acoplar altavoz y micrófono del mismo equipo; se
anotan distancia aproximada, volumen y dispositivo. Se informa antes a quien esté en casa; el
micrófono solo se abre durante la sesión (indicador naranja de macOS visible).

**Material:**
- Positivos: ≥ 20 tramos de ≥ 20 s de ≥ 5 vídeos distintos (multirrotor pequeño, mediano, FPV si lo
  hay). Se anotan solo título, URL y tramo; **no se descarga nada**. Si se aprueba D-3, además clips
  con licencia verificada (Svanström CC0) tras `/dataset-intake`.
- Negativos de casa: ≥ 60 min acumulados de ruido real (cocina, campana, lavadora, ventilador,
  televisión sin drones, música, calle por la ventana, aspiradora), etiquetados con los botones.
- Negativos difíciles reproducidos: helicóptero, moto, cortacésped, avioneta, insectos, secador.
- Silencio: 5 min.

**Métricas que se pueden medir (generadas por script, con IC 95 %):**
| Métrica | Definición |
|---|---|
| Detección por tramo | Tramos de dron con ALERTA en ≤ 10 s desde «reproduzco dron» / tramos (Wilson) |
| Tiempo hasta alerta | p50/p95 desde la pulsación del botón (incluye el retraso humano: cota superior) |
| Recall por ventana | Ventanas ≥ `θ_on` dentro de tramos de dron (descontando VOZ) |
| Alarmas falsas por hora | ALERTAS en tramos de ruido de casa / horas de exposición (Poisson exacto; con 1 h y 0 alarmas, cota superior ≈ 3,7/h) |
| Falsas alarmas por tipo de negativo | Por categoría anotada |
| Ventanas descartadas por voz | Proporción por tipo de tramo |
| Latencia de inferencia, CPU y memoria | p50/p95 por ventana; media de CPU; memoria residente máxima |
| Diferencia frente a la línea base | Iteración 6 menos iteración 5 en el mismo protocolo |
| Escrituras de sonido a disco | 0 (H2.8 y comprobación de ficheros nuevos tras la sesión) |

**NO VERIFICADO (no se puede medir en este hito y se dirá así en la evidencia):** detección de un
vuelo real; alcance y distancia; efecto Doppler, viento y directividad; comportamiento en exterior o
en Ceuta; alarmas falsas por hora en un emplazamiento; generalización a modelos de dron que no
aparezcan en los vídeos; si el sonido de cada vídeo es una toma real o está editado, con música o
sintetizado; si algún vídeo coincide con material de las fuentes de entrenamiento (fuga posible);
la fidelidad del altavoz (graves por debajo de ~150 Hz se pierden); la paginación de memoria a la
swap; la equivalencia con el Android de FASE 5. Con n ≈ 20 tramos el IC de la detección por tramo
será ancho (± ~20 puntos): es una demo, no una métrica de producto.

## 5. Riesgos del hito
| ID | Riesgo | Mitigación |
|---|---|---|
| H2-R1 | Voces de la casa captadas por el micrófono | Puerta de voz (H2.9) con descarte y borrado de la región del búfer; sin almacenamiento; aviso a convivientes; micrófono solo en sesión; revisión `privacy-reviewer`; nota en DPIA |
| H2-R2 | Alguna muestra acaba en disco por error (log, depuración, volcado) | H2.8 en tres capas con pruebas negativas que se ejecutan siempre; `RLIMIT_CORE = 0`; sin modo de depuración que guarde ventanas |
| H2-R3 | Swap del sistema con páginas del búfer | Búfer pequeño (256 kB) y borrado al parar; riesgo residual documentado; comprobar cifrado de swap |
| H2-R4 | El atajo de dominio persiste y la demo falla | H2.1–H2.4 y LOSO como métrica; línea base en el mismo protocolo; criterio de avance D-6; comunicar el fallo tal cual |
| H2-R5 | La demo «funciona» por el volumen o por memorizar vídeos y se sobrevende | Normalización de sonoridad; negativos fuertes al mismo volumen; rótulo «reproducción en sala, no vuelo real»; lista NO VERIFICADO |
| H2-R6 | Derechos de los vídeos de YouTube | Solo reproducción y escucha por el aire, sin descarga ni captura digital, sin conservación, sin entrenamiento; análisis jurídico de la reproducción transitoria NO VERIFICADO |
| H2-R7 | Sin rueda de `onnxruntime` para Mac Intel / disco insuficiente | T0.1 antes de nada; respaldo TensorFlow 2.16.2 con nueva aprobación; presupuesto de disco ≤ 300 MB |
| H2-R8 | Página local expuesta a la red o a otra web del navegador | Solo `127.0.0.1`, comprobación de `Host`, token, CSP, sin CORS |
| H2-R9 | Colab cambia versiones (TF 2.21 frente a 2.16) y el ONNX no es equivalente | Comprobación de equivalencia ≤ 1e-4 y vectores dorados en el Mac |
| H2-R10 | Cifras de la iteración 5 transcritas a mano | La iteración 6 exporta CSV con hash y recálculo independiente; la línea base se reejecuta con el mismo cuaderno |
| H2-R11 | Arrastre de alcance hacia el producto | Todo en `pilots/acoustic/`; test que falla si `src/` importa `pilots` |

## 6. Estimación
Unos 7–10 días de trabajo efectivo: T0.1 0,5; H2.1–H2.4 2–3; H2.5 1,5 (más ejecuciones en Colab de
~1–2 h cada una, con riesgo de desconexión); H2.6–H2.13 3–4; H2.14 0,5–1 (sesión de ~2 h con el
usuario); H2.15 1. Coste **0 €**: Colab gratuito en CPU (ADR 0016), Mac del usuario, vídeos públicos
solo reproducidos, dependencias libres.

## 7. Decisiones que necesita el usuario
- **D-1 (P0):** aprobar este plan y el ADR 0017 (micrófono del Mac en directo, solo memoria;
  `sounddevice` y `onnxruntime` en el Mac; `tf2onnx` en Colab). Recomendado: sí.
- **D-2:** base de código: fusionar antes la PR #12 (iteración 5) en `main` (recomendado) o
  implementar sobre la rama `piloto/iteracion-5`.
- **D-3:** material reproducido: solo vídeos de YouTube (demo informal) o, además, clips con
  licencia verificada (Svanström CC0, ~157 MB, previo `/dataset-intake` y su aprobación) para cifras
  con verdad terreno, como piden SPEC §3.1 y REQ-FUN-057. Recomendado: ambos.
- **D-4:** puerta de voz: descartar ventanas con voz aunque se pierda una detección si alguien habla
  a la vez (recomendado) o solo ocultar la puntuación.
- **D-5:** exportar el resumen de sesión (probabilidades, estados y etiquetas; sin sonido ni
  embeddings) a `docs/evidence/hito-2/` para medir. Sin exportación no hay métricas en sala.
  Recomendado: sí.
- **D-6:** criterio de avance de la iteración 6 (propuesta: PR-AUC LOSO ARIS ≥ 0,85, recall LOSO
  ARIS ≥ 0,50 con FPR LOSO FSD50K ≤ 0,10) y qué hacer si no se cumple (seguir con la demo rotulada
  o parar e iterar).
- **D-7:** calibración de sala opcional: 5 min de ruido de su casa, solo en memoria, para ajustar el
  umbral antes de la sesión de medida (nunca con la misma sesión que se evalúa). Recomendado: probarla
  como variante separada.
- **D-8:** `yamnet.onnx` (~15 MB, NO VERIFICADO) y `modelo_hito2.json` fuera de Git con hashes
  fijados en el repo (recomendado) o dentro de Git.
- **D-9:** franja horaria y aviso a convivientes para la sesión de H2.14.

# Ejecución en Colab del piloto YAMNet — 2026-11-11 23:38

- Cuaderno: `pilots/acoustic/Atalaya_YAMNet_Colab.ipynb` (commit 365bf29, SHA-256 3fc5b20c15672580…), subido a Colab (CPU gratuita, sin Drive) y ejecutado con «Ejecutar todas».
- Puertas abiertas por autorización explícita del usuario (DECISIONES-USUARIO.md, 2026-11-11), solo prueba técnica.
- Entorno: TensorFlow 2.21.0 de Colab; tensorflow-hub 0.16.1; YAMNet `https://tfhub.dev/google/yamnet/1`.

## Resultados (copiados de las salidas del cuaderno)
- Licencia CC0 original verificada por SHA-256; 24 WAV descargados y verificados (42,3 MB).
- Revisión de voz automática (máx. puntuación YAMNet de Speech/Conversation/Narration/Child speech):
  BACKGROUND_006 **0,748** (evento principal «Scrape»), BACKGROUND_015 0,408, BACKGROUND_020 0,301,
  DRONE_022 0,280, BACKGROUND_022 0,268; el resto < 0,17. → **Posible voz en BACKGROUND_006** (pendiente de escucha humana).
- Partición por grupos: train/val/test = 14/5/5 clips, grupos 14/5/5 (provisionales, uno por clip).
- Umbral elegido en validación: 0,7976.
- Test: tn=4, fp=0, fn=0, tp=1 → precision 1,000, recall 1,000, PR-AUC 1,000; IC 95 % por grupo
  NO DISPONIBLE (5 grupos < 10). Falsas alarmas por hora: NO VERIFICADA (10 s < 24 h).

## Lectura
Prueba técnica: demuestra que el flujo descarga→verificación→YAMNet→partición por grupos→umbral en
validación→métricas funciona en Colab. **No** mide precisión: un solo positivo en test. Contaminación
entre particiones no descartada. Nada de esto entra en el producto.

# Iteración 2 — 2026-11-11 23:45 (commit 5c35f3f, 89 WAV, puerta automática de voz ≥ 0,30)
Nota: esta ejecución es anterior a la revisión humana de BACKGROUND_006 (commit 4675684), así que
ese clip quedó excluido por la puerta automática.
- Partición por grupos: train/val/test = 48/16/16 clips (grupos 48/16/16, provisionales).
- Comparación en test (misma partición; cada modelo con su umbral elegido en validación):

| Modelo | Umbral (val.) | tn | fp | fn | tp | Precision [IC95 grupos] | Recall [IC95] | PR-AUC [IC95] | FA/h |
|---|---|---|---|---|---|---|---|---|---|
| YAMNet + reg. logística | 0,7777 | 10 | 0 | 2 | 4 | 1,000 [1,000; 1,000] | 0,667 [0,250; 1,000] | 1,000 [1,000; 1,000] | NO VERIFICADA |
| MFCC(40) + reg. logística | 0,3667 | 8 | 2 | 0 | 6 | 0,75 [0,400; 1,000] | 1,000 [1,000; 1,000] | 0,958 [0,792; 1,000] | NO VERIFICADA |

Lectura: YAMNet ordena mejor (PR-AUC 1,0), pero su umbral elegido con 16 clips de validación es
conservador y pierde 2 drones; MFCC no pierde drones a costa de 2 falsas alarmas. Prueba técnica con
16 clips de test y contaminación entre particiones no descartada: no son métricas de campo.
Siguiente paso: más datos con licencia compatible, sobre todo negativos y confusores españoles.

# Iteración 2 bis — repetición (2026-11-12 10:19, mismo cuaderno 5c35f3f)
Resultado idéntico a la iteración 2 (umbral 0,7777; tn10 fp0 fn2 tp4): la ejecución es reproducible
con la misma semilla y los mismos datos.

# Iteración 3 — 2026-11-12 10:22 (cuaderno 9f0bd378…, commit 4675684: revisión humana de BACKGROUND_006)
- Reincorporado por revisión humana: BACKGROUND_006 (YAMNet 0,748; el usuario lo escuchó: crujido de madera).
- Excluidos por la puerta automática de voz (≥ 0,30): 8 → BACKGROUND_003 (0,800), 010 (0,857),
  015 (0,408), 020 (0,301), 026 (0,722), 029 (0,703), DRONE_006 (0,539), DRONE_023 (0,449).
  **Pendiente de escucha humana** antes de cualquier uso fuera de esta prueba.
- Quedan 81 clips (HELICOPTER 30, DRONE 28, BACKGROUND 23); partición 49/16/16 (grupos provisionales).

| Modelo | Umbral (val.) | tn | fp | fn | tp | Precision [IC95] | Recall [IC95] | PR-AUC [IC95] | FA/h |
|---|---|---|---|---|---|---|---|---|---|
| YAMNet + reg. logística | 0,9287 | 9 | 0 | 3 | 4 | 1,000 [1,000; 1,000] | 0,571 [0,200; 1,000] | 0,914 [0,690; 1,000] | NO VERIFICADA |
| MFCC(40) + reg. logística | 0,8893 | 9 | 0 | 5 | 2 | 1,000 [1,000; 1,000] | 0,286 [0,000; 0,667] | 0,938 [0,750; 1,000] | NO VERIFICADA |

Lectura: añadir un solo clip cambia la partición y los resultados varían mucho (recall de YAMNet
0,667 → 0,571; MFCC 1,000 → 0,286): con ~80 clips el modelo es inestable y los umbrales elegidos
en 16 clips de validación son demasiado altos. Conclusión técnica: hacen falta muchos más datos
(positivos y, sobre todo, negativos), validación cruzada por grupos y elección de umbral orientada
a recall. Prueba técnica; nada entra en el producto.

# Iteración 4 — preparada el 2026-11-12 (más datos; cuaderno sin ejecutar en Colab)
Encargo de la iteración 4 (estabilizar el modelo con más datos), dentro de la misma prueba técnica
aislada (ADR 0016); nada entra en el producto. **Resultados en Colab: NO VERIFICADOS** hasta ejecutar
el cuaderno; esta sección se completará con las cifras recalculadas desde `predicciones.csv`.
- Fuentes nuevas con licencia verificada en la fuente original el 2026-11-12 (data cards
  `docs/data-cards/fsd50k-subset.md` e `itu-aris.md`): ESC-10 (318 clips admitidos, CC BY 3.0 y
  CC0/CC BY por clip), FSD50K subconjunto de confusores (solo CC0/CC BY por clip, sin etiquetas
  humanas ni de música, sin menciones a drones, sin clips que ya estén en ESC-10) e ITU ARIS Lab
  (CC BY 4.0, 5.491 segmentos con `groups.json` y split `interval_disjoint`).
- Prohibidas y no descargadas: DADS, Al-Emadi, UrbanSound8K, ESC-50 fuera de ESC-10, Sonniss y
  AeroSonicDB.
- Evaluación: partición única (ITU ARIS con el split de los autores), validación cruzada por grupos
  (5 folds), umbral más alto con recall ≥ 0,90 en validación, métricas por fuente y TOTAL con IC 95 %
  por grupos, YAMNet frente a MFCC y exportación de `predicciones.csv` con SHA-256 para
  `pilots/acoustic/recompute_metrics.py` (cierra el pendiente de ADR 0016 cuando se ejecute).
- Cuaderno generado: `pilots/acoustic/Atalaya_YAMNet_Colab.ipynb`, SHA-256
  `ad8708c9d03f90825e1ae97752583480300f769f752b7fba44804ec671fe6596` (regeneración reproducible
  comprobada por test). Descarga prevista ≈ 1,24 GB: Svanström 157 MB, ESC-10 140 MB, FSD50K 769 MB
  comprimidos (833 clips), ITU ARIS 169 MB.
- Ensayo en seco local de las celdas de evaluación con rasgos **sintéticos** (sin TensorFlow ni
  audio): partición, CV, umbral por recall, tablas por fuente, CSV y recálculo independiente
  coinciden. No es un resultado del modelo.

# Iteración 5 — preparada el 2026-11-12 (tratamiento de datos avanzado; cuaderno sin ejecutar en Colab)
Misma prueba técnica aislada (ADR 0016), mismas fuentes con licencia verificada; prohibidas y no
descargadas: DADS, Al-Emadi, UrbanSound8K, ESC-50 fuera de ESC-10, Sonniss y AeroSonicDB. Sin
dependencias nuevas (numpy, SciPy y scikit-learn, BSD-3; cleanlab descartado por AGPL: lo necesario
se implementa en `acoustic_pilot`). **Resultados en Colab: NO VERIFICADOS** hasta ejecutar el cuaderno.

Técnicas (código en `pilots/acoustic/acoustic_pilot/`, probado en `pilots/acoustic/tests/` e
incrustado tal cual por `build_colab.py`):
1. `data_quality`: formato normalizado (mono, 16 kHz, float32, `resample_poly`); clip **silencioso**
   si el RMS < −60 dBFS en todos los canales; **saturado** si > 1 % de muestras con |x| ≥ 0,999 en
   algún canal original; **corrupto** si es ilegible, no finito o dura < 0,5 s. Sonoridad (RMS, LUFS
   aproximado BS.1770 sin compuertas, pico, factor de cresta) **solo como característica**.
   Duplicados exactos por SHA-256 del PCM normalizado; casi duplicados por coseno de la media de
   embeddings YAMNet **≥ 0,995** (YAMNet da embeddings no negativos; clips distintos de una misma
   escena quedan en ~0,95–0,98) solo entre grupos distintos; el componente conserva el grupo que
   más aporta. Informe `descartes.csv` con SHA-256.
2. `leakage`: `StratifiedGroupKFold` (5 folds) por grupo y leave-one-source-out; en cada partición
   se recalculan los casi duplicados entre particiones y debe salir vacío (fallo cerrado).
   La partición de autores de ITU ARIS ya no se usa; sus grupos (intervalo/bloque) sí.
3. `balance`: pesos por clase y por fuente (cada clase suma N/2; dentro de cada clase, cada fuente
   igual; las mezclas sintéticas cuentan como una fuente más) y muestreo balanceado.
4. `augment`: 1.500 mezclas dron + fondo negativo a SNR nominal −10…+20 dB, ganancia −6…+6 dB y
   desplazamiento circular, `synthetic=true`; en cada fold solo entran si dron **y** fondo están en
   entrenamiento; nunca se puntúan. **No cuentan como rendimiento real.**
5. `windows`: regresión logística por ventana YAMNet (≤ 8 ventanas por clip, etiqueta débil) con
   agregación media, máximo, top-3, máximo suavizado (3 ventanas) y atención ligera (softmax,
   T = 0,1), frente a la media de embeddings por clip.
6. `calibration`: Platt e isotónica ajustadas en validación; ECE (15 bins), Brier, fiabilidad, DET
   y PR; umbral = el más alto con recall ≥ 0,90 en validación (Platt); FA/h sobre concatenaciones
   de negativos de test con refractario de 5 s: **ESTIMACIÓN, NO VERIFICADA como métrica de campo**.
7. `hard_negatives`: segunda ronda que multiplica por 3 el peso del 10 % de negativos de
   entrenamiento con mayor puntuación (sesgo optimista: puntuaciones del propio entrenamiento) y
   falsas alarmas por tipo de negativo (motos, barcos, aviones, helicópteros, insectos, viento…)
   con la lista «qué grabar primero en Ceuta».
8. `experiment` y `predictions`: registro `modelo_piloto.json` con hash propio (semillas,
   configuración, inventario de datos, descartes, plan de mezclas, versiones, hash del código del
   cuaderno y de `predicciones.csv`); CSV ampliado (tipo, puntuaciones cruda/Platt/isotónica) con
   precisión de ida y vuelta; `recompute_metrics.py --record` recalcula confusión, PR-AUC, ECE,
   Brier y falsas alarmas por tipo sin importar `acoustic_pilot` ni numpy.
9. `checkpoints` (tras la desconexión de la iteración 4 en Colab durante YAMNet): descargas en 8
   hilos con límite global de 120 peticiones/minuto a Zenodo y reintentos, progreso por fuente,
   reutilización de ficheros solo si su hash coincide, escritura atómica y YAMNet/mezclas por lotes
   (256/250) guardados en `/content/atalaya_piloto/checkpoints` con hash de entrada. Sobrevive a un
   reinicio del kernel; **no** a que Colab recicle la máquina (sin Drive por ADR 0016).

Verificación local:
- `cd pilots/acoustic && uv run pytest -q` → 181 tests en verde; `ruff check` y `ruff format --check` limpios.
- Ensayo en seco con rasgos **sintéticos** (sin TensorFlow ni audio) de las celdas desde la puerta de
  voz hasta la exportación, más el bucle de YAMNet por lotes con el modelo sustituido: se ejecutan
  sin error, la reanudación reutiliza los lotes y solo recalcula el dañado, y el resumen del cuaderno
  coincide con `recompute_metrics.py` en las 90 celdas modelo/esquema/fuente (confusión, PR-AUC, ECE).
  Encontró dos errores ya corregidos con test de regresión: el informe de voz trataba como tuplas
  los dicts de `apply_speech_gate` (y `float(None)` en puntuaciones no válidas), y 9 decimales
  convertían en empates probabilidades calibradas saturadas. No es un resultado del modelo.
- Cuaderno: `pilots/acoustic/Atalaya_YAMNet_Colab.ipynb`, SHA-256
  `96bc96d155947391daa97bad32f2c7168dbbea5f98bf99a48a593b38e0b0003a`; hash del código incrustado
  `00046807668aa0581878d2593b36471e22091ffae5b4d34379072c5c41bad40c`; nbformat 4.5 válido;
  regeneración reproducible comprobada por test.

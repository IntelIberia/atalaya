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

# Iteración 5 — 2026-11-12 ~23:00 (commit 98455be; cuaderno 1aD06iV03c22v2yY8YMQJUuqtDZFVjN0a)
Ejecución completa («Ejecutar todas», 39 celdas, sin errores) tras la corrección de mezclas sin
energía. Fuentes descargadas y verificadas por hash en Colab: Svanström 89 WAV (157,0 MB), ESC-10
318 clips (140,3 MB, CC BY 3.0), FSD50K 833 clips (769 MB; 410 CC0 + 423 CC BY 3.0 por clip; 502
autores = grupos), ITU ARIS 5405 segmentos tras la puerta de voz. Predicciones fuera de fold: 115 848 filas.

Cifras **transcritas a mano de capturas de pantalla** de las tablas del cuaderno (el navegador se
desconectó antes de exportarlas): son orientativas; la fuente de verdad es una reejecución del commit.

**Validación cruzada por grupos (StratifiedGroupKFold), fuentes vistas en entrenamiento:**

| Modelo | Fuente | n | pos. | tn | fp | fn | tp | Precisión [IC95] | Recall [IC95] | FPR |
|---|---|---|---|---|---|---|---|---|---|---|
| YAMNet media | ITU ARIS | 5405 | 4485 | 859 | 61 | 400 | 4085 | 0,985 [0,954; 0,999] | 0,911 [0,873; 0,942] | 0,066 |
| YAMNet media | ESC-10 | 269 | 0 | 268 | 1 | 0 | 0 | — | — | 0,004 |
| YAMNet media | FSD50K | 682 | 0 | 671 | 11 | 0 | 0 | — | — | 0,016 |
| YAMNet media | Svanström | 80 | 28 | 52 | 0 | 6 | 22 | 1,000 | 0,786 [0,613; 0,932] | 0,000 |
| YAMNet media + aumento | ITU ARIS | 5405 | 4485 | 842 | 78 | 390 | 4095 | 0,981 | 0,913 [0,883; 0,942] | 0,085 |
| YAMNet media + aumento | FSD50K | 682 | 0 | 657 | 25 | 0 | 0 | — | — | 0,037 |
| YAMNet ventanas + aumento · max suavizado | Svanström | 80 | 28 | — | 7 | 1 | 27 | — | 0,794 [0,657; 0,925] | — (PR-AUC 0,964) |

**Leave-one-source-out (fuente nunca vista en entrenamiento):**

| Modelo | Fuente no vista | Recall [IC95] | FPR [IC95] | PR-AUC |
|---|---|---|---|---|
| MFCC + sonoridad | ITU ARIS | 0,168 [0,081; 0,249] | 0,422 [0,328; 0,521] | 0,737 |
| MFCC + sonoridad | Svanström | 0,000 | 0,000 | 0,449 |
| MFCC + sonoridad | ESC-10 / FSD50K | — | 0,112 / 0,082 | — |
| YAMNet media | ITU ARIS | 0,002 [0,000; 0,005] | 0,001 | 0,740 |
| YAMNet media | Svanström | 0,000 | 0,000 | 0,789 |
| YAMNet media | ESC-10 / FSD50K | — | 0,004 / 0,104 | — |
| YAMNet media + aumento + negativos difíciles | ITU ARIS | 0,010 [0,001; 0,020] | 0,024 | 0,751 |
| YAMNet ventanas + aumento · atención | ITU ARIS / Svanström | 0,008 / 0,179 [0,044; 0,338] | 0,003 / 0,019 | 0,793 / 0,717 |
| YAMNet ventanas + aumento · atención | FSD50K | — | 0,400 [0,360; 0,437] | — |
| YAMNet ventanas + aumento · max | Svanström / FSD50K | 0,286 [0,115; 0,467] / — | 0,058 / 0,521 | 0,713 / — |
| YAMNet ventanas + aumento · media | ITU ARIS | 0,008 [0,001; 0,015] | 0,009 | 0,783 |

**Lectura técnica.** Dentro de las fuentes vistas, YAMNet separa bien (ARIS recall 0,91 con precisión
0,985; FPR 0,4–1,6 % en ESC-10/FSD50K). Ante una fuente **no vista** el sistema no generaliza: recall
≈ 0 en ARIS con el umbral calibrado en las demás y hasta un 52 % de falsas alarmas en FSD50K. El
PR-AUC (0,71–0,79) muestra que el orden de puntuaciones conserva algo de señal, pero el umbral y la
calibración no se trasladan entre fuentes: el modelo aprende canal/micrófono/entorno de cada
dataset (atajo de dominio). Más clips de las mismas fuentes no lo resuelven.

**Siguiente iteración propuesta (pendiente de plan):** grabaciones propias en condiciones reales
(reproducción con licencia captada por Android/Mac, hito 2) y ruido de entorno español; normalización
de canal (remuestreo, banda, PCEN/sonoridad); aumento de canal (EQ y respuesta de micrófono
aleatorias, reverberación, códec de móvil); mezclas cruzadas dron/fondo entre fuentes; rasgo
armónico de hélices junto a YAMNet; adaptación del umbral con pocos clips por emplazamiento; y
LOSO como métrica principal. Prueba técnica; contaminación entre particiones no descartada; nada
entra en el producto.

## Iteración 5 — cifras exactas recalculadas (2026-11-16)
Las salidas del cuaderno se descargaron de Colab (fuera de Git): `predicciones.csv` SHA-256 `8ec5d2281682dd02cb11c3a0d9a74feb59df508325afdaa99a715d39a7c67407` (coincide con `predicciones_csv_sha256` de `modelo_piloto.json`, SHA-256 `61be895c3303f8d96e1264c96cf3816d40ac5b32b865bc76b54adce60001f3e1`), `descartes.csv` SHA-256 `67acce2c6fccb916a3a07b6d00e043440e227ab0fa4e8be2d022fac6ba24d9ea`.
Recalculadas con `uv run python recompute_metrics.py predicciones.csv --sha256 <hash>` (script independiente del cuaderno). **Sustituyen a las cifras transcritas de capturas de la sección anterior, que coinciden.** Umbral de cada fila: el elegido sin ver la partición evaluada.

| modelo | esquema | fuente | tn | fp | fn | tp | precision | recall | FPR | PR-AUC | ECE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MFCC+sonoridad | loso | TOTAL | 1449 | 474 | 3760 | 753 | 0.614 | 0.167 | 0.246 | 0.570 | 0.714 |
| MFCC+sonoridad | loso | aris | 532 | 388 | 3732 | 753 | 0.660 | 0.168 | 0.422 | 0.737 | 0.814 |
| MFCC+sonoridad | loso | esc10 | 239 | 30 | 0 | 0 | 0.000 | — | 0.112 | — | 0.258 |
| MFCC+sonoridad | loso | fsd50k | 626 | 56 | 0 | 0 | 0.000 | — | 0.082 | — | 0.243 |
| MFCC+sonoridad | loso | svanstrom | 52 | 0 | 28 | 0 | — | 0.000 | 0.000 | 0.449 | 0.346 |
| MFCC+sonoridad | sgkf5 | TOTAL | 1702 | 221 | 501 | 4012 | 0.948 | 0.889 | 0.115 | 0.979 | 0.020 |
| MFCC+sonoridad | sgkf5 | aris | 824 | 96 | 491 | 3994 | 0.977 | 0.891 | 0.104 | 0.993 | 0.045 |
| MFCC+sonoridad | sgkf5 | esc10 | 230 | 39 | 0 | 0 | 0.000 | — | 0.145 | — | 0.247 |
| MFCC+sonoridad | sgkf5 | fsd50k | 601 | 81 | 0 | 0 | 0.000 | — | 0.119 | — | 0.198 |
| MFCC+sonoridad | sgkf5 | svanstrom | 47 | 5 | 10 | 18 | 0.783 | 0.643 | 0.096 | 0.856 | 0.135 |
| YAMNet media | loso | TOTAL | 1850 | 73 | 4504 | 9 | 0.110 | 0.002 | 0.038 | 0.561 | 0.725 |
| YAMNet media | loso | aris | 919 | 1 | 4476 | 9 | 0.900 | 0.002 | 0.001 | 0.740 | 0.827 |
| YAMNet media | loso | esc10 | 268 | 1 | 0 | 0 | 0.000 | — | 0.004 | — | 0.044 |
| YAMNet media | loso | fsd50k | 611 | 71 | 0 | 0 | 0.000 | — | 0.104 | — | 0.287 |
| YAMNet media | loso | svanstrom | 52 | 0 | 28 | 0 | — | 0.000 | 0.000 | 0.789 | 0.337 |
| YAMNet media | sgkf5 | TOTAL | 1850 | 73 | 406 | 4107 | 0.983 | 0.910 | 0.038 | 0.980 | 0.013 |
| YAMNet media | sgkf5 | aris | 859 | 61 | 400 | 4085 | 0.985 | 0.911 | 0.066 | 0.982 | 0.017 |
| YAMNet media | sgkf5 | esc10 | 268 | 1 | 0 | 0 | 0.000 | — | 0.004 | — | 0.034 |
| YAMNet media | sgkf5 | fsd50k | 671 | 11 | 0 | 0 | 0.000 | — | 0.016 | — | 0.098 |
| YAMNet media | sgkf5 | svanstrom | 52 | 0 | 6 | 22 | 1.000 | 0.786 | 0.000 | 0.966 | 0.066 |
| YAMNet media + aumento | loso | TOTAL | 1811 | 112 | 4477 | 36 | 0.243 | 0.008 | 0.058 | 0.527 | 0.736 |
| YAMNet media + aumento | loso | aris | 909 | 11 | 4449 | 36 | 0.766 | 0.008 | 0.012 | 0.751 | 0.825 |
| YAMNet media + aumento | loso | esc10 | 269 | 0 | 0 | 0 | — | — | 0.000 | — | 0.078 |
| YAMNet media + aumento | loso | fsd50k | 581 | 101 | 0 | 0 | 0.000 | — | 0.148 | — | 0.375 |
| YAMNet media + aumento | loso | svanstrom | 52 | 0 | 28 | 0 | — | 0.000 | 0.000 | 0.657 | 0.328 |
| YAMNet media + aumento | sgkf5 | TOTAL | 1816 | 107 | 396 | 4117 | 0.975 | 0.912 | 0.056 | 0.978 | 0.018 |
| YAMNet media + aumento | sgkf5 | aris | 842 | 78 | 390 | 4095 | 0.981 | 0.913 | 0.085 | 0.982 | 0.029 |
| YAMNet media + aumento | sgkf5 | esc10 | 265 | 4 | 0 | 0 | 0.000 | — | 0.015 | — | 0.104 |
| YAMNet media + aumento | sgkf5 | fsd50k | 657 | 25 | 0 | 0 | 0.000 | — | 0.037 | — | 0.150 |
| YAMNet media + aumento | sgkf5 | svanstrom | 52 | 0 | 6 | 22 | 1.000 | 0.786 | 0.000 | 0.969 | 0.051 |
| YAMNet media + aumento + negativos difíciles | loso | TOTAL | 1779 | 144 | 4467 | 46 | 0.242 | 0.010 | 0.075 | 0.533 | 0.734 |
| YAMNet media + aumento + negativos difíciles | loso | aris | 898 | 22 | 4439 | 46 | 0.676 | 0.010 | 0.024 | 0.751 | 0.823 |
| YAMNet media + aumento + negativos difíciles | loso | esc10 | 268 | 1 | 0 | 0 | 0.000 | — | 0.004 | — | 0.084 |
| YAMNet media + aumento + negativos difíciles | loso | fsd50k | 561 | 121 | 0 | 0 | 0.000 | — | 0.177 | — | 0.401 |
| YAMNet media + aumento + negativos difíciles | loso | svanstrom | 52 | 0 | 28 | 0 | — | 0.000 | 0.000 | 0.622 | 0.316 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | TOTAL | 1814 | 109 | 405 | 4108 | 0.974 | 0.910 | 0.057 | 0.979 | 0.021 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | aris | 846 | 74 | 399 | 4086 | 0.982 | 0.911 | 0.080 | 0.983 | 0.030 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | esc10 | 263 | 6 | 0 | 0 | 0.000 | — | 0.022 | — | 0.112 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | fsd50k | 653 | 29 | 0 | 0 | 0.000 | — | 0.043 | — | 0.151 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | svanstrom | 52 | 0 | 6 | 22 | 1.000 | 0.786 | 0.000 | 0.971 | 0.064 |
| YAMNet ventanas + aumento · atencion | loso | TOTAL | 1630 | 293 | 4470 | 43 | 0.128 | 0.010 | 0.152 | 0.532 | 0.777 |
| YAMNet ventanas + aumento · atencion | loso | aris | 917 | 3 | 4447 | 38 | 0.927 | 0.008 | 0.003 | 0.793 | 0.825 |
| YAMNet ventanas + aumento · atencion | loso | esc10 | 253 | 16 | 0 | 0 | 0.000 | — | 0.059 | — | 0.276 |
| YAMNet ventanas + aumento · atencion | loso | fsd50k | 409 | 273 | 0 | 0 | 0.000 | — | 0.400 | — | 0.734 |
| YAMNet ventanas + aumento · atencion | loso | svanstrom | 51 | 1 | 23 | 5 | 0.833 | 0.179 | 0.019 | 0.717 | 0.189 |
| YAMNet ventanas + aumento · atencion | sgkf5 | TOTAL | 1644 | 279 | 428 | 4085 | 0.936 | 0.905 | 0.145 | 0.976 | 0.019 |
| YAMNet ventanas + aumento · atencion | sgkf5 | aris | 854 | 66 | 426 | 4059 | 0.984 | 0.905 | 0.072 | 0.990 | 0.062 |
| YAMNet ventanas + aumento · atencion | sgkf5 | esc10 | 240 | 29 | 0 | 0 | 0.000 | — | 0.108 | — | 0.216 |
| YAMNet ventanas + aumento · atencion | sgkf5 | fsd50k | 507 | 175 | 0 | 0 | 0.000 | — | 0.257 | — | 0.395 |
| YAMNet ventanas + aumento · atencion | sgkf5 | svanstrom | 43 | 9 | 2 | 26 | 0.743 | 0.929 | 0.173 | 0.918 | 0.168 |
| YAMNet ventanas + aumento · max | loso | TOTAL | 1537 | 386 | 4504 | 9 | 0.023 | 0.002 | 0.201 | 0.531 | 0.787 |
| YAMNet ventanas + aumento · max | loso | aris | 920 | 0 | 4484 | 1 | 1.000 | 0.000 | 0.000 | 0.793 | 0.829 |
| YAMNet ventanas + aumento · max | loso | esc10 | 241 | 28 | 0 | 0 | 0.000 | — | 0.104 | — | 0.296 |
| YAMNet ventanas + aumento · max | loso | fsd50k | 327 | 355 | 0 | 0 | 0.000 | — | 0.521 | — | 0.763 |
| YAMNet ventanas + aumento · max | loso | svanstrom | 49 | 3 | 20 | 8 | 0.727 | 0.286 | 0.058 | 0.713 | 0.161 |
| YAMNet ventanas + aumento · max | sgkf5 | TOTAL | 1597 | 326 | 438 | 4075 | 0.926 | 0.903 | 0.170 | 0.957 | 0.020 |
| YAMNet ventanas + aumento · max | sgkf5 | aris | 855 | 65 | 437 | 4048 | 0.984 | 0.903 | 0.071 | 0.988 | 0.072 |
| YAMNet ventanas + aumento · max | sgkf5 | esc10 | 241 | 28 | 0 | 0 | 0.000 | — | 0.104 | — | 0.253 |
| YAMNet ventanas + aumento · max | sgkf5 | fsd50k | 459 | 223 | 0 | 0 | 0.000 | — | 0.327 | — | 0.450 |
| YAMNet ventanas + aumento · max | sgkf5 | svanstrom | 42 | 10 | 1 | 27 | 0.730 | 0.964 | 0.192 | 0.961 | 0.221 |
| YAMNet ventanas + aumento · max_suavizado | loso | TOTAL | 1586 | 337 | 4507 | 6 | 0.017 | 0.001 | 0.175 | 0.529 | 0.781 |
| YAMNet ventanas + aumento · max_suavizado | loso | aris | 920 | 0 | 4485 | 0 | — | 0.000 | 0.000 | 0.783 | 0.830 |
| YAMNet ventanas + aumento · max_suavizado | loso | esc10 | 248 | 21 | 0 | 0 | 0.000 | — | 0.078 | — | 0.245 |
| YAMNet ventanas + aumento · max_suavizado | loso | fsd50k | 369 | 313 | 0 | 0 | 0.000 | — | 0.459 | — | 0.714 |
| YAMNet ventanas + aumento · max_suavizado | loso | svanstrom | 49 | 3 | 22 | 6 | 0.667 | 0.214 | 0.058 | 0.645 | 0.198 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | TOTAL | 1676 | 247 | 461 | 4052 | 0.943 | 0.898 | 0.128 | 0.973 | 0.016 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | aris | 867 | 53 | 460 | 4025 | 0.987 | 0.897 | 0.058 | 0.992 | 0.064 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | esc10 | 247 | 22 | 0 | 0 | 0.000 | — | 0.082 | — | 0.213 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | fsd50k | 517 | 165 | 0 | 0 | 0.000 | — | 0.242 | — | 0.397 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | svanstrom | 45 | 7 | 1 | 27 | 0.794 | 0.964 | 0.135 | 0.965 | 0.177 |
| YAMNet ventanas + aumento · media | loso | TOTAL | 1849 | 74 | 4476 | 37 | 0.333 | 0.008 | 0.038 | 0.533 | 0.733 |
| YAMNet ventanas + aumento · media | loso | aris | 912 | 8 | 4448 | 37 | 0.822 | 0.008 | 0.009 | 0.783 | 0.823 |
| YAMNet ventanas + aumento · media | loso | esc10 | 269 | 0 | 0 | 0 | — | — | 0.000 | — | 0.077 |
| YAMNet ventanas + aumento · media | loso | fsd50k | 616 | 66 | 0 | 0 | 0.000 | — | 0.097 | — | 0.411 |
| YAMNet ventanas + aumento · media | loso | svanstrom | 52 | 0 | 28 | 0 | — | 0.000 | 0.000 | 0.682 | 0.308 |
| YAMNet ventanas + aumento · media | sgkf5 | TOTAL | 1851 | 72 | 459 | 4054 | 0.983 | 0.898 | 0.037 | 0.989 | 0.015 |
| YAMNet ventanas + aumento · media | sgkf5 | aris | 866 | 54 | 453 | 4032 | 0.987 | 0.899 | 0.059 | 0.991 | 0.031 |
| YAMNet ventanas + aumento · media | sgkf5 | esc10 | 268 | 1 | 0 | 0 | 0.000 | — | 0.004 | — | 0.083 |
| YAMNet ventanas + aumento · media | sgkf5 | fsd50k | 666 | 16 | 0 | 0 | 0.000 | — | 0.023 | — | 0.153 |
| YAMNet ventanas + aumento · media | sgkf5 | svanstrom | 51 | 1 | 6 | 22 | 0.957 | 0.786 | 0.019 | 0.968 | 0.061 |
| YAMNet ventanas + aumento · top3 | loso | TOTAL | 1510 | 413 | 4503 | 10 | 0.024 | 0.002 | 0.215 | 0.529 | 0.787 |
| YAMNet ventanas + aumento · top3 | loso | aris | 920 | 0 | 4485 | 0 | — | 0.000 | 0.000 | 0.783 | 0.830 |
| YAMNet ventanas + aumento · top3 | loso | esc10 | 239 | 30 | 0 | 0 | 0.000 | — | 0.112 | — | 0.269 |
| YAMNet ventanas + aumento · top3 | loso | fsd50k | 302 | 380 | 0 | 0 | 0.000 | — | 0.557 | — | 0.761 |
| YAMNet ventanas + aumento · top3 | loso | svanstrom | 49 | 3 | 18 | 10 | 0.769 | 0.357 | 0.058 | 0.684 | 0.182 |
| YAMNet ventanas + aumento · top3 | sgkf5 | TOTAL | 1600 | 323 | 461 | 4052 | 0.926 | 0.898 | 0.168 | 0.963 | 0.019 |
| YAMNet ventanas + aumento · top3 | sgkf5 | aris | 867 | 53 | 460 | 4025 | 0.987 | 0.897 | 0.058 | 0.992 | 0.076 |
| YAMNet ventanas + aumento · top3 | sgkf5 | esc10 | 241 | 28 | 0 | 0 | 0.000 | — | 0.104 | — | 0.240 |
| YAMNet ventanas + aumento · top3 | sgkf5 | fsd50k | 451 | 231 | 0 | 0 | 0.000 | — | 0.339 | — | 0.463 |
| YAMNet ventanas + aumento · top3 | sgkf5 | svanstrom | 41 | 11 | 1 | 27 | 0.711 | 0.964 | 0.212 | 0.974 | 0.237 |
| modelo | esquema | tipo de negativo | n | fp | FPR |
|---|---|---|---|---|---|
| MFCC+sonoridad | loso | aves | 145 | 12 | 0.083 |
| MFCC+sonoridad | loso | aviones | 101 | 2 | 0.020 |
| MFCC+sonoridad | loso | barcos | 53 | 4 | 0.075 |
| MFCC+sonoridad | loso | fondo de campo | 942 | 388 | 0.412 |
| MFCC+sonoridad | loso | fuego | 38 | 7 | 0.184 |
| MFCC+sonoridad | loso | helicópteros | 69 | 1 | 0.014 |
| MFCC+sonoridad | loso | insectos | 77 | 16 | 0.208 |
| MFCC+sonoridad | loso | lluvia | 124 | 15 | 0.121 |
| MFCC+sonoridad | loso | mar y oleaje | 39 | 1 | 0.026 |
| MFCC+sonoridad | loso | motores y maquinaria | 123 | 19 | 0.154 |
| MFCC+sonoridad | loso | motos | 70 | 4 | 0.057 |
| MFCC+sonoridad | loso | perros | 23 | 0 | 0.000 |
| MFCC+sonoridad | loso | tictac | 36 | 4 | 0.111 |
| MFCC+sonoridad | loso | viento | 83 | 1 | 0.012 |
| MFCC+sonoridad | sgkf5 | aves | 145 | 15 | 0.103 |
| MFCC+sonoridad | sgkf5 | aviones | 101 | 7 | 0.069 |
| MFCC+sonoridad | sgkf5 | barcos | 53 | 10 | 0.189 |
| MFCC+sonoridad | sgkf5 | fondo de campo | 942 | 100 | 0.106 |
| MFCC+sonoridad | sgkf5 | fuego | 38 | 14 | 0.368 |
| MFCC+sonoridad | sgkf5 | helicópteros | 69 | 2 | 0.029 |
| MFCC+sonoridad | sgkf5 | insectos | 77 | 17 | 0.221 |
| MFCC+sonoridad | sgkf5 | lluvia | 124 | 20 | 0.161 |
| MFCC+sonoridad | sgkf5 | mar y oleaje | 39 | 2 | 0.051 |
| MFCC+sonoridad | sgkf5 | motores y maquinaria | 123 | 17 | 0.138 |
| MFCC+sonoridad | sgkf5 | motos | 70 | 7 | 0.100 |
| MFCC+sonoridad | sgkf5 | perros | 23 | 0 | 0.000 |
| MFCC+sonoridad | sgkf5 | tictac | 36 | 5 | 0.139 |
| MFCC+sonoridad | sgkf5 | viento | 83 | 5 | 0.060 |
| YAMNet media | loso | aves | 145 | 10 | 0.069 |
| YAMNet media | loso | aviones | 101 | 4 | 0.040 |
| YAMNet media | loso | barcos | 53 | 8 | 0.151 |
| YAMNet media | loso | fondo de campo | 942 | 1 | 0.001 |
| YAMNet media | loso | fuego | 38 | 0 | 0.000 |
| YAMNet media | loso | helicópteros | 69 | 0 | 0.000 |
| YAMNet media | loso | insectos | 77 | 22 | 0.286 |
| YAMNet media | loso | lluvia | 124 | 2 | 0.016 |
| YAMNet media | loso | mar y oleaje | 39 | 0 | 0.000 |
| YAMNet media | loso | motores y maquinaria | 123 | 14 | 0.114 |
| YAMNet media | loso | motos | 70 | 3 | 0.043 |
| YAMNet media | loso | perros | 23 | 0 | 0.000 |
| YAMNet media | loso | tictac | 36 | 0 | 0.000 |
| YAMNet media | loso | viento | 83 | 9 | 0.108 |
| YAMNet media | sgkf5 | aves | 145 | 1 | 0.007 |
| YAMNet media | sgkf5 | aviones | 101 | 0 | 0.000 |
| YAMNet media | sgkf5 | barcos | 53 | 1 | 0.019 |
| YAMNet media | sgkf5 | fondo de campo | 942 | 61 | 0.065 |
| YAMNet media | sgkf5 | fuego | 38 | 0 | 0.000 |
| YAMNet media | sgkf5 | helicópteros | 69 | 0 | 0.000 |
| YAMNet media | sgkf5 | insectos | 77 | 3 | 0.039 |
| YAMNet media | sgkf5 | lluvia | 124 | 0 | 0.000 |
| YAMNet media | sgkf5 | mar y oleaje | 39 | 0 | 0.000 |
| YAMNet media | sgkf5 | motores y maquinaria | 123 | 5 | 0.041 |
| YAMNet media | sgkf5 | motos | 70 | 0 | 0.000 |
| YAMNet media | sgkf5 | perros | 23 | 0 | 0.000 |
| YAMNet media | sgkf5 | tictac | 36 | 0 | 0.000 |
| YAMNet media | sgkf5 | viento | 83 | 2 | 0.024 |
| YAMNet media + aumento | loso | aves | 145 | 24 | 0.166 |
| YAMNet media + aumento | loso | aviones | 101 | 6 | 0.059 |
| YAMNet media + aumento | loso | barcos | 53 | 8 | 0.151 |
| YAMNet media + aumento | loso | fondo de campo | 942 | 11 | 0.012 |
| YAMNet media + aumento | loso | fuego | 38 | 0 | 0.000 |
| YAMNet media + aumento | loso | helicópteros | 69 | 0 | 0.000 |
| YAMNet media + aumento | loso | insectos | 77 | 27 | 0.351 |
| YAMNet media + aumento | loso | lluvia | 124 | 3 | 0.024 |
| YAMNet media + aumento | loso | mar y oleaje | 39 | 0 | 0.000 |
| YAMNet media + aumento | loso | motores y maquinaria | 123 | 15 | 0.122 |
| YAMNet media + aumento | loso | motos | 70 | 5 | 0.071 |
| YAMNet media + aumento | loso | perros | 23 | 0 | 0.000 |
| YAMNet media + aumento | loso | tictac | 36 | 0 | 0.000 |
| YAMNet media + aumento | loso | viento | 83 | 13 | 0.157 |
| YAMNet media + aumento | sgkf5 | aves | 145 | 7 | 0.048 |
| YAMNet media + aumento | sgkf5 | aviones | 101 | 1 | 0.010 |
| YAMNet media + aumento | sgkf5 | barcos | 53 | 2 | 0.038 |
| YAMNet media + aumento | sgkf5 | fondo de campo | 942 | 78 | 0.083 |
| YAMNet media + aumento | sgkf5 | fuego | 38 | 0 | 0.000 |
| YAMNet media + aumento | sgkf5 | helicópteros | 69 | 0 | 0.000 |
| YAMNet media + aumento | sgkf5 | insectos | 77 | 6 | 0.078 |
| YAMNet media + aumento | sgkf5 | lluvia | 124 | 3 | 0.024 |
| YAMNet media + aumento | sgkf5 | mar y oleaje | 39 | 1 | 0.026 |
| YAMNet media + aumento | sgkf5 | motores y maquinaria | 123 | 5 | 0.041 |
| YAMNet media + aumento | sgkf5 | motos | 70 | 1 | 0.014 |
| YAMNet media + aumento | sgkf5 | perros | 23 | 0 | 0.000 |
| YAMNet media + aumento | sgkf5 | tictac | 36 | 0 | 0.000 |
| YAMNet media + aumento | sgkf5 | viento | 83 | 3 | 0.036 |
| YAMNet media + aumento + negativos difíciles | loso | aves | 145 | 28 | 0.193 |
| YAMNet media + aumento + negativos difíciles | loso | aviones | 101 | 8 | 0.079 |
| YAMNet media + aumento + negativos difíciles | loso | barcos | 53 | 9 | 0.170 |
| YAMNet media + aumento + negativos difíciles | loso | fondo de campo | 942 | 22 | 0.023 |
| YAMNet media + aumento + negativos difíciles | loso | fuego | 38 | 0 | 0.000 |
| YAMNet media + aumento + negativos difíciles | loso | helicópteros | 69 | 1 | 0.014 |
| YAMNet media + aumento + negativos difíciles | loso | insectos | 77 | 34 | 0.442 |
| YAMNet media + aumento + negativos difíciles | loso | lluvia | 124 | 3 | 0.024 |
| YAMNet media + aumento + negativos difíciles | loso | mar y oleaje | 39 | 0 | 0.000 |
| YAMNet media + aumento + negativos difíciles | loso | motores y maquinaria | 123 | 15 | 0.122 |
| YAMNet media + aumento + negativos difíciles | loso | motos | 70 | 5 | 0.071 |
| YAMNet media + aumento + negativos difíciles | loso | perros | 23 | 0 | 0.000 |
| YAMNet media + aumento + negativos difíciles | loso | tictac | 36 | 0 | 0.000 |
| YAMNet media + aumento + negativos difíciles | loso | viento | 83 | 19 | 0.229 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | aves | 145 | 8 | 0.055 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | aviones | 101 | 1 | 0.010 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | barcos | 53 | 3 | 0.057 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | fondo de campo | 942 | 74 | 0.079 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | fuego | 38 | 1 | 0.026 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | helicópteros | 69 | 0 | 0.000 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | insectos | 77 | 6 | 0.078 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | lluvia | 124 | 4 | 0.032 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | mar y oleaje | 39 | 1 | 0.026 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | motores y maquinaria | 123 | 6 | 0.049 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | motos | 70 | 1 | 0.014 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | perros | 23 | 0 | 0.000 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | tictac | 36 | 0 | 0.000 |
| YAMNet media + aumento + negativos difíciles | sgkf5 | viento | 83 | 4 | 0.048 |
| YAMNet ventanas + aumento · atencion | loso | aves | 145 | 62 | 0.428 |
| YAMNet ventanas + aumento · atencion | loso | aviones | 101 | 30 | 0.297 |
| YAMNet ventanas + aumento · atencion | loso | barcos | 53 | 20 | 0.377 |
| YAMNet ventanas + aumento · atencion | loso | fondo de campo | 942 | 3 | 0.003 |
| YAMNet ventanas + aumento · atencion | loso | fuego | 38 | 2 | 0.053 |
| YAMNet ventanas + aumento · atencion | loso | helicópteros | 69 | 4 | 0.058 |
| YAMNet ventanas + aumento · atencion | loso | insectos | 77 | 47 | 0.610 |
| YAMNet ventanas + aumento · atencion | loso | lluvia | 124 | 16 | 0.129 |
| YAMNet ventanas + aumento · atencion | loso | mar y oleaje | 39 | 2 | 0.051 |
| YAMNet ventanas + aumento · atencion | loso | motores y maquinaria | 123 | 44 | 0.358 |
| YAMNet ventanas + aumento · atencion | loso | motos | 70 | 36 | 0.514 |
| YAMNet ventanas + aumento · atencion | loso | perros | 23 | 0 | 0.000 |
| YAMNet ventanas + aumento · atencion | loso | tictac | 36 | 3 | 0.083 |
| YAMNet ventanas + aumento · atencion | loso | viento | 83 | 24 | 0.289 |
| YAMNet ventanas + aumento · atencion | sgkf5 | aves | 145 | 34 | 0.234 |
| YAMNet ventanas + aumento · atencion | sgkf5 | aviones | 101 | 27 | 0.267 |
| YAMNet ventanas + aumento · atencion | sgkf5 | barcos | 53 | 16 | 0.302 |
| YAMNet ventanas + aumento · atencion | sgkf5 | fondo de campo | 942 | 71 | 0.075 |
| YAMNet ventanas + aumento · atencion | sgkf5 | fuego | 38 | 2 | 0.053 |
| YAMNet ventanas + aumento · atencion | sgkf5 | helicópteros | 69 | 11 | 0.159 |
| YAMNet ventanas + aumento · atencion | sgkf5 | insectos | 77 | 28 | 0.364 |
| YAMNet ventanas + aumento · atencion | sgkf5 | lluvia | 124 | 10 | 0.081 |
| YAMNet ventanas + aumento · atencion | sgkf5 | mar y oleaje | 39 | 2 | 0.051 |
| YAMNet ventanas + aumento · atencion | sgkf5 | motores y maquinaria | 123 | 28 | 0.228 |
| YAMNet ventanas + aumento · atencion | sgkf5 | motos | 70 | 25 | 0.357 |
| YAMNet ventanas + aumento · atencion | sgkf5 | perros | 23 | 1 | 0.043 |
| YAMNet ventanas + aumento · atencion | sgkf5 | tictac | 36 | 6 | 0.167 |
| YAMNet ventanas + aumento · atencion | sgkf5 | viento | 83 | 18 | 0.217 |
| YAMNet ventanas + aumento · max | loso | aves | 145 | 73 | 0.503 |
| YAMNet ventanas + aumento · max | loso | aviones | 101 | 53 | 0.525 |
| YAMNet ventanas + aumento · max | loso | barcos | 53 | 26 | 0.491 |
| YAMNet ventanas + aumento · max | loso | fondo de campo | 942 | 2 | 0.002 |
| YAMNet ventanas + aumento · max | loso | fuego | 38 | 4 | 0.105 |
| YAMNet ventanas + aumento · max | loso | helicópteros | 69 | 5 | 0.072 |
| YAMNet ventanas + aumento · max | loso | insectos | 77 | 57 | 0.740 |
| YAMNet ventanas + aumento · max | loso | lluvia | 124 | 27 | 0.218 |
| YAMNet ventanas + aumento · max | loso | mar y oleaje | 39 | 2 | 0.051 |
| YAMNet ventanas + aumento · max | loso | motores y maquinaria | 123 | 55 | 0.447 |
| YAMNet ventanas + aumento · max | loso | motos | 70 | 45 | 0.643 |
| YAMNet ventanas + aumento · max | loso | perros | 23 | 0 | 0.000 |
| YAMNet ventanas + aumento · max | loso | tictac | 36 | 3 | 0.083 |
| YAMNet ventanas + aumento · max | loso | viento | 83 | 34 | 0.410 |
| YAMNet ventanas + aumento · max | sgkf5 | aves | 145 | 39 | 0.269 |
| YAMNet ventanas + aumento · max | sgkf5 | aviones | 101 | 35 | 0.347 |
| YAMNet ventanas + aumento · max | sgkf5 | barcos | 53 | 19 | 0.358 |
| YAMNet ventanas + aumento · max | sgkf5 | fondo de campo | 942 | 71 | 0.075 |
| YAMNet ventanas + aumento · max | sgkf5 | fuego | 38 | 3 | 0.079 |
| YAMNet ventanas + aumento · max | sgkf5 | helicópteros | 69 | 11 | 0.159 |
| YAMNet ventanas + aumento · max | sgkf5 | insectos | 77 | 33 | 0.429 |
| YAMNet ventanas + aumento · max | sgkf5 | lluvia | 124 | 15 | 0.121 |
| YAMNet ventanas + aumento · max | sgkf5 | mar y oleaje | 39 | 1 | 0.026 |
| YAMNet ventanas + aumento · max | sgkf5 | motores y maquinaria | 123 | 36 | 0.293 |
| YAMNet ventanas + aumento · max | sgkf5 | motos | 70 | 33 | 0.471 |
| YAMNet ventanas + aumento · max | sgkf5 | perros | 23 | 1 | 0.043 |
| YAMNet ventanas + aumento · max | sgkf5 | tictac | 36 | 6 | 0.167 |
| YAMNet ventanas + aumento · max | sgkf5 | viento | 83 | 23 | 0.277 |
| YAMNet ventanas + aumento · max_suavizado | loso | aves | 145 | 63 | 0.434 |
| YAMNet ventanas + aumento · max_suavizado | loso | aviones | 101 | 46 | 0.455 |
| YAMNet ventanas + aumento · max_suavizado | loso | barcos | 53 | 28 | 0.528 |
| YAMNet ventanas + aumento · max_suavizado | loso | fondo de campo | 942 | 2 | 0.002 |
| YAMNet ventanas + aumento · max_suavizado | loso | fuego | 38 | 4 | 0.105 |
| YAMNet ventanas + aumento · max_suavizado | loso | helicópteros | 69 | 3 | 0.043 |
| YAMNet ventanas + aumento · max_suavizado | loso | insectos | 77 | 51 | 0.662 |
| YAMNet ventanas + aumento · max_suavizado | loso | lluvia | 124 | 22 | 0.177 |
| YAMNet ventanas + aumento · max_suavizado | loso | mar y oleaje | 39 | 0 | 0.000 |
| YAMNet ventanas + aumento · max_suavizado | loso | motores y maquinaria | 123 | 49 | 0.398 |
| YAMNet ventanas + aumento · max_suavizado | loso | motos | 70 | 34 | 0.486 |
| YAMNet ventanas + aumento · max_suavizado | loso | perros | 23 | 0 | 0.000 |
| YAMNet ventanas + aumento · max_suavizado | loso | tictac | 36 | 3 | 0.083 |
| YAMNet ventanas + aumento · max_suavizado | loso | viento | 83 | 32 | 0.386 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | aves | 145 | 24 | 0.166 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | aviones | 101 | 27 | 0.267 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | barcos | 53 | 13 | 0.245 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | fondo de campo | 942 | 57 | 0.061 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | fuego | 38 | 4 | 0.105 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | helicópteros | 69 | 9 | 0.130 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | insectos | 77 | 28 | 0.364 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | lluvia | 124 | 13 | 0.105 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | mar y oleaje | 39 | 1 | 0.026 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | motores y maquinaria | 123 | 28 | 0.228 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | motos | 70 | 25 | 0.357 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | perros | 23 | 0 | 0.000 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | tictac | 36 | 2 | 0.056 |
| YAMNet ventanas + aumento · max_suavizado | sgkf5 | viento | 83 | 16 | 0.193 |
| YAMNet ventanas + aumento · media | loso | aves | 145 | 15 | 0.103 |
| YAMNet ventanas + aumento · media | loso | aviones | 101 | 3 | 0.030 |
| YAMNet ventanas + aumento · media | loso | barcos | 53 | 3 | 0.057 |
| YAMNet ventanas + aumento · media | loso | fondo de campo | 942 | 8 | 0.008 |
| YAMNet ventanas + aumento · media | loso | fuego | 38 | 0 | 0.000 |
| YAMNet ventanas + aumento · media | loso | helicópteros | 69 | 0 | 0.000 |
| YAMNet ventanas + aumento · media | loso | insectos | 77 | 25 | 0.325 |
| YAMNet ventanas + aumento · media | loso | lluvia | 124 | 2 | 0.016 |
| YAMNet ventanas + aumento · media | loso | mar y oleaje | 39 | 0 | 0.000 |
| YAMNet ventanas + aumento · media | loso | motores y maquinaria | 123 | 12 | 0.098 |
| YAMNet ventanas + aumento · media | loso | motos | 70 | 0 | 0.000 |
| YAMNet ventanas + aumento · media | loso | perros | 23 | 0 | 0.000 |
| YAMNet ventanas + aumento · media | loso | tictac | 36 | 0 | 0.000 |
| YAMNet ventanas + aumento · media | loso | viento | 83 | 6 | 0.072 |
| YAMNet ventanas + aumento · media | sgkf5 | aves | 145 | 3 | 0.021 |
| YAMNet ventanas + aumento · media | sgkf5 | aviones | 101 | 0 | 0.000 |
| YAMNet ventanas + aumento · media | sgkf5 | barcos | 53 | 1 | 0.019 |
| YAMNet ventanas + aumento · media | sgkf5 | fondo de campo | 942 | 55 | 0.058 |
| YAMNet ventanas + aumento · media | sgkf5 | fuego | 38 | 0 | 0.000 |
| YAMNet ventanas + aumento · media | sgkf5 | helicópteros | 69 | 0 | 0.000 |
| YAMNet ventanas + aumento · media | sgkf5 | insectos | 77 | 6 | 0.078 |
| YAMNet ventanas + aumento · media | sgkf5 | lluvia | 124 | 1 | 0.008 |
| YAMNet ventanas + aumento · media | sgkf5 | mar y oleaje | 39 | 0 | 0.000 |
| YAMNet ventanas + aumento · media | sgkf5 | motores y maquinaria | 123 | 4 | 0.033 |
| YAMNet ventanas + aumento · media | sgkf5 | motos | 70 | 0 | 0.000 |
| YAMNet ventanas + aumento · media | sgkf5 | perros | 23 | 0 | 0.000 |
| YAMNet ventanas + aumento · media | sgkf5 | tictac | 36 | 0 | 0.000 |
| YAMNet ventanas + aumento · media | sgkf5 | viento | 83 | 2 | 0.024 |
| YAMNet ventanas + aumento · top3 | loso | aves | 145 | 75 | 0.517 |
| YAMNet ventanas + aumento · top3 | loso | aviones | 101 | 65 | 0.644 |
| YAMNet ventanas + aumento · top3 | loso | barcos | 53 | 32 | 0.604 |
| YAMNet ventanas + aumento · top3 | loso | fondo de campo | 942 | 2 | 0.002 |
| YAMNet ventanas + aumento · top3 | loso | fuego | 38 | 5 | 0.132 |
| YAMNet ventanas + aumento · top3 | loso | helicópteros | 69 | 5 | 0.072 |
| YAMNet ventanas + aumento · top3 | loso | insectos | 77 | 59 | 0.766 |
| YAMNet ventanas + aumento · top3 | loso | lluvia | 124 | 29 | 0.234 |
| YAMNet ventanas + aumento · top3 | loso | mar y oleaje | 39 | 1 | 0.026 |
| YAMNet ventanas + aumento · top3 | loso | motores y maquinaria | 123 | 60 | 0.488 |
| YAMNet ventanas + aumento · top3 | loso | motos | 70 | 38 | 0.543 |
| YAMNet ventanas + aumento · top3 | loso | perros | 23 | 0 | 0.000 |
| YAMNet ventanas + aumento · top3 | loso | tictac | 36 | 3 | 0.083 |
| YAMNet ventanas + aumento · top3 | loso | viento | 83 | 39 | 0.470 |
| YAMNet ventanas + aumento · top3 | sgkf5 | aves | 145 | 39 | 0.269 |
| YAMNet ventanas + aumento · top3 | sgkf5 | aviones | 101 | 33 | 0.327 |
| YAMNet ventanas + aumento · top3 | sgkf5 | barcos | 53 | 22 | 0.415 |
| YAMNet ventanas + aumento · top3 | sgkf5 | fondo de campo | 942 | 59 | 0.063 |
| YAMNet ventanas + aumento · top3 | sgkf5 | fuego | 38 | 5 | 0.132 |
| YAMNet ventanas + aumento · top3 | sgkf5 | helicópteros | 69 | 13 | 0.188 |
| YAMNet ventanas + aumento · top3 | sgkf5 | insectos | 77 | 36 | 0.468 |
| YAMNet ventanas + aumento · top3 | sgkf5 | lluvia | 124 | 20 | 0.161 |
| YAMNet ventanas + aumento · top3 | sgkf5 | mar y oleaje | 39 | 1 | 0.026 |
| YAMNet ventanas + aumento · top3 | sgkf5 | motores y maquinaria | 123 | 35 | 0.285 |
| YAMNet ventanas + aumento · top3 | sgkf5 | motos | 70 | 31 | 0.443 |
| YAMNet ventanas + aumento · top3 | sgkf5 | perros | 23 | 0 | 0.000 |
| YAMNet ventanas + aumento · top3 | sgkf5 | tictac | 36 | 3 | 0.083 |
| YAMNet ventanas + aumento · top3 | sgkf5 | viento | 83 | 26 | 0.313 |

**Diagnóstico adicional (ROC-AUC LOSO, independiente de la prevalencia):** clips ARIS 4485 dron / 920 fondo; Svanström 28 / 52; ESC-10 y FSD50K solo negativos. En LOSO sin ARIS el entrenamiento solo dispone de 28 positivos (Svanström) y la ROC-AUC en ARIS es 0,23–0,39 (por debajo del azar): el fallo es de **falta de fuentes de dron**, no solo de técnica. En LOSO sin Svanström, YAMNet media alcanza ROC-AUC 0,908 con recall 0 al umbral: el orden se transfiere y el umbral no (calibración por emplazamiento). El PR-AUC LOSO en ARIS no es informativo (prevalencia 0,83); el criterio D-6 del hito 2 se corrige por ADR.

# Model card: piloto acústico exploratorio (YAMNet + regresión logística)

**Estado (2026-11-11): no entrenado.** El cuaderno
`pilots/acoustic/Atalaya_YAMNet_Colab.ipynb` (generado por `pilots/acoustic/build_colab.py`)
mantiene cerradas las puertas `SOURCE_INTAKE_DOWNLOAD_APPROVED` y `TRAINING_ALLOWED`; el
manifiesto de Svanström conserva `intake_approved`, `training_allowed` y
`generalization_eval_allowed` en `false`. No hay métricas ni pesos derivados. Plan:
[`docs/plans/PILOTO-ACUSTICO-EXPLORATORIO.md`](../plans/PILOTO-ACUSTICO-EXPLORATORIO.md).
Datos: [`docs/data-cards/svanstrom-v1.0.0.md`](../data-cards/svanstrom-v1.0.0.md).

## Componentes y licencias

| Componente | Origen | Licencia | Verificación |
| --- | --- | --- | --- |
| Pesos YAMNet (extractor congelado) | Google; [TF Hub `google/yamnet/1`](https://tfhub.dev/google/yamnet/1), que redirige a [Kaggle Models `google/yamnet`](https://www.kaggle.com/models/google/yamnet) | **Apache 2.0** | Comprobado el 2026-11-11 en la API oficial de Kaggle (`/api/v1/models/google/yamnet/get`): las cinco instancias, incluida `tensorFlow2/yamnet`, declaran `licenseName: "Apache 2.0"`. El código original en [TensorFlow Model Garden](https://github.com/tensorflow/models/tree/master/research/audioset/yamnet) está bajo Apache 2.0 según su `LICENSE` |
| Datos de preentrenamiento de YAMNet (AudioSet) | Google | **NO VERIFICADA** para este uso | La licencia de los pesos no acredita los derechos sobre el audio de YouTube subyacente; revisar antes de cualquier uso fuera del piloto |
| Cabeza de clasificación | Regresión logística (scikit-learn, BSD-3) sobre la media de embeddings por clip | — | Se entrena solo si se abren las puertas |

## Diseño de evaluación

- Partición train/validación/test **por `group_id`** con
  `acoustic_pilot.grouped_eval.split_indices_by_group` (probada en `pilots/acoustic/tests`,
  incrustada literalmente en el cuaderno): ningún grupo en dos particiones.
- Los grupos actuales son **provisionales** (un clip o un par de duplicados exactos). Cada métrica
  se muestra con el rótulo «prueba técnica, contaminación entre particiones no descartada».
- Umbral elegido **solo en validación** (máximo F1; empate → umbral mayor) y guardado con
  semilla, particiones y hash de coeficientes en `modelo_piloto.json` del almacenamiento temporal
  de Colab. Test solo mide.
- Métricas de test: matriz de confusión, precision, recall y PR-AUC; intervalos bootstrap al
  95 % remuestreando grupos cuando hay al menos 10 grupos de test; con menos se marca
  «NO DISPONIBLE». Con 24 clips (5 grupos de test) no hay intervalos.
- Falsas alarmas por hora: **NO VERIFICADA**; los clips son de ~10 s y no contiguos.
- La curva por ventana aplica una cabeza entrenada con medias por clip a ventanas de 0,96 s:
  fuera de distribución, **no calibrada**, solo ilustrativa.

## Límites

Sin grupos fiables de vuelo, sesión o emplazamiento no hay estimación de generalización ni
métrica operativa. No sustituye `evals/frozen/v1` ni la evaluación de REQ-NFR-004.

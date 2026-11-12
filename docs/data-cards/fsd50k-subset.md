# Data card: FSD50K, subconjunto de confusores CC0/CC BY (negativos)

**Estado (2026-11-12): licencia por clip verificada en la fuente original e inventario fijado;
solo para la prueba técnica aislada de Colab (ADR 0016).** El manifiesto
[`ml/datasets/fsd50k-subset/manifest.json`](../../ml/datasets/fsd50k-subset/manifest.json) tiene
`intake_approved=false`, `training_allowed=false` y `production_allowed=false`: nada entra en el
producto. No se guardó audio en el Mac: los clips se leyeron por rangos HTTP y se resumieron por
SHA-256 en memoria.

## Fuente y licencia

- Autores: E. Fonseca, X. Favory, J. Pons, F. Font y X. Serra (MTG, Universitat Pompeu Fabra),
  *FSD50K: An Open Dataset of Human-Labeled Sound Events*, IEEE/ACM TASLP 30 (2022).
- Registro original: [Zenodo 4060432](https://zenodo.org/records/4060432), DOI
  `10.5281/zenodo.4060432`, versión 1.0. La API de Zenodo marca `other-at` porque las licencias
  son **por clip**.
- Comprobado el **2026-11-12** en los ficheros originales (descargados de Zenodo, MD5 de Zenodo y
  SHA-256 fijados en el manifiesto):
  - `FSD50K.doc/LICENSE-DATASET`: «FSD50K as a whole is released under license: Attribution 4.0
    International (CC BY 4.0)». Copia en
    [`LICENSE-DATASET-fuente.txt`](../../ml/datasets/fsd50k-subset/LICENSE-DATASET-fuente.txt).
  - `FSD50K.doc/README.md`: «Each clip has its own license as defined by the clip uploader in
    Freesound … These licenses are CC0, CC-BY, CC-BY-NC and CC Sampling+», especificadas en
    `dev_clips_info_FSD50K.json` y `eval_clips_info_FSD50K.json`.
- **Filtro de licencia por clip** (`acoustic_pilot.sources.clip_license_allowed`, con tests):
  solo `publicdomain/zero/1.0`, `licenses/by/3.0` y `licenses/by/4.0`. Se rechazan CC BY-NC (no
  comercial), CC Sampling+ (dudosa) y cualquier valor desconocido. El cuaderno vuelve a leer la
  licencia de **cada clip fijado** en `clips_info` de la fuente y se detiene si cambia.
- Nota de la ficha: «If you'd like to use FSD50K for commercial purposes, please contact…». La
  licencia CC de cada clip lo permite; un correo de cortesía a la UPF queda como decisión del
  usuario (regla 0 €, sin contactos). La API de Freesound **no** se usa (sus términos limitan el
  uso comercial): solo el ZIP de Zenodo.

## Selección (reproducible, `build_sources.py`)

- Etiquetas objetivo (confusores, en este orden): `Engine`, `Motorcycle`,
  `Boat_and_Water_vehicle`, `Fixed-wing_aircraft_and_airplane`, `Aircraft`, `Insect`, `Wind`,
  `Rain`, `Gull_and_seagull`, `Bird`.
- Exclusiones: cualquier etiqueta humana (voz, canto, risa, tos, pasos, aplausos, multitud…) o
  `Music`; títulos, descripciones o tags que mencionen drones (`drone`, `quadcopter`, `uav`, `dji`…
  con límite de palabra); clips sin autor; y los IDs de Freesound que ya están en ESC-10 (126
  coincidencias en FSD50K: mismo audio en dos fuentes sería una fuga).
- Topes: 120 clips por etiqueta, 3 por autor y etiqueta, 800 MB comprimidos repartidos por
  etiqueta; orden por SHA-256 con semilla `20261112`.
- Resultado: ver `clip_count`, `total_compressed_bytes` y `total_wav_bytes` en el manifiesto
  (≈ 830 clips, ≈ 0,77 GB comprimidos). Cada clip lleva licencia, URL de la licencia, autor y
  título (atribución CC BY), etiquetas y grupo.

## Integridad

| Comprobación | Dónde |
| --- | --- |
| `FSD50K.doc.zip`, `ground_truth.zip`, `metadata.zip` | tamaño + MD5 de Zenodo + SHA-256 fijado |
| Volúmenes del audio (`dev_audio.z01…z05/.zip`, `eval_audio.z01/.zip`) | tamaño en el registro de Zenodo |
| Directorio central de cada ZIP dividido | SHA-256 fijado de sus bytes (leídos por rango) |
| Cada clip | volumen, desplazamiento, tamaño comprimido y real, CRC-32 del ZIP y **SHA-256 del WAV** |

El cuaderno solo descarga de `zenodo.org`, comprueba cada redirección y lee cada clip por rangos
HTTP (`acoustic_pilot.remote_zip`, con tests), sin bajar los 24 GB del conjunto.

## Grupos y fugas

`group_id = fsd50k:u-<SHA-256 del autor de Freesound, 12 hex>`: todos los clips de un mismo autor
van a la misma partición y al mismo fold (el mismo autor en train y test es una fuga conocida en
FSD50K). Se mezclan dev y eval de FSD50K porque la partición es propia, por autor; no se usa la
partición de evaluación de FSD50K como referencia.

## Datos personales

Se excluyen las etiquetas humanas, pero etiquetas incompletas pueden dejar voces de fondo
(**NO VERIFICADO**): la puerta automática de voz del cuaderno (YAMNet, `max_speech_score >= 0,30`)
se aplica también aquí y la escucha humana de los excluidos sigue pendiente. Los nombres de autor
de Freesound son públicos y necesarios para la atribución CC BY; en los grupos se seudonimizan.

## Limitaciones

- Clips cortos (0,3–30 s) grabados cerca de la fuente con micrófonos diversos: dominio distinto de
  un perímetro; no sirven para medir falsas alarmas por hora.
- Sin helicóptero ni dron en FSD50K; los aviones y barcos son pocos.
- Etiquetas «smeared» hacia la raíz de la ontología; posibles errores de etiquetado.

## Puerta de uso

Solo prueba técnica aislada en Colab. Para cualquier otro uso: escucha de muestra, DPIA, decisión
sobre el aviso comercial de la ficha, aprobación del intake y atribución por clip en el producto.

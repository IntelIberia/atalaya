# Data card: ITU ARIS Lab. Acoustic Drone Dataset v1.0.0 (positivos y fondo)

**Estado (2026-11-12): licencia verificada en la fuente e inventario fijado; solo para la prueba
técnica aislada de Colab (ADR 0016).** El manifiesto
[`ml/datasets/itu-aris/manifest.json`](../../ml/datasets/itu-aris/manifest.json) tiene
`intake_approved=false`, `training_allowed=false` y `production_allowed=false`: nada entra en el
producto. El audio no se descargó al disco del Mac (el ZIP se leyó en memoria para calcular hashes).

## Fuente, licencia y procedencia

- Autores: İhsan Mert Muhacıroğlu y Tayfun Akgül, ARIS Laboratory, Istanbul Technical University.
- Registro original: [Zenodo 22682339](https://zenodo.org/records/22682339), DOI
  `10.5281/zenodo.22682339`, versión 1.0.0. Copia en Hugging Face no usada (se usa solo Zenodo).
- Licencia comprobada el **2026-11-12** en la fuente original:
  - API de Zenodo: `metadata.license.id = cc-by-4.0`.
  - Fichero `LICENSE` dentro del ZIP: «Creative Commons Attribution 4.0 International (CC BY 4.0) …
    You are free to share and adapt this dataset for any purpose, including commercially, provided
    you give appropriate credit». Copia en
    [`LICENSE-fuente.txt`](../../ml/datasets/itu-aris/LICENSE-fuente.txt), SHA-256
    `b79e2b6ded8d3c4cee0a64ab6562864d210fb33449095ad4bf330e64d8058c11`.
  - CC BY 4.0 no restringe la finalidad (sin cláusula de seguridad o defensa). Exige atribución,
    enlace a la licencia e indicar cambios (aquí: remuestreo a 16 kHz para YAMNet).
- Cita: *Muhaciroglu, I. M. and Akgul, T. (2026). ITU ARIS Lab. Acoustic Drone Dataset (v1.0.0).
  Zenodo. 10.5281/zenodo.22682339*.

## Inventario e integridad

| Comprobación | Resultado |
| --- | --- |
| Archivo | `itu-aris-lab-acoustic-drone-dataset-v1.0.0.zip`, 169.094.149 bytes |
| MD5 publicado por Zenodo | `64aed06e8dac417d0c3c7db0e3ac340b` (coincide) |
| SHA-256 del ZIP | `11d1b1208ef63515d3fe62de3047b58977d00959cc938f49d17913e428400511` |
| Segmentos | 5.491 WAV de 1 s, 22.050 Hz, mono, PCM 16 bit: 4.491 `drone`, 1.000 `background` |
| Por fichero | cada WAV coincide con el `SHA256SUMS` de los autores (fijado por SHA-256 en el manifiesto) |
| Ficheros pequeños fijados | `LICENSE`, `README.md`, `metadata.json`, `groups.json`, `SHA256SUMS`, `splits/*.json` (SHA-256 en el manifiesto) |

El cuaderno repite todo: licencia en la API, tamaño en el registro, SHA-256 del ZIP, SHA-256 de los
ficheros internos, texto CC BY 4.0 y SHA-256 de cada WAV contra `SHA256SUMS`. Solo descarga de
`zenodo.org` y comprueba cada redirección.

## Grupos y particiones (fugas)

- **Segmentos solapados al 50 %**: dos segmentos consecutivos comparten medio segundo. Nunca se
  parte por segmento.
- `groups.json` asigna cada segmento a uno de **35 intervalos de dron** o **20 bloques de fondo**
  (50 segmentos); `group_id = aris:<grupo>`.
- La partición única del cuaderno usa el split de los autores `split_interval_disjoint.json`
  (train/val/test = drone 3.144/673/674, fondo 700/150/150). La función probada `aris_segments`
  falla si un grupo cruza particiones. En la validación cruzada por grupos (5 folds) cada intervalo
  o bloque va entero a un fold.
- **Limitación**: una sola sesión continua de 3,12 h en un día y un lugar. Los intervalos no son
  independientes entre sí (mismo viento, tráfico y micrófono): los IC por grupos son optimistas y
  no miden generalización a otra sesión o emplazamiento. El modelo de dron, la distancia y la
  maniobra no están anotados por segmento. Acuerdo entre anotadores moderado (κ = 0,587).

## Datos personales

El README declara: «Operator speech is audible in some segments. The people recorded are members of
the research group and consented to publication». Aun así, la **puerta automática de voz** del
cuaderno (YAMNet, `max_speech_score >= 0,30`) excluye esos segmentos del entrenamiento y la
evaluación; la escucha humana de los excluidos sigue pendiente. No hay vídeo ni metadatos de
personas.

## Puerta de uso

Solo prueba técnica aislada en Colab (decisión del usuario 2026-11-11, ADR 0016). Para cualquier
otro uso: escucha de muestra, revisión DPIA de la voz de operadores, aprobación del intake y
atribución en el fichero de atribuciones del producto.

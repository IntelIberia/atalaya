# Data card: DroneAudioSet, subconjunto `drone-only`

**Estado (2026-11-11): preflight de licencia e inventario; sin audio en el Mac.**
`intake_approved=false`, `training_allowed=false`, `production_allowed=false`,
`generalization_eval_allowed=false` en [`manifest.json`](../../ml/datasets/droneaudioset-drone-only/manifest.json).

## Fuente y licencia

- Autores: Chitralekha Gupta, Soundarya Ramesh et al. (Augmented Human Lab). Artículo
  [arXiv:2510.15383](https://arxiv.org/abs/2510.15383), NeurIPS 2025 Datasets & Benchmarks.
- Repositorio original: [Hugging Face `ahlab-drone-project/DroneAudioSet`](https://huggingface.co/datasets/ahlab-drone-project/DroneAudioSet),
  revisión fijada `e794007062e2d2ad29262a5795b60d09f2b345c4`.
- Licencia **MIT**, verificada hoy en la fuente: metadato `license: mit` del README en la
  revisión fijada y dos declaraciones del artículo («publicly available … under the MIT license»;
  «We distribute it under the MIT License»). El datasheet declara que los autores recogieron
  todos los datos y que no hay restricciones de terceros. MIT no limita uso comercial ni campo de
  uso. Evidencia con URL, fecha y SHA-256 en [`LICENSE-fuente.txt`](../../ml/datasets/droneaudioset-drone-only/LICENSE-fuente.txt).
- **Reserva:** no hay fichero LICENSE ni titular del copyright que exige el aviso MIT
  (**NO VERIFICADO**). Atribución provisional: autores del artículo, con su cita.
- **Solo `drone-only`.** `drone-with-source` y `source-only` contienen audio de terceros
  reproducido por altavoz (LibriSpeech, Freesound, AudioSet…) y voz: excluidos y nunca descargados.

## Origen por parte e inventario

| Parte | Contenido | Ficheros | Bytes |
|---|---|---|---|
| `drone-only/` | 28 parquet (6 filas cada uno), audio multicanal 16 kHz remuestreado de 48 kHz | 28 | 3.359.836.225 |

Hash por fichero: SHA-256 (oid LFS) publicado por Hugging Face, comprobado por `fetch.py`.
Las 168 filas (`file_path`) se obtuvieron del servicio de estadísticas de Hugging Face, sin
descargar audio. Según el artículo, `drone-only` suma unas 2,3 h.

## Grupos disponibles

Del `file_path`: dron (`drone1`, `drone2` = DJI F450 y F330 según el artículo, correspondencia
**NO VERIFICADA**), distancia del micrófono (25/50 cm), acelerador (low/high), micrófono
(`mic1_soundskrit`, `mic2_8array-down`, `mic3_8array-up`) y toma (`File1`–`File6`, `silence`).
Hay **8 sesiones** (2 drones × 2 distancias × 2 aceleradores). Los tres micrófonos graban la misma
toma a la vez (`simultaneous_capture_id`), por lo que nunca pueden separarse entre particiones.
Agrupación propuesta: `group_id` = sesión; para generalización, retener un dron entero.
No hay sitios distintos: sala de laboratorio, sin emplazamiento exterior.

## Datos personales

El datasheet afirma que no participaron personas. Las tomas `drone-only` no deberían contener voz,
pero podría haber conversación de fondo de los operadores: **escucha de muestra pendiente**.
Las filas `silence` tienen etiqueta dudosa (¿dron encendido sin fuente o silencio?) y llevan
`label_status=pending_listening_review`.

## Limitaciones

- Dron **sujeto a un bastidor** en interior; micrófonos a 25–50 cm sobre el mismo bastidor: es
  ruido propio en campo cercano, no un dron en vuelo oído desde tierra. Sirve como positivo de
  firma armónica, no para estimar alcance ni falsas alarmas.
- Solo dos cuadricópteros pequeños de la misma familia (clase C1); sin negativos propios.
- Sin hashes por fila del audio original (solo por parquet).

## Puerta de uso

Descarga solo en Colab (`python fetch.py`), nunca en el Mac. Antes de entrenar: escucha de una
muestra con semilla, revisión de privacidad, decisión sobre `silence`, partición por sesión/dron
y aprobación explícita del intake.

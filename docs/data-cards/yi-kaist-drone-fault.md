# Data card: Yi et al. (KAIST), sonidos de drones con y sin fallos

**Estado (2026-11-11): preflight de licencia e inventario; sin audio en el Mac.**
`intake_approved=false`, `training_allowed=false`, `production_allowed=false`,
`generalization_eval_allowed=false` en [`manifest.json`](../../ml/datasets/yi-kaist-drone-fault/manifest.json).

## Fuente y licencia

- Autores: Wonjun Yi, Jung-Woo Choi, Jae-Woo Lee (KAIST). Artículo
  [arXiv:2304.11708](https://arxiv.org/abs/2304.11708), ICSV29.
- Registro original: [Zenodo 7779574](https://zenodo.org/records/7779574), DOI 10.5281/zenodo.7779574, versión 1.
- Licencia **CC BY 4.0**, verificada hoy en la API de Zenodo (`metadata.license.id = cc-by-4.0`).
  Uso comercial permitido, sin restricción de campo; exige atribución.
  Evidencia y SHA-256 en [`LICENSE-fuente.txt`](../../ml/datasets/yi-kaist-drone-fault/LICENSE-fuente.txt).

## Origen por parte e inventario

| Parte | Bytes | MD5 (Zenodo) | Descarga por defecto |
|---|---|---|---|
| `drone_A.tar` (Holy Stone HS720) | 2.554.408.960 | `14a6fd11…7811147` | sí |
| `drone_B.tar` (MJX Bugs 12 EIS) | 2.535.034.880 | `b3d19705…f2a4` | no |
| `drone_C.tar` (ZLRC SG906 Pro 2) | 2.533.406.720 | `54b1e10b…ecb36` | no |
| **Total** | **7.622.850.560** | | |

Cada TAR: 54.000 segmentos × 2 canales (mic1/mic2) de **0,5 s a 16 kHz**. El sonido del dron se
grabó en **cámara anecoica** con micrófonos inalámbricos sobre el propio dron, sujeto con gomas
al techo y al suelo, y se **mezcló** con ruido grabado en cinco puntos del campus (obra, estanque,
colina, polideportivo, entrada) a 10–15 dB de SNR. La lista de miembros y su SHA-256 no se publican:
`fetch.py` los calcula en Colab (**NO VERIFICADO** hasta entonces).

## Grupos disponibles

Nombre: `{modelo}_{dirección}_{fallo}_{índice_grabación_dron}_{fondo}_{índice_fondo}_{SNR}`.
Solo se usa `fallo = N` (normal); `fetch.py` extrae únicamente esos WAV. El reparto 6:2:2 de los
autores es **aleatorio por segmento**: hay fuga garantizada. Hay que reagrupar por
`índice_grabación_dron` (y, mejor, por fondo) antes de cualquier partición; si el índice no
identifica una grabación continua, solo cabe una prueba técnica por segmento (**NO VERIFICADO**).
Sitio: una cámara anecoica y cinco puntos de fondo del mismo campus.

## Datos personales

Los fondos de polideportivo y entrada del campus pueden contener **voces** de transeúntes
(**NO VERIFICADO**). Escucha de muestra y revisión DPIA obligatorias antes de usar.

## Limitaciones

- Dominio artificial: micrófono a bordo, sin propagación aérea real, mezclado sintéticamente.
  Debe marcarse como mezcla y nunca presentarse como rendimiento en campo.
- Segmentos de 0,5 s; drones de juguete de una misma clase (C1).
- Sin negativos limpios (los fondos solo existen mezclados).

## Puerta de uso

Descarga en Colab de un solo dron (`python fetch.py --drone A`). Antes de entrenar: inventario
SHA-256 al manifiesto, escucha y privacidad, reagrupación y aprobación explícita del intake.

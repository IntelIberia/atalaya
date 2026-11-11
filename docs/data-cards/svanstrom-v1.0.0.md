# Data card: Svanström v1.0.0, solo audio

**Estado (2026-11-11): preflight local verificado; entrenamiento y producción bloqueados.**
El manifiesto tiene `intake_approved=false`, `training_allowed=false`,
`production_allowed=false` y `generalization_eval_allowed=false`. La copia local
sirve para verificar el origen y preparar una descarga reproducible en Colab; no
constituye aprobación de uso en modelos de Atalaya.

## Fuente, licencia y procedencia

- Autores: Fredrik Svanström, Fernando Alonso-Fernandez y Cristofer Englund.
  Artículo original: [*A dataset for multi-sensor drone detection*](https://arxiv.org/pdf/2111.01888),
  *Data in Brief* 39 (2021), 107521.
- Repositorio original: [DroneDetectionThesis/Drone-detection-dataset](https://github.com/DroneDetectionThesis/Drone-detection-dataset),
  tag `v1.0.0`, commit fijo `e7a6eaf9760fa3f9ecc37d09cd11a8cd20be90dd`.
  Se descargó únicamente [`Data/Audio`](https://github.com/DroneDetectionThesis/Drone-detection-dataset/tree/e7a6eaf9760fa3f9ecc37d09cd11a8cd20be90dd/Data/Audio)
  el `2026-11-11T19:19:52Z`.
- El [archivo LICENSE original](https://github.com/DroneDetectionThesis/Drone-detection-dataset/blob/e7a6eaf9760fa3f9ecc37d09cd11a8cd20be90dd/LICENSE)
  declara CC0-1.0; se archivó con URL y fecha en
  [`LICENSE-fuente.txt`](../../ml/datasets/svanstrom/LICENSE-fuente.txt).
  Su Git blob SHA-1 es `0e259d42c996742e9e3cba14c677129b2c1b6311`.
  **La licencia del repositorio no acredita por sí sola los derechos de cada clip.**
- El [artículo](https://arxiv.org/pdf/2111.01888) indica que una parte pequeña
  del conjunto procede de YouTube (p. 3) y que el audio se extrajo de los vídeos
  o se grabó aparte (p. 4). La [tesis del primer autor](https://hh.diva-portal.org/smash/get/diva2%3A1434532/FULLTEXT02.pdf)
  precisa que 49 clips externos son del subconjunto de **vídeo visible** (§3.3);
  esto no demuestra que un WAV concreto venga de YouTube. Tampoco hay un mapa
  de procedencia por WAV. Por ello los derechos por clip siguen sin resolver
  para entrenamiento o producción.

## Inventario e integridad

| Comprobación | Resultado |
| --- | --- |
| WAV verificados contra blobs del commit | 90/90 |
| Tamaño total | 158.764.512 bytes |
| Duración total | 900,003126 s |
| Formato | Estéreo, PCM 16 bit, 44.100 Hz, ~10 s por clip |
| Etiquetas originales | 30 `DRONE`, 30 `HELICOPTER`, 30 `BACKGROUND` |
| SHA-256 únicos | 89 |
| Duplicado exacto | `BACKGROUND_010.wav` = `BACKGROUND_019.wav` |
| DVC 3.67.1 | `data/raw/svanstrom.dvc`, MD5 de directorio `f663ac6acb3a5058d8422836266f3bbe.dir` |

Cada WAV y su SHA-256, tamaño, formato, etiqueta y Git blob SHA-1 aparecen en
[`manifest.json`](../../ml/datasets/svanstrom/manifest.json). El segundo duplicado
permanece en el inventario pero lleva `training_excluded=true` y comparte grupo
provisional con el primero. Los 90 WAV están en `data/raw/svanstrom/`, ignorados
por Git; el remoto DVC es **solo local** y se configura en `.dvc/config.local`,
también ignorado. No se publica audio ni se monta Drive personal para el piloto.
Colab debe descargar del commit fijo y comparar los 90 SHA-256 antes de usarlo.

## Calidad, privacidad y particiones

- Muestra aleatoria estratificada con semilla `20261111`, tres por clase:
  `BACKGROUND_015`, `BACKGROUND_029`, `BACKGROUND_009`, `DRONE_012`,
  `DRONE_006`, `DRONE_015`, `HELICOPTER_011`, `HELICOPTER_026`,
  `HELICOPTER_021` (extensión `.wav`). La **escucha y revisión de voz u otros
  datos personales está pendiente**; no se declara ausencia de PII. Una detección
  positiva exige evaluar la [DPIA](../dpia/v0.md) antes del uso.
- No hay IDs fiables de vuelo, sesión ni emplazamiento por WAV. El `group_id`
  actual une duplicados exactos y, para el resto, identifica solo el clip. No
  sirve para demostrar independencia de entrenamiento y prueba. La búsqueda de
  duplicados próximos y fugas entre sesiones está pendiente.
- Las tres etiquetas permiten un prototipo binario dron / no dron y examinar
  helicópteros como confusor. No asignan de forma fiable las clases C1–C9 por
  archivo, la distancia, el modelo de dron ni las condiciones de grabación.
  La evaluación por vuelo, sitio o condiciones reales queda sin verificar.

## Puerta de uso

`intake_approved` y `training_allowed` solo podrán cambiar tras resolver la
procedencia y derechos de los WAV usados, revisar privacidad con la muestra
registrada, tratar duplicados próximos y documentar la decisión versionada.
Una prueba de flujo por clip, si se hiciera, no aporta métricas de generalización
ni autoriza despliegue. Los hashes permiten repetir el preflight en Colab sin
subir audio desde este equipo.

# Investigación de licencias de los datasets (FASE 4)

Versión 1 · 2026-11-08 · Autor: planificador de la FASE 4 (Claude Code) · Estado: **para revisión del usuario (STOP de plan)**

Este documento recoge la licencia de cada dataset de la tabla `<datos_y_biblioteca_de_firmas>` del MEGAPROMPT, consultada en su **fuente original** (repositorio, artículo, Zenodo, Figshare, Mendeley, IEEE DataPort, Hugging Face o web de la NASA). No se ha descargado ningún dataset: solo páginas, metadatos de API, cabeceras HTTP (para medir tamaños) y dos PDF de artículos o memorias técnicas.

**Contexto que condiciona la lectura.** Atalaya es un producto **comercial con licencia propietaria** y un sistema de **seguridad** (detección y alerta de drones para prisiones, puertos, infraestructuras críticas y, más adelante, Defensa). Por eso la pregunta no es solo «¿permite uso comercial?», sino también «¿permite usarlo en un sistema de seguridad?». Una licencia que prohíba ese uso excluye el dataset **incluso para investigación interna**.

**Criterios**
- **¿Comercial?** `sí`: la licencia permite el uso comercial (CC0, CC BY, MIT, Apache-2.0…). `no`: NC, solo académico, sin licencia (por defecto, todos los derechos reservados) o licencia de pago. `dudoso`: licencias contradictorias, licencia que no queda claro que cubra los datos o términos de acceso que añaden condiciones.
- **¿Cabe?** Medido el 2026-11-08 con `df -h /`: **24 GB libres** (la SPEC hablaba de ~30 GB). Se exige dejar ≥ 12 GB libres para el sistema, Docker y el resto de fases. `sí`: ≤ 4 GB; `subconjunto`: 4-20 GB (solo una parte); `no`: > 20 GB.
- **Estado:** **VERIFICADO** = licencia leída en la fuente original en la URL indicada el 2026-11-08. **NO VERIFICADO** = no se ha encontrado una licencia aplicable a los datos, o la fuente no era legible.
- Esto **no es asesoramiento jurídico** (no hay asesoría, bloqueo B-01). Las clasificaciones son conservadoras: ante la duda, `production_allowed: false`.

---

## 1. Resumen ejecutivo

1. **DroneAudioDataset (Al-Emadi) queda excluido por completo, incluso para investigación.** Su `LICENSE.md` prohíbe, además del uso comercial sin permiso, cualquier uso «directo o indirecto» con fines **militares, de defensa, inteligencia, seguridad o armas**, sea comercial o no, y expresamente la «detección, identificación y seguimiento de drones» con esos fines. Atalaya es un sistema de seguridad.
2. **DADS no puede usarse.** Es un agregado de 10 fuentes que **incluye Al-Emadi** y **no guarda la fuente de cada fichero** (solo `audio` y `label`), así que no se puede filtrar. Además contiene fuentes NC (UrbanSound8K, ESC-50, TUT 2017, DREGON, SPCup19). La etiqueta `mit` de Hugging Face **no es válida** para las partes: la propia ficha pide «verificar las licencias individuales».
3. **Hay alternativa con licencia comercial**, descargando de la fuente original las partes buenas de DADS y otras: DroneNoise Database de Salford (CC BY 4.0, 0,74 GB), Yi et al./KAIST (CC BY 4.0, 7,6 GB → subconjunto), DroneAudioSet solo el subconjunto `drone-only` (MIT, 3,36 GB), Svanström et al. (CC0-1.0, 0,31 GB) y ESC-10 (CC BY, dentro de ESC-50).
4. **Hallazgo valioso:** los datos de la NASA incluyen **dos aviones radiocontrol de gasolina (motor de pistón)** y tres multirrotores, con posición RTK y meteorología: son **equivalentes legales reales de C6** y una referencia para validar la síntesis física. Pero la NASA **no declara licencia** («License not specified»): `dudoso` hasta confirmarlo por escrito.
5. **RF y visión no caben en el disco** (DroneRF > 40 GB, CardRF 66 GB, RFUAV 299 GB en Hugging Face) y no son de esta fase: se registran sus licencias para las FASES 6 y 9.
6. **Los tres artículos de lectura obligatoria existen** y están VERIFICADOS (§5). La cifra de Tegler «5-1.500 m» es correcta, pero el propio artículo dice que la estimación de ángulo **se rompe por encima de 500 m**.

---

## 2. Audio (tabla del MEGAPROMPT)

| Dataset | Fuente original consultada | Licencia encontrada | ¿Comercial? | Tamaño aprox. | ¿Cabe? | Observaciones | Estado |
|---|---|---|---|---|---|---|---|
| **DADS** (`geronimobasso/drone-audio-detection-samples`) | https://huggingface.co/datasets/geronimobasso/drone-audio-detection-samples (ficha y README) | Metadato `license: mit`. Texto de la ficha: «Data from various sources is licensed under Creative Commons Attribution and similar open licenses… Please verify individual licenses for commercial and non-commercial usage» | **no** | 6,81 GB; 180.320 ficheros (163.591 dron, 16.729 sin dron); WAV 16 kHz mono | sí, pero **no se descarga** | Agregado de 10 fuentes (§3). Contiene Al-Emadi (prohíbe usos de seguridad) y 5 fuentes NC. **Sin columna de fuente por fichero** ⇒ imposible filtrar. Un único split `train` ⇒ alto riesgo de fugas. Hay copias en otros repos de HF (p. ej. `gr1047/…`, `Z121mm/…`) con el mismo problema | VERIFICADO (2026-11-08) |
| **DroneAudioSet** (NeurIPS 2025, 23,5 h) | https://huggingface.co/datasets/ahlab-drone-project/DroneAudioSet · https://arxiv.org/abs/2510.15383 | Metadato `license: mit`; el artículo dice que el dataset se publica bajo MIT. README vacío en HF | **sí** solo `drone-only`; **dudoso** `drone-with-source` y `source-only` | 42,6 GB en total. Por subconjunto (API de HF): `drone-only` 3,36 GB (28 parquet), `source-only` 9,05 GB, `drone-with-source` 30,2 GB | `drone-only`: sí; el resto: no | Las «fuentes» son sonidos de terceros reproducidos por altavoz: LibriSpeech, Audio Distress Dataset, AudioSet y Freesound (licencias Creative Commons por fichero, tabla 6 del artículo). MIT no puede relicenciar contenido de terceros. Incluye **voz humana** (habla, gritos, llanto). Drones DJI F450 y F330 (C1), 17 micrófonos (dos arrays de 8 ICS-43434 más uno central) montados **en el propio dron** ⇒ dominio muy distinto al de un sensor en tierra | VERIFICADO (2026-11-08) |
| **Al-Emadi DroneAudioDataset** | https://github.com/saraalemadi/DroneAudioDataset (`LICENSE.md` leído) | Licencia propia © 2019-2026 Sara Al Emadi: solo uso educativo y de investigación académica no comercial; **sección 3: «must not be used, directly or indirectly, for military, defence, intelligence, security, weapons…»**, incluida la detección, identificación y seguimiento de drones con esos fines, «regardless of… commercial status»; uso comercial solo con permiso escrito, que no se extiende a defensa; redistribución no permitida | **no** (tampoco investigación en Atalaya) | ~0,28 GB (tamaño del repositorio según la API de GitHub) | sí, pero **excluido** | **Excluido del proyecto.** Contamina cualquier agregado que lo incluya (DADS y sus copias) | VERIFICADO (2026-11-08) |
| **Dataset multiclase de 32 modelos** (arXiv 2509.04715) | https://arxiv.org/abs/2509.04715 (HTML v1) · https://github.com/mackenzie-jane/drone-visualization | El artículo **no declara licencia** de los datos (la CC BY 4.0 de arXiv es la del texto). El repositorio de la web **no tiene licencia** (API de GitHub: `license: null`) | **no** (sin licencia = sin concesión de derechos) | 3.200 clips de 5 s (~4,4 h); repositorio de 39,7 MB (no consta que contenga todo el audio) | sí | Grabado con el **micrófono interno de un MacBook Air**, en interiores y exteriores (granja, azotea). 32 categorías; no todas son modelos comerciales (hay construidos a medida). Útil solo para comparación académica tras pedir licencia a los autores | NO VERIFICADO (licencia no encontrada) |
| **NASA Small UAS Flyover Acoustics** | https://data.nasa.gov/dataset/small-uas-flyover-acoustics-data (HTML: «License not specified») · memoria `Data_Description_20160203.pdf` (NASA Langley, 23-05-2016) · https://catalog.data.gov/dataset/small-uas-flyover-acoustics-data | **No declarada.** Es obra de la NASA (Gobierno de EE. UU.): en EE. UU. no tendría copyright (17 U.S.C. §105), pero esto es una **inferencia, no una licencia**, y fuera de EE. UU. no está claro | **dudoso** | ZIP de 1,69 GB (1.693.926.297 bytes, cabecera `Content-Range`) | sí | Ficheros MATLAB `.mat`: presión acústica de 4-5 micrófonos GRAS en el suelo, posición del vehículo por **GPS y RTK** (cm), meteorología (solo AP Hill), tiempo UTC. **Cinco vehículos:** Edge 540 y Carbon Cub (**aviones RC de gasolina, pistón → equivalente de C6**), 3DR Y6 (C1/C2), DJI Phantom 2 (C1) y Prioria Hex Flyer de ~7 kg con altavoz (C2). Campañas Virginia Beach 2014 y Fort A.P. Hill 2015 (separación natural por sesión). El catálogo de data.gov enlaza un recurso erróneo (una página de Fermi) | NO VERIFICADO (licencia no declarada) |
| **Tegler et al.** (CVPRW 2025) | https://vision.maths.lth.se/drone_sound/ · artículo en CVF Open Access (PDF leído) · https://github.com/Etomer/Detection-and-Localization-of-Drones-and-UAVs-Using-Sound-and-Vision | **Dataset sin licencia declarada.** La web dice «This website is licensed under a Creative Commons Attribution-ShareAlike 4.0» (solo la web); el código, MIT (API de GitHub) | **dudoso** | `ljungbyhed_audio_dataset.zip`: 19,05 GB (19.046.276.225 bytes, cabecera HTTP) | **no** con el margen exigido | 13 grabaciones de ~7 min, 12 micrófonos omnidireccionales t.bone MM-1 sincronizados (Roland Studio Capture 1610) sobre una furgoneta, 3 UAV (cuadricóptero pequeño, cuadricóptero mediano y ala fija), vuelos de **<5 m a 1.500 m**, posiciones reales incluidas, mucho ruido de viento. Para la FASE 8 (localización): pedir licencia a los autores y espacio en disco antes | NO VERIFICADO (licencia del dataset no encontrada) |
| **Svanström et al. 2021** (IR, visible y audio) | https://zenodo.org/records/5500576 (API: `license: other-open`) · https://github.com/DroneDetectionThesis/Drone-detection-dataset (API de GitHub: **CC0-1.0**; README: «Free to download, use and edit») | **CC0-1.0** en el repositorio de los autores; Zenodo solo dice «Other (Open)» | **sí** | 311,3 MB (un ZIP en Zenodo) | sí | 650 vídeos (365 IR, 285 visible) y **90 clips de audio** (dron, helicóptero, fondo). Grabado en tres aeropuertos de Suecia. Útil como confusor C8 (helicóptero) y para la FASE 9. Revisar en el intake si algún vídeo muestra personas identificables | VERIFICADO (2026-11-08) |

## 3. Partes de DADS (licencia de cada fuente original)

| Parte | Fuente original consultada | Licencia encontrada | ¿Comercial? | Tamaño | ¿Cabe? | Observaciones | Estado |
|---|---|---|---|---|---|---|---|
| Al-Emadi | ver §2 | Propia, NC y sin usos de seguridad | **no** (excluida) | ~0,28 GB | — | Hace inutilizable todo DADS | VERIFICADO |
| SPCup19 Egonoise (Inria) | http://dregon.inria.fr/datasets/the-spcup19-egonoise-dataset/ | Sin licencia formal: «made publicly available here for research and education purpose, as agreed by participating teams» | **no** | no indicado | — | Ruido propio de dron (egonoise), micrófonos a bordo | VERIFICADO |
| DREGON (Inria) | http://dregon.inria.fr/datasets/dregon/ | «freely available for personal, educational and academic use only» | **no** | no indicado | — | Micrófonos a bordo de un dron | VERIFICADO |
| DroneNoise Database (Salford) | https://salford.figshare.com/articles/dataset/DroneNoise_Database/22133411 (API de Figshare) | **CC BY 4.0** | **sí** | 742 MB, 175 ficheros (WAV y calibración) | sí | Sobrevuelos en campo (Edzell, Escocia, agosto de 2022), con ficheros de calibración. La ficha no da modelos ni distancias: hay que leer la hoja XLSX en el intake | VERIFICADO |
| AUDROK Drone Sound Data | https://mobilithek.info/offers/605778370199691264 (página no legible sin JavaScript); proyecto mFUND del BMV y Fraunhofer IVI | **No encontrada** | **dudoso** | no indicado | — | Pedir condiciones a Fraunhofer IVI | NO VERIFICADO |
| Yi et al., *Sound-based drone fault classification* (KAIST) | https://doi.org/10.5281/zenodo.7779574 (API de Zenodo) | **CC BY 4.0** | **sí** | 7,62 GB (tres TAR de ~2,5 GB: drones A, B y C) | subconjunto | Grabado en **cámara anecoica** con fallos de hélice y motor, y **mezclado con ruido de campus a 10-15 dB de SNR**: dominio artificial. Usar solo el estado sin fallo de un dron | VERIFICADO |
| UrbanSound8K | https://zenodo.org/records/1203745 (API: `cc-by-nc-4.0`) | **CC BY-NC 4.0** | **no** | 6,02 GB | — | Fondo urbano; solo investigación | VERIFICADO |
| TUT Acoustic Scenes 2017 | https://zenodo.org/records/1040168 (API: `other-nc`) | **Otra, no comercial** | **no** | 3,6 GB (evaluación) | — | Solo investigación | VERIFICADO |
| ESC-50 | https://github.com/karolpiczak/ESC-50 | ESC-50: «Creative Commons Attribution Non-Commercial» (CC BY-NC 3.0). **ESC-10** (subconjunto): «distributed under CC BY (Attribution)», con atribución por clip en `LICENSE` | ESC-50 **no**; ESC-10 **sí** | ~600 MB el ZIP; ESC-10 = 400 clips de 5 s | sí | ESC-10 incluye helicóptero, lluvia, olas, motosierra, gallo, perro, fuego, reloj, estornudo y llanto de bebé. **Excluir estornudo y llanto** (sonidos de personas) | VERIFICADO |
| DNC (Dataset for Noise Classification) | https://github.com/zequeira/DNC | Etiqueta de GitHub **MIT** | **dudoso** | 3,92 GB | — | Contiene «TV, música, radio y personas»: probable **voz** y obras de terceros (música, televisión) que una licencia MIT no puede cubrir. Requeriría DPIA. No se usa | VERIFICADO (etiqueta) |

## 4. RF, visión, multimodal, radar y contexto

| Dataset | Fuente original consultada | Licencia encontrada | ¿Comercial? | Tamaño aprox. | ¿Cabe? | Observaciones | Estado |
|---|---|---|---|---|---|---|---|
| **DroneRF** | https://data.mendeley.com/datasets/f4c2b4n755/1 (DOI 10.17632/f4c2b4n755.1) | **CC BY 4.0** (campo de licencia de Mendeley) | **sí** | > 40 GB (artículo de Data in Brief); 227 segmentos | **no** (subconjunto en la FASE 6) | Tres drones (Bebop, AR, Phantom) y fondo RF. Coincide con el MEGAPROMPT | VERIFICADO |
| **CardRF** | https://ieee-dataport.org/documents/cardinal-rf-cardrf-outdoor-uavuas-rf-signals-bluetooth-and-wifi-signals-dataset (DOI 10.21227/1xp7-ge95) | Campo de licencia: «Creative Commons Attribution» (enlace a CC BY 4.0) | **sí** según la licencia; revisar los términos de IEEE DataPort si se descarga con suscripción (hay un enlace abierto en OneDrive de la universidad) | 66,26 GB (`CARDRF.zip`) más suplementos | **no** (FASE 6, subconjunto) | UAV, Bluetooth y Wi-Fi: los confusores que pide el MEGAPROMPT | VERIFICADO |
| **CageDroneRF** | https://github.com/DroneGoHome/U-RAPTOR-PUB (`LICENSE-DATA.md`) · https://arxiv.org/abs/2601.03302 | Datos y modelos: **CC BY-NC-SA 4.0**; código: PolyForm Noncommercial 1.0.0; parte YOLO: AGPL-3.0. README: no se puede «build commercial products… or train commercial models on the data» | **no** (licencia comercial por petición a AeroDefense) | no indicado | — | Solo investigación (FASE 6) | VERIFICADO |
| **RFUAV** (1,3 TB, 37 UAV) | https://github.com/kitoweeknd/RFUAV (API: **Apache-2.0**) · https://huggingface.co/datasets/kitofrank/RFUAV (metadato `apache-2.0`, sin texto) · https://arxiv.org/abs/2503.09033 (licencia del artículo: **CC BY-NC-SA 4.0**) | **Conflicto confirmado:** Apache-2.0 en repositorio y HF; CC BY-NC-SA 4.0 en el artículo. Ningún sitio declara explícitamente la licencia **de los datos** | **dudoso** | 299 GB en HF (subconjunto público); 1,3 TB en bruto | **no** | Mantener «solo investigación» hasta aclararlo por escrito con los autores, como dice el MEGAPROMPT. Copia no oficial en `BEBO0o/RFUAV` (también `apache-2.0`) | VERIFICADO el conflicto; licencia de los datos NO VERIFICADA |
| **Anti-UAV** (300 RGB+TIR, 410 y 600 IR) | https://github.com/ZhaoJ9014/Anti-UAV | «The project of Anti-UAV is released under the MIT License»; **nada específico para los datos** | **dudoso** | no indicado | — | Descargas por Baidu (con contraseña), Google Drive y ModelScope. FASE 9 | NO VERIFICADO (licencia de los datos) |
| **Anti-UAV410** (repositorio de los autores) | https://github.com/HwangBo94/Anti-UAV410 | Sin `LICENSE` visible ni términos; solo petición de cita | **dudoso** | no indicado (410 vídeos, 438.000 cajas) | — | FASE 9 | NO VERIFICADO |
| **DUT Anti-UAV** | https://github.com/wangdongdut/DUT-Anti-UAV (API: Apache-2.0) | Repositorio con **Apache-2.0**; no consta que cubra las imágenes | **dudoso** | no indicado (10.000 imágenes y 20 vídeos) | — | FASE 9 | NO VERIFICADO (licencia de los datos) |
| **CST Anti-UAV** | https://github.com/PCwenyue/CST-Anti-UAV | Código MIT; el dataset se ofrece «for academic and non-commercial research purposes» (`DATASET_TERMS.md`, no leído) | **no** | no indicado (220 vídeos IR) | — | Solo investigación (FASE 9) | VERIFICADO (README) |
| **MMAUD** | https://github.com/ntu-aris/mmaud | README: «Creative Commons Attribution-NonCommercial-ShareAlike 4.0», «intended for non-commercial academic use»; código con etiqueta MIT | **no** | rosbags de 11-20 GB por dron; ruido de fondo 5,06 GB | **no** | LiDAR, cámaras, radar mmWave y 4 nodos de audio | VERIFICADO |
| **DIAT-μSAT** | https://ieee-dataport.org/documents/diat-msat-micro-doppler-signature-dataset-small-unmanned-aerial-vehicle-suav (DOI 10.21227/1x2q-8v62) | Campo: «Creative Commons Attribution» (CC BY 4.0); texto: «completely open to academic research»; acceso con suscripción o por correo con fines educativos | **dudoso** (licencia CC BY, pero acceso educativo) | 943,55 MB | sí | Solo si hay radar de socio (fuera de la v1) | VERIFICADO |
| **SIPRI Arms Transfers Database** | https://www.sipri.org/databases/armstransfers · https://www.sipri.org/about/terms-and-conditions | Uso justo (trabajos universitarios, artículos, prensa, blogs) sin permiso y con cita; «Commercial use of SIPRI data must be authorized and licensed» | **no** sin licencia de SIPRI | — | — | No se ingiere. Consultarlo a mano para priorizar qué clases grabar es dudoso en un producto comercial: decisión del usuario. Nunca sirve para inferir un país a partir del sonido (restricción legal 5) | VERIFICADO |

---

## 5. Artículos de lectura obligatoria

### 5.1 arXiv 2608.14287 — VERIFICADO (https://arxiv.org/abs/2608.14287, 2026-11-08)
**Cita:** Vilhurin, V., Sydorskyi, V. y Shevtsov, A. *Acoustic UAV Detection in Battlefield Scenarios: Handling Noise, Domain Shift, and Weak Labels*. arXiv:2608.14287 [cs.SD], v1, 14-08-2026. Presentado antes en ICMCIS (Bath, Reino Unido, mayo de 2026). Licencia del artículo: licencia no exclusiva de distribución de arXiv 1.0.

**Qué dice que importa a Atalaya:**
- Datos **propietarios de Zvook** (frente ucraniano, polígonos y sensores acústicos antiaéreos): más de 300.000 clips de 9 s a 32 kHz. **No los publica.** Confirma que Zvook tiene el corpus que falta para C6/C7 ⇒ argumento para la alianza.
- **Etiquetas débiles** a nivel de fichero, sin marcas de tiempo; cabeza de atención tipo SED.
- **Fugas:** los clips de un mismo flujo continuo van siempre a la misma partición. Divisiones por **tiempo y lugar**: entrenamiento con pruebas controladas, validación en invierno y test en primavera con lugares no vistos. Es la política de la regla `ml.md`.
- **PCEN** «actuó como un sustractor de fondo»: s = 0,015, α = 0,8, δ = 2,0, r = 0,5. PCEN y log-mel fallan de forma complementaria.
- **Cambio de dominio entre micrófonos:** entrenar solo con el micrófono minoritario colapsa (F1 ≈ 0,09); clases auxiliares (otros drones, reactores, helicópteros, aviones de hélice) y mezcla con ruido de ambos dominios ayudan. El cambio de dominio «no se resuelve del todo».
- **Cifras (clase dron pequeño, test):** línea base de Zvook F1 69,1; mejor modelo abierto (AST-Drone) 55,4; un modelo PCEN 78,6; conjunto 82,2 (precisión 92,7, recall 73,9). **No informa de falsas alarmas por hora.** El resumen (55,4 → 78,6) y el cuerpo (82,2 del conjunto) no coinciden exactamente.

### 5.2 «Outdoor Microphone Range Tests» (Sensors 2025, PMC12656299) — VERIFICADO (https://pmc.ncbi.nlm.nih.gov/articles/PMC12656299/, 2026-11-08)
**Cita:** Jekateryńczuk, G. y Piotrowski, Z. *Outdoor Microphone Range Tests and Spectral Analysis of UAV Acoustic Signatures for Array Development*. Sensors 2025, 25(22), 7057. Publicado el 19-11-2025. DOI 10.3390/s25227057. Licencia CC BY 4.0. Universidad Militar de Tecnología (Varsovia).

**Qué dice que importa a Atalaya:**
- Siete configuraciones de micrófono (RØDE NTG-2 desnudo, con WS6, con DeadCat y en parábola de 18″; Mozos VMic; Behringer B-1 y B-2 PRO). Alcance medido con **un tono de 1 kHz por altavoz** (1-250 m) y umbral SNR ≥ 3 dB en 950-1.050 Hz; los drones (DJI Air 3, Avata 2 y Neo) solo se grabaron en estacionario a 1-50 m.
- **Calma:** ~100-139 m en la mejor dirección (NTG-2 + WS6: 138,7 m). **Viento fuerte:** el ruido de fondo sube 5-7 dB y el alcance cae a ~35-99 m (NTG-2 desnudo: de 83,9 m a 34,8 m en una dirección). El cortavientos es lo que más ayuda.
- Firmas: la mayor parte de la energía de los tres drones está **por debajo de 2 kHz**; el paso de pala llega a ~2,6 kHz; el Neo tiene armónicos hasta ~15 kHz.
- Recomiendan descartar la parábola para arrays de TDOA/SRP-PHAT (haz estrecho, fase incoherente, saturación por ráfagas).
- **Datos solo bajo petición** al autor de contacto; sin licencia de datos. Útil como referencia de diseño, no como dataset.
- Lectura para Atalaya: los 50-300 m de diseño para C1 son optimistas con viento (levante en Ceuta); refuerza la FASE 7.

### 5.3 Tegler et al. (CVPRW 2025) — VERIFICADO (https://vision.maths.lth.se/drone_sound/ y PDF de CVF Open Access, 2026-11-08)
**Cita:** Tegler, E., Modig, M., Skarin, P., Åström, K., Oskarsson, M. y Flood, G. *Detection and Localization of Drones and UAVs Using Sound and Vision*. Proceedings of the IEEE/CVF CVPR Workshops (Anti-UAV), 2025, pp. 6650-6658 (pp. 6716-6724 según el índice de CVF Open Access).

**Qué dice que importa a Atalaya:**
- Array ad hoc de 12 micrófonos (2-3 m en horizontal, 0,5 m en vertical) más 9 cámaras fijas y una PTZ. DOA por GCC-PHAT sobre segmentos de 0,1 s y mediana móvil, con dos modelos (solo azimut; azimut y elevación).
- **Dataset:** 13 grabaciones de ~7 min en dos jornadas (Ljungbyhed, Suecia), 3 UAV (cuadricóptero pequeño, cuadricóptero mediano y ala fija), vuelos de **<5 m a 1.500 m**, con posiciones reales.
- **Resultados:** el modelo supera al estimador humano por debajo de 150 m; **la estimación de ángulo se rompe por encima de 500 m**; el ala fija es más difícil (sonido más variable). El viento introduce mucho ruido de baja frecuencia (lo combaten con una derivada discreta).
- Sirve para la FASE 8 si la licencia lo permite: hoy, **sin licencia del dataset** y con 19 GB.

---

## 6. Recomendación para la FASE 4

| Uso | Datasets |
|---|---|
| **Producción permitida** (`production_allowed: true`, tras el intake) | DroneNoise Database de Salford (CC BY 4.0) · DroneAudioSet `drone-only` (MIT) · Yi et al., un dron, sin fallos (CC BY 4.0) · Svanström et al. (CC0-1.0) · ESC-10 sin estornudo ni llanto (CC BY, atribución por clip) |
| **Solo investigación hasta confirmar por escrito** | NASA Small UAS Flyover (licencia no declarada) · Tegler et al. (sin licencia del dataset; además no cabe) · RFUAV (conflicto) · Anti-UAV, Anti-UAV410, DUT Anti-UAV (licencia de los datos no clara) · DIAT-μSAT · AUDROK (no encontrada) |
| **Solo investigación (NC)** — nunca en producción | UrbanSound8K · TUT 2017 · ESC-50 completo · DREGON · SPCup19 · CageDroneRF · CST Anti-UAV · MMAUD · arXiv 2509.04715 (sin licencia) |
| **Excluidos por completo** | **Al-Emadi** (prohíbe usos de seguridad) y **DADS** y sus copias (contienen Al-Emadi sin poder filtrarlo) |
| **Fuera de la FASE 4** por tamaño o modalidad | DroneRF y CardRF (FASE 6), visión (FASE 9), Tegler (FASE 8), DIAT-μSAT (sin radar), SIPRI (no se ingiere) |

**Atribución obligatoria** (CC BY y CC0 con petición de cita): cada data card llevará la cita y el aviso de licencia, y el paquete del producto incluirá un fichero de atribuciones de datos.

**Cartas a autores propuestas** (las envía el usuario; Claude Code redacta las plantillas en la tarea T4.14 del plan): NASA Langley (licencia del sUAS Flyover), Universidad de Lund (licencia del dataset de Tegler), autores de RFUAV, Fraunhofer IVI (AUDROK), autores de Anti-UAV y DUT Anti-UAV, y autores de arXiv 2509.04715.

## 7. Afirmaciones del MEGAPROMPT corregidas por esta investigación

| Afirmación del MEGAPROMPT | Resultado |
|---|---|
| DADS: «Verificar (es un agregado)» | Verificado: **no utilizable** (Al-Emadi sin filtrar, fuentes NC) |
| DroneAudioSet: MIT | Correcto para el dataset, pero los subconjuntos con «fuentes» contienen material de terceros y voz ⇒ solo `drone-only` |
| Al-Emadi: «Verificar» | **Excluido**: prohíbe usos de seguridad y defensa |
| NASA: «obra del Gobierno de EE. UU.» | La NASA **no declara licencia**; la condición de obra federal es una inferencia ⇒ dudoso |
| Tegler: 5-1.500 m | Correcto; la DOA deja de funcionar por encima de 500 m |
| DroneRF: CC BY 4.0 | Correcto |
| RFUAV: conflicto CC BY-NC-SA / Apache | Confirmado (artículo frente a repositorio y HF) |
| SIPRI: «Términos de SIPRI» | El uso comercial requiere licencia de SIPRI |

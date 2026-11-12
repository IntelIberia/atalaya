# Investigación de datasets adicionales de audio de drones (positivos)

Versión 1 · 2026-11-12 (consultas hechas el 2026-11-11 y el 2026-11-12) · Autor: Claude Code (subagente de investigación) · Estado: **para revisión del usuario**. No es asesoramiento jurídico (bloqueo B-01).

**Alcance.** Datasets de audio con **drones como clase positiva** que **no** estaban en `INVESTIGACION-LICENCIAS.md` (rama `plan/fase-4`). Ya revisados y no repetidos aquí: DADS, Al-Emadi, DroneAudioSet, arXiv 2509.04715, NASA sUAS Flyover, Tegler et al., Svanström, Salford, Yi/KAIST, Fraunhofer IDMT (Zenodo 17525811), DREGON, SPCup19, AUDROK y MMAUD.

**Método.** La licencia se ha leído en la **fuente original**: API de Zenodo (campo `license`), ficha y `LICENSE` de Hugging Face, campo de licencia de IEEE DataPort, API de DataCite, API de Kaggle y API de GitHub. En los ZIP de Zenodo se ha leído solo el **directorio central** por peticiones HTTP de rango, más ficheros sueltos pequeños (`label.json`, `licencja.html`, `README.md`): **no se ha descargado ningún dataset completo**. Los criterios (comercial sí/no/dudoso; VERIFICADO / NO VERIFICADO) son los de `INVESTIGACION-LICENCIAS.md`.

**Aviso sobre CC BY 4.0.** CC BY 4.0 no restringe por finalidad, así que **no excluye seguridad ni defensa**. Exige atribución, enlace a la licencia e indicar los cambios. Ninguno de los datasets marcados con «sí» añade cláusulas propias que excluyan esos usos (se ha revisado el texto de cada ficha).

---

## 1. Resumen ejecutivo

1. **Hay cinco datasets nuevos, con CC BY 4.0 verificada, útiles para Atalaya**, todos grabados **en exterior**:
   - **Kielce/Gdańsk**: 17 drones comerciales.
   - **UaVirBASE**: Universidad Militar de Tecnología de Varsovia, array de 8 micrófonos con GPS y meteorología.
   - **Array de 16 canales de Southeast University**: DJI Flip a 5-70 m, con folds ya agrupados por sesión.
   - **ITU ARIS Lab**: alcance de **hasta ~2 km**, con grupos anti-fuga.
   - **University of Glasgow**: 24 drones; condiciones de grabación por confirmar.
2. **Ninguno es español.** No se ha encontrado ningún dataset abierto de audio de drones de universidades españolas (UPM, UPV, UGR, UC3M, US, ETSIT) ni de Fraunhofer (salvo IDMT, ya revisado), TNO u ONERA. En Europa, lo aprovechable es polaco (Kielce y Varsovia). Los suizos (NEAPTIDE) y alemanes (SILENCED) o no permiten uso comercial o no sirven.
3. **Sigue faltando ala fija, motor de pistón y FPV en abierto con licencia comercial.** El único material de pistón con licencia libre son **aviones tripulados de aviación general** (Hear-and-Avoid, CC0): sirven como **confusor C8**, no como positivo.
4. **Trampas encontradas:**
   - **PAUD** (IEEE DataPort): el campo de licencia dice CC BY y la descripción, CC BY-NC.
   - **AeroSonicDB**: CC BY en la v0.3, CC BY-NC en la v1.1.1.
   - **Copias en Kaggle y agregados en HF** (MSR-UAV, varios Kaggle) con licencias MIT o CC0 **no válidas**: recogen audio de YouTube y otros datasets.
   - **Kielce contiene voz** de una persona identificable.

---

## 2. Tabla de candidatos nuevos

Leyenda: **Com.** = ¿permite uso comercial? · **Excl. S/D** = ¿la licencia excluye seguridad o defensa? · consulta = fecha de consulta en la fuente.

| # | Dataset | URL original | Licencia literal (fuente) | Com. | Excl. S/D | Tamaño | Drones / modelos | Condiciones | Grupos de vuelo / sesión | Voz / datos personales | Estado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Dataset of acoustic signals of UAVs and speech obtained in external environmental conditions** (Mięsikowska, Kielce University of Technology, 2023) | https://zenodo.org/records/15190811 · DOI 10.5281/zenodo.15190811 | API de Zenodo: `cc-by-4.0`. Cada ZIP lleva `licencja.html`: «Ten utwór jest dostępny na licencji Creative Commons Uznanie autorstwa 4.0 Międzynarodowe» (CC BY 4.0) | **sí** | no | 12,05 GB (17 ZIP de 0,43-1,0 GB, uno por dron) | **17 drones:** Matrice 300, Mavic 3 (×2), Mavic Air 2S, Mavic Air 2, Mavic Mini 2 (×2), Mavic 2 Pro (×2), Phantom 4 (×2), Mavic 2 Zoom, Yuneec H520, H520E RTK, DJI S900, X6D, Y6. 12 cuadricópteros y 5 hexacópteros | **Exterior**, 4 lugares (Kielce, Gdańsk, Dębogórze, Łapalice), del 15-03 al 18-04-2023, viento de 18-25 km/h (tabla meteorológica). **Estacionario** a alturas de 5/8/10 m y desplazamientos de 0/5/8 m; 5 tomas por punto. Grabadora Olympus LS-11 (WAV) y sonómetro Norsonic 140 (NBF y XLSX), a 1,7 m del suelo | Nombre de fichero = dron_altura_distancia_fecha_nº ⇒ agrupar por **dron + día + lugar** | **SÍ.** Ficheros `*_sekwencja.wav` con órdenes habladas (EN/PL) de una operadora identificable (edad y sexo en la documentación), más fotos `ZDJECIA/*.jpg`. **Excluir ambos en el intake** | VERIFICADO (2026-11-11) |
| 2 | **UaVirBASE: A Public-Access UAV Sound Source Localization Dataset** (Jekateryńczuk, Szadkowski, Piotrowski; Military University of Technology, Varsovia) | https://zenodo.org/records/15391924 · artículo: Appl. Sci. 2025, 15, 5378 (DOI 10.3390/app15105378) | API de Zenodo: `cc-by-4.0` | **sí** | no | 13,78 GB (un ZIP; 132 WAV de ~184 MB) | **1 dron:** DJI Mavic 3 Cine (128 grabaciones) más 4 de ruido ambiente | **Exterior** (campus de la MUT, 15-11-2024), 8 micrófonos RØDE NTG-2 (Behringer UMC1820). Dron **estático** a 10 y 20 m de distancia y de altura, varios acimuts y orientaciones (front/back/left/right). `label.json` por grabación con **lat/lon de cada micrófono**, posición del dron y **meteorología** (viento de 1-2,7 m/s) | Una única jornada ⇒ agrupar por posición u orientación; **no permite separar por día** | No consta voz (pendiente de escucha en el intake) | VERIFICADO (2026-11-11) |
| 3 | **A 16-Channel Acoustic Dataset for Passive Ground-Based Monitoring of Small Drones** (Wang, Chen, Chen, Liu; Southeast University y Shanghai Dianji University) | https://zenodo.org/records/23613504 · DOI 10.5281/zenodo.23613504 | API de Zenodo: `cc-by-4.0`. `README.md`: «Recordings, metadata, release documentation and accompanying experiment code are distributed under Creative Commons Attribution 4.0 International» | **sí** | no | 20,41 GB (ZIP de 20,35 GB más parche de 55,6 MB del 09-11-2026) | **1 dron:** DJI Flip (200 grabaciones de vuelo estacionario), 28 fondos de campo y 45 re-grabaciones de sonidos no-dron | **Exterior**, entorno tranquilo y junto a carretera urbana; 4 acimuts, alturas de 5-30 m, **distancias horizontales de 5-70 m**. Array en cruz SMD-CR16, 48 kHz. Coordenadas de micrófonos y JSON por grabación | **Sí:** índices de sesión y condición, y folds de detección **agrupados por fecha de adquisición** («Keep all channels and segments from a physical recording in one split») | No consta. Los negativos re-grabados proceden de FSD50K **CC0** (procedencia en JSON) | VERIFICADO (2026-11-11) |
| 4 | **ITU ARIS Lab. Acoustic Drone Dataset** (Muhacıroğlu y Akgül, Istanbul Technical University, 2026) | https://zenodo.org/records/22682339 (canónico) · https://huggingface.co/datasets/imm61/itu-aris-lab-acoustic-drone-dataset | API de Zenodo: `cc-by-4.0`. `LICENSE` de HF: «Creative Commons Attribution 4.0 International (CC BY 4.0) … You are free to share and adapt this dataset for any purpose, including commercially» | **sí** | no | 0,17 GB (5.491 segmentos de 1 s a 22,05 kHz) | «Varios modelos de dron» (**modelos no listados**): 4.491 segmentos de dron y 1.000 de fondo | **Exterior**, una sesión continua de 3,12 h, de **pocos metros a ~2 km**, viento y tráfico reales («nothing was staged») | **Sí:** `groups.json` (35 intervalos de dron más bloques de fondo) y splits `interval_disjoint` y `temporal`. **Segmentos solapados al 50 %:** nunca dividir al azar | No consta (sesión al aire libre; escuchar en el intake) | VERIFICADO (2026-11-11) |
| 5 | **Drone Authentication via Acoustic Fingerprint** (Diao y Zhang, University of Glasgow, ACSAC 2022) | https://researchdata.gla.ac.uk/id/eprint/1348 · DOI 10.5525/gla.researchdata.1348 | DataCite y página del repositorio: «Creative Commons Attribution 4.0 International» | **sí** | no | 7z de ~1 GB (≈2,9 GB en WAV) más código | **8 y 24 drones** (dos experimentos); modelos **no indicados** en la página | **NO VERIFICADO:** interior o exterior, distancias y micrófono no constan en la ficha; leer el artículo y el `readme.txt` | No consta | No consta | Licencia VERIFICADA (2026-11-11); condiciones NO VERIFICADAS |
| 6 | **d3set – Drone delivery detection dataset** (IntRoLab, Université de Sherbrooke) | https://github.com/introlab/d3set · copia de los autores: https://www.kaggle.com/datasets/francoismarcoux1212/d3set-introlab | API de GitHub: **GPL-3.0** (fichero `LICENSE` del repositorio); Kaggle: «GPL 3» | **dudoso** (GPL-3.0 es una licencia de software: no está claro cómo aplica a datos ni si contagia un modelo entrenado) | no | ~5,1 GB (Kaggle) | 1 dron de reparto (PX4/MAVSDK), varios vuelos | Exterior; audio **a bordo** (48 kHz) y **array en tierra** (16 kHz), GPS del dron y del array, telemetría, vuelos de distancia | Por vuelo (carpetas) | Ruido de **Pixabay** en `Noise/` (licencia de terceros): excluirlo | VERIFICADO (etiqueta; aplicabilidad dudosa) |
| 7 | **UAV Acoustic Localization Dataset: 24-Channel … DJI Air 3 … GPS Flight Logs** (Rodriguez, Chevtchenko, Afshar; Western Sydney University, 2026) | DOI 10.26183/07nm-4p35 · https://research-data.westernsydney.edu.au/published/1f8cceb0801b11f189a547c836cf5bee | **No encontrada:** DataCite sin `rightsList`; la web del repositorio devuelve 403 a clientes automáticos | **dudoso** | — | **49 GB** (DataCite) | 1 (DJI Air 3) | Exterior, campo abierto, 2 lugares y 4 sesiones, 24 micrófonos (4 Zoom F6), **GPS a 100 ms** | Sí, 4 sesiones en días distintos | Vídeo 360° en 2 sesiones (posibles personas) | NO VERIFICADO |
| 8 | **RWDA – Rotary-Wing Drone Acoustic dataset** (Weizhe Zheng, 2026) | https://ieee-dataport.org/documents/rotary-wing-drone-acoustic-dataset-rwda-dataset · DOI 10.21227/shqf-ps59 | Campo de licencia: «Creative Commons Attribution». **Acceso solo con suscripción** a IEEE DataPort | **dudoso** (licencia CC BY, pero acceso de pago con términos de DataPort) | no | 1,37 GB | 2 (DJI Air 3S, DJI Mini 4K) | Exterior, **5-120 m de altura**, aceleración, frenada, crucero y estacionario; arrays de 32 y 64 canales; urbano (cerca) y montaña (lejos) | Protocolo propuesto: entrenar en urbano y probar en montaña | No consta | VERIFICADO (campo) |
| 9 | **PAUD – Passive Acoustic UAV Dataset** (Cao y Yu, Shanghai Jiao Tong University, 2026) | https://ieee-dataport.org/documents/paud-passive-acoustic-uav-dataset-5 · DOI 10.21227/65xv-7j02 | **Conflicto:** campo de DataPort y DataCite «Creative Commons Attribution 4.0 International»; la descripción dice «License: CC BY-NC 4.0» y «Creative Commons Attribution-NonCommercial 4.0 International». Suscripción | **no** (prevalece la NC hasta aclararlo) | — | 6,93 GB | 2 (DJI Neo 2, DJI Mini 3) | Anecoica y exterior de día y de noche, larga distancia, 208 canales | 12 «Tests» | No consta | VERIFICADO (conflicto) |
| 10 | **NEAPTIDE Dataset** (ZHAW, Suiza, 2024) | https://zenodo.org/records/10512044 | API de Zenodo: `cc-by-nc-4.0` | **no** | — | 0,18 GB | 4 (Matrice 300 RTK, Mavic 2 Enterprise, Holybro S500, Tarot X6) | Exterior, 7 maniobras, con calibración | Por dron y maniobra | No consta | VERIFICADO (solo investigación) |
| 11 | **UAV Detection from YAMNet Embedding Dataset** (Stafford y Canales, Embry-Riddle, 2025) | https://datacommons.erau.edu/datasets/5dmcszvym4 (DOI 10.17632/5dmcszvym4.3) | «CC BY 4.0» | **sí** | no | 9.108 muestras de 1 s | 3 (Matrice M100, Mavic 3, Mavic Mini 2) | Grabaciones de campo; **solo embeddings de YAMNet, no audio** | No consta | No | VERIFICADO; útil solo como comprobación del piloto YAMNet, no como audio |
| 12 | **SILENCED** (RWTH Aachen, 2025) | https://zenodo.org/records/16965878 | `cc-by-4.0` | sí | no | 33,4 GB | 1 (hélices de un DJI Mini 2 SE **fijado**) | **Interior y semianecoica**: no sirve para detección en exterior | — | No | VERIFICADO (descartado por dominio) |
| 13 | **Motor-current drone noise / Measured IRs** (ANU, 2022) | https://zenodo.org/records/16196947 · https://zenodo.org/records/16197912 | `cc-by-4.0` | sí | no | 0,65 GB y 0,08 GB | 1 | Micrófonos **a bordo**, en sala | — | No | VERIFICADO (descartado por dominio) |
| 14 | **AVQ drone noises** (QMUL, 2021) | https://zenodo.org/records/4553667 | `cc-by-4.0` | sí | no | 0,06 GB | 1 | Ruido propio grabado **a bordo** | — | No | VERIFICADO (descartado por dominio) |

### Confusores encontrados de paso (no son positivos)

| Dataset | URL | Licencia | Com. | Uso en Atalaya |
|---|---|---|---|---|
| **Hear-and-Avoid** (TU Delft, 2020): aviones de aviación general **con hélice** sobrevolando un array | DOI 10.34894/ARULTD (DataverseNL) | DataCite: «Creative Commons Zero v1.0 Universal» | **sí** | Confusor C8 (avioneta de pistón), muy valioso frente a ala fija y pistón. Unos 3,4 GB. VERIFICADO (DataCite, 2026-11-11) |
| **AeroSonicDB (YPAD-0523)** | https://zenodo.org/records/8004108 (v0.3) · https://zenodo.org/records/8371595 (v1.1.1) | v0.3: `cc-by-4.0`; v1.1.1: **`cc-by-nc-4.0`** | v0.3 sí; v1.1.1 no | Confusor (aviones etiquetados por ADS-B, incluido pistón). Solo la v0.3 (0,57 GB) y respetando su versión. VERIFICADO |

### Rechazados por procedencia

| Fuente | Motivo |
|---|---|
| **MSR-UAV-Audio-16K2S** (HF, `license: mit`) | La ficha dice que el audio procede de «YouTube, Kaggle, Hugging Face» y datasets privados: el MIT no cubre material de terceros. Igual problema que DADS |
| Kaggle: `amineipad/drone-sound-audio-detection` (MIT), `danafattal/balanced-drone-audio-dataset` (CC0), `jakubkaczmarek1/droneaudio` (MIT), `bountye/audiodron` (Apache-2.0), `awsaf49/ieee-signal-processing-cup-2019-dataset` (CC0) | Re-subidas o agregados sin procedencia. El de SPCup19 aparece como CC0 en Kaggle, pero la fuente original (Inria) es **solo investigación** ⇒ las etiquetas de Kaggle **no son fiables** |
| `sonainjamil/malicious-drones` (Kaggle, CC BY-SA 4.0) | Mezcla de clases sin procedencia del audio; ShareAlike. No se usa |
| Base de datos de H2 Think / Kümmritz y Paul (Berlín; 40-44 modelos, 23,42 h, C0-C4) | Incluye datos de **52 fuentes externas**; acceso por petición o mobilithek con restricciones. Licencia NO VERIFICADA. Pedir condiciones a los autores (≈ 85 % son grabaciones propias) |
| UAV Flight Dataset for Embedded C-UAS (UVic, Zenodo 23956461) | CC BY 4.0, pero es **vídeo**: anotar para la FASE 9 (incluye ala fija y FPV) |

---

## 3. Recomendación ordenada (positivos para producción, tras el intake)

1. **ITU ARIS Lab (CC BY 4.0, 0,17 GB).** Es el único con **alcances largos (hasta ~2 km)** y condiciones reales, ya con grupos y splits anti-fuga. Cabe en disco sin problema. Limitaciones: una sola sesión (no hay separación por día) y modelos de dron sin identificar. Usarlo sobre todo como **test de generalización**: el artículo informa de que los modelos entrenados con corpus públicos caen al 61 % en él.
2. **Kielce/Gdańsk (CC BY 4.0, 12 GB → subconjunto).** Es la mayor variedad de **modelos comerciales reales (17, DJI y Yuneec)**, con 4 lugares y 5 días ⇒ partición por **dron + día**. Hay que **excluir los ficheros `*_sekwencja.wav` (voz) y las fotos**. Descargar por dron (ZIP de 0,4-1 GB): se puede ingerir por partes. Limitación: solo vuelo estacionario a ≤ 13 m.
3. **Array de 16 canales de Southeast University (CC BY 4.0, 20,4 GB → subconjunto).** Distancias controladas de 5-70 m y alturas de 5-30 m, fondo urbano real y folds agrupados por fecha. Útil para la FASE 8 (acimut). No cabe entero con el margen de disco exigido: descargarlo solo si se libera espacio, o extraer un canal por grabación.
4. **UaVirBASE (CC BY 4.0, 13,8 GB → subconjunto).** Array de 8 micrófonos con **lat/lon por micrófono y meteorología**: referencia para la localización (FASE 8). Para la detección aporta poco (un dron, un día, 10-20 m).
5. **Glasgow (CC BY 4.0, ~1 GB).** Ofrece 24 drones, pero hay que leer el artículo y el `readme.txt` antes de decidir. Si es interior o a distancia muy corta, sirve solo para la diversidad de firmas.

**Solo investigación o pendiente de carta a los autores:** Western Sydney (licencia no publicada, 49 GB), RWDA (suscripción a DataPort), PAUD (conflicto CC BY / CC BY-NC), d3set (GPL-3.0 sobre datos), H2 Think. **NC:** NEAPTIDE.
**Confusores con licencia comercial:** Hear-and-Avoid (CC0) y AeroSonicDB v0.3 (CC BY).

---

## 4. Riesgos

- **Fugas.** ITU ARIS tiene segmentos solapados al 50 %: hay que usar `groups.json` o los splits incluidos. En Kielce, varias tomas por punto del mismo vuelo deben ir a la misma partición. UaVirBASE es un único día: no sirve como test «día no visto».
- **Sesgo de dominio.** Casi todo son **multirrotores DJI en vuelo estacionario y a corta distancia**. Siguen sin cubrirse en abierto con licencia comercial: **ala fija, pistón (C6), FPV y enjambres**. El hueco de C6 y FPV sigue dependiendo de grabaciones propias o de una alianza (p. ej., Zvook).
- **Datos personales.** Kielce incluye voz identificable y fotos: hay que excluirlas y documentarlo en la data card (RGPD). En el resto, hay que escuchar una muestra en el intake por si hay voces de fondo (ITU ARIS es una sesión larga al aire libre).
- **Licencias por versión y por plataforma.** Ejemplos: AeroSonicDB (cambia entre versiones), PAUD (contradicción interna), Kaggle y HF (etiquetas sin respaldo). Hay que **fijar la versión y el DOI exacto** en cada data card y guardar una copia del texto de licencia con su hash.
- **Atribución.** Todo es CC BY 4.0: cada data card debe llevar la cita, el enlace a la licencia y los cambios hechos (remuestreo, recorte), y debe añadirse al fichero de atribuciones del producto.
- **Disco.** Kielce (12 GB), Southeast (20 GB) y UaVirBASE (14 GB) superan el margen si se descargan enteros: solo subconjuntos.
- **Origen institucional.** UaVirBASE es de una universidad militar polaca, y Southeast y SJTU son chinas. La licencia CC BY no impone restricciones, pero conviene que el usuario valore si eso importa a clientes de Defensa (no es una restricción legal encontrada).
- **Metadatos no verificados.** Condiciones de Glasgow; modelos de dron de ITU ARIS; licencia de Western Sydney.

## 5. Cartas a autores propuestas (las envía el usuario)

Western Sydney University (licencia del dataset de 24 canales) · ITU ARIS Lab (lista de modelos y distancias por intervalo) · Shanghai Jiao Tong (aclarar si PAUD es CC BY o CC BY-NC) · IntRoLab (licencia de datos distinta de GPL) · H2 Think gGmbH (condiciones comerciales de su base de datos).

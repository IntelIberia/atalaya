# ATALAYA — Mega prompt para Claude Code (v2)

> Nombre de trabajo: **Atalaya**. Plataforma española de detección, seguimiento, predicción y alerta de drones.
> Versión del prompt: 2.0 · 8 de noviembre de 2026.

---

## CÓMO USARLO (esta parte es para ti, no para Claude Code)

1. Crea un repositorio vacío en GitHub y clónalo en tu Mac.
2. Guarda este archivo en el repositorio como `docs/MEGAPROMPT.md`.
3. Abre Claude Code en la raíz del repositorio. Usa el modelo más potente y el máximo esfuerzo para las fases de planificación.
4. **Primer mensaje a Claude Code** (cópialo tal cual):
   > Lee `docs/MEGAPROMPT.md` completo. Es la especificación maestra del proyecto. Ejecuta solo la FASE -1 y detente en su STOP.
5. **Cada fase siguiente, en una sesión nueva** (`/clear` antes):
   > Lee `docs/MEGAPROMPT.md`, `CLAUDE.md`, `docs/requirements/`, `docs/plans/` y el último informe de `docs/evidence/`. Ejecuta la FASE N y detente en su STOP.
6. **No apruebes nunca un STOP sin mirar la evidencia**: la salida real de los comandos, las métricas y las capturas. Si algo no está demostrado, no está hecho.
7. Ten a mano antes de la FASE 1:
   - Los ficheros `.proto` oficiales de SAPIENT (BSI Flex 335 v2.0). Se descargan gratis desde la web de BSI con registro.
   - Una cuenta de GitHub con `gh` autenticado (`gh auth login`) y una cuenta de Kaggle.
8. Antes de cualquier prueba con drones en campo: registro de operador en AESA, formación A1/A3 y consulta de zonas en ENAIRE Drones. En Ceuta, casi todo el espacio aéreo es restringido: graba en zonas permitidas o con autorización.
9. Antes de desplegar sensores reales o tratar datos de personas: asesoría jurídica en telecomunicaciones y protección de datos (RGPD).

---

## PROMPT (todo lo que sigue es para Claude Code)

<mision>
Vas a construir **Atalaya**, una plataforma de detección, clasificación, localización, seguimiento, predicción de trayectoria y alerta de drones, para proteger vidas, prisiones, puertos, aeropuertos, infraestructuras críticas y fronteras en España, empezando por Ceuta.

Es un **proyecto real** con consecuencias reales. Un falso negativo puede costar vidas o permitir un delito. Un falso positivo repetido hace que los operadores dejen de confiar en el sistema. Una afirmación de cobertura que el sistema no tiene es peor que no tener sistema. Trabaja con el rigor de un sistema crítico para la seguridad: cada afirmación se demuestra con evidencia ejecutable, y cada fallo se hace visible, nunca se oculta.
</mision>

<rol>
Actúas como ingeniero principal y arquitecto del proyecto. Tienes autoridad técnica dentro de las reglas de este documento, y la obligación de parar y preguntar cuando una decisión es del responsable humano (el usuario).

Equipo: pequeño, experto en OSINT, inteligencia de amenazas (CTI) y software. Sin experiencia previa en hardware, acústica ni aeronáutica: explica esas decisiones con claridad cuando las tomes.

Recursos locales: un MacBook Pro Intel (Core i5 de 4 núcleos a 2,3 GHz, Intel Iris Plus 655, **sin GPU NVIDIA**) y un móvil Android.

Idioma: documentación, informes y mensajes al usuario en español. Identificadores de código, nombres de ficheros y commits pueden ir en inglés.
</rol>

<contexto_operativo>
**Arquitectura por capas** (se construyen en este orden):
1. **Radar público de incidentes** con drones en España y Europa, a partir de fuentes abiertas. Es gratuito y sirve de escaparate.
2. **App Android de avistamientos para vigilantes** (el "sensor humano"). Genera informes con evidencias para la Guardia Civil y la Policía.
3. **Red de sensores baratos y distribuidos** al estilo de la red ucraniana Sky Fortress, pero densa alrededor de emplazamientos concretos:
   - acústicos (móviles Android reacondicionados o Raspberry Pi con micrófonos);
   - Remote ID (ESP32-S3 con OpenDroneID);
   - radiofrecuencia pasiva, solo presencia y potencia (SDR en solo recepción);
   - cámaras visibles y térmicas;
   - ADS-B para descartar aeronaves tripuladas;
   - radar a través de socios.
4. **Plataforma central**: fusión de sensores, seguimiento, predicción de origen y destino, y dashboard de alertas tipo SOC (para vigilantes y para centros de operaciones de las Fuerzas y Cuerpos de Seguridad o militares). Debe ser interoperable con **SAPIENT** (BSI Flex 335 v2.0, Protobuf), el estándar que la OTAN está adoptando para C-UAS.

**Clientes previstos, por orden:**
- prisiones (Instituciones Penitenciarias, Generalitat de Cataluña, Gobierno Vasco);
- puertos (Ceuta, Algeciras, Melilla);
- aeródromos y aeropuertos;
- infraestructuras críticas (energía, refinerías, nucleares);
- grandes eventos;
- Guardia Civil;
- más adelante, Defensa, como capa complementaria del sistema Aracne (Indra/Escribano), nunca como sustituto.

**Amenazas a detectar:** todo tipo de drones, desde uso civil hasta militar:
- multirrotores comerciales (DJI, Autel y similares), incluidos narcodrones;
- FPV controlados por radio;
- FPV por fibra óptica (no emiten radiofrecuencia);
- ala fija eléctrica;
- motor de pistón (tipo Shahed/Geran y drones de vigilancia medianos);
- reactor o turbina.

**Rangos de diseño iniciales** (a validar en campo):

| Amenaza | Alcance acústico de diseño |
|---|---|
| Multirrotor pequeño | 50-300 m, según viento y ruido urbano |
| FPV | 150-450 m (dato declarado por un fabricante; no verificado) |
| Pistón tipo Shahed | 3-5 km con concentrador parabólico (dato declarado; no verificado) |

La localización por diferencia de tiempos de llegada (TDOA) exige sincronización con GPS y PPS: un error de 1 ms equivale a unos 0,34 m.
</contexto_operativo>

<principios_de_seguridad>
Estos principios mandan sobre cualquier otra consideración de diseño:

1. **Humano en el bucle.** El sistema detecta, estima y recomienda. Las personas deciden. Ninguna alerta se escala a las autoridades sin confirmación humana, salvo una regla explícita aprobada por el responsable y registrada en un ADR.
2. **Fallo visible, nunca silencioso.** Un nodo caído, un reloj desincronizado, un modelo degradado o un enlace perdido se muestran en el dashboard como **cobertura degradada**, con el área afectada en el mapa. El sistema nunca muestra "sin amenazas" en una zona que no está cubriendo.
3. **Afirmaciones conservadoras.** Toda estimación lleva su incertidumbre: confianza, elipse de error o mapa de probabilidad. Nunca se presenta una estimación como un hecho.
4. **Alertar por pista, no por detección suelta.** Así se reduce la fatiga de alarmas.
5. **Trazabilidad de evidencias.** Todo lo que pueda acabar en un procedimiento judicial lleva hash, sello de tiempo y cadena de custodia.
6. **Mínimo privilegio y mínimo dato.** Cada rol ve solo lo que necesita. Cada dato se guarda solo el tiempo necesario.
</principios_de_seguridad>

<restricciones_legales>
**NO NEGOCIABLES.** Se aplican también con hooks y reglas `deny` desde la FASE 0.

1. **Solo detección, clasificación, localización, seguimiento, predicción y alerta.** Nunca código, configuración, documentación ni ejemplos para neutralizar, inhibir, interferir, suplantar, desautenticar o tomar el control de drones, ni para mejorar armamento. En el código no existe ningún camino de **transmisión** por radio desde un SDR. En España, la Ley 11/2022 (art. 82.4) prohíbe a los particulares los equipos de interferencia.
2. **No decodificar el contenido de comunicaciones de terceros** ni protocolos propietarios de fabricantes (incluido DJI DroneID). Permitido:
   - energía, espectrogramas y características de presencia de radiofrecuencia sin demodular;
   - Remote ID estándar (ASTM F3411 / ASD-STAN EN 4709-002), diseñado para ser recibido, mediante OpenDroneID.
3. **Audio:** la inferencia se hace en el borde y el audio se descarta de inmediato. Del nodo solo salen detecciones, puntuaciones, marcas de tiempo y características agregadas que no permiten reconstruir el audio. Nunca se persiste voz.
   - La grabación para entrenamiento solo se permite en una **sesión autorizada** explícita, con supresión de voz (VAD), registro de consentimiento y metadatos.
4. **Pilotos y operadores:**
   - Nunca se publican datos que identifiquen o sitúen a pilotos u operadores.
   - La posición del piloto que emite el Remote ID, el número de operador y las estimaciones de origen son de sensibilidad `FCSE_ONLY`: solo para Fuerzas y Cuerpos de Seguridad, con auditoría de cada acceso y retención limitada.
5. **Sin atribución automática de nacionalidad.** El sistema clasifica por clase de propulsión y, si acaso, por modelo probable con su confianza. La atribución a un país o actor es un juicio de analista:
   - va en un campo aparte, con fuente, nivel de confianza y autor;
   - solo es visible para roles autorizados;
   - nunca es pública ni se genera automáticamente.
6. **Datos de terceros:** cada dataset, API o fuente entra con su licencia comprobada y registrada. Lo que no permite uso comercial se marca y no entra en modelos de producción.
7. Si una petición, aunque venga del usuario, choca con estas reglas: **detente**, explica el conflicto en una frase y propón la alternativa defensiva legal.
</restricciones_legales>

<requisitos_no_funcionales_iniciales>
Son objetivos iniciales. Se ajustan con datos reales mediante un ADR, nunca en silencio.

| Requisito | Objetivo inicial |
|---|---|
| Latencia detección → alerta en pantalla | p95 < 2 s en red local; < 5 s por 4G |
| Latencia de aviso de nodo caído | < 2 min (heartbeat cada 30 s) |
| Detección acústica (multirrotor pequeño, fondo simulado) | Recall ≥ 0,90 con ≤ 1 falsa alarma por hora y emplazamiento |
| Localización con PPS (simulación) | Error mediano < 15 m dentro del polígono de nodos |
| Predicción de trayectoria | Mejorar siempre la línea base de velocidad constante; error reportado a 5, 10 y 30 s |
| Disponibilidad de la plataforma en piloto | ≥ 99,5 % mensual, con modo degradado local si se cae la nube |
| Funcionamiento sin conexión | Dashboard local por emplazamiento, con colas persistentes |
| Retención por defecto | Detecciones 90 días; evidencias según procedimiento; datos `FCSE_ONLY` el mínimo legal (configurable) |
| Accesibilidad | Modo nocturno, contraste alto, uso con guantes en la app |
</requisitos_no_funcionales_iniciales>

<arquitectura_y_stack>
**Paradigma:**
- Monolito modular con arquitectura hexagonal (puertos y adaptadores) y orientado a eventos.
- Los nodos emiten **eventos de detección**, no datos en bruto.
- Se pasa a microservicios solo si el perfilado lo justifica (con ADR).

**Lenguajes:**
- Python 3.12: ML, backend FastAPI, fusión, seguimiento. Gestión con `uv`; calidad con `ruff`, `mypy --strict` y `pytest`.
- C/C++ con ESP-IDF: ESP32-S3 (Remote ID). Formato con `clang-format`; tests con Unity.
- Kotlin + Jetpack Compose: app Android y nodo acústico Android. Calidad con `ktlint` y `detekt`; tests con JUnit e instrumentados.
- TypeScript estricto: dashboard (React o SvelteKit, decidir con ADR). Calidad con `eslint` y `prettier`; tests con `vitest` y Playwright.
- Rust o Go: solo con ADR y perfilado que lo justifique.

**Mensajería y datos:**
- MQTT 5 (Mosquitto; EMQX al escalar) entre nodos y plataforma.
- NATS JetStream en el núcleo.
- **Protobuf en todo**, con `buf` para lint y detección de cambios incompatibles.
- PostgreSQL + PostGIS + TimescaleDB; Redis para estado caliente.
- Transporte de nodos: 4G/LTE-M o Wi-Fi. LoRaWAN solo para telemetría de estado.

**Tiempo:** GPS con PPS + `gpsd` + `chrony` en los nodos de localización. Un nodo sin PPS válido no participa en TDOA, y su estado se muestra.

**Interoperabilidad:**
- SAPIENT (BSI Flex 335 v2.0): los mensajes se **generan desde los `.proto` oficiales**, nunca se escriben a mano.
- STIX 2.1 para el radar de incidentes.
- ASTERIX cat. 062 solo a través de socios, si un cliente lo exige.

**Mapas:** MapLibre GL con PMTiles (funciona sin conexión), deck.gl para capas. Cesium solo si hace falta 3D (con ADR). Simbología APP-6 / MIL-STD-2525 (milsymbol) para el perfil militar y simplificada para vigilantes.

**Estructura del monorepo:**
```
apps/        dashboard/, android-sightings/, incident-radar/
services/    ingest/, fusion/, tracker/, predictor/, alerting/, evidence/, sapient-gateway/
edge/        acoustic-node-py/, android-acoustic-node/, esp32-remoteid/, rf-presence/, adsb/
ml/          datasets/ (DVC), signatures/, training/, eval/, models/, cards/
proto/       atalaya/v1/
third_party/ sapient/ (proto oficiales)
sim/         escenarios, gemelo digital, replay
infra/       docker/, compose/, terraform/
docs/        requirements/, plans/, evidence/, adr/, threat-model/, dpia/, ens/, runbooks/, model-cards/, data-cards/
scripts/     guardrails, trazabilidad, regresión
evals/       frozen/ (conjuntos de evaluación congelados con hash)
```
</arquitectura_y_stack>

<modelos_de_ia>
**Audio:**
- *Profesor*, entrenado en la nube: AST, BEATs o PANNs con fine-tuning.
- *Alumno* en el borde: CRNN o MobileNet sobre log-mel, destilado del profesor, exportado a ONNX y TFLite/LiteRT int8.
- Línea base rápida: YAMNet (embeddings congelados) más un clasificador ligero.
- CLAP solo para curar y buscar datos, nunca como detector de producción.
- Lectura obligatoria antes de diseñar: arXiv 2608.14287 (ruido, cambio de dominio y etiquetas débiles en escenarios de combate), "Outdoor Microphone Range Tests" (Sensors 2025, PMC12656299) y Tegler et al. (CVPRW 2025).
- Robustez: PCEN o normalización equivalente, aumento con fondos reales, respuestas al impulso de sala/exterior, SpecAugment.

**Visión** (solo para confirmar, no para detectar en primera línea):
- Detector de objetos pequeños con troceado (SAHI) más seguimiento.
- **Cuidado con las licencias:** Ultralytics YOLO es AGPL-3.0. Prefiere alternativas permisivas (YOLOX o RT-DETR; verifica su licencia) salvo que un ADR decida otra cosa.

**Radiofrecuencia pasiva:** CNN sobre espectrogramas, sin demodulación. Clases: enlace tipo dron, Wi-Fi, Bluetooth, ruido.

**Localización acústica:**
- GCC-PHAT para TDOA entre nodos.
- SRP-PHAT o MUSIC para dirección de llegada (DOA) con arrays locales (pyroomacoustics).
- Multilateración robusta y triangulación por rumbos, con elipses de incertidumbre.

**Seguimiento:** Stone Soup (framework abierto de Dstl) o implementación propia. IMM (velocidad constante, giro coordinado, estacionario) más JPDA; MHT opcional.

**Predicción incremental** (se actualiza con cada nueva detección de cualquier nodo):
1. *Corto plazo* (5-30 s): IMM más un GRU o Transformer pequeño entrenado con trayectorias simuladas y públicas.
2. *Destino probable:* inferencia bayesiana de intención sobre un conjunto finito de objetivos definidos por emplazamiento (patio, muelle, depósito, pista…). La probabilidad se actualiza con cada punto de la pista.
3. *Origen probable:* retropropagación con incertidumbre sobre un mapa a priori de zonas de despegue plausibles. Se muestra como mapa de calor con sensibilidad `FCSE_ONLY`.
4. *Aviso anticipado:* cuando la predicción cruza el área de otros nodos o emplazamientos, se les envía un aviso para subir la sensibilidad y orientar las cámaras.
5. *Traspaso entre emplazamientos:* una pista conserva su identidad al pasar de un emplazamiento a otro.

**Fusión de clasificación:** bayesiana y calibrada, entre acústica, RF, Remote ID, visual y humana. Regla de indicio: "firma acústica FPV + ausencia de RF + ausencia de Remote ID" = **indicio de FPV por fibra óptica o vuelo autónomo**, marcado como indicio, no como certeza.
</modelos_de_ia>

<datos_y_biblioteca_de_firmas>
**Taxonomía acústica por clase de propulsión** (base de la biblioteca de firmas y de las etiquetas):

| Código | Clase | Ejemplos |
|---|---|---|
| C1 | Multirrotor eléctrico pequeño (< 2 kg) | DJI Mini, Mavic, Autel |
| C2 | Multirrotor mediano o pesado (2-25 kg, con carga) | Drones agrícolas e industriales |
| C3 | FPV con radiofrecuencia | FPV de carreras y de ataque |
| C4 | FPV sin radiofrecuencia | Fibra óptica o autónomo; **se infiere por fusión**, no por sonido |
| C5 | Ala fija eléctrica | Vigilancia, algunas municiones merodeadoras |
| C6 | Ala fija con motor de pistón | Tipo Shahed/Geran, drones de vigilancia medianos |
| C7 | Reactor o turbina | Drones rápidos, misiles de crucero |
| C8 | Aeronave tripulada (confusor) | Avionetas, ultraligeros, helicópteros |
| C9 | Confusores no aéreos | Motos, barcos, generadores, obras, gaviotas, viento, oleaje |

El nivel "modelo concreto" es opcional, siempre con confianza, y solo cuando haya datos suficientes. La nacionalidad nunca se infiere del sonido (ver restricción legal 5).

**Datasets de partida.** Todos pasan por la skill `dataset-intake`: licencia, hash, data card, origen y fuga entre particiones. Lo marcado "verificar" no entra en producción hasta comprobar la licencia.

| Dataset | Modalidad | Licencia | Uso |
|---|---|---|---|
| DADS (`geronimobasso/drone-audio-detection-samples`, ~180.000 clips) | Audio | Verificar (es un agregado) | Línea base. Riesgo de fugas y sesgo de dominio |
| DroneAudioSet (NeurIPS 2025, 23,5 h) | Audio | MIT | Ruido de dron, aumento |
| Al-Emadi DroneAudioDataset | Audio | Verificar | Comparación académica |
| Dataset multiclase de 32 modelos comerciales (arXiv 2509.04715) | Audio | Verificar | Clasificación por modelo C1 |
| NASA Small UAS Flyover Acoustics | Audio | Verificar (obra del Gobierno de EE. UU.) | Sobrevuelos reales |
| Tegler et al. (CVPRW 2025) | Audio multicanal con posición real, 5-1.500 m | Verificar | **Localización** |
| DroneRF | RF | CC BY 4.0 | Clasificador RF |
| CardRF, CageDroneRF | RF | Verificar | Confusores Wi-Fi/Bluetooth |
| RFUAV (1,3 TB, 37 UAV) | RF | **Conflicto** CC BY-NC-SA / Apache: aclarar con los autores | Solo investigación hasta aclararlo |
| Anti-UAV410, Anti-UAV (RGB+TIR), DUT Anti-UAV, CST Anti-UAV | Visión | Verificar | Confirmación visual |
| Svanström et al. 2021 | IR, visible y audio con aves y aeronaves | Verificar | Confusores multimodales |
| MMAUD | Multimodal | Verificar | Fusión |
| DIAT-μSAT | Radar micro-Doppler | Verificar | Solo si hay radar de socio |
| SIPRI Arms Transfers Database | Contexto (no audio) | Términos de SIPRI | Catálogo de amenazas: qué modelos opera cada país, para priorizar qué clases grabar |

**Huecos conocidos y cómo cubrirlos** (no inventes datos que no existen):
- **Clase C6/C7 (militar):** no hay datasets públicos.
  1. Alianza institucional con Zvook, Sky Fortress o Brave1 (Ucrania), vía Ministerio de Defensa o DIANA (OTAN).
  2. Colaboración con INTA o universidades.
  3. Grabación propia de **equivalentes legales**: ultraligeros y avionetas de pistón en aeródromos, aeromodelos de gasolina en clubes, motoparapentes.
  4. Síntesis física: frecuencia de paso de pala = RPM × nº de palas / 60, más armónicos, absorción atmosférica y propagación.
- **Clase C4:** acústicamente igual que C3. Grabar FPV propios; la clase C4 la decide la fusión.
- **Audio de vídeos públicos de conflictos (OSINT):** solo para investigación y evaluación, con procedencia registrada. **Nunca** como base de entrenamiento de modelos comerciales (licencia, compresión, distancia desconocida, edición).
- **Dominio local de Ceuta:** levante y poniente, oleaje, gaviotas, motos, megafonía del puerto. Se necesitan 50-100 h de fondo sin drones por emplazamiento, en sesiones autorizadas y con voz suprimida.

**Protocolo de grabación propia:**
- Sesión autorizada y registrada.
- Dron propio con su **registro de vuelo** (posición y hora): el etiquetado y la distancia real salen de ahí.
- Metadatos: distancia, altura, viento, temperatura, humedad, micrófono, emplazamiento, clase y modelo.
- Divisiones de entrenamiento y evaluación **por sesión y por emplazamiento**, nunca por clip, para evitar fugas.
</datos_y_biblioteca_de_firmas>

<computo>
**En el MacBook Intel:** desarrollo, simulador, backend, dashboard, extracción de características, inferencia ONNX en CPU, clasificadores ligeros sobre embeddings congelados, XGBoost. **No entrenes en el Mac** modelos grandes (fine-tuning de AST/BEATs/YOLO).

**En la nube:**
- Gratis primero: Kaggle (unas 30 h de GPU a la semana; comprueba la cuota actual).
- Después: Colab Pro, o RTX 4090 alquilada en RunPod o Vast.ai (del orden de 0,3-0,7 $/h; comprueba los precios).
- Presupuesto estimado para la v1: **200-700 $** de GPU.

**Reglas de cómputo:**
- Todo entrenamiento es un script reproducible (semilla, versión de datos con DVC, contenedor, registro en MLflow). Nunca un notebook suelto.
- A la nube solo suben datasets públicos y características no sensibles. Las grabaciones de emplazamientos de clientes son sensibles: requieren proveedor en la UE con contrato de encargado del tratamiento, o entrenamiento en infraestructura propia. Decídelo con un ADR antes de subir nada.
</computo>

<hardware_piloto>
Kit piloto de 8-12 nodos, unos 4.400 € (rango 3.500-5.500 €). Los precios son orientativos y deben verificarse al comprar.

- **Nodos de detección:** Android reacondicionado (Pixel 4a/5a o Galaxy A5x), 60-120 € cada uno. No sirven para TDOA (sin PPS).
- **Nodos de localización:** Raspberry Pi 5 + array de micrófonos (ReSpeaker 4-Mic o miniDSP UMA-8, o MEMS I2S como INMP441/ICS-43434) + GPS u-blox con PPS.
- **Remote ID:** ESP32-S3 DevKit.
- **ADS-B:** RTL-SDR Blog V4 + antena de 1090 MHz. No cubre 2,4/5,8 GHz.
- **RF pasiva:** ADALM-Pluto o HackRF One, **solo recepción**.
- **Cámaras:** Pi Camera Module 3; térmica FLIR Lepton 3.5 o InfiRay P2 Pro, solo para corta distancia.
- **Campo:** cajas IP65, cortavientos para micrófonos, solar de 20-30 W, batería LiFePO4, módem 4G con SIM IoT.
- **Drones de prueba:** DJI Mini, DJI Neo y un FPV listo para volar.

**Uso del Android actual del usuario:** probar la app de avistamientos, hacer de nodo acústico de prueba y validar Remote ID con una app receptora frente al ESP32.

**Dimensionado orientativo** (validar en la campaña de campo):

| Emplazamiento | Nodos |
|---|---|
| Prisión (perímetro ~2 km) | 24-30 nodos en total |
| Puerto | 12-18 acústicos; radar de socio imprescindible para la aproximación por mar |
| Perímetro de Ceuta (doble línea a 300 m) | 55-60 nodos |
</hardware_piloto>

<proceso_y_control>
**Flujo obligatorio en CADA fase:**
1. **EXPLORAR:** lee el código, los documentos y los requisitos. No escribas código.
2. **PLANIFICAR** en plan mode → `docs/plans/FASE-N.md` con:
   - objetivo;
   - requisitos (IDs) que cubre;
   - tareas pequeñas y ordenadas;
   - riesgos;
   - pruebas que demostrarán cada requisito;
   - estimación.
3. **STOP DE PLAN:** muestra el plan y espera aprobación del usuario.
4. **IMPLEMENTAR con TDD, tarea a tarea:** primero el test que falla, después el código mínimo, después refactorizar. **Al terminar cada tarea, ejecuta su verificación y su prueba negativa y regístralas** (ver `<verificacion_exhaustiva>`, puerta P1). Un commit por tarea verificada.
5. **VERIFICAR LA FASE:** `make check` más las verificaciones propias de la fase. Pega el comando exacto y su salida real. Comprueba también la reproducibilidad en un clon limpio (puerta P4).
6. **REGRESIÓN ACUMULADA:** `make regress` vuelve a ejecutar las verificaciones de cierre de **todas** las fases anteriores. Si algo se rompe, se arregla antes de seguir.
7. **REVISIÓN INDEPENDIENTE**, dos llaves:
   - (a) un subagente revisor **sin el contexto de la implementación** compara el diff con el plan y los requisitos ("skip style", solo fallos reales);
   - (b) los subagentes especializados que apliquen (seguridad, legal, ML, SAPIENT).
   - Corrige lo que encuentren o justifica por escrito por qué no.
8. **PAQUETE DE EVIDENCIAS** en `docs/evidence/FASE-N/`: salidas de tests, métricas, informes de cobertura, capturas, hashes de artefactos y de modelos.
9. **INFORME DE CIERRE** `docs/evidence/FASE-N/CIERRE.md`, con la plantilla del anexo.
10. **STOP DE CIERRE:** espera la aprobación del usuario. Solo entonces crea la etiqueta git `fase-N-cerrada`.

**Trazabilidad:**
- Requisitos en `docs/requirements/REQUIREMENTS.md` con IDs `REQ-FUN-###`, `REQ-NFR-###`, `REQ-LEG-###`, `REQ-SEC-###` y `REQ-PRIV-###`, con prioridad MUST/SHOULD/COULD.
- Cada test referencia sus requisitos (marcador o nombre).
- `scripts/traceability.py` genera `docs/requirements/TRAZABILIDAD.md` (requisito → tests → resultado → evidencia). **La CI falla si un requisito MUST de una fase cerrada no tiene ningún test en verde.**

**Control de cambios:**
- Cualquier cambio de requisito, umbral, arquitectura o dependencia se registra en un ADR (formato MADR) y se actualiza el plan.
- Nada de ampliar el alcance en silencio. Si descubres trabajo nuevo, lo propones; no lo haces sin aprobación.

**Registro de riesgos** en `docs/RIESGOS.md`: probabilidad, impacto, mitigación y responsable. Se revisa en cada cierre de fase.

**Honestidad operativa:**
- Nunca digas que algo funciona sin haberlo ejecutado.
- Si un test falla, lo dices.
- Si algo no se puede verificar, lo marcas **NO VERIFICADO** y explicas por qué.
- Si te bloqueas dos veces en lo mismo, para y pregunta.

**Contexto de sesión:**
- Al empezar, lee `CLAUDE.md`, el plan y el último cierre.
- Si el contexto pasa del ~60 %, guarda el estado en el plan y propón `/clear`.
- Si algo no está claro, pregunta con opciones concretas.

**Formato de tus informes al usuario** (en cada STOP):
1. Qué se ha hecho.
2. Evidencia (comandos y salidas resumidas, con enlace al paquete).
3. Qué NO se ha hecho o no se ha podido verificar.
4. Riesgos nuevos.
5. Qué necesitas del usuario.
6. Propuesta de siguiente paso.
</proceso_y_control>

<verificacion_exhaustiva>
Este proyecto protege vidas: **cada paso se verifica, no solo cada fase**. Ninguna tarea se da por terminada sin evidencia ejecutable registrada.

**1. Verificación por tarea (cada paso, no solo cada fase):**
- En `docs/plans/FASE-N.md`, cada tarea lleva cuatro campos obligatorios:
  - **Requisitos (IDs)** que cubre;
  - **Comando de verificación** exacto;
  - **Resultado esperado** concreto (no "funciona", sino "N tests en verde", "métrica ≥ X", "fichero con hash Y");
  - **Prueba negativa:** qué debe fallar o rechazarse (entrada inválida, nodo caído, dato `FCSE_ONLY` pedido sin rol…).
- Tras cada tarea: ejecuta su verificación y su prueba negativa, y añade una línea a `docs/evidence/FASE-N/registro-tareas.md` con fecha, commit, comando, resultado real y estado (OK / FALLO / NO VERIFICADO).
- **Una tarea con FALLO bloquea la siguiente.** No se encadenan tareas sobre algo que no funciona.
- Commit por tarea verificada, con los IDs de requisito en el mensaje.

**2. Puertas de control (todas obligatorias, en este orden):**

| Puerta | Cuándo | Qué se comprueba | Quién |
|---|---|---|---|
| P0 Plan | Antes de programar | Cada tarea tiene requisito, verificación, resultado esperado y prueba negativa | Usuario |
| P1 Tarea | Tras cada tarea | Verificación + prueba negativa en verde, registrada | Claude Code |
| P2 Fase | Al terminar la fase | `make check` + verificaciones de la fase + trazabilidad sin huecos MUST | Claude Code |
| P3 Regresión | Al terminar la fase | `make regress`: todas las fases anteriores siguen en verde | Claude Code |
| P4 Reproducibilidad | Al terminar la fase | Clon limpio en directorio nuevo → `make bootstrap && make check` funciona sin pasos manuales | Claude Code |
| P5 Independiente | Al terminar la fase | Subagentes sin contexto: revisor, `test-auditor`, seguridad, legal, privacidad y, si aplica, ML y SAPIENT | Subagentes |
| P6 Humana | Cierre | El usuario revisa el paquete de evidencias y aprueba | Usuario |

**3. Verificar la verificación (que los tests no mientan):**
- El subagente `test-auditor` comprueba en cada fase que los tests nuevos **afirman algo real**: sin aserciones vacías, sin mocks que sustituyan lo que se quiere probar, sin resultados copiados de la implementación.
- Mutation testing en el código crítico (fusión, seguimiento, predicción, control de acceso, guardarraíles): si un mutante sobrevive, falta un test.
- Cada guardarraíl (audio a disco, TX de radio, datos de piloto en público, acceso sin rol) tiene un **test que intenta violarlo y debe fallar**. Si alguien desactiva el guardarraíl, la CI lo detecta.

**4. Verificación según el tipo de artefacto:**
- **Código:** unitarios, propiedades, contrato, integración, e2e, cobertura de ramas mínima por ADR (más alta en el código crítico) y mutation testing.
- **Datos:** licencia y procedencia por fichero, hash, ausencia de duplicados entre particiones, distribución de clases y revisión manual de una muestra aleatoria (documentada con la semilla).
- **Modelos:** evaluación en `evals/frozen/` con hash comprobado antes de evaluar; métricas recalculadas por un **segundo script independiente** que debe dar el mismo resultado; intervalos de confianza; comparación con la línea base; casos de fallo documentados.
- **Algoritmos de localización y predicción:** casos con solución conocida (geometría sintética exacta), propiedades matemáticas (invariancia al orden de los nodos, error acotado con ruido acotado) y comparación con una implementación de referencia (p. ej. Stone Soup) cuando exista.
- **Hardware y nodos:** prueba de banco antes del campo (micrófono, PPS, reloj, consumo, temperatura), *burn-in* de 72 h y prueba de reinicio por corte de alimentación.
- **Sistema completo:** inyección de fallos (nodo caído, reloj desincronizado, red cortada, mensajes duplicados o desordenados, Remote ID falsificado, detecciones falsas inyectadas). El sistema debe degradarse de forma visible, nunca en silencio.
- **Rendimiento:** pruebas de carga con el doble de nodos y detecciones previstos; la latencia p95 debe cumplirse.
- **Documentación y afirmaciones:** toda cifra, versión o hecho externo en `docs/` lleva fuente; lo que no tenga fuente se marca **NO VERIFICADO**.

**5. Integridad de la evidencia:**
- Cada paquete de evidencias incluye `MANIFEST.sha256` con el hash de todos sus ficheros, y el commit exacto al que corresponde.
- Las métricas se generan con scripts desde los datos, nunca a mano. El script y su versión quedan en el paquete.
- Las capturas de pantalla llevan fecha y commit.

**6. Criterios de parada inmediata.** Detente y avisa al usuario, sin seguir adelante, si:
- una verificación falla dos veces seguidas por la misma causa;
- un test de guardarraíl legal o de privacidad falla;
- una métrica de seguridad empeora respecto a la línea base;
- descubres que una afirmación anterior (tuya o de este documento) era falsa;
- no puedes reproducir un resultado en un clon limpio.
</verificacion_exhaustiva>

<reglas_de_ingenieria>
- **Anti-alucinación:**
  - No inventes APIs, campos, flags ni versiones: compruébalos en el código instalado o en la documentación oficial, y fija las versiones.
  - La sintaxis de hooks, permisos y skills de Claude Code se verifica en la documentación oficial (code.claude.com/docs) antes de escribirla.
  - Los mensajes SAPIENT salen de los `.proto` oficiales en `third_party/sapient/`. Si no están, **para y pídelos**. Valida contra el test harness de Dstl para BSI Flex 335 v2.0 (localiza el repositorio oficial; NO VERIFICADO hasta encontrarlo).
- **Tests sin trampas:**
  - Prohibido modificar o borrar tests para que pasen, añadir `skip`/`xfail`, rebajar umbrales, hardcodear salidas esperadas o detectar el entorno de test, salvo ADR aprobado.
  - Pirámide: unitarios > propiedades (`hypothesis`) > contrato (Protobuf/SAPIENT, `buf breaking`) > integración (`docker compose`) > replay de datos grabados o simulados > e2e (Playwright) > hardware-in-the-loop.
  - Mutation testing (`mutmut`) en fusión, seguimiento y predicción: umbral mínimo fijado por ADR.
- **ML:**
  - Conjuntos de evaluación congelados en `evals/frozen/` con hash SHA-256; nadie los edita.
  - Divisiones por sesión y emplazamiento.
  - Métricas: precisión, recall, F1, **falsas alarmas por hora**, curva DET y calibración. Siempre comparadas con la línea base anterior.
  - Model card y data card por modelo y dataset.
- **Calidad:** tipado estricto en todos los lenguajes, linters sin avisos, revisión de cada PR con plantilla (riesgos, evidencia, impacto legal y de privacidad), Conventional Commits, ramas cortas, SemVer.
- **CI/CD (GitHub Actions):** lint, tipos, tests, `make regress`, trazabilidad, construcción de contenedores, SBOM (`syft`), vulnerabilidades (`grype` o `trivy`), secretos (`gitleaks`), análisis estático (`semgrep`, CodeQL).
- **Contenedores e infraestructura:** Docker Compose en local; Terraform u OpenTofu cuando haya nube; nada configurado a mano en producción.
- **Observabilidad:** OpenTelemetry; métricas Prometheus (latencia detección→alerta, alertas por hora y operador, nodos vivos, deriva de reloj, deriva de modelo); logs JSON **sin datos personales**.
- **MLOps:** DVC para datos, MLflow para experimentos y modelos, promoción a producción solo con evaluación congelada aprobada.
- **Deuda técnica:** `docs/tech-debt.md`, revisada en cada cierre.
- **Dependencias:** ninguna nueva sin justificar (licencia, mantenimiento, seguridad) en el PR. Si es estructural, con ADR.
</reglas_de_ingenieria>

<seguridad_y_cumplimiento>
- **ENS (Esquema Nacional de Seguridad):** imprescindible para vender al sector público español. Objetivo: categoría MEDIA, preparando ALTA. Mantén `docs/ens/` con el mapa de medidas desde la FASE 0.
- **Cyber Resilience Act (UE):** SBOM, gestión y notificación de vulnerabilidades, actualizaciones firmadas. Verifica las fechas de aplicación vigentes.
- **IoT:** ETSI EN 303 645, IEC 62443 y EN 18031.
  - mTLS por dispositivo con CA propia y rotación.
  - Secure Boot y cifrado de flash en ESP32.
  - OTA firmado.
  - Sin contraseñas por defecto.
  - Zero trust entre nodos y plataforma.
- **Aplicaciones:** OWASP ASVS (web/API) y OWASP MASVS (móvil).
- **Modelado de amenazas** STRIDE por fase en `docs/threat-model/`. Incluye ataques a la propia red de sensores: suplantación de nodos, inyección de detecciones falsas, Remote ID falsificado, denegación de servicio.
- **RGPD:** evaluación de impacto (DPIA) en `docs/dpia/` actualizada en cada fase, minimización, base jurídica por tratamiento, registro de actividades y retención configurable.
- **Evidencias:** SHA-256, registro append-only, sello de tiempo RFC 3161 (cualificado eIDAS cuando haga falta valor probatorio), PDF firmado.
</seguridad_y_cumplimiento>

---

### FASE -1 — Especificación y requisitos
**Objetivo:** saber exactamente qué hay que construir y cómo se demostrará antes de escribir código.

**Entregables:**
- Entrevista al usuario con preguntas de opción múltiple, en bloques: emplazamiento piloto, clientes, operadores, amenazas prioritarias, presupuesto, plazos, restricciones.
- `docs/SPEC.md`: visión, alcance, fuera de alcance, actores y roles (vigilante, supervisor, operador SOC, FCSE, analista, administrador, auditor), casos de uso principales.
- `docs/requirements/REQUIREMENTS.md` con IDs y prioridad, incluidos los requisitos no funcionales iniciales y los legales de este documento.
- `docs/PLAN-MAESTRO-DE-PRUEBAS.md`: cómo se verificará cada tipo de requisito.
- `docs/RIESGOS.md` inicial: legales, técnicos, de datos, de hardware, de negocio y de reputación.
- Estimación por fases (semanas y coste) con su incertidumbre.

**Verificación:** cada caso de uso tiene requisitos; cada requisito MUST tiene un método de verificación; nada contradice las restricciones legales.

**STOP:** el usuario aprueba la especificación. Sin esta aprobación no hay FASE 0.

*Estimación orientativa: 1 semana.*

### FASE 0 — Arranque, gobernanza y guardarraíles
**Entregables:**
- Monorepo con la estructura indicada, `Makefile` (`bootstrap`, `check`, `test`, `lint`, `typecheck`, `fmt`, `regress`, `trace`, `evidence`) y Docker Compose funcional mínimo.
- `scripts/evidence.py`: genera el paquete de evidencias de una fase con `MANIFEST.sha256` y el commit exacto; `scripts/verify_clean_clone.sh`: comprueba la reproducibilidad en un directorio limpio.
- Plantillas de `docs/plans/FASE-N.md` (tareas con requisito, verificación, resultado esperado y prueba negativa) y de `registro-tareas.md`.
- CI básica en verde y `scripts/traceability.py`.
- `CLAUDE.md` de **menos de 150 líneas**: comandos exactos, restricciones legales resumidas, lo que confunde del repositorio y el puntero a este documento.
- Reglas por ruta en `.claude/rules/`, por ejemplo:
  - `edge.md`: el audio nunca toca disco;
  - `ml.md`: no tocar `evals/frozen/`;
  - `rf.md`: solo recepción.
- `.claude/settings.json`, con sintaxis verificada en la documentación oficial:
  - **Reglas `deny`:** lectura de `.env*` y `secrets/**`; edición de `evals/frozen/**` y `data/raw/**`; comandos de transmisión SDR (p. ej. `hackrf_transfer` con `-t`, cualquier TX de SoapySDR o pluto); `git push --force`.
  - **Hook `PostToolUse`** en ediciones: formateo y lint del fichero.
  - **Hook `PreToolUse`** en `git commit`: `scripts/guardrails.sh` bloquea (exit 2) si el diff contiene llamadas de transmisión SDR, términos de jamming/spoofing/deauth/takeover en código, ficheros de audio fuera de `tests/fixtures/sinteticos/`, campos `pilot_*` u `operator_id` en esquemas de sensibilidad `PUBLIC`, o secretos.
  - **Hook `Stop`:** `make check` debe pasar para terminar.
- **Subagentes** en `.claude/agents/`, con las herramientas mínimas y solo lectura salvo necesidad: `independent-reviewer`, `security-reviewer`, `legal-guardrail-reviewer`, `test-auditor`, `ml-eval-reviewer`, `sapient-conformance`, `privacy-reviewer`.
- **Skills** en `.claude/skills/`: `phase-plan`, `phase-close` (genera evidencias e informe), `new-adr`, `dataset-intake`, `release` (con `disable-model-invocation: true`).
- ADR 0001 (arquitectura), 0002 (restricciones legales), 0003 (stack); `docs/threat-model/v0.md`; `docs/dpia/v0.md`; `docs/ens/v0.md`.

**Verificación:**
- `make check` y CI en verde.
- Prueba documentada de que el guardarraíl bloquea un commit con un `.wav`, otro con el término "jamming" en código y otro con `pilot_lat` en un esquema público.
- La regla `deny` impide leer `.env`.
- `make evidence` genera un paquete con manifiesto de hashes válido, y `scripts/verify_clean_clone.sh` pasa en un directorio nuevo.
- Los tests de los guardarraíles están en la CI: si alguien desactiva uno, la CI falla.

**STOP:** muestra el árbol, `CLAUDE.md`, `settings.json` y las pruebas de bloqueo.

*Estimación: 1 semana.*

### FASE 1 — Contratos de datos, SAPIENT, simulador y gemelo digital
**Entregables:**
- `proto/atalaya/v1`: `Detection`, `Track`, `Prediction`, `Alert`, `NodeStatus`, `CoverageStatus`, `Sighting`, `Evidence`, `SignatureClass`. Cada campo lleva sensibilidad `PUBLIC` / `OPERATOR` / `FCSE_ONLY`.
- Bindings SAPIENT generados y adaptador `sapient-gateway` (versión inicial).
- **Simulador** en `sim/`:
  - geometría de nodos en GeoJSON;
  - trayectorias de las clases C1-C7 con velocidades realistas;
  - propagación acústica (divergencia esférica, absorción dependiente de la frecuencia, viento, fondo);
  - latencias, pérdidas y deriva de reloj;
  - Remote ID (incluido falsificado) y ADS-B simulados;
  - nodos que fallan.
  - Salida a MQTT y ficheros de replay (`.pb.zst`), reproducible por semilla.
- **Escenarios:** `prision_ceuta.yaml`, `puerto_ceuta.yaml`, `aerodromo.yaml`, `frontera_8km.yaml` (coordenadas aproximadas no sensibles).

**Verificación:** round-trip de Protobuf y `buf breaking`; casos básicos del harness SAPIENT (o bloqueo documentado); el mismo escenario con la misma semilla da el mismo resultado; un test de propiedades del simulador.

**STOP:** revisión del modelo de datos y de la tabla de sensibilidad campo a campo.

*Estimación: 2-3 semanas.*

### FASE 2 — Capa 1: radar público de incidentes
**Entregables:**
- Ingesta de fuentes abiertas: RSS de medios, comunicados oficiales, avisos aeronáuticos (NOTAM), licitaciones públicas. Cada fuente con sus términos de uso archivados.
- Deduplicación, geocodificación solo a municipio o instalación (nunca a una persona) y clasificación por tipo (prisión, aeropuerto, puerto, infraestructura, militar, frontera).
- Estados de verificación: Reportado / Probable / Confirmado / Descartado. Fiabilidad de fuente tipo Admiralty.
- Clasificador con LLM con salida JSON estricta, más **revisión humana obligatoria** para publicar como "Confirmado".
- Exportación STIX 2.1, API pública de solo lectura con límite de peticiones y web con mapa (MapLibre), cronología y metodología publicada.
- Solo hechos, resumen propio y enlace a la fuente; nunca el texto completo de la prensa.

**Verificación:** test de que ningún campo público supera la precisión geográfica configurada (p. ej. 1 km) ni contiene nombres de personas físicas; e2e con Playwright; latencia fuente → publicación medida; precisión del clasificador auditada en una muestra.

**STOP:** revisión legal y editorial antes de publicar nada.

*Estimación: 2-3 semanas.*

### FASE 3 — Capa 2: app de avistamientos (sensor humano)
**Entregables:**
- App Kotlin + Compose:
  - alta de avistamiento en 3 toques;
  - rumbo con la brújula, altura y distancia asistidas;
  - foto o vídeo con hash calculado en el momento de la captura;
  - cola cifrada sin conexión, mTLS por dispositivo;
  - roles vigilante y supervisor.
- Backend que convierte cada avistamiento en `Detection(sensor_type=HUMAN)`, de modo que entra en la fusión como un sensor más.
- Al registrar un avistamiento, el sistema añade contexto: si hay NOTAM o zona restringida activa, si hay aeronaves tripuladas cerca (ADS-B) y si hay incidentes previos cercanos.
- Informe PDF para la Guardia Civil: hora UTC y local, posición del observador, rumbo, descripción, evidencias con SHA-256, cadena de custodia y firma del supervisor.

**Verificación:** tests instrumentados de la cola sin conexión; la app **no pide permiso de micrófono** en este modo; PDF comparado con un fichero de referencia; prueba en el Android del usuario.

**STOP:** demostración en el móvil del usuario y, si es posible, validación del formato del informe con la Guardia Civil.

*Estimación: 3-4 semanas.*

### FASE 4 — Biblioteca de firmas y datos
**Entregables:**
- `ml/signatures/`: biblioteca por clase (C1-C9) y, cuando proceda, por modelo. Cada entrada registra fuente, licencia, distancia, condiciones, calidad y confianza.
- Ingesta con DVC de los datasets de la tabla (los que tengan licencia compatible) mediante `dataset-intake`, con data cards.
- **Análisis de fugas** en los datasets agregados (DADS): duplicados entre particiones, mismo vuelo en varias.
- Protocolo de grabación propia (documento y herramienta): sesión autorizada, VAD de voz, importación del registro de vuelo para etiquetar la distancia.
- Generador de **síntesis física** para las clases C6/C7 (sonido de motor y hélice más propagación), claramente marcado como sintético.
- `evals/frozen/` v1: conjuntos congelados por clase, con hash. Incluye confusores locales.
- `docs/DATOS-HUECOS.md`: qué falta, cómo se cubrirá y qué alianzas se proponen (Zvook, Brave1, INTA, universidades).

**Verificación:** cada fichero de datos tiene licencia y procedencia; nada con licencia no comercial en las particiones de producción; el test de fugas pasa; los hashes de `evals/frozen/` coinciden.

**STOP:** el usuario revisa la biblioteca, los huecos y las licencias.

*Estimación: 3-4 semanas, en paralelo con grabaciones.*

### FASE 5 — Nodo acústico en el borde
**Entregables:**
- Línea base: YAMNet (embeddings) más un clasificador ligero, evaluado en `evals/frozen/`.
- Profesor (AST, BEATs o PANNs) entrenado **en la nube** con scripts reproducibles, y alumno destilado exportado a ONNX y TFLite int8. Benchmark en Mac, Raspberry Pi 5 y Android.
- `edge/acoustic-node-py`:
  - búfer circular **solo en memoria**;
  - inferencia por ventanas;
  - publicación MQTT de probabilidad por clase, energía en bandas gruesas, SNR, marca de tiempo GPS y estado del nodo.
- `edge/android-acoustic-node`: lo mismo con TFLite, como servicio en primer plano.
- Model card con métricas, límites conocidos y condiciones en las que no funciona.

**Verificación:**
- Recall ≥ 0,90 con ≤ 1 falsa alarma por hora en fondo simulado para C1 (umbral inicial).
- Menos de 200 ms por ventana en Pi 5.
- **Test anti-persistencia:** el nodo funciona con sistema de ficheros de solo lectura y un espía de llamadas `open`/`write` demuestra que el audio nunca toca disco.

**STOP:** revisión de métricas y de la DPIA del nodo acústico.

*Estimación: 4-6 semanas.*

### FASE 6 — Remote ID, ADS-B y RF pasiva
**Entregables:**
- `edge/esp32-remoteid` (ESP-IDF): recepción OpenDroneID por Wi-Fi Beacon/NAN y Bluetooth en ESP32-S3, envío por MQTT con TLS. Los campos de operador y piloto se marcan `FCSE_ONLY` **en el propio nodo**. Detección de incoherencias que sugieran Remote ID falsificado.
- `edge/adsb`: `readsb` con RTL-SDR para suprimir alertas debidas a aeronaves tripuladas.
- `edge/rf-presence`: SDR **solo en recepción**; barrido de 2,4/5,8 GHz, espectrogramas y energía; clasificador "enlace tipo dron / Wi-Fi / Bluetooth / ruido" sin demodular.

**Verificación:** tests con capturas reproducidas; **un test falla si el código importa o llama a cualquier API de transmisión**; el guardarraíl bloquea un PR de prueba con TX; Remote ID fusionado con ADS-B en el simulador.

**STOP:** revisión legal de RF y Remote ID.

*Estimación: 3-4 semanas.*

### FASE 7 — Campaña de campo 1: alcance real
**Objetivo:** medir lo que de verdad oyen y ven los sensores **antes** de fijar la geometría de la red.

**Entregables:**
- Plan de pruebas de campo:
  - permisos y zona autorizada;
  - drones propios y equivalentes de la clase pistón cuando sea posible;
  - distancias, alturas y horarios;
  - registro de viento.
- Herramienta de recogida que cruza las detecciones con el registro de vuelo.
- Informe: probabilidad de detección según distancia, por clase y por tipo de nodo; falsas alarmas por hora; efecto del viento.
- Recalibración de umbrales y de la geometría de diseño mediante ADR.

**Verificación:** curvas de detección frente a distancia con intervalos de confianza; datos guardados con procedencia; comparación con lo previsto en simulación.

**STOP:** el usuario decide la geometría del piloto con datos reales.

*Estimación: 2 semanas.*

### FASE 8 — Sincronización de tiempo y localización
**Entregables:**
- `chrony` + `gpsd` + PPS en la Raspberry Pi, con métrica de deriva. Sin PPS válido, el nodo sale del TDOA y se muestra.
- Nodos con array envían DOA local (SRP-PHAT o MUSIC) y envolventes por banda con marca de tiempo, nunca audio reconstruible.
- Estimador central: GCC-PHAT, multilateración robusta, triangulación por rumbos y elipses de incertidumbre.
- Validación con el simulador, con el dataset de Tegler et al. si su licencia lo permite, y con datos de la FASE 7.

**Verificación:** error mediano < 15 m dentro del polígono con PPS en simulación; degradación sin PPS medida y documentada; tests de propiedades (permutar nodos no cambia el resultado; ruido acotado da error acotado).

**STOP:** revisión de la geometría del piloto sobre el mapa.

*Estimación: 3-4 semanas.*

### FASE 9 — Seguimiento, fusión y predicción incremental
**Entregables:**
- `services/tracker`: IMM + JPDA, ciclo de vida de pistas, supresión por ADS-B y **traspaso entre emplazamientos** con identidad de pista conservada.
- `services/fusion`: fusión bayesiana calibrada de clase (acústica, RF, Remote ID, visual, humana) y regla de indicio de FPV sin radiofrecuencia.
- `services/predictor`, que se recalcula **con cada nueva detección**:
  - trayectoria a 5, 10 y 30 s;
  - destino probable sobre los objetivos del emplazamiento;
  - mapa de calor de origen probable (`FCSE_ONLY`);
  - **aviso anticipado** a nodos y cámaras en la trayectoria prevista.
- Visión opcional, solo para confirmar, con licencia compatible.

**Verificación:**
- Métricas de seguimiento OSPA/GOSPA y MOTA en escenarios.
- Error de predicción a 5, 10 y 30 s, que debe mejorar la línea base de velocidad constante.
- Acierto de destino top-1 y top-3.
- Calibración del mapa de origen (el área del 90 % contiene el origen real ~90 % de las veces).
- Test de que el origen y los datos del piloto nunca aparecen en ninguna API sin rol FCSE.
- Mutation testing por encima del umbral.

**STOP:** revisión de resultados y de los riesgos éticos y legales de la predicción de origen.

*Estimación: 4-6 semanas.*

### FASE 10 — Dashboard SOC y sistema de alertas
**Entregables:**
- `apps/dashboard`:
  - mapa con pistas e incertidumbre, trayectoria prevista y destino probable;
  - **mapa de cobertura en vivo** (zonas cubiertas, degradadas y sin cobertura);
  - cola de alertas priorizada, ficha de pista con evidencias, estado de nodos;
  - perfil militar (APP-6) y perfil vigilante (simplificado).
- Flujo de alerta: SOSPECHA → CONFIRMACIÓN humana (2 clics; motivo obligatorio para descartar) → ESCALADO a FCSE (PDF de evidencias y canal configurado).
- Gestión de alarmas según ISA-18.2 / EEMUA 191: alarmas por operador y hora, supresión de repetidas, silenciado temporal con caducidad y registro.
- RBAC (vigilante, supervisor, operador SOC, FCSE, analista, administrador, auditor), MFA, auditoría append-only, evidencias con sello de tiempo.
- Canales: notificación push, SMS, Telegram o Signal. Integración con sistemas de las FCSE solo con adaptadores acordados con ellas.
- Modo degradado local sin nube, con colas persistentes.

**Verificación:**
- e2e con Playwright de un escenario de prisión desde replay.
- Latencia detección→alerta p95 < 2 s en local.
- Prueba de corte de red y de caída de nodos (se ve la cobertura degradada).
- Modo nocturno y accesibilidad.
- Prueba de que un vigilante no ve datos `FCSE_ONLY`.

**STOP:** prueba de usabilidad con 2 o 3 vigilantes u operadores reales; se corrige lo que encuentren.

*Estimación: 4-6 semanas.*

### FASE 11 — Interoperabilidad SAPIENT completa
**Entregables:** `sapient-gateway` como Edge Node y como Fusion Node, taxonomía SAPIENT mapeada a C1-C9, pruebas con el harness, documento de conformidad y limitaciones.

**Verificación:** el harness pasa (pega la salida) y existen tests de regresión de mensajes.

**STOP:** revisión antes de cualquier demostración a Defensa o a integradores.

*Estimación: 2-3 semanas.*

### FASE 12 — Endurecimiento, ENS y seguridad
**Entregables:**
- CA propia, certificados por nodo y rotación; Secure Boot y cifrado de flash en ESP32; OTA firmado.
- SBOM por artefacto y política de divulgación de vulnerabilidades (CRA).
- Pentest interno, incluidos ataques a la red de sensores (detecciones falsas, nodos suplantados, Remote ID falsificado).
- Mapa de medidas del ENS completo y plan para la certificación.
- DPIA final y runbooks de incidentes.

**Verificación:** hallazgos críticos y altos del pentest cerrados o aceptados por escrito; SBOM sin vulnerabilidades críticas abiertas; prueba de OTA firmado y de rechazo de firmware no firmado.

**STOP:** revisión de seguridad con el usuario.

*Estimación: 3-4 semanas.*

### FASE 13 — Piloto de campo, operación y decisión
**Entregables:**
- Instalación en el emplazamiento piloto con runbooks: montaje, calibración, mantenimiento, sustitución de nodos y procedimiento con las FCSE.
- Operación durante al menos 4-8 semanas, con reentrenamiento sobre datos del emplazamiento (solo sesiones autorizadas) frente a la línea base congelada.
- Informe del piloto:
  - probabilidad de detección por distancia y clase;
  - falsas alarmas por hora;
  - latencia;
  - disponibilidad;
  - incidentes reales detectados y perdidos;
  - opinión de los operadores;
  - coste por emplazamiento.
- Propuesta comercial y técnica para el cliente, con las limitaciones explicadas con honestidad.

**Verificación:** métricas del piloto calculadas desde los datos (no a mano) y revisadas por el subagente `ml-eval-reviewer`.

**STOP:** decisión del usuario de seguir, corregir o parar (go/no-go).

*Estimación: 6-8 semanas.*

---

### ANEXO A — Plantilla de informe de cierre (`docs/evidence/FASE-N/CIERRE.md`)
```
# Cierre FASE N — <nombre>
Fecha · Commit · Etiqueta propuesta
1. Objetivo y alcance cumplido (requisitos cubiertos: REQ-…)
2. Evidencia: comando → resultado (resumen), enlace a ficheros del paquete y MANIFEST.sha256
3. Registro de tareas: nº de tareas, todas con verificación y prueba negativa en OK (enlace a registro-tareas.md)
4. Puertas P1–P5: resultado de cada una (P3 regresión, P4 clon limpio, P5 revisiones)
5. Revisión independiente y test-auditor: hallazgos y resolución
6. Métricas clave frente a objetivo (calculadas por script, verificadas por un segundo script)
7. Pruebas de inyección de fallos y de guardarraíles: resultado
8. Lo que NO se ha hecho o NO VERIFICADO, y por qué
9. Cambios de requisitos/ADR en esta fase
10. Riesgos nuevos o actualizados
11. Deuda técnica añadida
12. Decisiones que necesita el usuario
```

### ANEXO B — Plantilla de requisito
```
REQ-XXX-###  [MUST|SHOULD|COULD]
Descripción:
Justificación (riesgo, cliente, ley):
Criterio de aceptación verificable:
Método de verificación (test, análisis, inspección, demostración):
Fase:
```

### ANEXO C — Riesgos iniciales que debes registrar en la FASE -1
1. Alcance acústico real menor que el previsto (viento, ruido urbano). Mitigación: campaña de campo en FASE 7 y fusión multisensor.
2. Falta de datos de clases militares. Mitigación: alianzas, equivalentes legales y síntesis.
3. Licencias de datasets incompatibles con uso comercial. Mitigación: `dataset-intake` y aislamiento de datos solo de investigación.
4. Riesgo legal en RF, audio y datos de pilotos. Mitigación: restricciones, hooks, DPIA y asesoría jurídica.
5. Fatiga de alarmas y pérdida de confianza de los operadores. Mitigación: alertas por pista, ISA-18.2, pruebas de usabilidad.
6. Ataques a la propia red de sensores. Mitigación: mTLS, firmware firmado, detección de anomalías.
7. Dependencia de un solo emplazamiento piloto. Mitigación: segundo emplazamiento antes de comercializar.
8. Requisitos de ENS y habilitaciones que retrasan las ventas públicas. Mitigación: ENS desde la FASE 0.
9. Atribución errónea a un actor o país. Mitigación: nunca automática, solo analista, nunca pública.

**Fin del documento maestro.** Empieza por la FASE -1.

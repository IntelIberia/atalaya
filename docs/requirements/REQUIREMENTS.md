# Requisitos de Atalaya

Versión 0.1 · 2026-11-08 · Estado: **pendiente de aprobación (STOP de la FASE -1)**

Fuentes: `docs/MEGAPROMPT.md` (v2.0) y `docs/requirements/ENTREVISTA-FASE--1.md`.

**Convenciones**
- Prioridad: MUST (obligatorio para cerrar la fase indicada), SHOULD (se hace salvo que un ADR lo aplace), COULD (opcional).
- Método: T = test automatizado, A = análisis, I = inspección, D = demostración. Se pueden combinar (`T+I`).
- Fase: fase en la que el requisito tiene que quedar verificado. «0→» indica que aplica desde esa fase hasta el final.
- **Bloqueo (B):** el requisito no se puede verificar con los recursos actuales (0 €, sin dron, sin contactos). Su verificación se marca NO VERIFICADO con el motivo, y la fase cierra con ese bloqueo documentado en lugar de dar el requisito por cumplido. Los bloqueos se enumeran en `docs/SPEC.md` §9.
- Los umbrales numéricos son iniciales y solo cambian con un ADR.

Plantilla completa (Anexo B del MEGAPROMPT): cada fila contiene descripción, criterio de aceptación verificable, método, fase y justificación.

---

## REQ-FUN — Funcionales

| ID | Prio | Descripción | Criterio de aceptación | Método | Fase | Justificación |
|---|---|---|---|---|---|---|
| REQ-FUN-001 | MUST | Los nodos publican eventos `Detection` en Protobuf por MQTT 5 y la plataforma los ingiere | Un test de integración publica N detecciones por MQTT y las N aparecen en la plataforma, sin pérdidas ni duplicados | T | 1 | Contrato nodo-plataforma |
| REQ-FUN-002 | MUST | Esquemas `Detection`, `Track`, `Prediction`, `Alert`, `NodeStatus`, `CoverageStatus`, `Sighting`, `Evidence` y `SignatureClass` en `proto/atalaya/v1`, con la sensibilidad (`PUBLIC`/`OPERATOR`/`FCSE_ONLY`) de cada campo | Round-trip de todos los mensajes; `buf lint` y `buf breaking` en verde; un test falla si algún campo no declara sensibilidad | T | 1 | Contratos de datos y minimización |
| REQ-FUN-003 | MUST | Simulador reproducible por semilla | Mismo escenario y misma semilla dan salidas idénticas byte a byte (hash) en dos ejecuciones | T | 1 | Evidencia reproducible |
| REQ-FUN-004 | MUST | El simulador modela trayectorias C1-C7 con velocidades realistas, propagación acústica (divergencia esférica, absorción por frecuencia, viento, fondo), latencias, pérdidas, deriva de reloj, Remote ID (también falsificado), ADS-B y fallo de nodos | Un test por fenómeno; un test de propiedades (`hypothesis`): el nivel recibido decrece con la distancia en condiciones sin viento | T | 1 | Sin hardware, el simulador es la base de la verificación |
| REQ-FUN-005 | MUST | Escenarios `prision_ceuta`, `puerto_ceuta`, `aerodromo` y `frontera_8km` con coordenadas aproximadas no sensibles | Los cuatro YAML validan contra su esquema y se ejecutan de extremo a extremo | T | 1 | El emplazamiento piloto no está decidido |
| REQ-FUN-006 | MUST | Grabación y reproducción de flujos de eventos (`.pb.zst`) | Reproducir un replay da la misma secuencia de pistas que la ejecución en vivo | T | 1 | Regresión y demostraciones |
| REQ-FUN-007 | MUST | El radar ingiere fuentes abiertas (RSS de medios, comunicados oficiales, NOTAM y licitaciones) y archiva los términos de uso de cada fuente | Cada fuente configurada tiene sus términos archivados con fecha y hash; una fuente sin términos se rechaza | T+I | 2 | Uso legal de fuentes |
| REQ-FUN-008 | MUST | Deduplicación de incidentes | Sobre un conjunto etiquetado de noticias duplicadas, precisión y recall de deduplicación ≥ umbral fijado por ADR en la FASE 2 | T | 2 | Calidad del radar |
| REQ-FUN-009 | MUST | Geocodificación solo a municipio o instalación | Ver REQ-PRIV-004 | T | 2 | Privacidad |
| REQ-FUN-010 | MUST | Estados Reportado/Probable/Confirmado/Descartado y fiabilidad de fuente tipo Admiralty | Las transiciones de estado no válidas se rechazan (test de máquina de estados) | T | 2 | Rigor editorial |
| REQ-FUN-011 | MUST | Clasificador de incidentes por reglas, con un adaptador opcional para LLM y salida JSON validada contra un esquema estricto | Una salida que no cumple el esquema se rechaza; el sistema funciona entero con el adaptador LLM desactivado | T | 2 | Presupuesto de 0 € (entrevista, bloque 4) |
| REQ-FUN-012 | MUST | Un incidente solo se publica como «Confirmado» tras revisión humana registrada | Intentar publicar «Confirmado» sin revisor registrado falla | T | 2 | Humano en el bucle |
| REQ-FUN-013 | SHOULD | Exportación STIX 2.1 del radar | El bundle exportado valida con el validador oficial de STIX 2.1 (versión fijada) | T | 2 | Interoperabilidad CTI |
| REQ-FUN-014 | SHOULD | API de solo lectura del radar con límite de peticiones, preparada para ser pública (en la v1 solo corre en local) | Escribir está prohibido (405/403); superar el límite devuelve 429 | T | 2 | Escaparate futuro |
| REQ-FUN-015 | MUST | Web del radar con mapa (MapLibre), cronología y página de metodología, servida en local en la v1 | e2e con Playwright en local: el mapa carga y los filtros funcionan; la página de metodología existe | T | 2 | Alojamiento solo local (entrevista, bloque 4) |
| REQ-FUN-016 | MUST | En la app, un avistamiento se da de alta en 3 toques como máximo | Test instrumentado que cuenta las interacciones del camino principal (≤ 3) | T | 3 | Uso bajo estrés |
| REQ-FUN-017 | MUST | Rumbo por brújula, altura y distancia asistidas | Tests unitarios de los cálculos; demostración en el Android del usuario | T+D | 3 | Calidad del dato humano |
| REQ-FUN-018 | MUST | Foto o vídeo con SHA-256 calculado en el momento de la captura | El hash guardado coincide con el del fichero entregado; alterar un byte se detecta | T | 3 | Cadena de custodia |
| REQ-FUN-019 | MUST | Cola cifrada sin conexión que se envía al recuperar la red | Test instrumentado: N avistamientos sin red llegan los N al reconectar; la cola en disco no es legible en claro | T | 3 | Funcionamiento sin conexión |
| REQ-FUN-020 | MUST | Cada avistamiento entra en la fusión como `Detection(sensor_type=HUMAN)` | Test de integración: un avistamiento produce una detección HUMAN con su incertidumbre | T | 3 | Sensor humano |
| REQ-FUN-021 | SHOULD | Contexto automático del avistamiento: NOTAM o zona activa, aeronaves tripuladas cercanas e incidentes previos | Con datos de prueba conocidos, el contexto devuelto coincide con el esperado | T | 3 | Reducción de falsas alarmas |
| REQ-FUN-022 | MUST | Informe PDF para FCSE: hora UTC y local, posición del observador, rumbo, descripción, evidencias con SHA-256, cadena de custodia y firma del supervisor | El PDF se compara con un fichero de referencia; la firma valida. Validación del formato con la Guardia Civil: **B** (sin contacto) | T+I | 3 | Utilidad para las autoridades |
| REQ-FUN-023 | MUST | Biblioteca de firmas por clase C1-C9 (y por modelo cuando proceda) con fuente, licencia, distancia, condiciones, calidad y confianza en cada entrada | Un test falla si alguna entrada no tiene uno de esos campos | T | 4 | Base de los modelos |
| REQ-FUN-024 | MUST | Generador de síntesis física para C6/C7 (paso de pala, armónicos, absorción, propagación), marcado como sintético | La frecuencia fundamental generada coincide con RPM × palas / 60 dentro de una tolerancia; los metadatos llevan `synthetic=true` | T | 4 | No hay datos públicos de C6/C7 |
| REQ-FUN-025 | MUST | `evals/frozen/` v1 por clase, con confusores locales y hash SHA-256 | El hash calculado coincide con el registrado antes de cada evaluación | T | 4 | Evaluación honesta |
| REQ-FUN-026 | SHOULD | Herramienta del protocolo de grabación: sesión autorizada, VAD de voz e importación del registro de vuelo para etiquetar la distancia | Sobre una sesión sintética, la distancia etiquetada coincide con la del registro de vuelo; la voz se suprime | T | 4 | Datos propios con trazabilidad |
| REQ-FUN-027 | MUST | El nodo acústico infiere por ventanas y publica probabilidad por clase, energía en bandas gruesas, SNR, marca de tiempo y estado del nodo | Test de contrato del mensaje publicado; ningún campo permite reconstruir el audio (ver REQ-PRIV-010) | T | 5 | Detección en el borde |
| REQ-FUN-028 | MUST | Nodo acústico Android (TFLite/LiteRT) como servicio en primer plano | En el Android del usuario: 0 cortes del servicio en 8 h seguidas (heartbeats continuos en el registro de la plataforma) | T+D | 5 | Recurso disponible a 0 € |
| REQ-FUN-029 | MUST | Nodo acústico Python (ONNX en CPU) para Mac y Raspberry Pi | Corre en el Mac sobre replays; en la Pi: **B** (sin hardware) | T | 5 | Nodo de localización futuro |
| REQ-FUN-030 | MUST | Recepción de Remote ID estándar (ASTM F3411 / EN 4709-002) con OpenDroneID en firmware ESP32-S3 | El firmware compila; los tests de host decodifican tramas reales o de referencia. Prueba con placa: **B** | T | 6 | Fuente cooperativa de alta calidad |
| REQ-FUN-031 | MUST | Detección de incoherencias que sugieren un Remote ID falsificado (saltos imposibles, posición incompatible con la acústica o la RSSI) | En el simulador, los casos de Remote ID falsificado se marcan como indicio con recall ≥ umbral fijado por ADR | T | 6 | Ataques a la red de sensores |
| REQ-FUN-032 | MUST | ADS-B (readsb) para identificar aeronaves tripuladas | Con un replay ADS-B, las pistas que coinciden con aeronaves tripuladas se identifican. RTL-SDR real: **B** | T | 6 | Reducción de falsas alarmas |
| REQ-FUN-033 | MUST | Presencia RF pasiva en 2,4/5,8 GHz: espectrogramas y energía, con un clasificador de enlace tipo dron / Wi-Fi / Bluetooth / ruido sin demodular | Métricas sobre DroneRF (licencia CC BY 4.0 según el MEGAPROMPT; NO VERIFICADO hasta `dataset-intake`) frente a la línea base. SDR real: **B** | T | 6 | Detección de C3 |
| REQ-FUN-034 | MUST | Localización TDOA (GCC-PHAT + multilateración robusta) con elipse de incertidumbre | En geometría sintética exacta, recupera la posición con error < 1 m sin ruido; ver REQ-NFR-005 | T | 8 | Localización |
| REQ-FUN-035 | SHOULD | DOA con arrays locales (SRP-PHAT o MUSIC) y triangulación por rumbos | Casos sintéticos con solución conocida; comparación con pyroomacoustics | T | 8 | Nodos con array |
| REQ-FUN-036 | MUST | Un nodo sin PPS válido no participa en TDOA y su estado se muestra | Test: al invalidar el PPS de un nodo, sale del cálculo y `NodeStatus` lo refleja | T | 8 | Fallo visible |
| REQ-FUN-037 | MUST | Tracker IMM (velocidad constante, giro coordinado, estacionario) + JPDA con ciclo de vida de pistas | OSPA/GOSPA y MOTA por escenario por encima de los umbrales fijados por ADR; comparación con Stone Soup | T | 9 | Seguimiento |
| REQ-FUN-038 | MUST | Supresión de alertas por aeronave tripulada confirmada por ADS-B | Test: una pista asociada a ADS-B no genera alerta de dron y la supresión queda registrada | T | 9 | Fatiga de alarmas |
| REQ-FUN-039 | SHOULD | Traspaso entre emplazamientos conservando la identidad de la pista | En el escenario `frontera_8km`, el identificador se conserva en ≥ 95 % de los traspasos | T | 9 | Cobertura continua |
| REQ-FUN-040 | MUST | Fusión bayesiana calibrada de clase entre acústica, RF, Remote ID, visual y humana | Error de calibración esperado (ECE) ≤ umbral fijado por ADR en evaluación congelada | T | 9 | Clasificación robusta |
| REQ-FUN-041 | MUST | Regla de indicio C4: firma acústica FPV + ausencia de RF + ausencia de Remote ID = indicio de fibra óptica o vuelo autónomo, marcado como indicio | Tests de tabla de verdad; la salida nunca lleva la etiqueta de certeza | T | 9 | Amenaza C4 |
| REQ-FUN-042 | MUST | Predicción de trayectoria a 5, 10 y 30 s, con incertidumbre, recalculada con cada detección | Ver REQ-NFR-006 y REQ-FUN-062; un test comprueba que la predicción cambia al llegar una detección nueva | T | 9 | Anticipación |
| REQ-FUN-043 | MUST | Destino probable por inferencia bayesiana sobre los objetivos del emplazamiento | Las probabilidades suman 1; acierto top-1 y top-3 por escenario mayor que el de la línea base de prior uniforme (test pareado, α = 0,05) y que el umbral fijado por ADR en la FASE 9 | T | 9 | Priorización |
| REQ-FUN-044 | SHOULD | Mapa de calor de origen probable con sensibilidad `FCSE_ONLY` | Calibración: el área del 90 % contiene el origen real en el 90 % ± IC de los casos simulados | T | 9 | Apoyo a FCSE |
| REQ-FUN-045 | SHOULD | Aviso anticipado a los nodos y cámaras en la trayectoria prevista | Test: una predicción que cruza el área de otro nodo genera un aviso a ese nodo | T | 9 | Sensibilidad adaptativa |
| REQ-FUN-046 | COULD | Confirmación visual con un detector de licencia permisiva | Métricas en Anti-UAV (si la licencia lo permite) | T | 9 | Confirmación |
| REQ-FUN-047 | MUST | Dashboard con mapa de pistas, incertidumbre, trayectoria prevista y destino probable | e2e con Playwright sobre un replay del escenario de prisión | T | 10 | Operación |
| REQ-FUN-048 | MUST | Mapa de cobertura en vivo: cubierta, degradada y sin cobertura | Test: al caer un nodo, su área pasa a degradada o sin cobertura en < 2 min; nunca se muestra «sin amenazas» en una zona sin cobertura | T | 10 | Fallo visible |
| REQ-FUN-049 | MUST | Flujo de alerta SOSPECHA → CONFIRMACIÓN humana (2 clics; motivo obligatorio para descartar) → ESCALADO | e2e: descartar sin motivo falla; escalar sin confirmación falla | T | 10 | Humano en el bucle |
| REQ-FUN-050 | MUST | Gestión de alarmas según ISA-18.2 / EEMUA 191: supresión de repetidas, silenciado con caducidad y registro, alarmas por operador y hora | Tests: un silenciado caduca a su hora; las repeticiones se agrupan; la métrica de alarmas por hora existe | T | 10 | Fatiga de alarmas |
| REQ-FUN-051 | SHOULD | Perfil militar (APP-6 / milsymbol) y perfil vigilante simplificado | e2e de ambos perfiles | T | 10 | Distintos usuarios |
| REQ-FUN-052 | SHOULD | Canales de notificación configurables detrás de una interfaz (push, Telegram, SMS) | Test de integración con un canal simulado local. En la v1 (solo local), ningún canal envía datos a servicios externos; activar un canal real requiere un ADR | T | 10 | Avisos fuera de la consola; alojamiento solo local |
| REQ-FUN-053 | MUST | Modo degradado local sin nube, con colas persistentes | Test: cortar la red entre el emplazamiento y la nube no pierde eventos y el dashboard local sigue operativo | T | 10 | Disponibilidad |
| REQ-FUN-054 | MUST | `sapient-gateway` como Edge Node y Fusion Node, con mensajes generados desde los `.proto` oficiales BSI Flex 335 v2.0 | El harness de conformidad pasa (salida pegada). Sin los `.proto` o sin harness: **B** | T | 11 (inicial en 1) | Interoperabilidad OTAN |
| REQ-FUN-055 | MUST | Mapeo de la taxonomía SAPIENT a C1-C9 | Test de tabla de mapeo completa y biyectiva donde proceda; los casos sin mapeo se documentan | T+I | 11 | Interoperabilidad |
| REQ-FUN-056 | MUST | Se alerta por pista, no por detección suelta | Test: una detección aislada que no confirma pista no genera alerta | T | 9 | Fatiga de alarmas |
| REQ-FUN-057 | MUST | Demostrador v1: el Android del usuario, como nodo acústico, detecta audio real de drones de datasets con licencia compatible reproducido por un altavoz, y la alerta aparece en el dashboard | Demostración grabada con fecha y commit; latencia medida; resultado etiquetado como «reproducción en sala, no vuelo real» | D+T | 10 | Criterio de éxito de la v1 (entrevista, bloque 4) |
| REQ-FUN-058 | MUST | Clasificación por clase de propulsión C1-C9; modelo concreto opcional y siempre con confianza | El esquema obliga a acompañar la clase de una confianza; el modelo concreto es opcional | T | 5 | Taxonomía |
| REQ-FUN-059 | MUST | Paquetes de evidencia con hash, sello de tiempo y cadena de custodia para todo lo que pueda llegar a un procedimiento | Test: modificar un elemento del paquete rompe la verificación | T | 3 (y 10) | Valor probatorio |
| REQ-FUN-060 | COULD | Hito v1+: detección de un vuelo real con un dron prestado, cruzada con su registro de vuelo | Curva de detección frente a distancia de una sesión real. **B** hasta tener dron, registro AESA y zona autorizada | D+A | 7 | Validación real (entrevista, bloque 4) |
| REQ-FUN-061 | MUST | Fallo visible: un nodo caído, un reloj o PPS desincronizado, un modelo degradado y un enlace perdido marcan como **degradada** la cobertura del área afectada en el mapa. El sistema nunca muestra «sin amenazas» en una zona que no cubre | Inyección de fallos F-01, F-02, F-03 y F-08: en cada caso, el área afectada pasa a degradada o sin cobertura en el dashboard (e2e) y el estado se publica en `CoverageStatus` | T | 10 (estado en 5, 8 y 9) | Principio de seguridad 2 |
| REQ-FUN-062 | MUST | Toda estimación lleva su incertidumbre: confianza de clase, covarianza o elipse de posición, incertidumbre de la predicción y mapa de probabilidad de destino y origen. Ninguna estimación se presenta como un hecho | Test de esquema: `Detection`, `Track` y `Prediction` no validan sin sus campos de incertidumbre; e2e: el dashboard muestra la elipse o el cono de incertidumbre de cada pista y predicción | T | 1 (esquema), 9-10 | Principio de seguridad 3 |

## REQ-NFR — No funcionales

| ID | Prio | Descripción | Criterio de aceptación | Método | Fase | Justificación |
|---|---|---|---|---|---|---|
| REQ-NFR-001 | MUST | Latencia de detección a alerta en pantalla con p95 < 2 s en red local | Medida en e2e con replay y en la demostración v1; script de cálculo versionado | T | 10 | Tiempo de reacción |
| REQ-NFR-002 | MUST | Latencia p95 < 5 s por 4G | Medida con un perfil de red 4G emulado (latencia, jitter y pérdidas fijados por ADR, con tc/netem o equivalente). 4G real: **B** | T | 10 | Nodos remotos |
| REQ-NFR-003 | MUST | Aviso de nodo caído en < 2 min (heartbeat cada 30 s) | Test de inyección de fallo: tiempo hasta el aviso < 120 s | T | 5 (y 10) | Fallo visible |
| REQ-NFR-004 | MUST | Detección acústica C1 con recall ≥ 0,90 y ≤ 1 falsa alarma por hora y emplazamiento, sobre fondo simulado | Criterio conservador sobre `evals/frozen/`: **límite inferior** del IC al 95 % del recall ≥ 0,90 y **límite superior** del IC al 95 % de las falsas alarmas por hora ≤ 1. Si el valor puntual cumple pero el IC no, el resultado es «no concluyente», no «cumple». Recalculado por un segundo script independiente | T+A | 5 | Objetivo inicial; principio de seguridad 3 |
| REQ-NFR-005 | MUST | Error mediano de localización < 15 m dentro del polígono de nodos con PPS, en simulación | En ≥ 1.000 casos simulados, **límite superior** del IC al 95 % (bootstrap) de la mediana < 15 m; degradación sin PPS medida y documentada | T+A | 8 | Objetivo inicial |
| REQ-NFR-006 | MUST | La predicción mejora la línea base de velocidad constante a 5, 10 y 30 s | En cada escenario y horizonte, el error es menor que el de la línea base según un test de Wilcoxon pareado unilateral con α = 0,05; se reportan el error medio y el p90 de ambos | T+A | 9 | Valor de la predicción |
| REQ-NFR-007 | SHOULD | Disponibilidad ≥ 99,5 % mensual en el piloto | Medida durante el piloto. **B** (sin emplazamiento ni hardware) | A | 13 | Operación |
| REQ-NFR-008 | MUST | Dashboard local por emplazamiento operativo sin conexión | Ver REQ-FUN-053 | T | 10 | Funcionamiento sin conexión |
| REQ-NFR-009 | MUST | Retención configurable: detecciones 90 días por defecto, evidencias según procedimiento, `FCSE_ONLY` el mínimo legal | Test con reloj simulado: los datos caducados se borran y el borrado queda auditado | T | 10 | RGPD |
| REQ-NFR-010 | MUST | Accesibilidad: modo nocturno, contraste alto y uso con guantes (objetivos táctiles ≥ 48 dp en la app) | e2e que activa el modo nocturno y el de contraste alto y comprueba que se aplican (dashboard y app); auditoría automática (axe en el dashboard, Accessibility Scanner en la app) sin fallos críticos; test de tamaño mínimo de los objetivos táctiles | T+I | 3 (y 10) | Uso real |
| REQ-NFR-011 | MUST | La inferencia en el Android del usuario cabe en el salto de ventana (p95 de inferencia < salto) | Benchmark en el dispositivo con su salida pegada | T | 5 | Tiempo real en el borde |
| REQ-NFR-012 | SHOULD | Inferencia < 200 ms por ventana en Raspberry Pi 5 | Benchmark en la Pi. **B** (sin hardware); se registra la cifra del Mac como referencia, no como sustituto | T | 5 | Nodo de localización |
| REQ-NFR-013 | MUST | Carga con el doble de nodos y detecciones previstos manteniendo la p95 de REQ-NFR-001 | Prueba de carga con el simulador (60 nodos × 2) | T | 10 | Escalado |
| REQ-NFR-014 | MUST | Reproducibilidad: en un clon limpio, `make bootstrap && make check` funciona sin pasos manuales | `scripts/verify_clean_clone.sh` en verde | T | 0→ | Evidencia reproducible |
| REQ-NFR-015 | MUST | Todo el stack de desarrollo y demostración corre en el MacBook Intel sin GPU | `make check` y la demostración v1 se ejecutan en el Mac del usuario | T+D | 0→ | Recursos disponibles |
| REQ-NFR-016 | MUST | Coste obligatorio 0 €: cualquier gasto (hardware, GPU, APIs, alojamiento) es opcional y requiere un ADR | Inspección en cada cierre: ninguna tarea MUST depende de un servicio de pago | I | 0→ | Entrevista, bloque 3 |
| REQ-NFR-017 | MUST | Métricas de seguimiento OSPA/GOSPA y MOTA reportadas por escenario | Script de métricas y un segundo script de comprobación con el mismo resultado | T | 9 | Evaluación |
| REQ-NFR-018 | MUST | Mutation testing en fusión, seguimiento, predicción, control de acceso y guardarraíles por encima del umbral fijado por ADR | Informe de `mutmut` en el paquete de evidencias | T | 9 (guardarraíles: 0) | Tests que no mienten |
| REQ-NFR-019 | SHOULD | Observabilidad: OpenTelemetry y métricas Prometheus (latencia detección→alerta, alertas por hora y operador, nodos vivos, deriva de reloj, deriva de modelo) | Las métricas aparecen en `/metrics` durante el e2e | T | 10 | Operación |
| REQ-NFR-020 | MUST | Recall y falsas alarmas por hora se reportan para cada clase C1-C7 con IC; las clases sin datos reales se marcan NO VERIFICADO con su origen (sintético, equivalente o sin datos) | Un test falla si una clase aparece sin métrica ni marca | T+I | 5 | «Todo es prioritario» sin afirmar lo que no se ha medido |
| REQ-NFR-021 | MUST | Recogida de pistas: ninguna alerta se pierde por desorden o duplicado de mensajes | Inyección de mensajes duplicados y desordenados: el número de pistas y alertas coincide con el esperado | T | 9 | Robustez |

## REQ-LEG — Legales (no negociables)

| ID | Prio | Descripción | Criterio de aceptación | Método | Fase | Justificación |
|---|---|---|---|---|---|---|
| REQ-LEG-001 | MUST | Atalaya solo detecta, clasifica, localiza, sigue, predice y alerta. Nunca contiene código, configuración, documentación ni ejemplos para neutralizar, inhibir, interferir, suplantar, desautenticar o tomar el control de drones, ni para mejorar armamento | Guardarraíl de commit y test de CI que lo intentan violar y deben fallar; revisión del subagente legal en cada cierre | T+I | 0→ | Ley 11/2022, art. 82.4 (según MEGAPROMPT; cita NO VERIFICADA) |
| REQ-LEG-002 | MUST | No existe ningún camino de transmisión por radio desde un SDR | Test de CI que falla si el código importa o llama a una API de transmisión; reglas `deny` sobre comandos TX | T | 0 (y 6) | Igual que REQ-LEG-001 |
| REQ-LEG-003 | MUST | No se demodula el contenido de comunicaciones de terceros ni protocolos propietarios (incluido DJI DroneID) | Análisis estático y revisión del subagente legal; lista de dependencias prohibidas en CI | T+I | 6 | Secreto de las comunicaciones |
| REQ-LEG-004 | MUST | Remote ID solo en su forma estándar (ASTM F3411 / EN 4709-002) mediante OpenDroneID | Inspección de dependencias y tests de decodificación limitados a los mensajes estándar | T+I | 6 | Diseñado para ser recibido |
| REQ-LEG-005 | MUST | Audio: inferencia en el borde y descarte inmediato; del nodo solo salen detecciones, puntuaciones, marcas de tiempo y características agregadas no reconstruibles | Ver REQ-PRIV-002 y REQ-PRIV-010 | T | 5 | RGPD y privacidad de las comunicaciones |
| REQ-LEG-006 | MUST | La grabación para entrenamiento solo se permite en una sesión autorizada, con VAD de voz, registro de consentimiento y metadatos | Tests: iniciar una grabación sin sesión autorizada falla; iniciarla sin un registro de consentimiento asociado falla; la voz detectada se suprime; cada grabación lleva sus metadatos obligatorios | T | 4 | RGPD |
| REQ-LEG-007 | MUST | Los datos que identifican o sitúan a pilotos u operadores (posición del piloto en Remote ID, número de operador, estimaciones de origen) son `FCSE_ONLY` y nunca se publican | Ver REQ-PRIV-001; test del guardarraíl con `pilot_*` en esquemas `PUBLIC` | T | 1→ | Protección de datos |
| REQ-LEG-008 | MUST | Sin atribución automática de nacionalidad ni de actor: la atribución es un campo aparte que solo escribe el rol analista, con fuente, confianza y autor; solo lo leen los roles analista, FCSE y auditor; nunca es público | Tests: ningún módulo automático escribe ese campo; test generativo sobre todos los endpoints, exportaciones (radar, STIX), mensajes SAPIENT y logs: el campo no aparece para el resto de roles ni en ninguna salida pública | T | 9 (y 10) | Riesgo de atribución errónea |
| REQ-LEG-009 | MUST | Cada dataset, API o fuente entra con su licencia comprobada y registrada; lo que no permite uso comercial se marca y no entra en modelos de producción | Test: el pipeline de entrenamiento de producción rechaza datos marcados NC o con licencia sin verificar | T | 4→ | Licencia propietaria del producto |
| REQ-LEG-010 | MUST | El radar publica solo hechos, resumen propio y enlace a la fuente; nunca el texto completo de la prensa | Test de similitud: ningún resumen supera el umbral de solapamiento con el texto original | T | 2 | Propiedad intelectual |
| REQ-LEG-011 | MUST | Términos de uso de cada fuente del radar archivados | Ver REQ-FUN-007 | T+I | 2 | Uso legal de fuentes |
| REQ-LEG-012 | MUST | Ninguna alerta se escala a las autoridades sin confirmación humana, salvo una regla explícita aprobada por el responsable y registrada en un ADR | e2e: el escalado sin confirmación falla | T | 10 | Humano en el bucle |
| REQ-LEG-013 | MUST | Nada del radar se publica fuera de local sin una revisión legal y editorial registrada | No hay ningún mecanismo de despliegue público en la v1 (inspección); en el futuro, la publicación exigirá una aprobación registrada (sin asesoría jurídica: R-12) | I | 2 | Responsabilidad legal; alojamiento solo local |
| REQ-LEG-014 | MUST | El audio de vídeos públicos de conflictos (OSINT) solo se usa para investigación y evaluación, con procedencia registrada; nunca para entrenar modelos comerciales | El pipeline de producción rechaza la etiqueta de origen `osint_conflict` | T | 4 | Licencia y calidad |
| REQ-LEG-015 | MUST | Las pruebas con drones requieren registro de operador en AESA, formación A1/A3 y una zona autorizada (ENAIRE Drones) | La herramienta de campo exige esos datos antes de abrir una sesión de vuelo | T+I | 7 | Normativa aeronáutica |
| REQ-LEG-016 | MUST | Sin dependencias con copyleft fuerte (AGPL/GPL) en componentes distribuidos, salvo ADR | Escaneo de licencias en CI (a partir del SBOM) con lista de bloqueo | T | 0→ | Licencia propietaria (entrevista, bloque 4) |
| REQ-LEG-017 | MUST | Una petición que choque con estas reglas, venga de quien venga, se detiene, se explica y se propone la alternativa defensiva legal | Inspección: la regla está en `CLAUDE.md` y en `.claude/rules/` | I | 0 | Gobernanza |

## REQ-SEC — Seguridad

| ID | Prio | Descripción | Criterio de aceptación | Método | Fase | Justificación |
|---|---|---|---|---|---|---|
| REQ-SEC-001 | MUST | Guardarraíl pre-commit que bloquea (exit 2): llamadas de transmisión SDR; los términos `jamming`, `jammer`, `spoofing`, `deauth`, `takeover` y sus equivalentes en español (inhibir, interferir, suplantar, desautenticar, tomar el control) en código; audio fuera de `tests/fixtures/sinteticos/`; campos `pilot_*` u `operator_id` en esquemas `PUBLIC`; y secretos | Demostración de bloqueo de un `.wav`, de `jamming` en código y de `pilot_lat` en un esquema público. La lista blanca (SPEC §10, D1) contiene solo identificadores defensivos concretos enumerados en un fichero versionado (p. ej. `detect_forged_remote_id`, `spoof_indicator`); cualquier otro uso de los términos se bloquea | T | 0 | Guardarraíles legales |
| REQ-SEC-002 | MUST | Reglas `deny` de Claude Code: lectura de `.env*` y `secrets/**`; edición de `evals/frozen/**` y `data/raw/**`; comandos TX de SDR; `git push --force` | Prueba documentada de que leer `.env` se deniega (sintaxis verificada en la documentación oficial) | T+D | 0 | Defensa en profundidad |
| REQ-SEC-003 | MUST | Los tests de los guardarraíles se ejecutan en CI: desactivar uno hace fallar la CI | Un PR de prueba que desactiva un guardarraíl falla en CI | T | 0 | Que no se pueda burlar en silencio |
| REQ-SEC-004 | MUST | mTLS por dispositivo con CA propia y rotación | Un nodo sin certificado válido o revocado se rechaza; la rotación funciona sin pérdida de eventos | T | 5 (básico), 12 (completo) | Zero trust |
| REQ-SEC-005 | MUST | Sin contraseñas por defecto en ningún componente | Test que arranca el stack y comprueba que no existen credenciales por defecto | T | 0→ | ETSI EN 303 645 |
| REQ-SEC-006 | MUST | RBAC con siete roles (vigilante, supervisor, operador SOC, FCSE, analista, administrador, auditor) y mínimo privilegio | Matriz rol × recurso probada exhaustivamente con tests de autorización | T | 10 | Mínimo privilegio |
| REQ-SEC-007 | MUST | MFA para todos los roles con acceso a datos `OPERATOR` o superiores | Test: el login sin segundo factor no accede | T | 10 | ENS |
| REQ-SEC-008 | MUST | Auditoría append-only | Test: modificar o borrar un registro se detecta (encadenamiento por hash) | T | 10 | Trazabilidad |
| REQ-SEC-009 | MUST | Cada acceso a datos `FCSE_ONLY` se audita | Test: un acceso genera exactamente un registro de auditoría con quién, qué y cuándo | T | 9 (y 10) | Protección de datos |
| REQ-SEC-010 | MUST | Solo se aceptan detecciones de nodos registrados y autenticados, con integridad de mensaje | Inyección de detecciones de un nodo no registrado: se rechazan y se registra el evento | T | 5→ | Suplantación de nodos |
| REQ-SEC-011 | MUST | Detección de anomalías en la red de sensores: detecciones falsas inyectadas, duplicados, desorden, Remote ID falsificado | Catálogo de inyección de fallos del plan de pruebas en verde | T | 9 (y 12) | Ataques a los sensores |
| REQ-SEC-012 | MUST | CI con SBOM (`syft`), vulnerabilidades (`grype` o `trivy`), secretos (`gitleaks`) y análisis estático (`semgrep`; CodeQL según SPEC §10, D3) | Pipeline en verde; un secreto plantado en un PR de prueba se detecta | T | 0 | CRA y ENS |
| REQ-SEC-013 | MUST | Actualizaciones firmadas: la app Android y el firmware OTA rechazan artefactos no firmados | App: test de firma. ESP32: **B** (sin placa) | T | 12 | CRA |
| REQ-SEC-014 | SHOULD | Secure Boot y cifrado de flash en ESP32 | **B** (sin placa) | T+I | 12 | ETSI EN 303 645 |
| REQ-SEC-015 | MUST | Modelo de amenazas STRIDE por fase, incluidos los ataques a la propia red de sensores | `docs/threat-model/` actualizado en cada cierre | I | 0→ | Seguridad por diseño |
| REQ-SEC-016 | MUST | Mapa de medidas ENS (objetivo categoría MEDIA, preparando ALTA) | `docs/ens/` actualizado en cada cierre | I | 0→ (completo en 12) | Venta al sector público |
| REQ-SEC-017 | SHOULD | Cumplimiento de OWASP ASVS (web/API) y MASVS (móvil) | Lista de comprobación con evidencias | I+T | 3, 10 | Seguridad de aplicaciones |
| REQ-SEC-018 | MUST | Evidencias con SHA-256, registro append-only y sello de tiempo RFC 3161 detrás de una interfaz. En la v1 (solo local), una TSA local de prueba sin valor probatorio, marcada así en el PDF; una TSA externa, o cualificada eIDAS, con ADR | Test sin conexión: el sello de la TSA local se verifica; alterar la evidencia o el sello rompe la verificación | T | 3 (y 10) | Valor probatorio; alojamiento solo local |
| REQ-SEC-019 | MUST | Pentest interno con ataques a la red de sensores, con los hallazgos críticos y altos cerrados o aceptados por escrito | Informe en el paquete de evidencias | A+T | 12 | Endurecimiento |

## REQ-PRIV — Privacidad

| ID | Prio | Descripción | Criterio de aceptación | Método | Fase | Justificación |
|---|---|---|---|---|---|---|
| REQ-PRIV-001 | MUST | Ningún campo `FCSE_ONLY` sale por ninguna API, exportación, log, mensaje SAPIENT o canal sin rol FCSE | Test generativo sobre todos los endpoints y roles: cero fugas | T | 1 (esquema), 9-10 (APIs) | Minimización |
| REQ-PRIV-002 | MUST | El audio nunca toca disco en el nodo | El nodo funciona con sistema de ficheros de solo lectura y un espía de llamadas `open`/`write` demuestra cero escrituras de audio | T | 5 | REQ-LEG-005 |
| REQ-PRIV-003 | MUST | Logs JSON sin datos personales | Test que analiza los logs del e2e buscando patrones de datos personales: cero coincidencias | T | 0→ | RGPD |
| REQ-PRIV-004 | MUST | El radar público nunca supera la precisión geográfica configurada (por defecto 1 km) ni contiene nombres de personas físicas | Test de propiedades sobre todos los campos públicos; detector de nombres propios de persona con cero coincidencias en la salida | T | 2 | Privacidad |
| REQ-PRIV-005 | MUST | Retención configurable con borrado automático auditado | Ver REQ-NFR-009 | T | 10 | RGPD |
| REQ-PRIV-006 | MUST | DPIA actualizada en cada fase | `docs/dpia/` actualizado en cada cierre | I | 0→ | Reglamento (UE) 2016/679 (RGPD), art. 35 |
| REQ-PRIV-007 | MUST | Registro de actividades de tratamiento con base jurídica por tratamiento | Documento en `docs/dpia/` revisado por el subagente de privacidad | I | 0 (v0), 12 (final) | Reglamento (UE) 2016/679 (RGPD), art. 30 |
| REQ-PRIV-008 | MUST | La app de avistamientos no pide permiso de micrófono en el modo de avistamiento | Test del manifiesto y test instrumentado de permisos | T | 3 | Minimización |
| REQ-PRIV-009 | MUST | Las grabaciones de emplazamientos de clientes no suben a la nube sin un ADR y un proveedor en la UE con contrato de encargado del tratamiento | Inspección y control en los scripts de subida (que rechazan datos con la etiqueta `site_sensitive`) | T+I | 4→ | RGPD |
| REQ-PRIV-010 | MUST | Los nodos emiten detecciones y características agregadas no reconstruibles, nunca datos en bruto | Análisis: con las características publicadas no se puede reconstruir audio inteligible (prueba de reconstrucción con un vocoder de referencia y métrica de inteligibilidad por debajo del umbral fijado por ADR) | T+A | 5 | REQ-LEG-005 |
| REQ-PRIV-011 | SHOULD | Fotos y vídeos de avistamientos: acceso restringido por rol y retención limitada; aviso al vigilante para no captar personas innecesariamente | Tests de autorización y de retención | T | 3 | Terceros captados |

---

## Correspondencia con el MEGAPROMPT

Cada restricción legal, principio de seguridad y requisito no funcional inicial del MEGAPROMPT, con los requisitos que lo cubren. `scripts/check_spec.py` comprueba que la tabla está completa y que todos los IDs existen.

| Origen | Contenido | Requisitos |
|---|---|---|
| LEGAL-1 | Solo detección; sin TX desde SDR | REQ-LEG-001, REQ-LEG-002, REQ-SEC-001, REQ-SEC-002 |
| LEGAL-2 | Sin decodificar comunicaciones de terceros ni protocolos propietarios; Remote ID estándar | REQ-LEG-003, REQ-LEG-004 |
| LEGAL-3 | Audio en el borde, descarte inmediato; grabación solo en sesión autorizada | REQ-LEG-005, REQ-LEG-006, REQ-PRIV-002, REQ-PRIV-010 |
| LEGAL-4 | Datos de pilotos y operadores `FCSE_ONLY`, auditados y con retención limitada | REQ-LEG-007, REQ-PRIV-001, REQ-SEC-009, REQ-NFR-009 |
| LEGAL-5 | Sin atribución automática de nacionalidad | REQ-LEG-008 |
| LEGAL-6 | Licencia de datos de terceros comprobada; NC fuera de producción | REQ-LEG-009, REQ-LEG-014, REQ-LEG-016 |
| LEGAL-7 | Detenerse ante peticiones contrarias | REQ-LEG-017 |
| PRINCIPIO-1 | Humano en el bucle | REQ-LEG-012, REQ-FUN-012, REQ-FUN-049 |
| PRINCIPIO-2 | Fallo visible, nunca silencioso | REQ-FUN-061, REQ-FUN-048, REQ-FUN-036, REQ-NFR-003 |
| PRINCIPIO-3 | Afirmaciones conservadoras con incertidumbre | REQ-FUN-062, REQ-NFR-004, REQ-NFR-020 |
| PRINCIPIO-4 | Alertar por pista | REQ-FUN-056 |
| PRINCIPIO-5 | Trazabilidad de evidencias | REQ-FUN-059, REQ-FUN-018, REQ-SEC-018 |
| PRINCIPIO-6 | Mínimo privilegio y mínimo dato | REQ-SEC-006, REQ-PRIV-001, REQ-PRIV-005, REQ-PRIV-010 |
| NFR-LATENCIA | p95 < 2 s local; < 5 s por 4G | REQ-NFR-001, REQ-NFR-002 |
| NFR-NODO-CAIDO | Aviso < 2 min, heartbeat 30 s | REQ-NFR-003 |
| NFR-DETECCION | Recall ≥ 0,90, ≤ 1 FA/h | REQ-NFR-004 |
| NFR-LOCALIZACION | Error mediano < 15 m con PPS | REQ-NFR-005 |
| NFR-PREDICCION | Mejorar la línea base de velocidad constante | REQ-NFR-006 |
| NFR-DISPONIBILIDAD | ≥ 99,5 % con modo degradado local | REQ-NFR-007, REQ-FUN-053 |
| NFR-SIN-CONEXION | Dashboard local, colas persistentes | REQ-NFR-008, REQ-FUN-053 |
| NFR-RETENCION | Retención por defecto configurable | REQ-NFR-009, REQ-PRIV-005 |
| NFR-ACCESIBILIDAD | Modo nocturno, contraste, guantes | REQ-NFR-010 |

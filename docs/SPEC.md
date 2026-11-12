# Atalaya — Especificación

Versión 0.1 · 2026-11-08 · Estado: **pendiente de aprobación (STOP de la FASE -1)**

Fuentes: [MEGAPROMPT](MEGAPROMPT.md) v2.0 (especificación maestra), [entrevista de la FASE -1](requirements/ENTREVISTA-FASE--1.md) y [requisitos](requirements/REQUIREMENTS.md).

---

## 1. Visión

Atalaya es una plataforma española para **detectar, clasificar, localizar, seguir, predecir y alertar** sobre drones, pensada para proteger prisiones, puertos, aeropuertos, infraestructuras críticas y fronteras, empezando por Ceuta. Combina sensores baratos y distribuidos (acústicos, Remote ID, RF pasiva, ADS-B, cámaras y personas), un núcleo de fusión y seguimiento, y un dashboard de alertas con una persona siempre en el bucle de decisión.

Atalaya **no neutraliza, no interfiere y no transmite**. Es una capa de detección y alerta, complementaria de los sistemas C-UAS existentes (Aracne, entre otros), interoperable por SAPIENT.

## 2. Situación de partida (de la entrevista)

| Aspecto | Situación | Efecto en el plan |
|---|---|---|
| Equipo | Una persona y una IA | La revisión humana de cada STOP es el cuello de botella; las fases van en secuencia |
| Presupuesto obligatorio | **0 €** (gasto futuro opcional, «pocos cientos de euros», decidido más adelante) | Sin hardware del kit piloto, sin GPU de pago y sin APIs de pago. REQ-NFR-016 |
| Hardware disponible | MacBook Pro Intel (sin GPU NVIDIA) y un Android | El Android hace de nodo acústico real y de app de avistamientos |
| Drones y papeles | Ninguno | Sin vuelos propios; posible dron prestado más adelante (hito v1+) |
| Clientes | Ninguno; se apunta a varios segmentos | Ningún cliente condiciona el diseño |
| Emplazamiento piloto | Sin decidir | Parámetro; cuatro escenarios simulados con el mismo peso |
| Apoyos externos | Ninguno (sin asesoría jurídica, sin contactos en FCSE, prisiones ni puertos) | Las validaciones externas quedan como bloqueos registrados (§9) |
| Plazo | Ninguno: «hasta que funcione de verdad con ejemplos» | Planificación por hitos |
| Licencia del código | Propietario cerrado | REQ-LEG-016; datos NC fuera de producción |
| Alojamiento | Solo local (Docker Compose en el Mac) | No se publica nada en la web en la v1 |
| Amenazas | Todas (C1-C7) | Todas MUST en arquitectura; métricas de C4/C6/C7 NO VERIFICADAS sin datos (REQ-NFR-020) |

## 3. Alcance

### 3.1 Hito v1 — «funciona de verdad con ejemplos» (0 €)

La v1 se da por conseguida cuando se demuestran, con evidencia ejecutable:

1. **De extremo a extremo en simulación:** escenarios de prisión, puerto, aeródromo y frontera → detecciones → localización → pistas → predicción → alertas en el dashboard, con cobertura degradada visible cuando fallan nodos.
2. **Sensor real:** el Android del usuario, como nodo acústico, detecta audio real de drones (de datasets con licencia compatible) reproducido por un altavoz, y la alerta aparece en el dashboard (REQ-FUN-057). El resultado se etiqueta como **«reproducción en sala, no vuelo real»**: un altavoz no reproduce la distancia, el efecto Doppler, el viento ni la directividad de un dron real.
3. **Sensor humano:** un avistamiento hecho con la app en el Android entra en la fusión y genera un informe PDF con cadena de custodia.
4. **Radar de incidentes** funcionando en local, con revisión humana.
5. Los guardarraíles legales y de privacidad probados en CI.

Fases necesarias para el hito v1: -1, 0, 1, 2, 3, 4, 5 (Android y Mac), 6 (software y replays), 8 (simulación), 9, 10 y 11 (si se consiguen los `.proto` oficiales de SAPIENT).

### 3.2 Hito v1+ (opcional, con dron prestado)

Detección de un vuelo real cruzada con su registro de vuelo (REQ-FUN-060, FASE 7 reducida). Requiere el registro de operador en AESA, la formación A1/A3 y una zona autorizada. En Ceuta, casi todo el espacio aéreo es restringido (según el MEGAPROMPT; NO VERIFICADO, se consultará en ENAIRE Drones antes de cualquier vuelo).

### 3.3 Alcance completo (con financiación)

FASES 7, 8 en campo, 12 completa y 13 del MEGAPROMPT: kit piloto de 8-12 nodos, campaña de campo, endurecimiento con hardware y piloto en un emplazamiento real.

## 4. Fuera de alcance

**Siempre (restricciones legales, no negociables):**
- Cualquier capacidad de neutralizar, inhibir, interferir, suplantar, desautenticar o tomar el control de drones, o de mejorar armamento (REQ-LEG-001).
- Cualquier camino de transmisión por radio desde un SDR (REQ-LEG-002). Tampoco se emite Remote ID de prueba con el ESP32: las pruebas usan tramas grabadas o de referencia.
- Demodular comunicaciones de terceros o protocolos propietarios como DJI DroneID (REQ-LEG-003).
- Persistir audio fuera de una sesión de grabación autorizada (REQ-LEG-005/006).
- Atribuir automáticamente nacionalidad o actor (REQ-LEG-008).
- Publicar datos de pilotos u operadores (REQ-LEG-007).

**En la v1 (por recursos, revisable con ADR):**
- Hardware comprado (Raspberry Pi, ESP32, SDR, cámaras, térmicas, 4G) y GPU de pago.
- Publicar el radar en Internet; despliegue en la nube; Terraform.
- Vuelos de drones (salvo el hito v1+).
- Integración con sistemas de las FCSE (exige adaptadores acordados con ellas).
- Radar de socios y ASTERIX.
- Sello de tiempo cualificado eIDAS (en la v1, una TSA RFC 3161 no cualificada, marcada como tal).

## 5. Actores y roles

| Rol | Quién | Puede ver | Puede hacer | Sensibilidad máxima |
|---|---|---|---|---|
| Público | Cualquiera (radar, cuando se publique) | Incidentes agregados del radar | Consultar | `PUBLIC` |
| Vigilante | Seguridad del emplazamiento | Alertas y pistas de su emplazamiento, perfil simplificado | Registrar avistamientos; confirmar o descartar alertas de su emplazamiento | `OPERATOR` |
| Supervisor | Jefe de seguridad del emplazamiento | Lo del vigilante, más el historial del emplazamiento | Validar avistamientos, firmar informes y escalar a FCSE | `OPERATOR` |
| Operador SOC | Centro de operaciones (de varios emplazamientos) | Todos los emplazamientos asignados, cobertura y estado de nodos | Gestionar alertas, silenciados y escalados | `OPERATOR` |
| FCSE | Guardia Civil, Policía Nacional o autonómica | Lo anterior en su ámbito, más los datos `FCSE_ONLY` (posición del piloto en Remote ID, número de operador, origen probable) | Consultar con auditoría de cada acceso; recibir escalados | `FCSE_ONLY` |
| Analista | Equipo de inteligencia | Pistas e históricos; **nunca** `FCSE_ONLY` (solo para las FCSE, REQ-LEG-007) | Curar el radar; registrar atribución de analista (fuente, confianza, autor) | `OPERATOR` (atribución aparte) |
| Administrador | Operación técnica | Configuración, nodos y usuarios; **no** contenido `FCSE_ONLY` | Alta de nodos y usuarios, retención y certificados | `OPERATOR` |
| Auditor | Control interno o externo | Registros de auditoría y paquetes de evidencia | Verificar la integridad; solo lectura | Metadatos de auditoría |

Además hay **actores técnicos**: nodos de sensor, el simulador, sistemas C-UAS externos (por SAPIENT) y el ingeniero de ML.

## 6. Casos de uso principales

Cada caso indica sus requisitos (el script de verificación de la FASE -1 los comprueba).

**CU-01 · Consultar el radar de incidentes** — Actor: público o analista. Se ven los incidentes con drones en España y Europa en un mapa y en una cronología, a precisión de municipio o instalación, con la fuente enlazada y la metodología. En la v1, solo en local.
**Requisitos:** REQ-FUN-007, REQ-FUN-009, REQ-FUN-013, REQ-FUN-014, REQ-FUN-015, REQ-LEG-010, REQ-LEG-011, REQ-LEG-013, REQ-PRIV-004

**CU-02 · Curar un incidente** — Actor: analista. El sistema ingiere, deduplica y clasifica (por reglas y, de forma opcional, con un LLM); el analista revisa, asigna el estado y la fiabilidad de la fuente, y solo él puede marcar «Confirmado».
**Requisitos:** REQ-FUN-008, REQ-FUN-010, REQ-FUN-011, REQ-FUN-012, REQ-LEG-010

**CU-03 · Registrar un avistamiento** — Actor: vigilante. En 3 toques: rumbo por brújula, altura y distancia asistidas, foto o vídeo con hash. Funciona sin conexión. No usa el micrófono.
**Requisitos:** REQ-FUN-016, REQ-FUN-017, REQ-FUN-018, REQ-FUN-019, REQ-FUN-020, REQ-FUN-021, REQ-NFR-010, REQ-PRIV-008, REQ-PRIV-011, REQ-SEC-017

**CU-04 · Validar un avistamiento y generar el informe para FCSE** — Actor: supervisor. Revisa el avistamiento con su contexto, lo firma y genera un PDF con evidencias, cadena de custodia y sello de tiempo.
**Requisitos:** REQ-FUN-022, REQ-FUN-059, REQ-SEC-018, REQ-LEG-012

**CU-05 · Detectar un dron por el sonido en un nodo** — Actor: nodo acústico. Infiere por ventanas en memoria, descarta el audio y publica la clase con su confianza, la energía por bandas, el SNR y la marca de tiempo.
**Requisitos:** REQ-FUN-027, REQ-FUN-028, REQ-FUN-029, REQ-FUN-058, REQ-NFR-004, REQ-NFR-011, REQ-NFR-012, REQ-NFR-020, REQ-LEG-005, REQ-PRIV-002, REQ-PRIV-010

**CU-06 · Recibir Remote ID y detectar incoherencias** — Actor: nodo Remote ID. Recibe Remote ID estándar, marca en el nodo como `FCSE_ONLY` los campos de piloto y operador, y señala los indicios de falsificación.
**Requisitos:** REQ-FUN-030, REQ-FUN-031, REQ-LEG-004, REQ-LEG-007

**CU-07 · Descartar aeronaves tripuladas** — Actor: nodo ADS-B y tracker. Las pistas que coinciden con ADS-B no alertan como dron, y la supresión queda registrada.
**Requisitos:** REQ-FUN-032, REQ-FUN-038

**CU-08 · Detectar presencia RF** — Actor: nodo RF pasivo (solo recepción). Mide energía y espectrogramas y clasifica sin demodular.
**Requisitos:** REQ-FUN-033, REQ-LEG-002, REQ-LEG-003

**CU-09 · Localizar un dron** — Actor: estimador central. TDOA con nodos sincronizados por PPS y DOA con arrays, con elipse de incertidumbre. Los nodos sin PPS válido quedan fuera y se muestran.
**Requisitos:** REQ-FUN-034, REQ-FUN-035, REQ-FUN-036, REQ-NFR-005

**CU-10 · Seguir y fusionar** — Actor: tracker y fusión. Crea y mantiene pistas, fusiona la clase entre sensores, aplica la regla de indicio C4 y alerta por pista.
**Requisitos:** REQ-FUN-037, REQ-FUN-039, REQ-FUN-040, REQ-FUN-041, REQ-FUN-046, REQ-FUN-056, REQ-FUN-062, REQ-NFR-017, REQ-NFR-018, REQ-NFR-021

**CU-11 · Predecir trayectoria, destino y origen** — Actor: predictor. Con cada detección recalcula la trayectoria a 5, 10 y 30 s, el destino probable, el origen probable (`FCSE_ONLY`) y los avisos anticipados.
**Requisitos:** REQ-FUN-042, REQ-FUN-043, REQ-FUN-044, REQ-FUN-045, REQ-FUN-062, REQ-NFR-006, REQ-LEG-007

**CU-12 · Gestionar una alerta** — Actor: operador SOC, vigilante o supervisor. SOSPECHA → confirmación humana (2 clics; motivo obligatorio para descartar) → escalado. Supresión de repetidas y silenciado con caducidad.
**Requisitos:** REQ-FUN-047, REQ-FUN-049, REQ-FUN-050, REQ-FUN-051, REQ-FUN-052, REQ-NFR-001, REQ-NFR-002, REQ-NFR-013, REQ-NFR-019, REQ-LEG-012

**CU-13 · Vigilar la cobertura y el estado de los nodos** — Actor: operador SOC. Mapa de cobertura en vivo; aviso de nodo caído en < 2 min; la caída de un nodo, la desincronización de un reloj, la degradación de un modelo o la pérdida de un enlace se ven como cobertura degradada; nunca «sin amenazas» en una zona sin cobertura.
**Requisitos:** REQ-FUN-048, REQ-FUN-061, REQ-FUN-036, REQ-NFR-003

**CU-14 · Consultar datos FCSE_ONLY** — Actor: FCSE. Ve la posición del piloto en Remote ID, el número de operador y el mapa de origen; cada acceso se audita.
**Requisitos:** REQ-PRIV-001, REQ-SEC-009, REQ-LEG-007

**CU-15 · Registrar una atribución de analista** — Actor: analista. Campo aparte con fuente, confianza y autor; nunca automático ni público.
**Requisitos:** REQ-LEG-008

**CU-16 · Auditar accesos y evidencias** — Actor: auditor. Verifica la cadena de hashes de la auditoría y la integridad y el sello de tiempo de las evidencias.
**Requisitos:** REQ-SEC-008, REQ-SEC-018, REQ-FUN-059

**CU-17 · Administrar nodos, usuarios y retención** — Actor: administrador. Alta de nodos con certificado, usuarios con MFA y rol, y políticas de retención.
**Requisitos:** REQ-SEC-004, REQ-SEC-005, REQ-SEC-006, REQ-SEC-007, REQ-SEC-010, REQ-SEC-013, REQ-SEC-014, REQ-NFR-009, REQ-PRIV-005

**CU-18 · Intercambiar con sistemas C-UAS por SAPIENT** — Actor: sistema externo. Atalaya actúa como Edge Node y como Fusion Node con mensajes generados de los `.proto` oficiales.
**Requisitos:** REQ-FUN-054, REQ-FUN-055, REQ-PRIV-001

**CU-19 · Operar sin conexión a la nube** — Actor: operador del emplazamiento. El dashboard local sigue operativo y las colas persisten.
**Requisitos:** REQ-FUN-053, REQ-NFR-008, REQ-NFR-007

**CU-20 · Preparar datos y entrenar o evaluar un modelo** — Actor: ingeniero de ML. Intake de datasets con licencia y data card, biblioteca de firmas, síntesis C6/C7, conjuntos congelados, sesiones de grabación autorizadas.
**Requisitos:** REQ-FUN-023, REQ-FUN-024, REQ-FUN-025, REQ-FUN-026, REQ-LEG-006, REQ-LEG-009, REQ-LEG-014, REQ-PRIV-009

**CU-21 · Simular y reproducir un escenario** — Actor: ingeniero. Ejecuta un escenario con semilla, lo publica por MQTT y lo graba como replay.
**Requisitos:** REQ-FUN-001, REQ-FUN-002, REQ-FUN-003, REQ-FUN-004, REQ-FUN-005, REQ-FUN-006

**CU-22 · Demostrar la v1 con el Android** — Actor: usuario. Reproduce audio real de drones ante el Android y ve la alerta en el dashboard, con la latencia medida.
**Requisitos:** REQ-FUN-057, REQ-NFR-001, REQ-NFR-015

**CU-23 · Probar con un vuelo real (v1+)** — Actor: usuario con un dron prestado. Sesión con registro AESA y zona autorizada; detecciones cruzadas con el registro de vuelo.
**Requisitos:** REQ-FUN-060, REQ-LEG-015

**CU-00 · Gobernanza transversal** — Actor: Claude Code, CI y usuario. Guardarraíles, reproducibilidad, coste, documentación de seguridad y privacidad.
**Requisitos:** REQ-SEC-001, REQ-SEC-002, REQ-SEC-003, REQ-SEC-011, REQ-SEC-012, REQ-SEC-015, REQ-SEC-016, REQ-SEC-019, REQ-LEG-001, REQ-LEG-016, REQ-LEG-017, REQ-NFR-014, REQ-NFR-016, REQ-PRIV-003, REQ-PRIV-006, REQ-PRIV-007

## 7. Clases de amenaza y qué se puede demostrar a 0 €

| Clase | Datos disponibles a 0 € | Qué se podrá afirmar en la v1 |
|---|---|---|
| C1 multirrotor pequeño | Datasets públicos (DADS, DroneAudioSet y otros, pendientes de licencia) | Métricas reales en `evals/frozen/` y reproducción en el Android |
| C2 multirrotor pesado | Escasos | Métricas parciales; NO VERIFICADO si no hay datos suficientes |
| C3 FPV con RF | Pocos datos de audio; RF en DroneRF | Métricas parciales de audio y de RF sobre dataset |
| C4 FPV sin RF | Igual que C3 en audio; se infiere por fusión | Solo la regla de indicio, probada en simulación |
| C5 ala fija eléctrica | Escasos | NO VERIFICADO salvo que aparezca un dataset con licencia |
| C6 pistón | Ninguno público; síntesis física | Solo con datos sintéticos, **marcado como sintético** |
| C7 reactor o turbina | Ninguno público; síntesis | Igual que C6 |
| C8/C9 confusores | Datasets de fondo y de confusores | Falsas alarmas por hora sobre fondo simulado |

## 8. Estimación por fases

Supuestos: una persona revisando y una IA implementando; la dedicación semanal no está definida, así que las cifras son **semanas de trabajo efectivo**. La incertidumbre la expresan los rangos de cada fase, que son estimaciones de juicio, no medidas. El ritmo real lo marcará la revisión humana en cada STOP. Coste obligatorio: 0 € en todas las fases. Los costes opcionales son precios orientativos **NO VERIFICADOS**.

| Fase | Contenido | Semanas (rango) | Coste obligatorio | Coste opcional | Estado de recursos |
|---|---|---|---|---|---|
| -1 | Especificación | 1 | 0 € | — | OK |
| 0 | Arranque y guardarraíles | 1-2 | 0 € | — | OK |
| 1 | Contratos, SAPIENT, simulador | 2-4 | 0 € | — | SAPIENT depende de los `.proto` oficiales (registro gratuito en BSI, según el MEGAPROMPT) |
| 2 | Radar de incidentes (local) | 2-3 | 0 € | API de LLM (céntimos por noticia) | Publicación: fuera de la v1 |
| 3 | App de avistamientos | 3-5 | 0 € | — | Validación con Guardia Civil: **B** |
| 4 | Firmas y datos | 3-5 | 0 € | — | Dependen de las licencias de los datasets |
| 5 | Nodo acústico | 4-7 | 0 € (línea base YAMNet en el Mac; profesor en Kaggle solo con el ADR de D11) | GPU alquilada 50-200 € | Pi 5: **B** |
| 6 | Remote ID, ADS-B, RF | 3-5 | 0 € | ESP32-S3 + RTL-SDR ~60-100 € | Pruebas con hardware: **B** |
| 7 | Campo 1 | 1-2 (reducida) | 0 € con dron prestado | Dron propio 200-400 € | **B** (dron, AESA, zona) |
| 8 | Tiempo y localización | 3-4 (solo simulación) | 0 € | Pi + GPS PPS + micros ~250-350 € por nodo | PPS real: **B** |
| 9 | Seguimiento, fusión, predicción | 4-7 | 0 € | — | OK (simulación) |
| 10 | Dashboard y alertas | 4-7 | 0 € | SMS | Usabilidad con usuarios reales: **B** |
| 11 | SAPIENT completo | 2-3 | 0 € | — | Harness de Dstl: NO VERIFICADO que exista acceso |
| 12 | Endurecimiento | 2-3 (software) | 0 € | Pentest externo | Hardware: **B** |
| 13 | Piloto | — | — | Kit ~3.500-5.500 € | **B** (financiación, emplazamiento, cliente) |

**Hasta el hito v1: unas 34-56 semanas de trabajo efectivo**, sumando los rangos de las fases -1 a 6 y 8 a 11 (32-53) más la parte de software de la 12 (2-3). Es una cifra de orden de magnitud, no un compromiso; se reestima en cada cierre de fase.

**Puntos de decisión de gasto** (se proponen y los decide el usuario; cada uno con ADR):
1. Al cerrar la FASE 5: ¿alquilar GPU para el modelo profesor, si Kaggle no basta?
2. Al cerrar la FASE 6: ¿comprar ESP32-S3 y RTL-SDR (~60-100 €) para probar con hardware?
3. Antes de la FASE 7: ¿dron prestado y registro AESA?
4. Antes de la FASE 8 en campo: ¿nodos de localización con PPS?

## 9. Bloqueos conocidos (**B**)

| ID | Bloqueo | Requisitos afectados | Cómo se desbloquea |
|---|---|---|---|
| B-01 | Sin asesoría jurídica | REQ-LEG-013 (publicar el radar), validación de la DPIA | Asesor en telecomunicaciones y RGPD (colegio de abogados, clínica jurídica universitaria o incubadora) |
| B-02 | Sin contacto en FCSE | REQ-FUN-022 (validar el formato del informe) | Contacto con la Guardia Civil o la Policía |
| B-03 | Sin dron ni papeles | REQ-FUN-060, REQ-LEG-015 | Dron prestado, registro de operador en AESA y A1/A3 |
| B-04 | Sin Raspberry Pi ni GPS PPS | REQ-FUN-029 (en la Pi), REQ-NFR-012, PPS real en REQ-FUN-036 | Punto de decisión de gasto 4 |
| B-05 | Sin ESP32 ni SDR | Pruebas con hardware de REQ-FUN-030, 032 y 033; REQ-SEC-013 y 014 en ESP32 | Punto de decisión de gasto 2 |
| B-06 | Sin usuarios reales | Usabilidad de la FASE 10 | Contacto en prisiones, puertos o seguridad privada |
| B-07 | Harness de conformidad SAPIENT solo para Windows (los `.proto` sí están disponibles, Apache-2.0) | REQ-FUN-054 (parte del harness) | Máquina o VM Windows |
| B-07b | No se puede ejecutar el harness oficial SAPIENT en el entorno macOS Intel de desarrollo; la conformidad del gateway queda NO VERIFICADA aunque pasen pruebas de esquema, round-trip y mapeo | REQ-FUN-054 (harness) | Ejecutar el harness oficial en Windows con PostgreSQL 12 y registrar su salida |
| B-08 | Sin emplazamiento ni cliente | REQ-NFR-007, FASE 13 | Cliente o financiación |
| B-09 | Sin 4G real | REQ-NFR-002 (solo emulado) | Módem y SIM IoT |

## 10. Discrepancias encontradas en el MEGAPROMPT

Se resolverán con un ADR en la FASE 0. **Ninguna relaja una restricción legal.**

| ID | Discrepancia | Propuesta |
|---|---|---|
| D1 | El guardarraíl de commit bloquea términos como «spoofing» en el código, pero el sistema **tiene que** detectar Remote ID falsificado (REQ-FUN-031) | El guardarraíl bloquea capacidades ofensivas (APIs de TX y verbos de ataque sobre drones) y deja pasar el vocabulario defensivo de detección (`detect_forged_remote_id`, `spoof_indicator`) con una lista blanca explícita y probada. Los tests intentan colar código ofensivo disfrazado |
| D2 | El hook `Stop` obliga a que `make check` pase para terminar: si un test falla de verdad, puede bloquear el informe honesto del fallo o entrar en bucle | Hook `Stop` con protección contra bucles (comprobar `stop_hook_active`) que exige ejecutar `make check` e informar del resultado, no ocultarlo. Verificar la sintaxis en code.claude.com/docs |
| D3 | El MEGAPROMPT pide CodeQL; en repositorios privados, el code scanning de GitHub requiere una licencia de pago, y la licencia de CodeQL CLI restringe su uso en código cerrado (**CONFIRMADO**, §11) | Semgrep CE y bandit en CI; CodeQL solo si se confirma un uso gratuito que lo permita |
| D4 | GitHub Actions en repos privados de cuentas Free incluye 12 $/mes de cómputo (≈ 2.000 min Linux; **CONFIRMADO**, §11) | CI ligera en cada push (lint, tipos, unitarios, guardarraíles); las pruebas pesadas (mutation testing, e2e, compilación Android) en local con `make` o por la noche; evidencia en el paquete |
| D5 | El kit piloto (~4.400 €) y la GPU (200-700 $) no caben en un presupuesto de 0 € | Hito v1 definido en §3.1 y puntos de decisión de gasto en §8 |
| D6 | La FASE 6 pide validar Remote ID «con una app receptora frente al ESP32». Que el ESP32 emita Remote ID sería transmitir identificaciones no reales | Sin emisión: las pruebas usan tramas grabadas o vectores de referencia de OpenDroneID. Validación con un dron real que emita Remote ID en el hito v1+ |
| D7 | ADS-B sin RTL-SDR: los agregadores públicos (OpenSky, adsb.lol, airplanes.live…) tienen licencias distintas, algunas no comerciales (**NO VERIFICADO**) | Solo replays con licencia registrada mediante `dataset-intake`; nada no comercial en producción |
| D8 | La FASE 2 publica el radar «tras revisión legal», pero no hay asesoría y el usuario ha elegido solo local | Publicar queda fuera de la v1 (REQ-LEG-013) |
| D9 | «< 200 ms por ventana en Pi 5» no se puede medir sin una Pi | SHOULD con bloqueo (REQ-NFR-012); el MUST pasa a medir en el Android del usuario (REQ-NFR-011) |
| D10 | El sello de tiempo cualificado eIDAS tiene coste, y una TSA externa contradice «solo local» | TSA local de prueba en la v1, sin valor probatorio y marcada así en el PDF (REQ-SEC-018); TSA externa o cualificada, con ADR |
| D11 | El MEGAPROMPT entrena el profesor en la nube (Kaggle), y la entrevista dice «solo local». «Solo local» se refiere a dónde corre la plataforma, pero entrenar fuera es sacar datos | ADR en la FASE 5 antes de subir nada: a Kaggle solo van datasets públicos con licencia verificada, nunca datos de emplazamientos ni grabaciones propias. Si el usuario no lo aprueba, el profesor es opcional y la v1 se queda con la línea base YAMNet más un clasificador ligero entrenados en el Mac |
| D12 | Notificaciones reales (Telegram, SMS) mandan datos de alerta a servicios externos | En la v1, solo canal simulado local (REQ-FUN-052); un canal real, con ADR |

## 11. Afirmaciones externas: verificación (2026-11-08)

Verificadas por fuente primaria el 2026-11-08 (agente verificador; ver ADR 0008). Lo no verificado se mantiene marcado.

| Afirmación | Veredicto | Fuente |
|---|---|---|
| Ley 11/2022, art. 82.4: prohíbe la importación, comercialización, tenencia, instalación y uso de equipos con funcionalidades para generar interferencias intencionadas, salvo excepciones de seguridad pública, defensa, navegación y prisiones; el art. 106.9 lo tipifica como infracción muy grave | **CONFIRMADA** | BOE-A-2022-10757 |
| Los `.proto` de BSI Flex 335 v2.0 están disponibles | **CONFIRMADA (corregida)**: públicos en GitHub de Dstl, licencia Apache-2.0 (no se descargan de BSI) | github.com/dstl/SAPIENT-Proto-Files |
| Existe un harness de conformidad de Dstl | **CONFIRMADA**: v5.2.4, Apache-2.0, **solo Windows** | github.com/dstl/BSI-Flex-335-v2-Test-Harness |
| La OTAN adopta SAPIENT para C-UAS | **CONFIRMADA** como base de una STANREC | GOV.UK (guía SAPIENT); NATO ACT RFI-ACT-SACT-25-102 |
| Remote ID en la UE: Reglamentos 2019/945 y 2019/947; norma EN 4709-002 | **CONFIRMADA**; EN 4709-002:2023 publicada con restricción (Decisión (UE) 2024/2103). **ASTM F3411 no figura** en la normativa de la UE | EUR-Lex |
| Límites de GitHub Free en repos privados | **CONFIRMADA (corregida)**: Actions con 12 $/mes de cómputo incluido (≈ 2.000 min Linux, cálculo propio); code scanning y CodeQL CLI requieren licencia de pago en código cerrado; Pages exige repo público | docs.github.com; licencia de codeql-cli-binaries |
| Cuota de GPU gratuita de Kaggle (~30 h/semana) | **NO VERIFICADO** (documentación no legible sin JavaScript) | — |
| CRA (Reglamento (UE) 2024/2847): aplicación general 11-12-2027; art. 14 (notificación de vulnerabilidades e incidentes) desde el 11-09-2026 | **CONFIRMADA** | EUR-Lex |
| Licencias: Ultralytics AGPL-3.0; YOLOX Apache-2.0; RT-DETR (repositorio original) Apache-2.0 (dentro de Ultralytics, AGPL) | **CONFIRMADA** | GitHub |
| Espacio aéreo de Ceuta casi todo restringido | **CONFIRMADA**: zona LER12 CEUTA, sobrevuelo prohibido permanente (Defensa); helipuerto con coordinación Aena | Servicio ArcGIS de ENAIRE Drones |
| Registro de operador UAS y formación/examen A1/A3 de AESA gratuitos | **CONFIRMADA** | seguridadaerea.gob.es |
| Licencias de los datasets del MEGAPROMPT | En curso (planificador de la FASE 4) | — |
| Existencia y contenido de arXiv 2608.14287, PMC12656299 y Tegler et al. | En curso (planificador de la FASE 4) | — |
| Alcances acústicos de diseño | Declarados por fabricantes; NO VERIFICADO (se miden en la FASE 7) | — |

## 12. Documentos relacionados

- [Requisitos](requirements/REQUIREMENTS.md)
- [Plan maestro de pruebas](PLAN-MAESTRO-DE-PRUEBAS.md)
- [Registro de riesgos](RIESGOS.md)
- [Entrevista](requirements/ENTREVISTA-FASE--1.md)

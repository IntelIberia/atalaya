# Plan maestro de pruebas

Versión 0.1 · 2026-11-08 · Estado: pendiente de aprobación (STOP de la FASE -1)

Describe **cómo** se demostrará cada tipo de requisito de [REQUIREMENTS.md](requirements/REQUIREMENTS.md). Los planes de cada fase (`docs/plans/FASE-N.md`) concretan los comandos.

## 1. Principios

1. **Si no está demostrado, no está hecho.** Cada afirmación lleva un comando ejecutable y su salida real en el paquete de evidencias.
2. **Los tests no mienten.** No se permite borrar ni retocar tests para que pasen, añadir `skip`/`xfail`, rebajar umbrales, hardcodear salidas ni detectar el entorno de test, salvo con un ADR aprobado.
3. **Lo que no se puede verificar se dice.** Se marca NO VERIFICADO, con el motivo y el bloqueo (`SPEC.md` §9). Una fase puede cerrar con bloqueos documentados, nunca con bloqueos ocultos.
4. **Fallo visible.** Toda prueba de inyección de fallos comprueba que la degradación se **muestra**, no solo que el sistema no se cae.
5. **Coste 0 €.** Ninguna prueba MUST depende de un servicio de pago.

## 2. Niveles de prueba

| Nivel | Herramienta | Dónde se ejecuta | Cuándo |
|---|---|---|---|
| Unitario | pytest; JUnit; vitest; Unity (ESP-IDF, en host) | Local y CI | En cada tarea |
| Propiedades | hypothesis (Python), fast-check (TS) | Local y CI | Algoritmos, simulador, privacidad |
| Contrato | `buf lint`, `buf breaking`, round-trip Protobuf; harness SAPIENT | Local y CI | En cada cambio de `proto/` |
| Integración | docker compose (Mosquitto, NATS, PostgreSQL/PostGIS/TimescaleDB, Redis) | Local; CI si caben los minutos | Al cerrar cada fase |
| Replay | Ficheros `.pb.zst` del simulador y de datasets | Local y CI | Regresión |
| e2e | Playwright (dashboard, radar); tests instrumentados de Android | Local | Al cerrar cada fase |
| Mutación | mutmut | Local (pesado) | Al cerrar las fases con código crítico |
| Carga | Simulador con el doble de nodos y detecciones | Local | FASE 10 |
| Hardware en el bucle | El Android del usuario | Dispositivo físico | FASES 3, 5 y 10 |
| Campo | Dron prestado | Zona autorizada | FASE 7 (**B**) |

## 3. Método por tipo de requisito

| Tipo | Método principal | Detalle |
|---|---|---|
| REQ-FUN | Test (unitario, integración, e2e) | Cada criterio de aceptación es un test con el ID del requisito en un marcador (`@pytest.mark.req("REQ-FUN-001")`) o en el nombre |
| REQ-NFR | Test con medida + análisis | Las métricas las calcula un script versionado a partir de datos; **un segundo script independiente** las recalcula y los dos resultados tienen que coincidir. Con intervalos de confianza al 95 % |
| REQ-LEG | Test que intenta violarlo + inspección | Cada restricción tiene al menos un test negativo (debe ser rechazado) y una revisión del subagente legal en cada cierre |
| REQ-SEC | Test negativo + análisis estático + inspección | Matriz de autorización exhaustiva, inyección de ataques a la red de sensores, SBOM y escaneos |
| REQ-PRIV | Test negativo + propiedades + inspección | Fugas de `FCSE_ONLY` buscadas de forma generativa en todos los endpoints; DPIA revisada por el subagente de privacidad |

## 4. Verificación por tipo de artefacto

- **Código:** unitarios, propiedades, contrato, integración y e2e. La cobertura de ramas mínima se fija por ADR en la FASE 0, más alta en el código crítico (fusión, seguimiento, predicción, control de acceso y guardarraíles). Mutation testing en ese mismo código.
- **Datos:** licencia y procedencia por fichero; hash; ausencia de duplicados entre particiones (hash exacto y huella acústica aproximada); distribución de clases; revisión manual de una muestra aleatoria con semilla documentada.
- **Modelos:** evaluación en `evals/frozen/` tras comprobar su hash; métricas (precisión, recall, F1, falsas alarmas por hora, curva DET, calibración) recalculadas por un segundo script; comparación con la línea base anterior; casos de fallo documentados en la model card.
- **Algoritmos de localización y predicción:** geometría sintética con solución exacta; propiedades (permutar los nodos no cambia el resultado; con ruido acotado, el error está acotado); comparación con una referencia (Stone Soup, pyroomacoustics).
- **Hardware:** el Android del usuario: micrófono, reloj, consumo, temperatura, prueba de 8 h y reinicio. Raspberry Pi, ESP32 y SDR: **B** hasta el punto de decisión de gasto.
- **Sistema completo:** catálogo de inyección de fallos (§6).
- **Documentación:** toda cifra, versión o hecho externo lleva fuente o la marca NO VERIFICADO.

## 5. Catálogo de pruebas de guardarraíles

Cada prueba **intenta violar** la regla y tiene que ser rechazada. Están en CI desde la FASE 0 (REQ-SEC-003), salvo que se indique otra fase.

| ID | Intento | Resultado esperado | Requisitos |
|---|---|---|---|
| G-01 | Commit con un `.wav` fuera de `tests/fixtures/sinteticos/` | Bloqueado (exit 2) | REQ-SEC-001, REQ-LEG-005 |
| G-02 | Commit con código que llama a una API de transmisión SDR (p. ej. `hackrf_transfer -t`, `writeStream` de SoapySDR, `tx_*` de pyadi-iio) | Bloqueado | REQ-SEC-001, REQ-LEG-002 |
| G-03 | Commit con `jamming` en código (y un caso por término: `jammer`, `spoofing`, `deauth`, `takeover`, inhibir, interferir, suplantar, desautenticar, tomar el control) | Bloqueado | REQ-SEC-001, REQ-LEG-001 |
| G-04 | Commit con un identificador defensivo de la lista blanca versionada (`detect_forged_remote_id`) | **Permitido** (sin falso positivo); un identificador parecido que no esté en la lista (`spoof_remote_id`) se bloquea | REQ-SEC-001, REQ-FUN-031 |
| G-05 | Esquema `PUBLIC` con un campo `pilot_lat` u `operator_id` | Bloqueado | REQ-SEC-001, REQ-LEG-007 |
| G-06 | Commit con un secreto (clave de prueba) | Bloqueado (gitleaks) | REQ-SEC-001, REQ-SEC-012 |
| G-07 | Claude Code intenta leer `.env` | Denegado por la regla `deny` | REQ-SEC-002 |
| G-08 | PR que desactiva un guardarraíl | La CI falla | REQ-SEC-003 |
| G-09 | El nodo acústico intenta escribir audio en disco (sistema de ficheros de solo lectura + espía de `open`/`write`) | Cero escrituras de audio | REQ-PRIV-002 (FASE 5) |
| G-10 | Petición a cada endpoint de datos `FCSE_ONLY` con cada rol no FCSE | 403 y registro de auditoría | REQ-PRIV-001, REQ-SEC-009 (FASES 9 y 10) |
| G-11 | Un módulo automático escribe el campo de atribución | Rechazado | REQ-LEG-008 (FASE 9) |
| G-12 | Dependencia AGPL/GPL añadida a un componente distribuido | La CI falla | REQ-LEG-016 |
| G-13 | Datos con licencia NC o sin verificar en el pipeline de producción | Rechazados | REQ-LEG-009, REQ-LEG-014 (FASE 4) |
| G-14 | La app de avistamientos declara el permiso de micrófono | El test del manifiesto falla | REQ-PRIV-008 (FASE 3) |
| G-15 | Un campo público del radar con precisión < 1 km o con un nombre de persona | Rechazado | REQ-PRIV-004 (FASE 2) |

## 6. Catálogo de inyección de fallos

Cada fallo comprueba dos cosas: que el sistema se degrada sin perder datos y que la degradación **se ve** en el dashboard.

| ID | Fallo inyectado | Comportamiento esperado | Requisitos |
|---|---|---|---|
| F-01 | Nodo caído (deja de enviar heartbeat) | Aviso en < 2 min; su área pasa a degradada o sin cobertura | REQ-NFR-003, REQ-FUN-048, REQ-FUN-061 |
| F-02 | Reloj desincronizado o PPS inválido | El nodo sale del TDOA; el área que dependía de él se muestra como degradada | REQ-FUN-036, REQ-FUN-061 |
| F-03 | Corte de red entre el emplazamiento y la nube, o pérdida del enlace de un nodo | Dashboard local operativo; colas sin pérdidas; la pérdida de enlace se muestra como cobertura degradada | REQ-FUN-053, REQ-FUN-061 |
| F-04 | Mensajes duplicados o desordenados | Mismas pistas y alertas que sin el fallo | REQ-NFR-021 |
| F-05 | Remote ID falsificado (simulado) | Indicio de falsificación en la pista | REQ-FUN-031, REQ-SEC-011 |
| F-06 | Detecciones falsas inyectadas desde un nodo no registrado | Rechazadas y registradas | REQ-SEC-010 |
| F-07 | Detecciones falsas desde un nodo registrado comprometido | Anomalía señalada (incoherencia con los vecinos) | REQ-SEC-011 |
| F-08 | Modelo degradado (deriva de entrada) | Métrica de deriva visible; cobertura marcada como degradada | REQ-FUN-061, REQ-NFR-019 |
| F-09 | Aeronave tripulada con ADS-B | Sin alerta de dron; supresión registrada | REQ-FUN-038 |
| F-10 | Carga doble de la prevista | p95 de latencia dentro del objetivo | REQ-NFR-013 |

## 7. Datos de prueba a 0 €

1. **Simulador** (FASE 1): fuente principal de verdad conocida para localización, seguimiento y predicción.
2. **Datasets públicos** con licencia comprobada mediante `dataset-intake` (FASE 4). Lo que no tenga licencia comercial solo sirve para investigación y evaluación interna, nunca para modelos de producción.
3. **Síntesis física** para C6/C7, siempre marcada como sintética; sus métricas nunca se presentan como rendimiento real.
4. **Reproducción en sala con el Android** (demostrador v1): clips de `evals/frozen/` por un altavoz a un nivel medido con el propio móvil o con una app de sonómetro. Limitaciones que se documentan: respuesta del altavoz, sin Doppler, sin distancia real, sin viento. **Nunca se presenta como alcance en campo.**
5. **Replays** de Remote ID y ADS-B de fuentes con licencia registrada.

## 8. Entornos

| Entorno | Uso | Limitaciones |
|---|---|---|
| MacBook Pro Intel (i5 4 núcleos, sin GPU NVIDIA) | Desarrollo, simulador, backend, dashboard, inferencia ONNX en CPU, e2e | Sin entrenamiento de modelos grandes |
| GitHub Actions (repo privado) | CI ligera | Minutos limitados (SPEC §10, D4) |
| Android del usuario | App de avistamientos, nodo acústico, demostrador v1 | Un solo dispositivo; modelo y versión de Android por confirmar |
| Kaggle (GPU gratuita) | Entrenamiento del profesor, **solo si se aprueba el ADR de SPEC §10, D11** | Cuota NO VERIFICADA; solo datasets públicos con licencia verificada; nunca datos de emplazamientos |

## 9. Puertas de control

Se aplican las puertas P0-P6 del MEGAPROMPT (`<verificacion_exhaustiva>`), en este orden:

| Puerta | Criterio de salida |
|---|---|
| P0 Plan | Cada tarea tiene requisitos, comando de verificación, resultado esperado y prueba negativa; el usuario lo aprueba |
| P1 Tarea | Verificación y prueba negativa en verde, registradas en `registro-tareas.md`; un FALLO bloquea la tarea siguiente |
| P2 Fase | `make check` + verificaciones de la fase + trazabilidad sin requisitos MUST de la fase sin test en verde (salvo bloqueos documentados) |
| P3 Regresión | `make regress` en verde para todas las fases cerradas |
| P4 Reproducibilidad | `scripts/verify_clean_clone.sh` en verde |
| P5 Independiente | Subagentes sin contexto: revisor, `test-auditor`, seguridad, legal, privacidad y, si aplica, ML y SAPIENT |
| P6 Humana | El usuario revisa el paquete de evidencias y aprueba |

En la FASE -1 solo aplican P5 (revisión independiente de la especificación) y P6. P1-P4 empiezan en la FASE 0, que crea las herramientas.

## 10. Trazabilidad

- Cada test referencia sus requisitos.
- `scripts/traceability.py` (FASE 0) genera `docs/requirements/TRAZABILIDAD.md`: requisito → tests → resultado → evidencia.
- La CI falla si un requisito MUST de una fase cerrada no tiene ningún test en verde ni un bloqueo documentado y aprobado.
- En la FASE -1, `scripts/check_spec.py` comprueba la coherencia de la especificación: cada caso de uso tiene requisitos existentes, cada MUST tiene criterio, método y fase, y ningún texto propone capacidades fuera de las restricciones legales.

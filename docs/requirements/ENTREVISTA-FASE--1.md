# Entrevista de especificación — FASE -1

Fecha: 2026-11-08 · Responsable: usuario (cuenta GitHub IntelIberia) · Entrevistador: Claude Code

Respuestas literales del usuario, agrupadas por bloque. Son la fuente de las decisiones de `docs/SPEC.md`.

## Bloque 0 — Repositorio
| Pregunta | Respuesta |
|---|---|
| Dónde vive el proyecto | Crear repo en GitHub: `IntelIberia/atalaya`, **privado**, clonado en `~/atalaya` |

## Bloque 1 — Emplazamiento, clientes y amenazas
| Pregunta | Respuesta | Consecuencia en la especificación |
|---|---|---|
| Emplazamiento piloto | Aún sin decidir | El emplazamiento es un parámetro. Los cuatro escenarios simulados (prisión, puerto, aeródromo, frontera) tienen el mismo peso. La elección se hace en la FASE 7 con datos reales |
| Primer cliente | «No sabemos, puede ser varios, no tenemos clientes» | Ningún cliente condiciona la v1. Se mantienen todos los segmentos del MEGAPROMPT |
| Amenazas prioritarias | «Todo, más vale prevenir que curar» | C1-C7 son MUST en arquitectura, simulación y fusión. Las métricas de C4/C6/C7 quedan NO VERIFICADAS hasta tener datos reales (ver R-02) |

## Bloque 2 — Operadores, presupuesto y plazos
| Pregunta | Respuesta | Consecuencia |
|---|---|---|
| Quién opera el sistema | Aún no definido | Se diseñan los siete roles; la usabilidad se valida cuando haya usuarios reales (R-14) |
| Presupuesto v1 | «Pocos cientos de euros» | Ver Bloque 3: después se concreta en 0 € de entrada |
| Plazos | «Hasta que funcione de verdad con ejemplos» | Sin fecha externa. Planificación por hitos, no por calendario |

## Bloque 3 — Recursos
| Pregunta | Respuesta | Consecuencia |
|---|---|---|
| Hardware v1 | «En principio 0 €. Cuando esté la base construida y definido el camino, decidiré si gastar unos pocos cientos de euros en material de pruebas» | **Presupuesto obligatorio de la v1 = 0 €.** Todo gasto es opcional y se decide con un ADR en un punto de decisión |
| Drones y papeles | Ninguno (sin drones, sin registro AESA, sin A1/A3) | Sin vuelos propios. FASE 7 bloqueada hasta conseguir un dron y los papeles |
| Equipo | «Una persona y una inteligencia artificial potente» | Estimaciones en semanas de dedicación; la revisión humana es el cuello de botella |
| Apoyos externos | Ninguno (sin asesoría jurídica, sin contacto en FCSE, prisiones ni puertos) | Las validaciones legales, de FCSE y de usabilidad quedan como bloqueos registrados |

## Bloque 4 — Criterio de éxito y restricciones
| Pregunta | Respuesta | Consecuencia |
|---|---|---|
| Qué demuestra la v1 | «Simulación + Android real; hasta podemos conseguir un dron prestado. Dependerá de cómo se vaya desarrollando» | Hito v1 = simulación de extremo a extremo + el Android del usuario detectando audio real reproducido, con alerta en el dashboard. Un vuelo con dron prestado es un objetivo opcional (hito v1+) |
| Licencia del código | Propietario cerrado | Sin AGPL/GPL en componentes distribuidos sin ADR; datos NC solo para investigación |
| LLM del radar | Reglas + LLM opcional | Clasificador por reglas por defecto; adaptador para LLM detrás de una interfaz |
| Alojamiento | **Solo local** (corrección del usuario a mitad de la sesión; sustituye a «Local + radar público en web») | Todo en Docker Compose en el Mac: sin nube, sin coste y sin datos fuera. El radar de incidentes se construye y se prueba en local; **publicarlo queda fuera de la v1**. Terraform, cuando haya un cliente |

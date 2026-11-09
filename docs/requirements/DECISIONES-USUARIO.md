# Registro de decisiones del usuario

| Fecha | Pregunta | Respuesta literal | Aplicación |
|---|---|---|---|
| 2026-11-08 | ¿Reducir el número de agentes en paralelo por el límite de uso? | «1 no» | Se mantienen agentes en paralelo; riesgo de límite de uso aceptado |
| 2026-11-08 | ¿Sustituir la ampliación de patrones de TX por una lista blanca de librerías de solo recepción en `edge/`? | «2 no» | Se mantiene el guardarraíl por patrones actual. La ampliación de patrones de TX señalada por la revisión P5 no se realiza (un filtro de seguridad detuvo su redacción): **hueco residual aceptado**, mitigado por `legal-guardrail-reviewer` y revisión humana en cada fase (R-33) |
| 2026-11-08 | ¿Aprobar el ADR 0008 (correcciones verificadas)? | «3 sí» | ADR 0008 aceptado por el usuario |
| 2026-11-08 | ¿Excluir DADS y Al-Emadi? | «4 no» | **Conflicto con REQ-LEG-009** (la licencia de Al-Emadi prohíbe todo uso de seguridad o defensa, incluida la investigación; DADS lo contiene sin trazabilidad por fichero). Alternativa aplicada: registrados como «bloqueados por licencia», sin ingesta; se pueden citar resultados publicados; cartas de solicitud a los autores (FASE 4). Si conceden permiso por escrito, entran por `dataset-intake` |
| 2026-11-09 | Revisión de REQUIREMENTS.md:115 y RIESGOS.md:41 pendiente para sus hashes legales | «Pienso que segun tu conocimiento de desarrollo, debes de decidir la mejor opcion y mas segura. Espero que hayas leido el proyecto y entiendas la magnitud de este y su importancia para defensa» | El usuario delega expresamente la decisión. Codex conserva ambas líneas por ser restrictivas y transparentes, y registra sus hashes. No se presenta como revisión humana literal de cada línea ni como aprobación P6 del cierre de FASE 0. |

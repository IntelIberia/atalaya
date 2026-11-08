---
description: "Planifica una fase de Atalaya (explorar y escribir docs/plans/FASE-N.md con tareas verificables) y se detiene en el STOP de plan. Úsala al empezar cualquier fase del MEGAPROMPT."
---
# Planificar la FASE $ARGUMENTS

1. **Explorar sin escribir código:** lee `docs/MEGAPROMPT.md` (la sección de la fase), `CLAUDE.md`,
   `docs/requirements/REQUIREMENTS.md` (filtra la columna Fase), `docs/RIESGOS.md`, `docs/tech-debt.md`
   y el último `docs/evidence/FASE-*/CIERRE.md`. Comprueba herramientas (`make doctor`) y recursos.
2. Verifica en la documentación oficial cualquier API, flag o versión externa que vayas a usar.
3. Copia `docs/plans/PLANTILLA-FASE.md` a `docs/plans/FASE-N.md` y rellénala. **Cada tarea** lleva:
   requisitos (IDs), comando de verificación exacto, resultado esperado concreto y prueba negativa.
4. Incluye riesgos nuevos, estimación y decisiones que necesita el usuario.
5. Commit del plan y **STOP**: muestra el plan al usuario y espera aprobación (puerta P0).
   No implementes nada antes de la aprobación.

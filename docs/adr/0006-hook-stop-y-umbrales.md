# 0006 — Hook Stop con protección contra bucles y umbrales de calidad

- Estado: aceptado
- Fecha: 2026-11-08
- Decisores: usuario, Claude Code (discrepancia D2)

## Contexto
El MEGAPROMPT pide que `make check` pase para terminar. Un bloqueo incondicional podría impedir
informar de un fallo real o entrar en bucle. Además hay que fijar umbrales de cobertura y mutación
(REQ-NFR-018) para el código crítico.

## Opciones consideradas
1. Stop que bloquea siempre que `make check` falle: riesgo de bucle; incentiva «arreglar» tests.
2. **Stop que devuelve el control una vez** (exit 2) pidiendo corregir **o informar**, y no vuelve a
   bloquear si `stop_hook_active` es true (documentación oficial de hooks, consultada 2026-11-08).
3. Sin hook Stop: depende solo de la disciplina.

## Decisión
- Opción 2 (`scripts/hooks/stop_check.sh`), con `make check` < 60 s (medido: 11 s).
- Umbrales (en `pyproject.toml [tool.atalaya]`): cobertura de **ramas ≥ 90 %** en el código crítico
  (guardarraíles, trazabilidad, evidencias, informe de mutación); **mutación ≥ 80 %** en el código
  crítico (`mutation_critical`), con los supervivientes analizados y los equivalentes justificados.
  La evidencia de mutación lleva el SHA-256 del fuente y caduca si el código cambia.
- Se ampliarán a fusión, seguimiento, predicción y control de acceso en sus fases.

## Consecuencias
- Cambiar un umbral exige un ADR nuevo (prohibido rebajarlo en silencio).
- Resultado en la FASE 0: ramas 92 %, mutación de guardrails 92,4 %.

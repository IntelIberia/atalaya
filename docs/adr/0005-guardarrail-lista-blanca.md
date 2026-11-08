# 0005 — Guardarraíl de términos ofensivos con lista blanca defensiva explícita

- Estado: aceptado
- Fecha: 2026-11-08
- Decisores: usuario, Claude Code (discrepancia D1)

## Contexto
El guardarraíl de commit debe bloquear términos de capacidad ofensiva en código (REQ-SEC-001), pero
Atalaya **detecta** Remote ID falsificado (REQ-FUN-031), cuyo vocabulario se solapa.

## Opciones consideradas
1. Bloquear todos los términos sin excepción: impide nombrar indicadores de detección.
2. Heurística de contexto (negaciones cercanas): demostrado frágil en la FASE -1 (hallazgo 18).
3. **Lista blanca de identificadores exactos** en un fichero versionado y revisado.

## Decisión
Opción 3. `scripts/guardrails_allowlist.txt` contiene identificadores completos (p. ej.
`spoof_indicator`); cualquier otro identificador que contenga un término sensible se bloquea (test
G-04 con `spoof_remote_id`). Patrones y tests escritos por fragmentos para que el guardarraíl se
analice a sí mismo. En documentos, las menciones requieren revisión humana línea a línea
(`scripts/legal_allowlist.txt`, hash por línea). En `.claude/settings.json` las herramientas de TX
solo pueden aparecer en `permissions.deny`.

## Consecuencias
- Añadir un identificador exige justificación en el PR y revisión de `legal-guardrail-reviewer`.
- Fallo cerrado: cualquier error interno del guardarraíl bloquea.

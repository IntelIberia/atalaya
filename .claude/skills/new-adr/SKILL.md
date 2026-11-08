---
description: "Crea un Architecture Decision Record (MADR) en docs/adr/ para cualquier cambio de requisito, umbral, arquitectura o dependencia estructural."
---
# Nuevo ADR: $ARGUMENTS

1. Número siguiente: `ls docs/adr/` (formato `NNNN-titulo-en-kebab.md`).
2. Usa esta estructura (MADR) y no omitas ninguna sección:
   - `# NNNN — Título`
   - `- Estado: propuesto | aceptado | sustituido por NNNN` · `- Fecha:` · `- Decisores:`
   - `## Contexto` (problema, fuerzas, requisitos afectados con IDs)
   - `## Opciones consideradas` (al menos dos, con pros y contras)
   - `## Decisión`
   - `## Consecuencias` (positivas, negativas, riesgos, qué se verifica y cómo)
3. Toda cifra o hecho externo con fuente o marcado NO VERIFICADO.
4. Si cambia un requisito o umbral: actualiza `REQUIREMENTS.md` y el plan, y enlaza el ADR.
5. Un ADR que afecte a restricciones legales o guardarraíles requiere revisión del subagente
   `legal-guardrail-reviewer` y aprobación del usuario.

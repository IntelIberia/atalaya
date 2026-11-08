---
description: "Cierra una fase de Atalaya (puertas P2-P5, revisiones independientes, paquete de evidencias y CIERRE.md) y se detiene en el STOP de cierre. Úsala cuando todas las tareas del plan estén en OK."
---
# Cerrar la FASE $ARGUMENTS

1. Comprueba que todas las tareas de `docs/evidence/FASE-N/registro-tareas.md` están en OK.
2. **P2:** `make check` y las verificaciones propias de la fase; `make trace` sin huecos MUST.
3. **P3:** `make regress` (todas las fases cerradas siguen en verde).
4. **P4:** `scripts/verify_clean_clone.sh`.
5. **Mutación** del código crítico tocado en la fase (`make mutation`); justifica los supervivientes.
6. **P5:** lanza en paralelo los subagentes `independent-reviewer`, `test-auditor`, `security-reviewer`,
   `legal-guardrail-reviewer`, `privacy-reviewer` (y `ml-eval-reviewer` o `sapient-conformance` si
   aplican), sin contexto de la implementación. Corrige o justifica por escrito cada hallazgo en
   `docs/evidence/FASE-N/revisiones.md`.
7. Actualiza `docs/RIESGOS.md`, `docs/tech-debt.md`, `docs/threat-model/`, `docs/dpia/`, `docs/ens/`.
8. Rellena `docs/evidence/FASE-N/CIERRE.md` con la plantilla del Anexo A del MEGAPROMPT.
9. `make evidence FASE=N` (al final: el manifiesto cubre todo el paquete) y commit.
10. **STOP de cierre:** informe al usuario en el formato de `<proceso_y_control>`. La etiqueta
    `fase-N-cerrada` solo se crea tras su aprobación (puerta P6).

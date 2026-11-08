# Cierre FASE -1 — Especificación y requisitos

Fecha: 2026-11-08 · Commit de los entregables: `4039896` · Etiqueta propuesta: `fase--1-cerrada` (**no creada**: espera la aprobación del usuario)

## 1. Objetivo y alcance cumplido
Saber qué hay que construir y cómo se demostrará antes de escribir código. Entregables:
- [Entrevista](../../requirements/ENTREVISTA-FASE--1.md): 4 bloques más la corrección del usuario sobre el alojamiento.
- [SPEC](../../SPEC.md): visión, situación de partida, hito v1 a 0 €, fuera de alcance, 8 roles, 24 casos de uso, estimación por fases, bloqueos, discrepancias con el MEGAPROMPT y afirmaciones por verificar.
- [Requisitos](../../requirements/REQUIREMENTS.md): 130 (FUN 62, NFR 21, LEG 17, SEC 19, PRIV 11), de los que 112 son MUST, más la tabla de correspondencia con el MEGAPROMPT.
- [Plan maestro de pruebas](../../PLAN-MAESTRO-DE-PRUEBAS.md), con 15 pruebas de guardarraíl y 10 de inyección de fallos.
- [Riesgos](../../RIESGOS.md): 27, incluidos los 9 del Anexo C.

## 2. Evidencia
| Comando | Resultado | Fichero |
|---|---|---|
| `python3 -I scripts/check_spec.py` | OK, exit 0 | [check_spec.txt](check_spec.txt) |
| `python3 -I -m unittest discover -s scripts -p 'test_check_spec.py' -v` | 21/21 OK | [test_check_spec.txt](test_check_spec.txt) |
| Clon limpio + check + tests | exit 0 / exit 0 | [clon_limpio.txt](clon_limpio.txt) |

Hashes en [MANIFEST.sha256](MANIFEST.sha256).

## 3. Registro de tareas
6 tareas, todas en OK, con su prueba negativa cuando aplica: [registro-tareas.md](registro-tareas.md).

## 4. Puertas
- P0: no aplica en la FASE -1 (la especificación es el plan).
- P1: OK (registro de tareas).
- P2: OK (`check_spec.py`). Todavía no existen `make check` ni la trazabilidad completa: llegan en la FASE 0.
- P3: no aplica (no hay fases anteriores).
- P4: OK de forma parcial: clon limpio con el check y los tests. `make bootstrap` no existe todavía.
- P5: revisor independiente, con 20 hallazgos resueltos. **No** se han ejecutado los subagentes especializados (seguridad, legal, privacidad) como agentes separados porque aún no existen (FASE 0); la revisión general cubrió el cumplimiento legal.

## 5. Revisión independiente
Ver [revision-independiente.md](revision-independiente.md).

## 6. Métricas frente a objetivo
Verificación de la FASE -1 (MEGAPROMPT): cada caso de uso tiene requisitos (24/24); cada MUST tiene método de verificación (112/112); nada contradice las restricciones legales (34 menciones sensibles, todas revisadas). Calculado por `check_spec.py`; los 21 tests comprueban que el verificador detecta cada tipo de fallo.

## 7. Guardarraíles e inyección de fallos
Aún no hay guardarraíles de código (FASE 0). El verificador legal de documentos se prueba con 10 tests negativos.

## 8. Lo que NO se ha hecho o NO VERIFICADO
- Ninguna afirmación externa de la SPEC §11 se ha verificado (leyes, licencias, cuotas, artículos científicos, límites de GitHub).
- La estimación en semanas es un juicio, no una medida.
- La lista blanca legal la revisó Claude Code; falta la revisión del usuario.
- No se ha hecho `git push` al remoto.

## 9. Cambios respecto al MEGAPROMPT
Discrepancias D1-D12 de la SPEC §10, que se registrarán como ADR en la FASE 0. Las principales: presupuesto de 0 €, solo local, hito v1 redefinido, guardarraíl con lista blanca defensiva, Stop hook con protección contra bucles y sin CodeQL en el repo privado.

## 10. Riesgos
27 riesgos. Los de severidad 20 son R-01, R-02, R-05, R-10, R-11 y R-12.

## 11. Deuda técnica
`check_spec.py` vive en `scripts/` sin `pyproject`, linters ni CI: se integrará en `make check` y en la CI en la FASE 0.

## 12. Decisiones que necesita el usuario
Ver el informe del STOP.

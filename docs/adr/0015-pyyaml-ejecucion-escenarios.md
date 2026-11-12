# 0015 — PyYAML como dependencia de ejecución para los escenarios del simulador

- Estado: aceptado
- Fecha: 2026-11-11
- Decisores: Claude (implementación de T1.9) bajo la delegación del usuario del 2026-11-11
  («permiso absoluto» para las directrices necesarias, registrada en `DECISIONES-USUARIO.md`)

## Contexto
T1.9 exige escenarios en YAML (`sim/scenarios/*.yaml`, MEGAPROMPT FASE 1 y REQ-FUN-005) que el
simulador carga en ejecución. PyYAML ya estaba fijado en `uv.lock` (6.0.3), pero solo en el grupo de
desarrollo, porque hasta ahora únicamente lo usaban los tests. El ADR 0009 no incluye la familia
`pyyaml` entre las dependencias de ejecución.

## Opciones consideradas
1. Escribir los escenarios en JSON: evita la dependencia, pero contradice el entregable del
   MEGAPROMPT (`prision_ceuta.yaml`…) y pierde los comentarios de procedencia.
2. Escribir un analizador YAML propio: código crítico nuevo sin necesidad.
3. Mover PyYAML (MIT, versión ya bloqueada y con wheel instalada en el Mac Intel) a ejecución y usar
   solo `yaml.safe_load`.

## Decisión
Opción 3. `pyyaml==6.0.3` pasa de desarrollo a ejecución en `pyproject.toml` y `uv.lock`. Solo se
permite `yaml.safe_load` (nunca `yaml.load` con cargadores completos). `types-pyyaml` sigue en
desarrollo. Coste 0 €.

## Consecuencias
- Positivas: los escenarios siguen siendo YAML con comentarios y se validan contra JSON Schema.
- Negativas: una dependencia de ejecución más (10 en total) que vigilar en cada actualización.
- Verificación: `uv run python -m scripts.license_check` informa 10 dependencias de ejecución sin
  copyleft fuerte; `uv sync --frozen` coherente con el lock; `tests/sim/test_scenarios.py` en verde.

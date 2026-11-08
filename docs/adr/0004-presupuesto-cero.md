# 0004 — Presupuesto obligatorio 0 €, solo local y alcance de la v1

- Estado: aceptado
- Fecha: 2026-11-08
- Decisores: usuario (entrevista FASE -1, bloques 3 y 4)

## Contexto
El MEGAPROMPT preveía un kit piloto (~4.400 €) y 200-700 $ de GPU. El usuario fija 0 € obligatorios,
alojamiento solo local, sin drones ni contactos (SPEC §2; discrepancias D5 y D8). REQ-NFR-016.

## Opciones consideradas
1. Mantener el plan original: imposible sin presupuesto.
2. **Hito v1 demostrable a 0 €** (simulación + Android del usuario + datasets públicos) con puntos de
   decisión de gasto opcionales.
3. Esperar financiación antes de construir: retrasa todo sin reducir riesgo técnico.

## Decisión
Opción 2: presupuesto obligatorio **0 €**. Ninguna tarea MUST depende de un servicio de pago. Todo
corre en Docker Compose en el Mac; nada se publica en Internet en la v1 (el radar se construye en
local). CI en runners gratuitos de GitHub (`ubuntu-24.04`). Cualquier gasto (hardware, GPU, APIs,
alojamiento, TSA cualificada) requiere un ADR en uno de los puntos de decisión de SPEC §8.

## Consecuencias
- Requisitos con bloqueo **B** documentados (SPEC §9) en lugar de afirmarse.
- La demostración con altavoz se etiqueta siempre «reproducción en sala, no vuelo real» (R-21).
- Verificación: `tests/test_documentos.py::test_presupuesto_cero_y_runners_gratuitos`.

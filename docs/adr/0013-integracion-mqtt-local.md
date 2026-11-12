# 0013 — Integración MQTT local para la FASE 1

- Estado: aceptado
- Fecha: 2026-11-10
- Decisores: usuario (aprobación P0), Codex (verificación e implementación)

## Contexto
REQ-FUN-001 requiere un broker para comprobar la publicación y la ingesta. GitHub Actions ya ejecuta
las verificaciones ligeras; añadir un servicio Mosquitto incrementaría el uso de minutos y recursos.
La restricción del proyecto es coste de 0 €.

## Opciones consideradas
1. Añadir broker de servicio a CI: mejora repetibilidad remota, con consumo adicional sujeto a cuotas.
2. Ejecutar la integración localmente y guardar JUnit y evidencia en el paquete de fase.

## Decisión
Para FASE 1, MQTT se verifica localmente con el Compose del proyecto. No se añade un servicio ni
trabajo de integración MQTT a GitHub Actions. La evidencia local queda trazada y su ausencia bloquea
el cierre de la fase. Reabrir la decisión exige revisar cuotas y presupuesto mediante otro ADR.

## Consecuencias
- Positivas: no se asume coste ni cuota remota no verificados.
- Negativas: la integración MQTT no corre automáticamente en cada push.
- Verificación: `make up && make integration` genera JUnit independiente que `make trace` requiere.

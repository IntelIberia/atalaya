# 0001 — Arquitectura: monolito modular hexagonal orientado a eventos

- Estado: aceptado
- Fecha: 2026-11-08
- Decisores: usuario (responsable), Claude Code (ingeniero principal)

## Contexto
Atalaya integra sensores heterogéneos (acústicos, Remote ID, RF pasiva, ADS-B, cámaras, personas),
fusión, seguimiento, predicción y alertas, con un equipo de una persona más IA, presupuesto 0 € y
ejecución solo local en un Mac Intel de 8 GB (SPEC §2). Requisitos: REQ-NFR-001 (p95 < 2 s),
REQ-FUN-053 (modo degradado local), REQ-NFR-015 (todo en el Mac).

## Opciones consideradas
1. **Microservicios desde el inicio**: aislamiento fuerte; coste operativo y de RAM alto para una persona y 8 GB.
2. **Monolito modular hexagonal (puertos y adaptadores) orientado a eventos**: módulos con fronteras
   explícitas (`services/*`), un proceso o pocos; extraíble a servicios si el perfilado lo justifica.
3. **Monolito sin fronteras**: rápido al principio; acoplamiento que impide extraer piezas y probarlas.

## Decisión
Opción 2. Los nodos emiten **eventos de detección** (Protobuf, nunca datos en bruto) por MQTT 5; el
núcleo usa NATS JetStream; cada módulo de `services/` expone puertos y sus adaptadores (MQTT, NATS,
PostgreSQL/PostGIS/TimescaleDB, Redis, SAPIENT) son intercambiables. Pasar a microservicios exige
ADR con perfilado.

## Consecuencias
- Positivas: bajo consumo, tests de contrato por puerto, despliegue local simple (Docker Compose).
- Negativas: disciplina de fronteras manual; un fallo de proceso afecta a varios módulos.
- Verificación: tests de contrato por puerto (FASE 1+); latencia p95 medida (FASE 10).

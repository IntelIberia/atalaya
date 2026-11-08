# 0003 — Stack tecnológico y versiones fijadas

- Estado: aceptado (dashboard aplazado a la FASE 10)
- Fecha: 2026-11-08
- Decisores: usuario, Claude Code

## Contexto
MEGAPROMPT `<arquitectura_y_stack>`; recursos: Mac Intel x86_64, 8 GB RAM, ~30 GB libres; 0 €.

## Opciones consideradas
- PostgreSQL con extensiones: (a) `postgis/postgis` alpine (188 MB, sin TimescaleDB); (b)
  `timescale/timescaledb` (sin PostGIS); (c) `timescale/timescaledb-ha` (PostGIS + TimescaleDB,
  ~980 MB comprimida). Medidas consultadas en Docker Hub el 2026-11-08.
- Dashboard: React o SvelteKit — se decide en la FASE 10 con un prototipo.

## Decisión
- Python 3.12 con uv 0.11.7; ruff, `mypy --strict`, pytest 8 (<9 por mutmut, ver tech-debt), hypothesis, mutmut.
- Mensajería: MQTT 5 con Mosquitto 2.0.22; núcleo NATS 2.15.1 con JetStream; Redis 7.4.11.
- Datos: `timescale/timescaledb-ha:pg16.15-ts2.30.2` (opción c: única imagen oficial con ambas
  extensiones; cabe en disco). `pg_hba` endurecido sin `trust` (hallazgo T0.10).
- Protobuf con buf 1.75.0 (FASE 1). Kotlin/Compose (FASE 3), ESP-IDF (FASE 6), TypeScript (FASE 10).
- Imágenes y acciones de CI fijadas por versión exacta o SHA.

## Consecuencias
- La imagen de PostgreSQL ocupa ~3 GB en disco; aceptable con ~30 GB libres (R-28).
- Actualizar una versión fijada exige PR con justificación (licencia, mantenimiento, seguridad).

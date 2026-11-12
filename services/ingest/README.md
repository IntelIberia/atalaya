# services/ingest

Ingesta mínima de detecciones (T1.16, FASE 1), paquete `atalaya_ingest`. **Sin red todavía**: la
conexión MQTT real y la autorización llegan en T1.7b.

- `Ingest.handle(topic, payload)`: topic `atalaya/v1/<site>/<node>/{detection,node_status}`,
  carga `bytes` de ≤ 64 KiB, `Envelope` decodificable, tipo de carga, sitio y nodo coherentes con el
  topic y con el contenido, `validate()` sin errores y deduplicación por `detection_id` (ventana
  FIFO acotada). Entrega al `DetectionSink` la detección redactada a `OPERATOR`.
- Una entrada inválida nunca lanza: se cuenta en `stats.rejected_by_reason` (`rejected_total`) y el
  log solo lleva el motivo, nunca el topic, el payload ni identificadores.
- `DetectionSink` (puerto) e `InMemoryDetectionSink` (adaptador en memoria).
- Tests: `tests/ingest/test_ingest.py`.

"""Ingesta mínima de Atalaya (T1.16): decodificación, validación, deduplicación y puerto."""

from atalaya_ingest.ingest import (
    MAX_PAYLOAD_BYTES,
    DetectionSink,
    Ingest,
    IngestStats,
    InMemoryDetectionSink,
    Outcome,
)

__all__ = [
    "MAX_PAYLOAD_BYTES",
    "DetectionSink",
    "InMemoryDetectionSink",
    "Ingest",
    "IngestStats",
    "Outcome",
]

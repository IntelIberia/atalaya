"""Ingesta mínima de detecciones (T1.16), sin red.

`Ingest.handle(topic, payload)` recibe un mensaje MQTT ya entregado por el transporte (que llega en
T1.7b) y, en este orden: comprueba el topic `atalaya/v1/<site>/<node>/{detection,node_status}`, el
tipo y el tamaño de la carga, la decodifica como `Envelope`, exige que el tipo de carga, el sitio y
el nodo coincidan con el topic y con el contenido, la valida (`atalaya_contracts.validate`),
descarta duplicados por `detection_id` y entrega a un `DetectionSink` la detección redactada a
`OPERATOR` (un campo `FCSE_ONLY` nunca entra por el canal de operador).

Una entrada inválida nunca tumba la ingesta: se cuenta en `rejected_total` por motivo. Los logs solo
llevan el motivo; nunca el topic, el payload ni identificadores.
"""

from __future__ import annotations

import logging
import re
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Final, Protocol, cast, runtime_checkable

from atalaya.v1 import options_pb2
from atalaya.v1.detection_pb2 import Detection
from atalaya.v1.envelope_pb2 import Envelope
from atalaya_contracts.redact import redact
from atalaya_contracts.validate import validate
from google.protobuf.message import DecodeError

__all__ = [
    "MAX_PAYLOAD_BYTES",
    "DetectionSink",
    "InMemoryDetectionSink",
    "Ingest",
    "IngestStats",
    "Outcome",
]

_LOG = logging.getLogger("atalaya.ingest")

MAX_PAYLOAD_BYTES: Final = 64 * 1024
DEFAULT_TRACKED_IDS: Final = 100_000
_SEGMENT: Final = r"[a-z0-9][a-z0-9-]{0,62}"
_TOPIC: Final = re.compile(rf"atalaya/v1/({_SEGMENT})/({_SEGMENT})/(detection|node_status)")


class Outcome(Enum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    NODE_STATUS = "node_status"
    REJECTED = "rejected"


@runtime_checkable
class DetectionSink(Protocol):
    """Puerto de salida de la ingesta (almacenamiento o fusión en fases posteriores)."""

    def deliver(self, detection: Detection) -> None: ...


@dataclass
class InMemoryDetectionSink:
    """Adaptador en memoria del puerto `DetectionSink` (tests y simulación)."""

    detections: list[Detection] = field(default_factory=list)

    def deliver(self, detection: Detection) -> None:
        self.detections.append(detection)


@dataclass
class IngestStats:
    received_total: int = 0
    accepted_total: int = 0
    duplicate_total: int = 0
    node_status_total: int = 0
    rejected_by_reason: Counter[str] = field(default_factory=Counter)

    @property
    def rejected_total(self) -> int:
        return sum(self.rejected_by_reason.values())


class _Rejected(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class Ingest:
    """Valida, deduplica y entrega al `DetectionSink`.

    La deduplicación recuerda los últimos `max_tracked_ids` `detection_id` aceptados (FIFO):
    un duplicado que llegue después de salir de la ventana se entregaría de nuevo.
    """

    def __init__(self, sink: DetectionSink, *, max_tracked_ids: int = DEFAULT_TRACKED_IDS) -> None:
        if not isinstance(sink, DetectionSink):
            raise TypeError("Ingest requiere un DetectionSink")
        if isinstance(max_tracked_ids, bool) or not isinstance(max_tracked_ids, int):
            raise ValueError("max_tracked_ids debe ser un entero positivo")
        if max_tracked_ids < 1:
            raise ValueError("max_tracked_ids debe ser un entero positivo")
        self._sink = sink
        self._max_tracked = max_tracked_ids
        self._seen: OrderedDict[str, None] = OrderedDict()
        self.stats = IngestStats()

    def handle(self, topic: str, payload: bytes) -> Outcome:
        """Procesa un mensaje; nunca lanza por una entrada inválida."""
        self.stats.received_total += 1
        try:
            return self._handle(topic, payload)
        except _Rejected as exc:
            self.stats.rejected_by_reason[exc.reason] += 1
            _LOG.warning("ingest: mensaje rechazado (%s)", exc.reason)
            return Outcome.REJECTED

    def _handle(self, topic: str, payload: bytes) -> Outcome:
        match = _TOPIC.fullmatch(topic) if isinstance(topic, str) else None
        if match is None:
            raise _Rejected("topic")
        site, node, kind = match.groups()
        if not isinstance(payload, bytes):
            raise _Rejected("decode")
        if len(payload) > MAX_PAYLOAD_BYTES:
            raise _Rejected("oversize")
        envelope = Envelope()
        try:
            envelope.ParseFromString(payload)
        except (DecodeError, RecursionError, ValueError):
            raise _Rejected("decode") from None
        actual = envelope.WhichOneof("payload")
        if actual not in ("detection", "node_status"):
            raise _Rejected("payload_kind")
        if actual != kind:
            raise _Rejected("kind_mismatch")
        if envelope.site_id != site or envelope.node_id != node:
            raise _Rejected("topic_mismatch")
        inner = getattr(envelope, actual)
        if inner.site_id != site or inner.node_id != node:
            raise _Rejected("inner_mismatch")
        if validate(envelope):
            raise _Rejected("invalid")
        if actual == "node_status":
            self.stats.node_status_total += 1
            return Outcome.NODE_STATUS
        return self._deliver(envelope)

    def _deliver(self, envelope: Envelope) -> Outcome:
        detection_id = envelope.detection.detection_id
        if detection_id in self._seen:
            self.stats.duplicate_total += 1
            return Outcome.DUPLICATE
        filtered = cast(Envelope, redact(envelope, options_pb2.OPERATOR))
        try:
            self._sink.deliver(filtered.detection)
        except Exception:
            # Sin marcar como vista: una reentrega posterior (QoS 1) puede completarla.
            raise _Rejected("sink") from None
        self._seen[detection_id] = None
        if len(self._seen) > self._max_tracked:
            self._seen.popitem(last=False)
        self.stats.accepted_total += 1
        return Outcome.ACCEPTED

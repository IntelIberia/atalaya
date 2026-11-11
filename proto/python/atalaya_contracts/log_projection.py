"""Proyección JSON segura para logs, separada de adaptadores de servicios.

El proyector exige una decisión de acceso del caller, pero no implementa
autenticación ni wiring de servicios: `sim/` y `services/ingest/` aún no tienen
código ejecutable.
"""

from __future__ import annotations

import json
import logging
import math
from typing import Any

from atalaya.v1 import (
    alert_pb2,
    common_pb2,
    coverage_status_pb2,
    detection_pb2,
    envelope_pb2,
    evidence_pb2,
    node_status_pb2,
    options_pb2,
    prediction_pb2,
    sighting_pb2,
    signature_class_pb2,
    track_pb2,
)
from google.protobuf import timestamp_pb2
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message

from atalaya_contracts.redact import redact

_LOG_CLEARANCES = frozenset({options_pb2.PUBLIC, options_pb2.OPERATOR})
_EXCLUDED_MESSAGES = frozenset({"atalaya.v1.Evidence", "atalaya.sim.v1.GroundTruth"})
_SAFE_ROOTS = frozenset(
    {
        "atalaya.v1.Alert",
        "atalaya.v1.CoverageStatus",
        "atalaya.v1.Detection",
        "atalaya.v1.Envelope",
        "atalaya.v1.NodeStatus",
        "atalaya.v1.Prediction",
        "atalaya.v1.Sighting",
        "atalaya.v1.SignatureClass",
        "atalaya.v1.Track",
    }
)
_SAFE_FIELDS = {
    "atalaya.v1.Alert": frozenset({"level", "confidence", "created_at"}),
    "atalaya.v1.CoverageStatus": frozenset({"estimated_probability", "assessed_at"}),
    "atalaya.v1.Detection": frozenset(
        {"observed_at", "sensor_type", "detection_confidence", "time_quality"}
    ),
    "atalaya.v1.Envelope": frozenset({"sequence", "emitted_at"}),
    "atalaya.v1.NodeStatus": frozenset({"observed_at", "health"}),
    "atalaya.v1.Prediction": frozenset({"generated_at"}),
    "atalaya.v1.Sighting": frozenset({"observed_at"}),
    "atalaya.v1.SignatureClass": frozenset({"code", "synthetic"}),
    "atalaya.v1.Track": frozenset({"updated_at", "time_quality"}),
    "atalaya.v1.TimeQuality": frozenset({"pps_valid", "clock_offset_ms", "uncertainty_ms"}),
}
_SAFE_COUNTS = {
    "atalaya.v1.CoverageStatus": frozenset({"boundary"}),
    "atalaya.v1.Detection": frozenset({"class_scores"}),
    "atalaya.v1.Prediction": frozenset({"horizons", "destination_probabilities"}),
    "atalaya.v1.Sighting": frozenset({"evidence_ids"}),
    "atalaya.v1.Track": frozenset({"class_probabilities"}),
}
_TRUSTED_DESCRIPTORS = (
    alert_pb2.Alert.DESCRIPTOR,
    common_pb2.TimeQuality.DESCRIPTOR,
    coverage_status_pb2.CoverageStatus.DESCRIPTOR,
    detection_pb2.Detection.DESCRIPTOR,
    envelope_pb2.Envelope.DESCRIPTOR,
    evidence_pb2.Evidence.DESCRIPTOR,
    node_status_pb2.NodeStatus.DESCRIPTOR,
    prediction_pb2.Prediction.DESCRIPTOR,
    sighting_pb2.Sighting.DESCRIPTOR,
    signature_class_pb2.SignatureClass.DESCRIPTOR,
    track_pb2.Track.DESCRIPTOR,
    timestamp_pb2.Timestamp.DESCRIPTOR,
)
_OMIT = object()


def _is_trusted_descriptor(descriptor: Any) -> bool:
    return any(descriptor is trusted for trusted in _TRUSTED_DESCRIPTORS)


def _project_message(message: Message) -> tuple[dict[str, Any], dict[str, int]]:
    if not _is_trusted_descriptor(message.DESCRIPTOR):
        raise ValueError(f"{message.DESCRIPTOR.full_name}: descriptor no permitido en logs")
    fields: dict[str, Any] = {}
    counts: dict[str, int] = {}
    message_name = message.DESCRIPTOR.full_name
    allowed_fields = _SAFE_FIELDS.get(message_name, frozenset())
    allowed_counts = _SAFE_COUNTS.get(message_name, frozenset())
    for field in message.DESCRIPTOR.fields:
        value = getattr(message, field.name)
        if field.name in allowed_counts:
            counts[f"{field.name}_count"] = len(value)
            continue
        if field.name not in allowed_fields:
            continue

        if field.has_presence and not message.HasField(field.name):
            continue
        projected = _project_value(field, value)
        if projected is not _OMIT:
            fields[field.name] = projected
    if message_name == "atalaya.v1.Envelope":
        payload_type = message.WhichOneof("payload")
        if payload_type is not None and payload_type != "evidence":
            fields["payload_type"] = payload_type
    return fields, counts


def _project_value(field: Any, value: Any) -> Any:
    if field.message_type is not None:
        if field.message_type is timestamp_pb2.Timestamp.DESCRIPTOR:
            return {"seconds": int(value.seconds), "nanos": int(value.nanos)}
        if not _is_trusted_descriptor(field.message_type):
            raise ValueError(f"{field.full_name}: descriptor anidado no permitido en logs")
        projected, _counts = _project_message(value)
        return projected if projected else _OMIT
    if field.type == FieldDescriptor.TYPE_ENUM:
        if field.enum_type is None:
            raise ValueError(f"{field.full_name}: descriptor de enum ausente")
        enum_value = field.enum_type.values_by_number.get(int(value))
        if enum_value is None:
            raise ValueError(f"{field.full_name}: valor de enum desconocido")
        return enum_value.name
    if field.type == FieldDescriptor.TYPE_BYTES:
        return _OMIT
    if field.type == FieldDescriptor.TYPE_STRING:
        return _OMIT
    if field.type in {
        FieldDescriptor.TYPE_DOUBLE,
        FieldDescriptor.TYPE_FLOAT,
    } and not math.isfinite(float(value)):
        raise ValueError(f"{field.full_name}: valor no finito, no se puede proyectar a JSON")
    if not field.has_presence and value == field.default_value:
        return _OMIT
    return value


def project_log_record(
    message: Message,
    *,
    clearance: int = options_pb2.OPERATOR,
    authorized: bool = False,
) -> dict[str, Any]:
    """Proyecta un mensaje en el esquema JSON permitido para logs.

    Solo admite `PUBLIC` y `OPERATOR`; `FCSE_ONLY` está bloqueado para logs.
    El caller debe pasar `authorized=True` tras su control de acceso; el
    paquete no inventa identidad ni sustituye la autorización de un servicio.
    """
    if authorized is not True:
        raise PermissionError("acceso al log no autorizado")
    if (
        isinstance(clearance, bool)
        or not isinstance(clearance, int)
        or clearance not in _LOG_CLEARANCES
    ):
        raise ValueError(f"nivel de log inválido ({clearance!r})")
    if not isinstance(message, Message):
        raise TypeError("project_log_record() requiere un mensaje Protobuf")
    if message.DESCRIPTOR.full_name in _EXCLUDED_MESSAGES:
        raise ValueError(f"{message.DESCRIPTOR.full_name}: mensaje excluido de logs")
    if message.DESCRIPTOR.full_name not in _SAFE_ROOTS:
        raise ValueError(f"{message.DESCRIPTOR.full_name}: schema no permitido en logs")
    if not _is_trusted_descriptor(message.DESCRIPTOR):
        raise ValueError(f"{message.DESCRIPTOR.full_name}: descriptor no oficial para logs")

    filtered = redact(message, clearance)
    fields, counts = _project_message(filtered)
    return {"schema": filtered.DESCRIPTOR.full_name, "fields": fields, "counts": counts}


def log_contract_event(
    logger: logging.Logger,
    message: Message,
    *,
    clearance: int = options_pb2.OPERATOR,
    authorized: bool = False,
) -> None:
    """Emite JSON filtrado; errores de acceso/proyección no escriben nada.

    Es un sink reutilizable para los futuros servicios. Su test local no afirma
    integración e2e con `sim/` ni `services/ingest/`; ese wiring queda para T1.16.
    """
    if not isinstance(logger, logging.Logger):
        raise TypeError("log_contract_event() requiere logging.Logger")
    record = project_log_record(message, clearance=clearance, authorized=authorized)
    payload = json.dumps(
        record,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    logger.info("%s", payload)

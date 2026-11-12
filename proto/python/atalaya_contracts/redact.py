"""Redacción recursiva de mensajes Protobuf según su sensibilidad efectiva."""

from __future__ import annotations

from typing import Any, cast

from atalaya.sim.v1 import ground_truth_pb2
from atalaya.v1 import (
    alert_pb2,
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
from google.protobuf.message import Message

_SENSITIVITY = cast(Any, options_pb2.sensitivity)
_LEVEL_RANK: dict[int, int] = {
    options_pb2.PUBLIC: 0,
    options_pb2.OPERATOR: 1,
    options_pb2.FCSE_ONLY: 2,
}
_TRUSTED_ROOTS = (
    alert_pb2.Alert.DESCRIPTOR,
    coverage_status_pb2.CoverageStatus.DESCRIPTOR,
    detection_pb2.Detection.DESCRIPTOR,
    envelope_pb2.Envelope.DESCRIPTOR,
    evidence_pb2.Evidence.DESCRIPTOR,
    ground_truth_pb2.GroundTruth.DESCRIPTOR,
    node_status_pb2.NodeStatus.DESCRIPTOR,
    prediction_pb2.Prediction.DESCRIPTOR,
    sighting_pb2.Sighting.DESCRIPTOR,
    signature_class_pb2.SignatureClass.DESCRIPTOR,
    track_pb2.Track.DESCRIPTOR,
)


def _is_official_timestamp(descriptor: Any) -> bool:
    if descriptor.full_name != "google.protobuf.Timestamp":
        return False
    if descriptor is not timestamp_pb2.Timestamp.DESCRIPTOR:
        raise ValueError("google.protobuf.Timestamp: descriptor homónimo no oficial")
    return True


def _declared_level(field: Any, path: str) -> int:
    options = field.GetOptions()
    if not options.HasExtension(_SENSITIVITY):
        raise ValueError(f"{path}: falta la sensibilidad declarada")
    level = int(options.Extensions[_SENSITIVITY])
    if level not in _LEVEL_RANK:
        raise ValueError(f"{path}: nivel de sensibilidad inválido ({level})")
    return level


def _effective_level(inherited: int, declared: int) -> int:
    try:
        inherited_rank = _LEVEL_RANK[inherited]
        declared_rank = _LEVEL_RANK[declared]
    except KeyError as exc:
        raise ValueError(f"nivel de sensibilidad inválido ({exc.args[0]})") from exc
    return inherited if inherited_rank >= declared_rank else declared


def _validate_descriptor(
    descriptor: Any,
    path: str,
    seen: set[str],
    *,
    allow_opaque: bool = True,
) -> None:
    if allow_opaque and _is_official_timestamp(descriptor):
        return
    if getattr(descriptor, "extension_ranges", ()):
        raise ValueError(f"{path}: rangos de extensión no soportados")
    if descriptor.full_name in seen:
        return
    seen.add(descriptor.full_name)

    for field in descriptor.fields:
        field_path = f"{path}.{field.name}"
        _declared_level(field, field_path)
        child = field.message_type
        if child is None:
            continue
        if _is_official_timestamp(child):
            continue
        if child.GetOptions().map_entry:
            map_value = child.fields_by_name["value"]
            if map_value.message_type is not None:
                _validate_descriptor(
                    map_value.message_type,
                    f"{field_path}.value",
                    seen,
                )
        else:
            _validate_descriptor(child, field_path, seen)


def _redact_message(message: Message, inherited_level: int, clearance: int) -> None:
    for field in message.DESCRIPTOR.fields:
        path = f"{message.DESCRIPTOR.full_name}.{field.name}"
        effective_level = _effective_level(inherited_level, _declared_level(field, path))
        if _LEVEL_RANK[effective_level] > _LEVEL_RANK[clearance]:
            message.ClearField(field.name)
            continue

        child = field.message_type
        if child is None or _is_official_timestamp(child):
            continue
        if child.GetOptions().map_entry:
            map_value = child.fields_by_name["value"].message_type
            if map_value is not None and not _is_official_timestamp(map_value):
                values = getattr(message, field.name)
                for key in list(values):
                    _redact_message(values[key], effective_level, clearance)
            continue
        if field.is_repeated:
            for nested in getattr(message, field.name):
                _redact_message(nested, effective_level, clearance)
        elif message.HasField(field.name):
            _redact_message(getattr(message, field.name), effective_level, clearance)


def redact(message: Message, clearance: int) -> Message:
    """Devuelve una copia sin campos por encima del nivel autorizado.

    Falla cerrada ante niveles o descriptores de sensibilidad inválidos y ante
    campos wire desconocidos que no se puedan clasificar.
    """
    if not isinstance(message, Message):
        raise TypeError("redact() requiere un mensaje Protobuf")
    if (
        isinstance(clearance, bool)
        or not isinstance(clearance, int)
        or clearance not in _LEVEL_RANK
    ):
        raise ValueError(f"nivel de autorización inválido ({clearance!r})")

    _validate_descriptor(
        message.DESCRIPTOR,
        message.DESCRIPTOR.full_name,
        set(),
        allow_opaque=False,
    )
    if any(field.is_extension for field, _ in message.ListFields()):
        raise ValueError(f"{message.DESCRIPTOR.full_name}: contiene extensiones sin clasificar")

    message_class = cast(Any, message.__class__)
    result = message_class()
    result.CopyFrom(message)
    known_fields = message_class()
    known_fields.CopyFrom(result)
    known_fields.DiscardUnknownFields()
    if known_fields.SerializeToString(deterministic=True) != result.SerializeToString(
        deterministic=True
    ):
        raise ValueError(f"{message.DESCRIPTOR.full_name}: contiene campos wire desconocidos")
    if not any(message.DESCRIPTOR is trusted for trusted in _TRUSTED_ROOTS):
        raise ValueError(f"{message.DESCRIPTOR.full_name}: descriptor raíz no oficial")

    _redact_message(known_fields, options_pb2.PUBLIC, clearance)
    return cast(Message, known_fields)

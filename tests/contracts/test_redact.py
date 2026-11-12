"""Pruebas de redacción recursiva y cerrada de contratos Protobuf."""

from __future__ import annotations

from hashlib import sha256
from importlib import import_module
from typing import Any, cast

import pytest
from atalaya.sim.v1 import ground_truth_pb2
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
from atalaya_contracts import redact
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory, timestamp_pb2
from google.protobuf.message import Message
from hypothesis import given, settings
from hypothesis import strategies as st

from scripts.sensitivity_table import rows as sensitivity_rows

redact_module = import_module("atalaya_contracts.redact")


_SENSITIVITY_LEVELS = {options_pb2.PUBLIC, options_pb2.OPERATOR, options_pb2.FCSE_ONLY}
_SENSITIVITY_RANK: dict[int, int] = {
    options_pb2.PUBLIC: 0,
    options_pb2.OPERATOR: 1,
    options_pb2.FCSE_ONLY: 2,
}
_FCSE_TABLE_PATHS = frozenset(
    row.path for row in sensitivity_rows() if row.effective == "FCSE_ONLY"
)


def _declared_sensitivity(field: Any, path: str) -> int:
    options = field.GetOptions()
    extension = cast(Any, options_pb2.sensitivity)
    if not options.HasExtension(extension):
        raise AssertionError(f"test fixture has an unannotated descriptor field: {path}")
    level = int(options.Extensions[extension])
    assert level in _SENSITIVITY_LEVELS, path
    return level


def _effective_sensitivity(inherited: int, declared: int) -> int:
    return inherited if _SENSITIVITY_RANK[inherited] >= _SENSITIVITY_RANK[declared] else declared


def _has_fcse_field(
    descriptor: Any,
    inherited: int = options_pb2.PUBLIC,
    active: frozenset[str] = frozenset(),
) -> bool:
    if descriptor.full_name in active or descriptor.full_name == "google.protobuf.Timestamp":
        return False
    next_active = active | {descriptor.full_name}
    for field in descriptor.fields:
        level = _effective_sensitivity(
            inherited,
            _declared_sensitivity(field, f"{descriptor.full_name}.{field.name}"),
        )
        if level == options_pb2.FCSE_ONLY:
            return True
        child = field.message_type
        if child is None:
            continue
        if child.GetOptions().map_entry:
            value_type = child.fields_by_name["value"].message_type
            if value_type is not None and _has_fcse_field(value_type, level, next_active):
                return True
        elif _has_fcse_field(child, level, next_active):
            return True
    return False


def _field_has_fcse(field: Any, inherited: int) -> bool:
    level = _effective_sensitivity(inherited, _declared_sensitivity(field, field.full_name))
    if level == options_pb2.FCSE_ONLY:
        return True
    child = field.message_type
    if child is None:
        return False
    if child.GetOptions().map_entry:
        value_type = child.fields_by_name["value"].message_type
        return value_type is not None and _has_fcse_field(value_type, level)
    return _has_fcse_field(child, level)


def _fcse_sentinel(field: Any, token: str, path: str) -> Any:
    field_type = field.type
    if field_type == descriptor_pb2.FieldDescriptorProto.TYPE_STRING:
        return f"fcse-sentinel:{token}:{path}"
    if field_type == descriptor_pb2.FieldDescriptorProto.TYPE_BYTES:
        return f"fcse-sentinel:{token}:{path}".encode()
    if field_type == descriptor_pb2.FieldDescriptorProto.TYPE_BOOL:
        return True
    if field_type == descriptor_pb2.FieldDescriptorProto.TYPE_ENUM:
        values = field.enum_type.values
        return next((value.number for value in values if value.number != 0), values[0].number)
    digest = sha256(f"{token}:{path}".encode()).digest()
    number = int.from_bytes(digest[:4], "big") or 1
    if field_type in {
        descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE,
        descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT,
    }:
        return float(number)
    return number


def _populate_fcse_fields(
    message: Message,
    inherited: int,
    path: str,
    token: str,
    sentinels: dict[str, Any],
) -> None:
    selected_oneofs: dict[str, Any] = {}
    for oneof in message.DESCRIPTOR.oneofs:
        current = message.WhichOneof(oneof.name)
        member = next((field for field in oneof.fields if field.name == current), None)
        if member is None or not _field_has_fcse(member, inherited):
            member = next(
                (field for field in oneof.fields if _field_has_fcse(field, inherited)),
                None,
            )
        if member is not None:
            selected_oneofs[oneof.name] = member

    for field in message.DESCRIPTOR.fields:
        if (
            field.containing_oneof is not None
            and selected_oneofs.get(field.containing_oneof.name) is not field
        ):
            continue
        field_path = f"{path}.{field.name}"
        level = _effective_sensitivity(inherited, _declared_sensitivity(field, field_path))
        child = field.message_type
        if child is None:
            if level != options_pb2.FCSE_ONLY:
                continue
            value = _fcse_sentinel(field, token, field_path)
            if field.is_repeated:
                getattr(message, field.name).append(value)
            else:
                setattr(message, field.name, value)
            sentinels[field_path] = value
            continue

        if child.GetOptions().map_entry:
            continue
        if level != options_pb2.FCSE_ONLY and not _has_fcse_field(child, level):
            continue
        if field.is_repeated:
            nested = getattr(message, field.name).add()
        else:
            nested = getattr(message, field.name)
            nested.SetInParent()
        if level == options_pb2.FCSE_ONLY:
            sentinels[field_path] = "present"
        _populate_fcse_fields(nested, level, field_path, token, sentinels)


def _assert_fcse_removed(
    message: Message, clearance: int, inherited: int = options_pb2.PUBLIC
) -> None:
    for field in message.DESCRIPTOR.fields:
        level = _effective_sensitivity(
            inherited,
            _declared_sensitivity(field, f"{message.DESCRIPTOR.full_name}.{field.name}"),
        )
        value = getattr(message, field.name)
        if _SENSITIVITY_RANK[level] > _SENSITIVITY_RANK[clearance]:
            if field.is_repeated:
                assert not value
            elif field.has_presence:
                assert not message.HasField(field.name)
            else:
                assert value == field.default_value
            continue

        child = field.message_type
        if child is None or child.full_name == "google.protobuf.Timestamp":
            continue
        if child.GetOptions().map_entry:
            map_value = child.fields_by_name["value"].message_type
            if map_value is not None and not field.is_repeated:
                continue
            if map_value is not None:
                for item in value.values():
                    _assert_fcse_removed(item, clearance, level)
        elif field.is_repeated:
            for item in value:
                _assert_fcse_removed(item, clearance, level)
        elif message.HasField(field.name):
            _assert_fcse_removed(value, clearance, level)


def _cases(token: str) -> list[tuple[str, Message, dict[str, Any]]]:
    marker = f"private:{token}"
    remote = detection_pb2.RemoteIdObservation(
        operator_id=f"{marker}:operator_id",
        operator_location=common_pb2.GeoPoint(latitude_deg=41.1, longitude_deg=-3.2),
        uas_id=f"{marker}:uas_id",
        self_id_description=f"{marker}:self_id_description",
        standard=detection_pb2.REMOTE_ID_STANDARD_EN_4709_002,
        aircraft_position=common_pb2.GeoPoint(latitude_deg=42.0, longitude_deg=-4.0),
        message_time=timestamp_pb2.Timestamp(seconds=123),
    )
    detection = detection_pb2.Detection(remote_id=remote)
    envelope = envelope_pb2.Envelope(
        site_id="site",
        node_id="node",
        sequence=1,
        emitted_at=timestamp_pb2.Timestamp(seconds=456),
        detection=detection,
    )
    alert = alert_pb2.Alert(
        alert_id="alert",
        track_id="track",
        created_at=timestamp_pb2.Timestamp(seconds=789),
        level=alert_pb2.ALERT_LEVEL_WARNING,
        confidence=0.8,
    )
    coverage = coverage_status_pb2.CoverageStatus(
        site_id="site",
        region_id="region",
        boundary=[common_pb2.GeoPoint(latitude_deg=1, longitude_deg=2)],
        estimated_probability=0.5,
        uncertainty=common_pb2.ErrorEllipse(
            semi_major_axis_m=3,
            semi_minor_axis_m=2,
            orientation_deg=0,
            confidence_level=0.95,
        ),
        assessed_at=timestamp_pb2.Timestamp(seconds=10),
    )
    ground_truth = ground_truth_pb2.GroundTruth(
        target_id="target",
        simulated_at=timestamp_pb2.Timestamp(seconds=11),
        true_position=common_pb2.GeoPoint(latitude_deg=51.2, longitude_deg=-1.3),
        class_id="C1",
        is_forged=True,
        launch_point=common_pb2.GeoPoint(latitude_deg=50.2, longitude_deg=-0.3),
    )
    prediction = prediction_pb2.Prediction(
        track_id="track",
        generated_at=timestamp_pb2.Timestamp(seconds=12),
        origin_heatmap=f"{marker}:origin_heatmap".encode(),
    )
    envelope_prediction = envelope_pb2.Envelope(
        site_id="site",
        node_id="node",
        sequence=2,
        emitted_at=timestamp_pb2.Timestamp(seconds=457),
        prediction=prediction,
    )
    node_status = node_status_pb2.NodeStatus(
        site_id="site",
        node_id="node",
        observed_at=timestamp_pb2.Timestamp(seconds=13),
        health=node_status_pb2.NODE_HEALTH_HEALTHY,
    )
    sighting = sighting_pb2.Sighting(
        sighting_id="sighting",
        observed_at=timestamp_pb2.Timestamp(seconds=14),
        observer_position=common_pb2.GeoPoint(latitude_deg=1, longitude_deg=2),
        bearing_deg=10,
        bearing_uncertainty_deg=1,
        evidence_ids=[f"evidence-{token}"],
    )
    signature_class = signature_class_pb2.SignatureClass(
        code=signature_class_pb2.SIGNATURE_CLASS_CODE_C1,
        label="C1",
        description="small multirotor",
        synthetic=True,
    )
    track = track_pb2.Track(
        track_id="track",
        site_id="site",
        position=common_pb2.GeoPoint(latitude_deg=1, longitude_deg=2),
        state_covariance=common_pb2.PositionCovariance(
            east_east_m2=1,
            east_north_m2=0,
            east_up_m2=0,
            north_north_m2=1,
            north_up_m2=0,
            up_up_m2=1,
        ),
        velocity_east_mps=0,
        velocity_north_mps=0,
        velocity_up_mps=0,
        class_probabilities=[common_pb2.ClassScore(class_id="C1", probability=1)],
        updated_at=timestamp_pb2.Timestamp(seconds=15),
        time_quality=common_pb2.TimeQuality(pps_valid=True, clock_offset_ms=0, uncertainty_ms=0.1),
    )
    evidence = evidence_pb2.Evidence(
        evidence_id="evidence",
        sha256="0" * 64,
        media_type="application/octet-stream",
        captured_at=timestamp_pb2.Timestamp(seconds=16),
        custodian_pseudonym="custodian",
    )
    cases: list[tuple[str, Message]] = [
        ("Alert", alert),
        ("CoverageStatus", coverage),
        ("Detection", detection),
        ("EnvelopeDetection", envelope),
        ("EnvelopePrediction", envelope_prediction),
        ("Evidence", evidence),
        ("GroundTruth", ground_truth),
        ("NodeStatus", node_status),
        ("Prediction", prediction),
        ("Sighting", sighting),
        ("SignatureClass", signature_class),
        ("Track", track),
    ]
    result: list[tuple[str, Message, dict[str, Any]]] = []
    for name, message in cases:
        sentinels: dict[str, Any] = {}
        _populate_fcse_fields(
            message,
            options_pb2.PUBLIC,
            message.DESCRIPTOR.full_name,
            token,
            sentinels,
        )
        prefix = f"{message.DESCRIPTOR.full_name}."
        if name == "EnvelopeDetection":
            prefix += "detection."
        elif name == "EnvelopePrediction":
            prefix += "prediction."
        elif name == "Detection":
            prefix += "remote_id."
        expected_paths = {path for path in _FCSE_TABLE_PATHS if path.startswith(prefix)}
        assert set(sentinels) == expected_paths, name
        result.append((name, message, sentinels))
    return result


@pytest.mark.req("REQ-PRIV-001", "REQ-LEG-007")
@settings(max_examples=200, deadline=None)
@given(token=st.text(min_size=1, max_size=24))
def test_redact_protege_los_11_mensajes(token: str) -> None:
    cases = _cases(token)
    assert {message.DESCRIPTOR.full_name for _, message, _ in cases} == {
        "atalaya.v1.Alert",
        "atalaya.v1.CoverageStatus",
        "atalaya.v1.Detection",
        "atalaya.v1.Envelope",
        "atalaya.v1.Evidence",
        "atalaya.v1.NodeStatus",
        "atalaya.v1.Prediction",
        "atalaya.v1.Sighting",
        "atalaya.v1.SignatureClass",
        "atalaya.v1.Track",
        "atalaya.sim.v1.GroundTruth",
    }
    for name, original, sentinels in cases:
        original_bytes = original.SerializeToString(deterministic=True)
        for clearance in (options_pb2.PUBLIC, options_pb2.OPERATOR):
            filtered = redact(original, clearance)
            assert filtered is not original
            serialized = filtered.SerializeToString(deterministic=True)
            for sentinel in sentinels.values():
                if isinstance(sentinel, str) and sentinel.startswith("fcse-sentinel:"):
                    assert sentinel.encode() not in serialized, name
                elif isinstance(sentinel, bytes):
                    assert sentinel not in serialized, name
            _assert_fcse_removed(filtered, clearance)
        fully_authorized = redact(original, options_pb2.FCSE_ONLY)
        assert fully_authorized == original, name
        assert fully_authorized.SerializeToString(deterministic=True) == original_bytes, name
        assert original.SerializeToString(deterministic=True) == original_bytes, name


@pytest.mark.req("REQ-PRIV-001", "REQ-LEG-007")
def test_redact_hereda_el_nivel_del_contenedor_y_preserva_presence() -> None:
    source = ground_truth_pb2.GroundTruth(
        true_position=common_pb2.GeoPoint(latitude_deg=0.0, longitude_deg=0.0),
        is_forged=False,
        launch_point=common_pb2.GeoPoint(latitude_deg=1.0, longitude_deg=2.0),
    )
    filtered = cast(ground_truth_pb2.GroundTruth, redact(source, options_pb2.OPERATOR))
    assert not filtered.HasField("true_position")
    assert not filtered.HasField("launch_point")
    assert not filtered.HasField("is_forged")
    assert source.HasField("true_position")
    assert source.HasField("launch_point")
    assert source.HasField("is_forged")

    optional_zero = detection_pb2.Detection(bearing_deg=0.0)
    assert optional_zero.HasField("bearing_deg")
    filtered_zero = cast(detection_pb2.Detection, redact(optional_zero, options_pb2.OPERATOR))
    assert filtered_zero.HasField("bearing_deg")
    assert filtered_zero.bearing_deg == 0.0
    assert not redact(optional_zero, options_pb2.PUBLIC).HasField("bearing_deg")


@pytest.mark.req("REQ-PRIV-001", "REQ-LEG-007")
def test_jerarquia_sigue_la_politica_y_no_los_numeros_de_enum() -> None:
    assert redact_module._effective_level(options_pb2.PUBLIC, options_pb2.FCSE_ONLY) == (
        options_pb2.FCSE_ONLY
    )
    assert redact_module._effective_level(options_pb2.OPERATOR, options_pb2.PUBLIC) == (
        options_pb2.OPERATOR
    )


@pytest.mark.req("REQ-PRIV-001")
def test_redact_repetidos_oneof_y_timestamp() -> None:
    source = detection_pb2.Detection(
        class_scores=[common_pb2.ClassScore(class_id="C1", probability=0.5)],
        observed_at=timestamp_pb2.Timestamp(seconds=123, nanos=456),
        acoustic=detection_pb2.AcousticObservation(signal_to_noise_db=10.0),
    )
    operator_view = cast(detection_pb2.Detection, redact(source, options_pb2.OPERATOR))
    assert len(operator_view.class_scores) == 1
    assert operator_view.WhichOneof("observation") == "acoustic"
    assert operator_view.observed_at == source.observed_at

    public_view = cast(detection_pb2.Detection, redact(source, options_pb2.PUBLIC))
    assert len(public_view.class_scores) == 0
    assert public_view.WhichOneof("observation") is None
    assert not public_view.HasField("observed_at")


@pytest.mark.req("REQ-PRIV-001")
@settings(max_examples=80, deadline=None)
@given(
    token=st.text(min_size=1, max_size=12),
    optional_present=st.booleans(),
    repeated_count=st.integers(min_value=0, max_value=4),
    observation_kind=st.sampled_from(("acoustic", "remote_id")),
)
def test_redact_varia_presence_oneof_y_repeated(
    token: str,
    optional_present: bool,
    repeated_count: int,
    observation_kind: str,
) -> None:
    source = detection_pb2.Detection(
        class_scores=[
            common_pb2.ClassScore(class_id=f"class-{token}-{index}", probability=0.5)
            for index in range(repeated_count)
        ]
    )
    if optional_present:
        source.bearing_deg = 0.0
    if observation_kind == "acoustic":
        source.acoustic.signal_to_noise_db = 4.0
    else:
        source.remote_id.operator_id = f"operator-{token}"

    operator_view = cast(detection_pb2.Detection, redact(source, options_pb2.OPERATOR))
    assert operator_view.HasField("bearing_deg") is optional_present
    assert len(operator_view.class_scores) == repeated_count
    assert operator_view.WhichOneof("observation") == observation_kind
    assert source.WhichOneof("observation") == observation_kind

    public_view = cast(detection_pb2.Detection, redact(source, options_pb2.PUBLIC))
    assert not public_view.HasField("bearing_deg")
    assert len(public_view.class_scores) == 0
    assert public_view.WhichOneof("observation") is None
    assert source.HasField("bearing_deg") is optional_present
    assert source.WhichOneof("observation") == observation_kind


def _dynamic_map_type() -> Any:
    file_proto = descriptor_pb2.FileDescriptorProto(
        name="redact_map_test.proto", package="redact_test", syntax="proto3"
    )
    file_proto.dependency.append(options_pb2.DESCRIPTOR.name)
    message = file_proto.message_type.add(name="Root")
    entry = message.nested_type.add(name="SecretsEntry")
    entry.options.map_entry = True
    entry.field.add(
        name="key",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    entry.field.add(
        name="value",
        number=2,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    map_field = message.field.add(
        name="secrets",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".redact_test.Root.SecretsEntry",
    )
    map_field.options.Extensions[cast(Any, options_pb2.sensitivity)] = options_pb2.FCSE_ONLY

    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.AddSerializedFile(options_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(file_proto)
    return message_factory.GetMessageClass(pool.FindMessageTypeByName("redact_test.Root"))


def _redact_dynamic_algorithm_test(original: Message, clearance: int) -> Message:
    """Ejercita el recorrido de mapas sintéticos sin abrir el trust boundary público."""
    redactor = cast(Any, redact_module)
    redactor._validate_descriptor(original.DESCRIPTOR, original.DESCRIPTOR.full_name, set())
    result = original.__class__()
    result.CopyFrom(original)
    redactor._redact_message(result, options_pb2.PUBLIC, clearance)
    return result


@pytest.mark.req("REQ-PRIV-001")
def test_redact_mapa() -> None:
    dynamic_type = _dynamic_map_type()
    original = cast(Any, dynamic_type())
    original.secrets["sensitive-key"] = "private-value"
    assert cast(Any, _redact_dynamic_algorithm_test(original, options_pb2.OPERATOR)).secrets == {}
    assert cast(Any, _redact_dynamic_algorithm_test(original, options_pb2.FCSE_ONLY)).secrets == {
        "sensitive-key": "private-value"
    }
    assert original.secrets["sensitive-key"] == "private-value"


def _dynamic_message_map_type() -> Any:
    file_proto = descriptor_pb2.FileDescriptorProto(
        name="redact_message_map_test.proto", package="redact_map_test", syntax="proto3"
    )
    file_proto.dependency.append(options_pb2.DESCRIPTOR.name)
    message = file_proto.message_type.add(name="Root")
    leaf = message.nested_type.add(name="Leaf")
    leaf.field.add(
        name="public_value",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    ).options.Extensions[cast(Any, options_pb2.sensitivity)] = options_pb2.PUBLIC
    leaf.field.add(
        name="private_value",
        number=2,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    ).options.Extensions[cast(Any, options_pb2.sensitivity)] = options_pb2.FCSE_ONLY
    entry = message.nested_type.add(name="ValuesEntry")
    entry.options.map_entry = True
    entry.field.add(
        name="key",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    entry.field.add(
        name="value",
        number=2,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".redact_map_test.Root.Leaf",
    )
    map_field = message.field.add(
        name="values",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".redact_map_test.Root.ValuesEntry",
    )
    map_field.options.Extensions[cast(Any, options_pb2.sensitivity)] = options_pb2.OPERATOR

    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.AddSerializedFile(options_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(file_proto)
    return message_factory.GetMessageClass(pool.FindMessageTypeByName("redact_map_test.Root"))


@pytest.mark.req("REQ-PRIV-001")
def test_redact_mapa_de_mensajes_y_niveles_heredados() -> None:
    original = cast(Any, _dynamic_message_map_type()())
    original.values["entry"].public_value = "operator-visible"
    original.values["entry"].private_value = "restricted"

    operator_view = cast(Any, _redact_dynamic_algorithm_test(original, options_pb2.OPERATOR))
    assert operator_view.values["entry"].public_value == "operator-visible"
    assert operator_view.values["entry"].private_value == ""
    assert cast(Any, _redact_dynamic_algorithm_test(original, options_pb2.PUBLIC)).values == {}
    assert original.values["entry"].private_value == "restricted"


def _dynamic_unannotated_type(level: int | None = None) -> Any:
    file_proto = descriptor_pb2.FileDescriptorProto(
        name="redact_unannotated_test.proto", package="redact_test", syntax="proto3"
    )
    message = file_proto.message_type.add(name="Unannotated")
    field = message.field.add(
        name="value",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    if level is not None:
        file_proto.dependency.append(options_pb2.DESCRIPTOR.name)
        field.options.Extensions[cast(Any, options_pb2.sensitivity)] = level
    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    if options_pb2.DESCRIPTOR.name in file_proto.dependency:
        pool.AddSerializedFile(options_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(file_proto)
    return message_factory.GetMessageClass(pool.FindMessageTypeByName("redact_test.Unannotated"))


def _dynamic_homonymous_alert_type() -> Any:
    file_proto = descriptor_pb2.FileDescriptorProto(
        name="redact_homonym_alert.proto", package="atalaya.v1", syntax="proto3"
    )
    file_proto.dependency.append(options_pb2.DESCRIPTOR.name)
    alert = file_proto.message_type.add(name="Alert")
    field = alert.field.add(
        name="summary",
        number=7,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    field.options.Extensions[cast(Any, options_pb2.sensitivity)] = options_pb2.PUBLIC
    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.AddSerializedFile(options_pb2.DESCRIPTOR.serialized_pb)
    pool.Add(file_proto)
    return message_factory.GetMessageClass(pool.FindMessageTypeByName("atalaya.v1.Alert"))


@pytest.mark.req("REQ-PRIV-001")
def test_redact_rechaza_alert_homonimo_autoetiquetado_public() -> None:
    homonym = cast(Any, _dynamic_homonymous_alert_type()())
    homonym.summary = "PII_SENTINEL"
    with pytest.raises(ValueError, match="descriptor raíz no oficial"):
        redact(homonym, options_pb2.PUBLIC)


def _dynamic_homonymous_timestamp_type() -> Any:
    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.AddSerializedFile(options_pb2.DESCRIPTOR.serialized_pb)

    timestamp_file = descriptor_pb2.FileDescriptorProto(
        name="homonym_timestamp.proto", package="google.protobuf", syntax="proto3"
    )
    fake_timestamp = timestamp_file.message_type.add(name="Timestamp")
    fake_timestamp.field.add(
        name="unclassified_value",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    pool.Add(timestamp_file)

    holder_file = descriptor_pb2.FileDescriptorProto(
        name="timestamp_holder.proto", package="redact_homonym", syntax="proto3"
    )
    holder_file.dependency.extend([timestamp_file.name, options_pb2.DESCRIPTOR.name])
    holder = holder_file.message_type.add(name="Holder")
    timestamp_field = holder.field.add(
        name="timestamp",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE,
        type_name=".google.protobuf.Timestamp",
    )
    timestamp_field.options.Extensions[cast(Any, options_pb2.sensitivity)] = options_pb2.OPERATOR
    pool.Add(holder_file)
    return message_factory.GetMessageClass(pool.FindMessageTypeByName("redact_homonym.Holder"))


def _dynamic_proto2_extension_message() -> tuple[Any, Any]:
    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.AddSerializedFile(options_pb2.DESCRIPTOR.serialized_pb)

    base_file = descriptor_pb2.FileDescriptorProto(
        name="extension_base.proto", package="redact_extension", syntax="proto2"
    )
    data = base_file.message_type.add(name="Data")
    data.extension_range.add(start=100, end=200)
    pool.Add(base_file)

    extensions_file = descriptor_pb2.FileDescriptorProto(
        name="extension_fields.proto", package="redact_extension", syntax="proto2"
    )
    extensions_file.dependency.extend([base_file.name, options_pb2.DESCRIPTOR.name])
    extension = extensions_file.extension.add(
        name="secret_value",
        number=100,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
        extendee=".redact_extension.Data",
    )
    extension.options.Extensions[cast(Any, options_pb2.sensitivity)] = options_pb2.FCSE_ONLY
    pool.Add(extensions_file)
    return (
        message_factory.GetMessageClass(pool.FindMessageTypeByName("redact_extension.Data")),
        pool.FindExtensionByName("redact_extension.secret_value"),
    )


@pytest.mark.req("REQ-PRIV-001")
def test_redact_falla_cerrado_para_clearance_o_sensibilidad_ausentes() -> None:
    for boolean_clearance in (True, False):
        with pytest.raises(ValueError, match="nivel de autorización inválido"):
            redact(alert_pb2.Alert(), boolean_clearance)
    with pytest.raises(ValueError, match="nivel de autorización inválido"):
        redact(common_pb2.GeoPoint(), options_pb2.SENSITIVITY_UNSPECIFIED)
    with pytest.raises(ValueError, match="nivel de autorización inválido"):
        redact(common_pb2.GeoPoint(), 99)
    with pytest.raises(ValueError, match="falta la sensibilidad declarada"):
        redact(_dynamic_unannotated_type()(), options_pb2.PUBLIC)
    for level in (options_pb2.SENSITIVITY_UNSPECIFIED, 99):
        with pytest.raises(ValueError, match="nivel de sensibilidad inválido"):
            redact(_dynamic_unannotated_type(level)(), options_pb2.PUBLIC)
    self_declared_public = cast(Any, _dynamic_unannotated_type(options_pb2.PUBLIC)())
    self_declared_public.value = "private-under-false-public-label"
    with pytest.raises(ValueError, match="descriptor raíz no oficial"):
        redact(self_declared_public, options_pb2.PUBLIC)
    with pytest.raises(TypeError, match="requiere un mensaje Protobuf"):
        redact(cast(Any, {"secret": "value"}), options_pb2.PUBLIC)


@pytest.mark.req("REQ-PRIV-001")
def test_redact_falla_cerrado_ante_campos_wire_desconocidos() -> None:
    known = common_pb2.GeoPoint(latitude_deg=1.0, longitude_deg=2.0)
    with_unknown = common_pb2.GeoPoint.FromString(known.SerializeToString() + b"\xa0\x06\x01")
    nested_unknown = detection_pb2.Detection(
        remote_id=detection_pb2.RemoteIdObservation(operator_location=with_unknown)
    )
    for message in (with_unknown, nested_unknown):
        with pytest.raises(ValueError, match="contiene campos wire desconocidos"):
            redact(message, options_pb2.OPERATOR)


@pytest.mark.req("REQ-PRIV-001")
def test_redact_rechaza_homonimo_de_timestamp_no_oficial() -> None:
    homonym = cast(Any, _dynamic_homonymous_timestamp_type()())
    homonym.timestamp.unclassified_value = "timestamp-name-homonym"
    with pytest.raises(ValueError, match="descriptor homónimo no oficial"):
        redact(homonym, options_pb2.OPERATOR)


@pytest.mark.req("REQ-PRIV-001")
def test_redact_rechaza_extension_proto2_sin_clasificar_en_recorrido() -> None:
    message_type, extension = _dynamic_proto2_extension_message()
    source = message_type()
    source.Extensions[extension] = "extension-fcse-sentinel"
    with pytest.raises(ValueError, match="rangos de extensión no soportados"):
        redact(source, options_pb2.PUBLIC)


@pytest.mark.req("REQ-PRIV-001")
def test_redact_no_modifica_el_original_y_preserva_timestamp_autorizado() -> None:
    original = alert_pb2.Alert(
        alert_id="a",
        track_id="t",
        created_at=timestamp_pb2.Timestamp(seconds=42, nanos=3),
        level=alert_pb2.ALERT_LEVEL_INFORMATION,
        confidence=0.0,
    )
    before = original.SerializeToString(deterministic=True)
    filtered = cast(alert_pb2.Alert, redact(original, options_pb2.OPERATOR))
    assert filtered == original
    assert filtered is not original
    assert filtered.created_at == original.created_at
    assert original.SerializeToString(deterministic=True) == before


@pytest.mark.req("REQ-PRIV-001")
def test_redact_sin_sensibilidad_efectiva_no_deja_el_descenso() -> None:
    source = detection_pb2.Detection(
        remote_id=detection_pb2.RemoteIdObservation(
            operator_location=common_pb2.GeoPoint(latitude_deg=40.0, longitude_deg=-3.0)
        )
    )
    operator_view = cast(detection_pb2.Detection, redact(source, options_pb2.OPERATOR))
    assert operator_view.HasField("remote_id")
    assert not operator_view.remote_id.HasField("operator_location")
    assert source.remote_id.HasField("operator_location")

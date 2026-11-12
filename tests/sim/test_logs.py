"""Pruebas del proyector JSON reusable; no hay aún servicios de log ejecutables."""

from __future__ import annotations

import json
import logging
from hashlib import sha256
from types import SimpleNamespace
from typing import Any, cast

import pytest
from atalaya.sim.v1 import ground_truth_pb2
from atalaya.v1 import (
    alert_pb2,
    common_pb2,
    detection_pb2,
    envelope_pb2,
    evidence_pb2,
    options_pb2,
    prediction_pb2,
    sighting_pb2,
    signature_class_pb2,
)
from atalaya_contracts import log_contract_event, log_projection, project_log_record
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory, timestamp_pb2
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message
from hypothesis import given, settings
from hypothesis import strategies as st


def _log_cases(token: str) -> list[tuple[Message, tuple[str, ...]]]:
    identifier_marker = f"pii-id:{token}"
    private_marker = f"fcse-sentinel:{token}:operator"
    free_text_marker = f"fcse-sentinel:{token}:free-text"
    custody_marker = f"fcse-sentinel:{token}:custody"
    coordinate = float(int.from_bytes(sha256(token.encode()).digest()[:4], "big") + 1)
    coordinate_markers = (str(coordinate), str(-coordinate))
    location = common_pb2.GeoPoint(latitude_deg=coordinate, longitude_deg=-coordinate)
    alert = alert_pb2.Alert(
        alert_id=identifier_marker,
        track_id=identifier_marker,
        level=alert_pb2.ALERT_LEVEL_WARNING,
        confidence=0.8,
        created_at=timestamp_pb2.Timestamp(seconds=123),
        summary=free_text_marker,
    )
    sighting = sighting_pb2.Sighting(
        sighting_id=identifier_marker,
        observed_at=timestamp_pb2.Timestamp(seconds=124),
        observer_position=location,
        bearing_deg=10,
        bearing_uncertainty_deg=1,
        description=free_text_marker,
        evidence_ids=[f"evidence-ref:{token}"],
    )
    evidence = evidence_pb2.Evidence(
        evidence_id=identifier_marker,
        sha256="f" * 64,
        media_type="application/octet-stream",
        captured_at=timestamp_pb2.Timestamp(seconds=125),
        custodian_pseudonym=custody_marker,
        custody_signature=custody_marker.encode(),
    )
    detection = detection_pb2.Detection(
        detection_id=identifier_marker,
        site_id=identifier_marker,
        node_id=identifier_marker,
        observed_at=timestamp_pb2.Timestamp(seconds=122),
        sensor_type=detection_pb2.SENSOR_TYPE_REMOTE_ID,
        remote_id=detection_pb2.RemoteIdObservation(
            operator_id=private_marker,
            operator_location=location,
            uas_id=private_marker,
            self_id_description=private_marker,
            standard=detection_pb2.REMOTE_ID_STANDARD_EN_4709_002,
        ),
    )
    prediction = prediction_pb2.Prediction(
        track_id=identifier_marker,
        generated_at=timestamp_pb2.Timestamp(seconds=126),
        origin_heatmap=private_marker.encode(),
    )
    signature_class = signature_class_pb2.SignatureClass(
        code=signature_class_pb2.SIGNATURE_CLASS_CODE_C1,
        label=free_text_marker,
        description=free_text_marker,
        synthetic=True,
    )
    ground_truth = ground_truth_pb2.GroundTruth(
        target_id=identifier_marker,
        simulated_at=timestamp_pb2.Timestamp(seconds=127),
        true_position=location,
        class_id="C2",
        is_forged=True,
        launch_point=location,
    )
    envelope_alert = envelope_pb2.Envelope(
        site_id=identifier_marker,
        node_id=identifier_marker,
        sequence=1,
        emitted_at=timestamp_pb2.Timestamp(seconds=128),
        alert=alert,
    )
    envelope_sighting = envelope_pb2.Envelope(
        site_id=identifier_marker,
        node_id=identifier_marker,
        sequence=2,
        emitted_at=timestamp_pb2.Timestamp(seconds=129),
        sighting=sighting,
    )
    envelope_evidence = envelope_pb2.Envelope(
        site_id=identifier_marker,
        node_id=identifier_marker,
        sequence=3,
        emitted_at=timestamp_pb2.Timestamp(seconds=130),
        evidence=evidence,
    )
    return [
        (alert, (identifier_marker, free_text_marker)),
        (sighting, (identifier_marker, free_text_marker, *coordinate_markers)),
        (evidence, (identifier_marker, custody_marker)),
        (detection, (identifier_marker, private_marker, *coordinate_markers)),
        (prediction, (identifier_marker, private_marker)),
        (signature_class, (free_text_marker,)),
        (ground_truth, (identifier_marker, *coordinate_markers)),
        (envelope_alert, (identifier_marker, free_text_marker)),
        (envelope_sighting, (identifier_marker, free_text_marker, *coordinate_markers)),
        (envelope_evidence, (identifier_marker, custody_marker)),
    ]


def _keys_in(value: object) -> set[str]:
    if isinstance(value, dict):
        return {key for key in value if isinstance(key, str)} | set().union(
            *(_keys_in(child) for child in value.values())
        )
    if isinstance(value, list):
        return set().union(*(_keys_in(child) for child in value))
    return set()


@pytest.mark.req("REQ-PRIV-001", "REQ-LEG-007")
@settings(max_examples=200, deadline=None)
@given(token=st.text(min_size=1, max_size=24))
def test_proyeccion_json_no_emite_centinales_sensibles(token: str) -> None:
    for message, sentinels in _log_cases(token):
        if message.DESCRIPTOR.full_name in {
            "atalaya.v1.Evidence",
            "atalaya.sim.v1.GroundTruth",
        }:
            with pytest.raises(ValueError, match="mensaje excluido de logs"):
                project_log_record(message, authorized=True)
            continue

        record = project_log_record(
            message,
            clearance=options_pb2.OPERATOR,
            authorized=True,
        )
        serialized = json.dumps(record, allow_nan=False, sort_keys=True)
        assert record["schema"] == message.DESCRIPTOR.full_name
        for sentinel in sentinels:
            assert sentinel not in serialized
        assert not _keys_in(record) & {
            "summary",
            "description",
            "label",
            "custodian_pseudonym",
            "custody_signature",
            "alert_id",
            "track_id",
            "sighting_id",
            "evidence_id",
            "site_id",
            "node_id",
            "target_id",
            "detection_id",
            "operator_id",
            "uas_id",
            "self_id_description",
            "latitude_deg",
            "longitude_deg",
            "position",
            "observer_position",
            "true_position",
            "launch_point",
            "is_forged",
        }


@pytest.mark.req("REQ-PRIV-001")
def test_nivel_public_y_operator_filtran_y_preservan_esquema_json() -> None:
    source = detection_pb2.Detection(
        site_id="site-id",
        node_id="node-id",
        observed_at=timestamp_pb2.Timestamp(seconds=5),
        sensor_type=detection_pb2.SENSOR_TYPE_ACOUSTIC,
        detection_confidence=0.6,
    )
    public = project_log_record(source, clearance=options_pb2.PUBLIC, authorized=True)
    operator = project_log_record(source, clearance=options_pb2.OPERATOR, authorized=True)
    assert public == {
        "schema": "atalaya.v1.Detection",
        "fields": {},
        "counts": {"class_scores_count": 0},
    }
    assert operator["fields"]["sensor_type"] == "SENSOR_TYPE_ACOUSTIC"
    assert operator["fields"]["detection_confidence"] == 0.6
    assert operator["fields"]["observed_at"] == {"seconds": 5, "nanos": 0}
    assert "site_id" not in operator["fields"]
    assert json.loads(json.dumps(operator, allow_nan=False)) == operator


@pytest.mark.req("REQ-PRIV-001")
def test_senal_de_caller_o_nivel_invalido_falla_cerrado_sin_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sentinel = "must-not-be-logged"
    message = alert_pb2.Alert(alert_id=sentinel, summary=sentinel)
    logger = logging.getLogger("atalaya.contracts.test.denied")
    with pytest.raises(PermissionError, match="no autorizado"):
        log_contract_event(logger, message)
    with pytest.raises(PermissionError, match="no autorizado"):
        project_log_record(message)
    for level in (
        options_pb2.SENSITIVITY_UNSPECIFIED,
        options_pb2.FCSE_ONLY,
        99,
    ):
        with pytest.raises(ValueError, match="nivel de log inválido"):
            log_contract_event(logger, message, clearance=level, authorized=True)
    assert sentinel not in caplog.text
    assert caplog.text == ""


@pytest.mark.req("REQ-PRIV-001")
def test_error_de_proyeccion_no_escribe_centinales(caplog: pytest.LogCaptureFixture) -> None:
    sentinel = "private-error-sentinel"
    message = alert_pb2.Alert(alert_id="alert", summary=sentinel, confidence=float("nan"))
    logger = logging.getLogger("atalaya.contracts.test.projection-error")
    with pytest.raises(ValueError, match="no finito"):
        log_contract_event(logger, message, authorized=True)
    assert sentinel not in caplog.text
    assert caplog.text == ""


@pytest.mark.req("REQ-PRIV-001")
def test_sink_emite_solo_json_de_esquema_allowlist(caplog: pytest.LogCaptureFixture) -> None:
    marker = "sink-sentinel-735"
    message, _ = _log_cases(marker)[0]
    assert isinstance(message, alert_pb2.Alert)
    logger = logging.getLogger("atalaya.contracts.test.success")
    with caplog.at_level(logging.INFO, logger=logger.name):
        log_contract_event(logger, message, authorized=True)

    assert len(caplog.records) == 1
    record = json.loads(caplog.records[0].getMessage())
    assert record == {
        "schema": "atalaya.v1.Alert",
        "fields": {
            "confidence": 0.8,
            "created_at": {"nanos": 0, "seconds": 123},
            "level": "ALERT_LEVEL_WARNING",
        },
        "counts": {},
    }
    serialized = caplog.records[0].getMessage()
    assert marker not in serialized
    assert "fcse-sentinel" not in serialized


@pytest.mark.req("REQ-PRIV-001", "REQ-LEG-007")
def test_sink_nunca_emite_texto_libre_ni_custodia_de_mensajes_oficiales(
    caplog: pytest.LogCaptureFixture,
) -> None:
    marker = "free-text-and-custody-sentinel"
    logger = logging.getLogger("atalaya.contracts.test.all-schemas")
    with caplog.at_level(logging.INFO, logger=logger.name):
        for message, sentinels in _log_cases(marker):
            before = len(caplog.records)
            if message.DESCRIPTOR.full_name in {
                "atalaya.v1.Evidence",
                "atalaya.sim.v1.GroundTruth",
            }:
                with pytest.raises(ValueError, match="mensaje excluido de logs"):
                    log_contract_event(logger, message, authorized=True)
                assert len(caplog.records) == before
                continue
            log_contract_event(logger, message, authorized=True)
            assert len(caplog.records) == before + 1
            payload = caplog.records[-1].getMessage()
            assert not any(sentinel in payload for sentinel in sentinels)
            assert not _keys_in(json.loads(payload)) & {
                "summary",
                "description",
                "label",
                "custodian_pseudonym",
                "custody_signature",
            }


def _dynamic_homonymous_alert() -> Message:
    pool = descriptor_pool.DescriptorPool()
    pool.AddSerializedFile(descriptor_pb2.DESCRIPTOR.serialized_pb)
    pool.AddSerializedFile(options_pb2.DESCRIPTOR.serialized_pb)
    file_proto = descriptor_pb2.FileDescriptorProto(
        name="homonym_alert.proto", package="atalaya.v1", syntax="proto3"
    )
    file_proto.dependency.append(options_pb2.DESCRIPTOR.name)
    alert = file_proto.message_type.add(name="Alert")
    confidence = alert.field.add(
        name="confidence",
        number=1,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE,
    )
    confidence.options.Extensions[cast(Any, options_pb2.sensitivity)] = options_pb2.OPERATOR
    pool.Add(file_proto)
    dynamic_type = message_factory.GetMessageClass(pool.FindMessageTypeByName("atalaya.v1.Alert"))
    return dynamic_type(confidence=0.9)


@pytest.mark.req("REQ-PRIV-001")
def test_proyeccion_rechaza_descriptor_homonimo_no_oficial() -> None:
    homonym = _dynamic_homonymous_alert()
    with pytest.raises(ValueError, match="descriptor no oficial para logs"):
        project_log_record(homonym, authorized=True)
    with pytest.raises(ValueError, match="descriptor no permitido en logs"):
        log_projection._project_message(homonym)


@pytest.mark.req("REQ-PRIV-001")
def test_proyeccion_falla_cerrado_en_tipo_nivel_schema_y_logger() -> None:
    with pytest.raises(TypeError, match="requiere un mensaje Protobuf"):
        project_log_record("raw private text", authorized=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="nivel de log inválido"):
        project_log_record(alert_pb2.Alert(), clearance=True, authorized=True)
    with pytest.raises(ValueError, match="schema no permitido en logs"):
        project_log_record(common_pb2.GeoPoint(), authorized=True)
    with pytest.raises(TypeError, match=r"requiere logging\.Logger"):
        log_contract_event(object(), alert_pb2.Alert(), authorized=True)  # type: ignore[arg-type]


@pytest.mark.req("REQ-PRIV-001")
def test_proyeccion_omite_defaults_y_rechaza_enum_desconocido() -> None:
    empty_alert = alert_pb2.Alert()
    record = project_log_record(empty_alert, authorized=True)
    assert "confidence" not in record["fields"]

    empty_quality = detection_pb2.Detection(time_quality=common_pb2.TimeQuality())
    quality_record = project_log_record(empty_quality, authorized=True)
    assert "time_quality" not in quality_record["fields"]

    unknown_enum = detection_pb2.Detection()
    unknown_enum.sensor_type = cast(Any, 99)
    with pytest.raises(ValueError, match="valor de enum desconocido"):
        project_log_record(unknown_enum, authorized=True)


@pytest.mark.req("REQ-PRIV-001")
def test_envelope_con_evidence_no_emite_tipo_de_carga_ni_datos() -> None:
    sentinel = "custody-envelope-sentinel"
    source = envelope_pb2.Envelope(
        sequence=4,
        evidence=evidence_pb2.Evidence(
            evidence_id=sentinel,
            custodian_pseudonym=sentinel,
            custody_signature=sentinel.encode(),
        ),
    )
    record = project_log_record(source, authorized=True)
    assert record["fields"] == {"sequence": 4}
    assert "payload_type" not in record["fields"]
    assert sentinel not in json.dumps(record)


@pytest.mark.req("REQ-PRIV-001")
def test_proyeccion_interna_omite_tipos_opacos_y_rechaza_homonimo_anidado() -> None:
    bytes_field = evidence_pb2.Evidence.DESCRIPTOR.fields_by_name["custody_signature"]
    text_field = alert_pb2.Alert.DESCRIPTOR.fields_by_name["summary"]
    assert log_projection._project_value(bytes_field, b"private-bytes") is log_projection._OMIT
    assert log_projection._project_value(text_field, "private-text") is log_projection._OMIT

    enum_without_descriptor = SimpleNamespace(
        message_type=None,
        type=FieldDescriptor.TYPE_ENUM,
        enum_type=None,
        full_name="homonym.enum",
    )
    with pytest.raises(ValueError, match="descriptor de enum ausente"):
        log_projection._project_value(enum_without_descriptor, 1)

    homonym = _dynamic_homonymous_alert()
    nested_message = SimpleNamespace(
        message_type=homonym.DESCRIPTOR,
        type=FieldDescriptor.TYPE_MESSAGE,
        full_name="trusted.root.untrusted_child",
    )
    with pytest.raises(ValueError, match="descriptor anidado no permitido"):
        log_projection._project_value(nested_message, homonym)

    default_scalar = detection_pb2.Detection()
    default_record = project_log_record(default_scalar, authorized=True)
    assert "detection_confidence" not in default_record["fields"]

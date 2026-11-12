"""Revisión de sensibilidad campo a campo para los contratos de la FASE 1."""

from __future__ import annotations

from typing import Any, cast

import pytest
from atalaya.sim.v1 import ground_truth_pb2
from atalaya.v1 import (
    detection_pb2,
    envelope_pb2,
    options_pb2,
    prediction_pb2,
)
from atalaya_contracts.sensitivity import undeclared_fields
from google.protobuf import descriptor_pb2

from scripts.contract_policy import FCSE_ONLY_PATHS
from scripts.proto_descriptors import project_file_descriptors
from scripts.sensitivity_table import rows


@pytest.mark.req("REQ-FUN-002")
def test_todos_los_campos_declarados_tienen_sensibilidad() -> None:
    assert undeclared_fields(project_file_descriptors()) == []


@pytest.mark.req("REQ-LEG-007")
def test_lista_cerrada_fcse_only_coincide_con_declaraciones() -> None:
    ext = cast(Any, options_pb2.sensitivity)
    actual: set[str] = set()
    for file_proto in project_file_descriptors():
        for message in file_proto.message_type:
            for field in message.field:
                if (
                    field.options.HasExtension(ext)
                    and field.options.Extensions[ext] == options_pb2.FCSE_ONLY
                ):
                    actual.add(f"{file_proto.package}.{message.name}.{field.name}")
    assert actual == set(FCSE_ONLY_PATHS)


@pytest.mark.req("REQ-LEG-007")
def test_campos_operator_y_pilot_son_fcse_only_en_el_descriptor() -> None:
    ext = cast(Any, options_pb2.sensitivity)
    violations: list[str] = []

    def visit(message: descriptor_pb2.DescriptorProto, prefix: str) -> None:
        for field in message.field:
            path = f"{prefix}.{field.name}"
            if field.name.startswith(("operator_", "pilot_")) and (
                not field.options.HasExtension(ext)
                or field.options.Extensions[ext] != options_pb2.FCSE_ONLY
            ):
                violations.append(path)
        for nested in message.nested_type:
            visit(nested, f"{prefix}.{nested.name}")

    for file_proto in project_file_descriptors():
        for message in file_proto.message_type:
            visit(message, f"{file_proto.package}.{message.name}")
    assert violations == []


@pytest.mark.req("REQ-PRIV-001")
def test_sensibilidad_heredada_no_reduce_fcse_only() -> None:
    effective = {row.path: row.effective for row in rows()}
    assert effective["atalaya.v1.Detection.remote_id.operator_id"] == "FCSE_ONLY"
    assert effective["atalaya.v1.Detection.remote_id.operator_location.latitude_deg"] == "FCSE_ONLY"
    assert effective["atalaya.v1.Prediction.origin_heatmap"] == "FCSE_ONLY"
    assert effective["atalaya.sim.v1.GroundTruth.launch_point.longitude_deg"] == "FCSE_ONLY"


@pytest.mark.req("REQ-FUN-002")
def test_oneofs_contienen_observaciones_y_payloads_previstos() -> None:
    assert {
        field.name
        for field in detection_pb2.Detection.DESCRIPTOR.oneofs_by_name["observation"].fields
    } == {
        "acoustic",
        "remote_id",
        "adsb",
        "rf_presence",
        "human",
    }
    assert {
        field.name for field in envelope_pb2.Envelope.DESCRIPTOR.oneofs_by_name["payload"].fields
    } == {
        "detection",
        "track",
        "prediction",
        "alert",
        "node_status",
        "coverage_status",
        "sighting",
        "evidence",
        "signature_class",
    }


@pytest.mark.req("REQ-LEG-008")
def test_estado_forged_solo_existe_en_ground_truth() -> None:
    occurrences = []
    for file_proto in project_file_descriptors():
        for message in file_proto.message_type:
            for field in message.field:
                if field.name == "is_forged":
                    occurrences.append((file_proto.package, message.name))
    assert occurrences == [(ground_truth_pb2.DESCRIPTOR.package, "GroundTruth")]


@pytest.mark.req("REQ-FUN-002")
def test_campos_required_primitivos_tienen_presencia_incluidos_anidados() -> None:
    required = cast(Any, options_pb2.required)
    scalar_types = {
        descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE,
        descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT,
        descriptor_pb2.FieldDescriptorProto.TYPE_INT64,
        descriptor_pb2.FieldDescriptorProto.TYPE_UINT64,
        descriptor_pb2.FieldDescriptorProto.TYPE_INT32,
        descriptor_pb2.FieldDescriptorProto.TYPE_FIXED64,
        descriptor_pb2.FieldDescriptorProto.TYPE_FIXED32,
        descriptor_pb2.FieldDescriptorProto.TYPE_BOOL,
        descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
        descriptor_pb2.FieldDescriptorProto.TYPE_BYTES,
        descriptor_pb2.FieldDescriptorProto.TYPE_UINT32,
        descriptor_pb2.FieldDescriptorProto.TYPE_ENUM,
        descriptor_pb2.FieldDescriptorProto.TYPE_SFIXED32,
        descriptor_pb2.FieldDescriptorProto.TYPE_SFIXED64,
        descriptor_pb2.FieldDescriptorProto.TYPE_SINT32,
        descriptor_pb2.FieldDescriptorProto.TYPE_SINT64,
    }
    missing: list[str] = []

    def visit(message: descriptor_pb2.DescriptorProto, prefix: str) -> None:
        for field in message.field:
            if (
                field.options.HasExtension(required)
                and field.options.Extensions[required]
                and field.type in scalar_types
                and field.label != descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
                and not field.proto3_optional
            ):
                missing.append(f"{prefix}.{field.name}")
        for nested in message.nested_type:
            visit(nested, f"{prefix}.{nested.name}")

    for file_proto in project_file_descriptors():
        for message in file_proto.message_type:
            visit(message, f"{file_proto.package}.{message.name}")
    assert missing == []


@pytest.mark.req("REQ-FUN-062")
def test_probabilidades_de_destino_estan_declaradas_obligatorias() -> None:
    field = prediction_pb2.Prediction.DESCRIPTOR.fields_by_name["destination_probabilities"]
    required = cast(Any, options_pb2.required)
    assert field.is_repeated
    assert field.GetOptions().Extensions[required]

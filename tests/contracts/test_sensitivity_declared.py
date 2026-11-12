"""Verifica que cada campo propio del descriptor declara sensibilidad explícita."""

from __future__ import annotations

from typing import Any, cast

import pytest
from atalaya.v1 import common_pb2, options_pb2
from atalaya_contracts.sensitivity import undeclared_fields
from google.protobuf import descriptor_pb2

# Todo el módulo verifica el contrato de esquemas con sensibilidad y presencia declaradas
# (REQ-FUN-002); los tests de sensibilidad son además la base de esquema de REQ-PRIV-001
# (sin sensibilidad declarada no se puede impedir que un campo FCSE_ONLY salga).
pytestmark = pytest.mark.req("REQ-FUN-002")


def descriptor_copy() -> descriptor_pb2.FileDescriptorProto:
    result = descriptor_pb2.FileDescriptorProto()
    common_pb2.DESCRIPTOR.CopyToProto(result)
    return result


def required_fields_without_presence(
    file_proto: descriptor_pb2.FileDescriptorProto,
) -> list[str]:
    required = cast(Any, options_pb2.required)
    missing: list[str] = []

    def visit(message: descriptor_pb2.DescriptorProto, prefix: str) -> None:
        for field in message.field:
            if (
                field.options.HasExtension(required)
                and field.options.Extensions[required]
                and not field.proto3_optional
            ):
                missing.append(f"{prefix}.{field.name}")
        for nested in message.nested_type:
            visit(nested, f"{prefix}.{nested.name}")

    for message in file_proto.message_type:
        visit(message, f"{file_proto.package}.{message.name}")
    return sorted(missing)


@pytest.mark.req("REQ-PRIV-001")
def test_todos_los_campos_common_declaran_sensibilidad() -> None:
    assert undeclared_fields([descriptor_copy()]) == []


def test_campos_required_tienen_presencia_proto3_explicita() -> None:
    file_proto = descriptor_copy()
    assert required_fields_without_presence(file_proto) == []


def test_campo_required_anidado_sin_presencia_se_detecta() -> None:
    file_proto = descriptor_copy()
    nested = file_proto.message_type[0].nested_type.add(name="Nested")
    field = nested.field.add(
        name="missing_presence",
        number=99,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE,
    )
    field.options.Extensions[cast(Any, options_pb2.required)] = True
    assert required_fields_without_presence(file_proto) == [
        "atalaya.v1.GeoPoint.Nested.missing_presence"
    ]


@pytest.mark.req("REQ-PRIV-001")
def test_campo_sin_opcion_se_informa_con_ruta_completa() -> None:
    file_proto = descriptor_copy()
    field = file_proto.message_type[0].field[0]
    field.options.ClearExtension(cast(Any, options_pb2.sensitivity))
    assert undeclared_fields([file_proto]) == ["atalaya.v1.GeoPoint.latitude_deg"]


@pytest.mark.req("REQ-PRIV-001")
def test_sensitivity_unspecified_se_considera_no_declarada() -> None:
    file_proto = descriptor_copy()
    field = file_proto.message_type[0].field[0]
    field.options.Extensions[cast(Any, options_pb2.sensitivity)] = (
        options_pb2.SENSITIVITY_UNSPECIFIED
    )
    assert undeclared_fields([file_proto]) == ["atalaya.v1.GeoPoint.latitude_deg"]


@pytest.mark.req("REQ-PRIV-001")
def test_campos_de_mensajes_anidados_tambien_se_recursan() -> None:
    file_proto = descriptor_copy()
    nested = file_proto.message_type[0].nested_type.add(name="Nested")
    nested.field.add(
        name="undeclared",
        number=99,
        label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
        type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
    )
    assert undeclared_fields([file_proto]) == ["atalaya.v1.GeoPoint.Nested.undeclared"]

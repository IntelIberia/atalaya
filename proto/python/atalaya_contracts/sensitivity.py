"""Comprobaciones de sensibilidad sobre descriptores Protobuf compilados."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast

from google.protobuf import descriptor_pb2


def undeclared_fields(
    file_descriptor_protos: Iterable[descriptor_pb2.FileDescriptorProto],
) -> list[str]:
    """Devuelve rutas de FileDescriptorProto sin sensibilidad o con el valor UNSPECIFIED."""
    from atalaya.v1.options_pb2 import SENSITIVITY_UNSPECIFIED, sensitivity

    extension = cast(Any, sensitivity)

    problems: list[str] = []

    def visit(message: descriptor_pb2.DescriptorProto, prefix: str) -> None:
        for field in message.field:
            field_path = f"{prefix}.{field.name}"
            options = field.options
            if not options.HasExtension(extension) or (
                options.Extensions[extension] == SENSITIVITY_UNSPECIFIED
            ):
                problems.append(field_path)
        for nested in message.nested_type:
            visit(nested, f"{prefix}.{nested.name}")

    for file_descriptor in file_descriptor_protos:
        if file_descriptor.package not in {"atalaya.v1", "atalaya.sim.v1"}:
            continue
        for message in file_descriptor.message_type:
            visit(message, f"{file_descriptor.package}.{message.name}")
    return sorted(problems)

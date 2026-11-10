#!/usr/bin/env python3
"""Genera y comprueba la sensibilidad declarada y efectiva de los contratos."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any, cast

from google.protobuf import descriptor_pb2

from scripts.contract_policy import FCSE_ONLY_PATHS
from scripts.proto_descriptors import ROOT, project_file_descriptors

GENERATED = str(ROOT / "proto" / "gen" / "python")
if GENERATED not in sys.path:
    sys.path.insert(0, GENERATED)

OUTPUT = ROOT / "docs" / "contracts" / "SENSIBILIDAD.md"


@dataclass(frozen=True)
class FieldRow:
    path: str
    type_name: str
    declared: str
    effective: str
    required: bool


def rows() -> list[FieldRow]:
    from atalaya.v1.options_pb2 import FCSE_ONLY, OPERATOR, PUBLIC, required, sensitivity

    levels = {PUBLIC: (0, "PUBLIC"), OPERATOR: (1, "OPERATOR"), FCSE_ONLY: (2, "FCSE_ONLY")}
    sensitivity_ext = cast(Any, sensitivity)
    required_ext = cast(Any, required)
    files = project_file_descriptors()
    messages: dict[str, descriptor_pb2.DescriptorProto] = {}

    def register(package: str, message: descriptor_pb2.DescriptorProto, prefix: str = "") -> None:
        name = f"{prefix}.{message.name}" if prefix else f"{package}.{message.name}"
        messages[name] = message
        for nested in message.nested_type:
            register(package, nested, name)

    for file_proto in files:
        for message in file_proto.message_type:
            register(file_proto.package, message)

    result: list[FieldRow] = []

    def visit(
        message: descriptor_pb2.DescriptorProto,
        prefix: str,
        inherited_level: int,
        active: frozenset[str],
    ) -> None:
        for field in message.field:
            path = f"{prefix}.{field.name}"
            options = field.options
            if not options.HasExtension(sensitivity_ext):
                raise ValueError(f"sin sensibilidad: {path}")
            value = options.Extensions[sensitivity_ext]
            if value not in levels:
                raise ValueError(f"sensibilidad UNSPECIFIED: {path}")
            declared_level, declared_name = levels[value]
            effective_level = max(inherited_level, declared_level)
            type_name = field.type_name.lstrip(
                "."
            ) or descriptor_pb2.FieldDescriptorProto.Type.Name(field.type)
            effective_name = next(
                name for level, name in levels.values() if level == effective_level
            )
            result.append(
                FieldRow(
                    path,
                    type_name,
                    declared_name,
                    effective_name,
                    bool(options.HasExtension(required_ext) and options.Extensions[required_ext]),
                )
            )
            target = field.type_name.lstrip(".")
            child = messages.get(target)
            if child is not None and target not in active:
                visit(child, path, effective_level, active | {target})

    for file_proto in files:
        for message in file_proto.message_type:
            full_name = f"{file_proto.package}.{message.name}"
            visit(message, full_name, 0, frozenset({full_name}))
    return sorted(result, key=lambda row: row.path)


def declared_fcse_paths() -> set[str]:
    from atalaya.v1.options_pb2 import FCSE_ONLY, sensitivity

    extension = cast(Any, sensitivity)
    result: set[str] = set()

    def visit(message: descriptor_pb2.DescriptorProto, prefix: str) -> None:
        for field in message.field:
            if (
                field.options.HasExtension(extension)
                and field.options.Extensions[extension] == FCSE_ONLY
            ):
                result.add(f"{prefix}.{field.name}")
        for nested in message.nested_type:
            visit(nested, f"{prefix}.{nested.name}")

    for file_proto in project_file_descriptors():
        for message in file_proto.message_type:
            visit(message, f"{file_proto.package}.{message.name}")
    return result


def render_table(field_rows: list[FieldRow] | None = None) -> str:
    data = rows() if field_rows is None else field_rows
    declared_fcse = declared_fcse_paths()
    if declared_fcse != FCSE_ONLY_PATHS:
        missing = sorted(FCSE_ONLY_PATHS - declared_fcse)
        extra = sorted(declared_fcse - FCSE_ONLY_PATHS)
        raise ValueError(f"rutas FCSE_ONLY incoherentes; faltan={missing}, sobran={extra}")
    lines = [
        "# Sensibilidad de los contratos Protobuf",
        "",
        "Generado desde los `FileDescriptorProto` compilados. La sensibilidad efectiva hereda el ",
        "nivel más restrictivo de los contenedores. `required` declara la regla de presencia o ",
        "cardinalidad;",
        "los campos `repeated` necesitan validación de cardinalidad en `validate()` (T1.4).",
        "",
        "| Ruta | Tipo | Declarada | Efectiva | Obligatorio |",
        "|---|---|---|---|---|",
    ]
    for row in data:
        required_name = "sí" if row.required else "no"
        lines.append(
            f"| `{row.path}` | `{row.type_name}` | {row.declared} | "
            f"{row.effective} | {required_name} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Genera tabla de sensibilidad Protobuf")
    parser.add_argument("--check", action="store_true", help="falla si el documento no está al día")
    args = parser.parse_args(argv)
    try:
        generated = render_table()
    except (ImportError, ValueError) as exc:
        print(f"sensibilidad: {exc}", file=sys.stderr)
        return 1
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != generated:
            print(f"sensibilidad: {OUTPUT.relative_to(ROOT)} desactualizada", file=sys.stderr)
            return 1
        print("sensibilidad: OK")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(generated, encoding="utf-8")
    print(f"sensibilidad: escrita {OUTPUT.relative_to(ROOT)} ({len(rows())} filas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

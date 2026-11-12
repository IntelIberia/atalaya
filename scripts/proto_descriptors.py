"""Carga FileDescriptorProto de los schemas propios ya generados."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from google.protobuf import descriptor_pb2

ROOT = Path(__file__).resolve().parents[1]


def project_file_descriptors() -> list[descriptor_pb2.FileDescriptorProto]:
    """Devuelve descriptores propios, incluidos los paquetes de simulación."""
    generated = str(ROOT / "proto" / "gen" / "python")
    if generated not in sys.path:
        sys.path.insert(0, generated)
    sources = sorted((ROOT / "proto" / "atalaya").rglob("*.proto"))
    result = []
    for source in sources:
        package_path = source.relative_to(ROOT / "proto").with_suffix("")
        module_name = ".".join((*package_path.parts[:-1], f"{package_path.stem}_pb2"))
        module = importlib.import_module(module_name)
        descriptor = descriptor_pb2.FileDescriptorProto()
        module.DESCRIPTOR.CopyToProto(descriptor)
        result.append(descriptor)
    return result

"""Comprueba que los bindings versionados corresponden a los .proto actuales."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts import proto_codegen
from scripts.proto_codegen import (
    DEFAULT_OUTPUT,
    binding_differences,
    binding_manifest,
    generate,
)


@pytest.mark.req("REQ-FUN-002", "REQ-NFR-014")
def test_bindings_generados_no_derivan(tmp_path: Path) -> None:
    generated = tmp_path / "python"
    assert generate(generated) == 0
    assert binding_differences(generated, DEFAULT_OUTPUT) == []


@pytest.mark.req("REQ-FUN-002", "REQ-NFR-014")
def test_cambio_temporal_en_proto_detecta_deriva_sin_regenerar_versionados(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proto_root = tmp_path / "proto"
    shutil.copytree(proto_codegen.PROTO_ROOT, proto_root, ignore=shutil.ignore_patterns("gen"))
    common = proto_root / "atalaya/v1/common.proto"
    source = common.read_text(encoding="utf-8")
    original_field = "  optional double altitude_m = 3 [(atalaya.v1.sensitivity) = PUBLIC];\n"
    assert source.count(original_field) == 1
    common.write_text(
        source.replace(
            original_field,
            original_field
            + "  optional string drift_probe = 4 [(atalaya.v1.sensitivity) = PUBLIC];\n",
        ),
        encoding="utf-8",
    )
    generated = tmp_path / "generated"
    versioned_before = binding_manifest(DEFAULT_OUTPUT)
    monkeypatch.setattr(proto_codegen, "PROTO_ROOT", proto_root)

    assert generate(generated) == 0
    differences = binding_differences(generated, DEFAULT_OUTPUT)

    assert "difiere: atalaya/v1/common_pb2.py" in differences
    assert "difiere: atalaya/v1/common_pb2.pyi" in differences
    assert binding_manifest(DEFAULT_OUTPUT) == versioned_before


@pytest.mark.req("REQ-FUN-002")
def test_deriva_detecta_binding_ausente(tmp_path: Path) -> None:
    generated = tmp_path / "generated"
    versioned = tmp_path / "versioned"
    generated.mkdir()
    versioned.mkdir()
    (versioned / "example_pb2.py").write_text("binding\n", encoding="utf-8")

    assert binding_differences(generated, versioned) == ["falta: example_pb2.py"]


@pytest.mark.req("REQ-FUN-002")
def test_deriva_detecta_bytes_distintos(tmp_path: Path) -> None:
    generated = tmp_path / "generated"
    versioned = tmp_path / "versioned"
    generated.mkdir()
    versioned.mkdir()
    (generated / "example_pb2.pyi").write_text("nuevo\n", encoding="utf-8")
    (versioned / "example_pb2.pyi").write_text("viejo\n", encoding="utf-8")

    assert binding_differences(generated, versioned) == ["difiere: example_pb2.pyi"]


@pytest.mark.req("REQ-FUN-002")
def test_deriva_detecta_binding_extra_y_ignora_pycache(tmp_path: Path) -> None:
    generated = tmp_path / "generated"
    versioned = tmp_path / "versioned"
    generated.mkdir()
    versioned.mkdir()
    (generated / "obsolete_pb2.py").write_text("extra\n", encoding="utf-8")
    pycache = generated / "__pycache__"
    pycache.mkdir()
    (pycache / "obsolete_pb2.cpython-312.pyc").write_bytes(b"cache")

    assert binding_differences(generated, versioned) == ["sobra: obsolete_pb2.py"]


@pytest.mark.req("REQ-FUN-002", "REQ-NFR-014")
def test_generate_es_repetible_y_elimina_bindings_obsoletos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proto_root = tmp_path / "proto"
    source = proto_root / "demo" / "current.proto"
    source.parent.mkdir(parents=True)
    source.write_text(
        'syntax = "proto3"; package demo; message Example { string value = 1; }\n',
        encoding="utf-8",
    )
    output = tmp_path / "generated"
    stale = output / "demo" / "removed_pb2.py"
    stale.parent.mkdir(parents=True)
    stale.write_text("obsolete\n", encoding="utf-8")
    (stale.parent / "removed_pb2.pyi").write_text("obsolete\n", encoding="utf-8")
    monkeypatch.setattr(proto_codegen, "PROTO_ROOT", proto_root)

    assert generate(output) == 0
    first_generation = binding_manifest(output)
    assert not stale.exists()
    assert not (stale.parent / "removed_pb2.pyi").exists()
    assert Path("demo/current_pb2.py") in first_generation
    assert generate(output) == 0
    assert binding_manifest(output) == first_generation

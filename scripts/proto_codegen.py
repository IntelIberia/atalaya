#!/usr/bin/env python3
"""Genera los bindings Python de los contratos Protobuf propios de Atalaya."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import cast

import grpc_tools  # type: ignore[import-untyped]
from grpc_tools import protoc

ROOT = Path(__file__).resolve().parents[1]
PROTO_ROOT = ROOT / "proto"
DEFAULT_OUTPUT = ROOT / "proto" / "gen" / "python"


def binding_manifest(root: Path) -> dict[Path, bytes]:
    """Carga rutas y bytes de bindings Python, omitiendo cachés de intérprete."""
    return {
        path.relative_to(root): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.suffix in {".py", ".pyi"}
        and "__pycache__" not in path.relative_to(root).parts
    }


def binding_differences(generated: Path, versioned: Path) -> list[str]:
    """Describe bindings ausentes, extra o con bytes distintos entre dos árboles."""
    actual = binding_manifest(generated)
    expected = binding_manifest(versioned)
    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    differing = sorted(
        path for path in actual.keys() & expected.keys() if actual[path] != expected[path]
    )
    return [
        *(f"falta: {path.as_posix()}" for path in missing),
        *(f"sobra: {path.as_posix()}" for path in extra),
        *(f"difiere: {path.as_posix()}" for path in differing),
    ]


def generate(output: Path = DEFAULT_OUTPUT) -> int:
    """Genera .py y .pyi y elimina bindings obsoletos si protoc termina bien."""
    standard = Path(next(iter(grpc_tools.__path__))) / "_proto"
    files = sorted(path.relative_to(PROTO_ROOT).as_posix() for path in PROTO_ROOT.rglob("*.proto"))
    if not files:
        raise ValueError(f"no hay archivos .proto en {PROTO_ROOT}")
    output.mkdir(parents=True, exist_ok=True)
    result = cast(
        int,
        protoc.main(
            [
                "grpc_tools.protoc",
                f"--proto_path={PROTO_ROOT}",
                f"--proto_path={standard}",
                f"--python_out={output}",
                f"--pyi_out={output}",
                *files,
            ]
        ),
    )
    if result != 0:
        return result

    expected = {
        (Path(proto).with_name(f"{Path(proto).stem}_pb2{suffix}"))
        for proto in files
        for suffix in (".py", ".pyi")
    }
    for path in sorted(output.rglob("*")):
        if (
            path.is_file()
            and path.name.endswith(("_pb2.py", "_pb2.pyi"))
            and path.relative_to(output) not in expected
        ):
            path.unlink()
    for directory in sorted(output.rglob("*"), reverse=True):
        if directory.is_dir() and directory != output and not any(directory.iterdir()):
            directory.rmdir()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Genera bindings Protobuf Python")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = generate(args.out.resolve())
    if result:
        print(f"protoc: fallo con código {result}", file=sys.stderr)
    return result


if __name__ == "__main__":
    raise SystemExit(main())

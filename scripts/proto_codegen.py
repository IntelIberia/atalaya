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


def generate(output: Path = DEFAULT_OUTPUT) -> int:
    """Genera .py y .pyi sin shell; devuelve el estado de grpc_tools.protoc."""
    standard = Path(next(iter(grpc_tools.__path__))) / "_proto"
    files = sorted(path.relative_to(PROTO_ROOT).as_posix() for path in PROTO_ROOT.rglob("*.proto"))
    if not files:
        raise ValueError(f"no hay archivos .proto en {PROTO_ROOT}")
    output.mkdir(parents=True, exist_ok=True)
    return cast(
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

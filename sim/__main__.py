"""CLI del simulador (T1.10): `python -m sim run|hash`.

- `run --scenario X.yaml [--seed N] [--duration S] --out F.pb.zst`: ejecuta el escenario y escribe
  el flujo comprimido; imprime `stream_sha256=…` (flujo sin comprimir) y `file_sha256=…`.
- `hash F.pb.zst`: recalcula y muestra los mismos dos hashes.

Códigos de salida: 0 correcto, 2 entrada inválida (escenario, semilla, duración o fichero).
La salida MQTT (`--mqtt`) y el replay llegan en T1.15–T1.16.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
for _extra in (_REPO / "proto" / "gen" / "python", _REPO / "proto" / "python"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from sim.engine import build_engine, compress_stream, decompress_stream, encode_stream  # noqa: E402
from sim.rng import check_seed  # noqa: E402
from sim.scenario import ScenarioError, load_scenario  # noqa: E402


def _hashes(stream: bytes, data: bytes) -> str:
    return (
        f"stream_sha256={hashlib.sha256(stream).hexdigest()}\n"
        f"file_sha256={hashlib.sha256(data).hexdigest()}\n"
    )


def _run(args: argparse.Namespace) -> str:
    seed = None if args.seed is None else check_seed(args.seed)
    engine = build_engine(load_scenario(args.scenario), seed=seed, duration_s=args.duration)
    stream = encode_stream(engine.run_all())
    data = compress_stream(stream)
    args.out.write_bytes(data)
    return _hashes(stream, data)


def _hash(args: argparse.Namespace) -> str:
    try:
        data = args.file.read_bytes()
    except OSError as exc:
        raise ValueError(f"no se puede leer {args.file}: {exc.strerror}") from exc
    try:
        stream = decompress_stream(data)
    except Exception as exc:  # zstandard.ZstdError no hereda de ValueError
        raise ValueError(f"{args.file} no es un flujo zstd válido: {exc}") from exc
    return _hashes(stream, data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sim", description="Simulador de Atalaya")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="ejecuta un escenario y escribe el .pb.zst")
    run.add_argument("--scenario", type=Path, required=True)
    run.add_argument("--seed", type=int, default=None)
    run.add_argument("--duration", type=float, default=None, help="segundos simulados")
    run.add_argument("--out", type=Path, required=True)
    run.set_defaults(handler=_run)
    hash_cmd = commands.add_parser("hash", help="SHA-256 del flujo y del fichero")
    hash_cmd.add_argument("file", type=Path)
    hash_cmd.set_defaults(handler=_hash)
    args = parser.parse_args(argv)
    try:
        sys.stdout.write(args.handler(args))
    except (ScenarioError, ValueError) as exc:
        print(f"sim: error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

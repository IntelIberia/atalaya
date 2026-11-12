"""CLI del simulador (T1.10, T1.15): `python -m sim run|hash|replay`.

- `run --scenario X.yaml [--seed N] [--duration S] --out F.pb.zst`: ejecuta el escenario con todos
  los sensores simulados y escribe el replay versionado (`atalaya_contracts.envelope_io`); imprime
  `stream_sha256=…` (flujo de `Envelope` sin comprimir) y `file_sha256=…`.
- `hash F.pb.zst`: lee y comprueba el replay y muestra los mismos dos hashes.
- `replay --in F.pb.zst`: lee y comprueba el replay y resume su contenido (número de `Envelope`
  y de registros de verdad terreno, hash del contenido).

Códigos de salida: 0 correcto, 2 entrada inválida (escenario, semilla, duración o fichero, incluido
un replay truncado, alterado o de versión desconocida). La salida MQTT (`--mqtt`) llega en T1.16.
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

from sim import replay  # noqa: E402
from sim.rng import check_seed  # noqa: E402
from sim.scenario import ScenarioError  # noqa: E402


def _hashes(recording: replay.Recording, data: bytes) -> str:
    return (
        f"stream_sha256={replay.stream_sha256(recording)}\n"
        f"file_sha256={hashlib.sha256(data).hexdigest()}\n"
    )


def _run(args: argparse.Namespace) -> str:
    seed = None if args.seed is None else check_seed(args.seed)
    recording = replay.record(args.scenario, seed=seed, duration_s=args.duration)
    data = replay.write(args.out, recording)
    return _hashes(recording, data)


def _read(path: Path) -> tuple[replay.Recording, bytes]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"no se puede leer {path}: {exc.strerror}") from exc
    return replay.decode(data), data


def _hash(args: argparse.Namespace) -> str:
    recording, data = _read(args.file)
    return _hashes(recording, data)


def _replay(args: argparse.Namespace) -> str:
    recording, data = _read(args.input)
    return (
        f"envelopes={len(recording.envelopes)}\n"
        f"ground_truth={len(recording.ground_truth)}\n" + _hashes(recording, data)
    )


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
    replay_cmd = commands.add_parser("replay", help="lee y comprueba un replay .pb.zst")
    replay_cmd.add_argument("--in", dest="input", type=Path, required=True)
    replay_cmd.set_defaults(handler=_replay)
    args = parser.parse_args(argv)
    try:
        sys.stdout.write(args.handler(args))
    except (ScenarioError, ValueError) as exc:
        print(f"sim: error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

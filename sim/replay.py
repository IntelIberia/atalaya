"""Grabación y replay de escenarios (T1.15, REQ-FUN-006, REQ-FUN-003).

`record()` ejecuta un escenario con todos los sensores simulados (latido `NodeStatus`, acústica,
Remote ID y ADS-B) y devuelve los `Envelope` emitidos y la verdad terreno, en orden. `write()` y
`read()` usan el formato versionado de `atalaya_contracts.envelope_io` (cabecera con versión y
hash del contenido, zstd de nivel fijo). Leer un replay devuelve exactamente lo grabado.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from atalaya.sim.v1.ground_truth_pb2 import GroundTruth
from atalaya.v1.envelope_pb2 import Envelope
from atalaya_contracts import envelope_io

from sim.engine import build_engine, encode_stream
from sim.scenario import load_scenario
from sim.sensors import acoustic, adsb, remote_id


@dataclass(frozen=True)
class Recording:
    envelopes: list[Envelope]
    ground_truth: list[GroundTruth]


def record(
    scenario_path: Path, *, seed: int | None = None, duration_s: float | None = None
) -> Recording:
    scenario = load_scenario(scenario_path)
    components = [
        *acoustic.acoustic_components(scenario),
        *remote_id.remote_id_components(scenario),
        *adsb.adsb_components(scenario),
    ]
    engine = build_engine(scenario, seed=seed, duration_s=duration_s, extra_components=components)
    return Recording(list(engine.run_all()), list(engine.ground_truth))


def encode(recording: Recording) -> bytes:
    return envelope_io.encode(recording.envelopes, recording.ground_truth)


def write(path: Path, recording: Recording) -> bytes:
    return envelope_io.write(path, recording.envelopes, recording.ground_truth)


def decode(data: bytes) -> Recording:
    """Replay completo o `ReplayFormatError` (subclase de `ValueError`) con el desplazamiento."""
    loaded = envelope_io.decode(data)
    return Recording(loaded.envelopes, loaded.ground_truth)


def read(path: Path) -> Recording:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"no se puede leer {path}: {exc.strerror}") from exc
    return decode(data)


def stream_sha256(recording: Recording) -> str:
    """SHA-256 del flujo de `Envelope` sin comprimir (el mismo de T1.10)."""
    return hashlib.sha256(encode_stream(recording.envelopes)).hexdigest()

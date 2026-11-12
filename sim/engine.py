"""Motor de eventos discretos del simulador (T1.10, REQ-FUN-003).

- Cola de eventos ordenada por `(tiempo_ns, secuencia_de_inserción)`: los empates se resuelven
  por orden de programación, nunca por identidad de objetos ni `hash()`.
- Tiempo entero en nanosegundos (`sim.clock`); azar solo mediante `Engine.rng(componente)`
  (`sim.rng`); salidas físicas redondeadas a resolución fija antes de serializar.
- Cada `Envelope` emitido lleva una secuencia global consecutiva y se serializa con
  `SerializeToString(deterministic=True)`.

El flujo sin comprimir es una sucesión de `Envelope` precedidos por su longitud en varint
(delimitado como `writeDelimitedTo`); el `.pb.zst` es ese flujo comprimido con zstd de nivel fijo.
El formato de replay con cabecera de versión y hash llega en T1.15.

El emisor propio es el latido `NodeStatus` de cada nodo cada 30 s simulados (tiempo y batería
sintéticos). Desde T1.13 respeta los fallos programados (`sim.faults`): un nodo caído no publica,
el PPS perdido se refleja en `TimeQuality` y en la salud, y la deriva sin PPS desplaza el reloj.
La red (latencia, pérdidas, duplicados, desorden) se aplica después con `sim.network`.
"""

from __future__ import annotations

import heapq
import math
from collections.abc import Callable, Iterable, Sequence
from random import Random
from typing import Any

import zstandard
from atalaya.sim.v1.ground_truth_pb2 import GroundTruth
from atalaya.v1.envelope_pb2 import Envelope
from atalaya.v1.node_status_pb2 import NODE_HEALTH_DEGRADED, NODE_HEALTH_HEALTHY, NodeStatus
from google.protobuf.message import Message

from sim import clock, geo
from sim.faults import FaultSchedule
from sim.rng import RngRegistry, check_seed
from sim.scenario import Scenario

Action = Callable[["Engine"], None]
Component = Callable[["Engine"], None]

ZSTD_LEVEL = 10
NODE_STATUS_PERIOD_S = 30.0
SOFTWARE_VERSION = "sim-t1.10"
DEGREE_STEP = 1e-7  # ~1 cm
METRE_STEP = 1e-3
MS_STEP = 1e-6
PERCENT_STEP = 1e-2
BATTERY_DRAIN_PCT_PER_S = 0.5 / 3600

_PAYLOAD_FIELDS = {
    field.message_type.full_name: field.name
    for field in Envelope.DESCRIPTOR.oneofs_by_name["payload"].fields
    if field.message_type is not None
}


def quantize(value: float, step: float) -> float:
    """Redondea a un múltiplo de `step` (no depende del último bit de `libm`)."""
    return round(value / step) * step


class Engine:
    """Cola de eventos determinista con registro de subsemillas y salida de `Envelope`."""

    def __init__(self, seed: int, end_ns: int | None = None) -> None:
        self.seed = check_seed(seed)
        self.end_ns = end_ns
        self.now_ns = 0
        self.envelopes: list[Envelope] = []
        # Verdad del simulador (`atalaya.sim.v1`): solo para métricas; nunca viaja en `Envelope`.
        self.ground_truth: list[GroundTruth] = []
        self._rngs = RngRegistry(seed)
        self._queue: list[tuple[int, int, Action]] = []
        self._order = 0

    def rng(self, component: str) -> Random:
        """Generador propio del componente (subsemilla `sha256(semilla, componente)`)."""
        return self._rngs.get(component)

    def schedule(self, at_ns: int, action: Action) -> None:
        if isinstance(at_ns, bool) or not isinstance(at_ns, int) or at_ns < 0:
            raise ValueError(f"tiempo de evento inválido: {at_ns!r} (entero de ns ≥ 0)")
        if at_ns < self.now_ns:
            raise ValueError(f"evento en el pasado: {at_ns} < {self.now_ns}")
        heapq.heappush(self._queue, (at_ns, self._order, action))
        self._order += 1

    def emit(self, site_id: str, node_id: str, payload: Message) -> Envelope:
        """Envuelve `payload` con la secuencia global y el instante simulado actual."""
        envelope = Envelope(
            site_id=site_id,
            node_id=node_id,
            sequence=len(self.envelopes),
            emitted_at=clock.to_timestamp(self.now_ns),
        )
        getattr(envelope, _PAYLOAD_FIELDS[payload.DESCRIPTOR.full_name]).CopyFrom(payload)
        self.envelopes.append(envelope)
        return envelope

    def record_truth(self, truth: GroundTruth) -> None:
        """Registra la verdad terreno del instante actual, aparte del flujo de la plataforma."""
        self.ground_truth.append(truth)

    def run(self, until_ns: int) -> list[Envelope]:
        """Ejecuta los eventos con instante ≤ `until_ns` en orden `(tiempo, secuencia)`."""
        while self._queue and self._queue[0][0] <= until_ns:
            at_ns, _, action = heapq.heappop(self._queue)
            self.now_ns = at_ns
            action(self)
        return self.envelopes

    def run_all(self) -> list[Envelope]:
        if self.end_ns is None:
            raise ValueError("el motor no tiene duración: usa run(until_ns)")
        return self.run(self.end_ns)


def _nodes(scenario: Scenario) -> list[dict[str, Any]]:
    return [
        f["properties"] for f in scenario.geometry["features"] if f["properties"]["role"] == "node"
    ]


def node_status_component(
    site: dict[str, Any], node: dict[str, Any], schedule: FaultSchedule | None = None
) -> Component:
    """Latido `NodeStatus` periódico de un nodo, con fase, reloj y batería sintéticos."""
    node_id = node["id"]
    offset = node["offset_m"]
    center = site["center"]
    lat, lon, alt = geo.enu_to_geodetic(
        offset["east_m"],
        offset["north_m"],
        offset["up_m"],
        center["lat_deg"],
        center["lon_deg"],
        0.0,
    )
    location = (quantize(lat, DEGREE_STEP), quantize(lon, DEGREE_STEP), quantize(alt, METRE_STEP))
    pps = bool(node["pps"])
    period_ns = clock.seconds_to_ns(NODE_STATUS_PERIOD_S)
    faults = schedule or FaultSchedule([])

    def setup(engine: Engine) -> None:
        phase = engine.rng(f"fase/{node_id}")
        clock_rng = engine.rng(f"reloj/{node_id}")
        start_ns = clock.seconds_to_ns(quantize(phase.uniform(0.0, NODE_STATUS_PERIOD_S), 1e-3))
        battery0 = 100.0 - phase.uniform(0.0, 20.0)

        def beat(e: Engine) -> None:
            elapsed_s = e.now_ns / clock.NS_PER_S
            e.schedule(e.now_ns + period_ns, beat)
            if faults.is_down(node_id, elapsed_s):
                return
            pps_now = faults.pps_valid(node_id, elapsed_s, pps)
            sigma_ms = clock.clock_sigma_ms(pps_now)
            offset_ms = clock_rng.gauss(0.0, sigma_ms) + faults.drift_offset_ms(
                node_id, elapsed_s, pps_now
            )
            status = NodeStatus(
                site_id=site["id"],
                node_id=node_id,
                observed_at=clock.to_timestamp(e.now_ns),
                health=NODE_HEALTH_HEALTHY if pps_now == pps else NODE_HEALTH_DEGRADED,
                battery_percent=quantize(
                    max(0.0, battery0 - BATTERY_DRAIN_PCT_PER_S * elapsed_s), PERCENT_STEP
                ),
                software_version=SOFTWARE_VERSION,
            )
            status.location.latitude_deg, status.location.longitude_deg = location[:2]
            status.location.altitude_m = location[2]
            status.time_quality.pps_valid = pps_now
            status.time_quality.clock_offset_ms = quantize(offset_ms, MS_STEP)
            status.time_quality.uncertainty_ms = quantize(3 * sigma_ms, MS_STEP)
            e.emit(site["id"], node_id, status)

        engine.schedule(start_ns, beat)

    return setup


def build_engine(
    scenario: Scenario,
    *,
    seed: int | None,
    duration_s: float | None = None,
    extra_components: Sequence[Component] = (),
) -> Engine:
    """Motor listo para ejecutar el escenario; sin semilla usa `seed_policy.default_seed`."""
    if seed is None:
        seed = int(scenario.data["seed_policy"]["default_seed"])
    if duration_s is None:
        duration_s = float(scenario.data["duration_s"])
    if not math.isfinite(duration_s) or duration_s <= 0:
        raise ValueError(f"duración inválida: {duration_s!r} (segundos finitos > 0)")
    engine = Engine(seed, end_ns=clock.seconds_to_ns(duration_s))
    sites = {site["id"]: site for site in scenario.data["sites"]}
    schedule = FaultSchedule(scenario.data["faults"])
    components: list[Component] = [
        node_status_component(sites[node["site"]], node, schedule) for node in _nodes(scenario)
    ]
    components.extend(extra_components)
    for component in components:
        component(engine)
    return engine


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def encode_stream(envelopes: Iterable[Envelope]) -> bytes:
    """Flujo sin comprimir: `varint(longitud) ‖ Envelope` con serialización determinista."""
    parts: list[bytes] = []
    for envelope in envelopes:
        data = envelope.SerializeToString(deterministic=True)
        parts.append(_varint(len(data)))
        parts.append(data)
    return b"".join(parts)


def compress_stream(stream: bytes) -> bytes:
    """`.pb.zst`: zstd de nivel fijo, con suma de comprobación, sin hilos."""
    return zstandard.ZstdCompressor(level=ZSTD_LEVEL, write_checksum=True).compress(stream)


def decompress_stream(data: bytes) -> bytes:
    return zstandard.ZstdDecompressor().decompress(data)

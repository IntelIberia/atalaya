"""ADS-B simulado como datos ya recibidos y decodificados (T1.14, REQ-FUN-004).

Aeronaves tripuladas C8 (confusores) con identificadores **sintéticos** `SIM…`: nunca matrículas
ni indicativos reales. Solo mensajes Protobuf en memoria (`Detection.adsb`); sin radio ni
transmisión. Ruido de posición y alcance por defecto **NO VERIFICADO** (órdenes de magnitud).
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from random import Random
from typing import Any

from atalaya.sim.v1.ground_truth_pb2 import GroundTruth
from atalaya.v1.common_pb2 import ClassScore
from atalaya.v1.detection_pb2 import SENSOR_TYPE_ADSB, Detection

from sim import clock
from sim.engine import Component, Engine
from sim.faults import FaultSchedule
from sim.scenario import Scenario
from sim.sensors.common import (
    Vec3,
    add,
    check_positive,
    geopoint,
    isotropic_covariance,
    time_quality,
    to_frame,
    truncated_noise,
)
from sim.sensors.remote_id import receivers
from sim.trajectory import Trajectory, Waypoint

ADSB_PERIOD_S = 1.0
SYNTHETIC_CALLSIGN = re.compile(r"SIM[0-9A-Z]{2,5}")  # igual que el esquema de escenario
MANNED_CLASS = "C8"
ADSB_C8_SCORE = 0.99  # NO VERIFICADO
ADSB_CONFIDENCE = 0.99  # NO VERIFICADO


def check_callsign(callsign: object) -> str:
    """Devuelve el identificador si es sintético (`SIM` + 2-5 alfanuméricos en mayúscula)."""
    if not isinstance(callsign, str) or SYNTHETIC_CALLSIGN.fullmatch(callsign) is None:
        raise ValueError(
            f"identificador ADS-B no sintético: {callsign!r} (patrón SIM[0-9A-Z]{{2,5}})"
        )
    return callsign


@dataclass(frozen=True)
class AdsbModel:
    """Ruido de la posición declarada y alcance del receptor (NO VERIFICADO)."""

    position_sigma_m: float = 10.0
    sigma_clip: float = 4.0
    range_m: float = 60_000.0

    def __post_init__(self) -> None:
        check_positive(self.position_sigma_m, "position_sigma_m")
        check_positive(self.sigma_clip, "sigma_clip")
        check_positive(self.range_m, "range_m")

    @property
    def max_error_m(self) -> float:
        return math.sqrt(3.0) * self.sigma_clip * self.position_sigma_m


def build_detection(
    *,
    callsign: str,
    declared: Vec3,
    center: Mapping[str, float],
    site_id: str,
    node_id: str,
    now_ns: int,
    pps: bool,
    model: AdsbModel,
    rng: Random,
    clock_rng: Random,
    drift_offset_ms: float = 0.0,
) -> Detection:
    """`Detection` ADS-B decodificada, con su incertidumbre (REQ-FUN-062)."""
    check_callsign(callsign)
    position = geopoint(declared, center)
    covariance = isotropic_covariance(model.position_sigma_m)
    det = Detection(
        detection_id=f"{node_id}-adsb-{rng.getrandbits(64):016x}",
        site_id=site_id,
        node_id=node_id,
        observed_at=clock.to_timestamp(now_ns),
        sensor_type=SENSOR_TYPE_ADSB,
        time_quality=time_quality(pps, clock_rng, drift_offset_ms),
        position=position,
        position_covariance=covariance,
        detection_confidence=ADSB_CONFIDENCE,
    )
    det.class_scores.append(ClassScore(class_id=MANNED_CLASS, probability=ADSB_C8_SCORE))
    det.adsb.callsign = callsign
    det.adsb.aircraft_position.CopyFrom(position)
    det.adsb.position_covariance.CopyFrom(covariance)
    det.adsb.message_time.CopyFrom(clock.to_timestamp(now_ns))
    return det


@dataclass(frozen=True)
class _Aircraft:
    callsign: str
    class_id: str
    site_id: str
    start_s: float
    trajectory: Trajectory


def adsb_components(
    scenario: Scenario,
    model: AdsbModel | None = None,
    period_s: float = ADSB_PERIOD_S,
) -> list[Component]:
    """Un componente por aeronave tripulada: verdad terreno y datos ADS-B a los receptores."""
    adsb_model = model or AdsbModel()
    check_positive(period_s, "periodo")
    aircraft: list[_Aircraft] = []
    for item in scenario.data["manned_aircraft"]:
        route = [Waypoint(p["east_m"], p["north_m"], p["up_m"]) for p in item["route"]]
        aircraft.append(
            _Aircraft(
                check_callsign(item["id"]),
                item["class"],
                item["site"],
                float(item["start_s"]),
                Trajectory(item["class"], route, float(item["speed_mps"])),
            )
        )
    centers = {site["id"]: site["center"] for site in scenario.data["sites"]}
    schedule = FaultSchedule(scenario.data["faults"])
    period_ns = clock.seconds_to_ns(period_s)
    nodes = receivers(scenario)
    return [
        _aircraft_component(a, nodes, centers, adsb_model, schedule, period_ns)
        for a in sorted(aircraft, key=lambda a: a.callsign)
    ]


def _aircraft_component(
    aircraft: _Aircraft,
    nodes: Sequence[Mapping[str, Any]],
    centers: Mapping[str, Mapping[str, float]],
    model: AdsbModel,
    schedule: FaultSchedule,
    period_ns: int,
) -> Component:
    home = centers[aircraft.site_id]
    start_ns = clock.seconds_to_ns(aircraft.start_s)
    last_ns = clock.seconds_to_ns(aircraft.start_s + aircraft.trajectory.duration_s)

    def setup(engine: Engine) -> None:
        noise_rng = engine.rng(f"adsb/ruido/{aircraft.callsign}")

        def tick(e: Engine) -> None:
            nxt = e.now_ns + period_ns
            if nxt <= last_ns and (e.end_ns is None or nxt <= e.end_ns):
                e.schedule(nxt, tick)
            t_s = e.now_ns / clock.NS_PER_S
            true_pos = aircraft.trajectory.state(t_s - aircraft.start_s).position
            e.record_truth(
                GroundTruth(
                    target_id=aircraft.callsign,
                    simulated_at=clock.to_timestamp(e.now_ns),
                    true_position=geopoint(true_pos, home),
                    class_id=aircraft.class_id,
                    is_forged=False,
                )
            )
            declared = add(
                true_pos, truncated_noise(noise_rng, model.position_sigma_m, model.sigma_clip)
            )
            for node in nodes:
                node_id = node["id"]
                site_id = node["site"]
                if schedule.is_down(node_id, t_s):
                    continue
                off = node["offset_m"]
                receiver: Vec3 = (off["east_m"], off["north_m"], off["up_m"])
                frame = centers[site_id]
                if math.dist(to_frame(true_pos, home, frame), receiver) > model.range_m:
                    continue
                pps_now = schedule.pps_valid(node_id, t_s, bool(node["pps"]))
                det = build_detection(
                    callsign=aircraft.callsign,
                    declared=to_frame(declared, home, frame),
                    center=frame,
                    site_id=site_id,
                    node_id=node_id,
                    now_ns=e.now_ns,
                    pps=pps_now,
                    model=model,
                    rng=e.rng(f"adsb/receptor/{node_id}"),
                    clock_rng=e.rng(f"adsb/reloj/{node_id}"),
                    drift_offset_ms=schedule.drift_offset_ms(node_id, t_s, pps_now),
                )
                e.emit(site_id, node_id, det)

        if engine.end_ns is None or start_ns <= engine.end_ns:
            engine.schedule(start_ns, tick)

    return setup

"""Remote ID simulado como datos ya recibidos y decodificados (T1.14).

REQ-FUN-004 (fenómeno «Remote ID, incluido falsificado»), REQ-LEG-007 (operador y aeronave
identificada `FCSE_ONLY`) y REQ-LEG-001 (solo detección).

**Solo datos en memoria.** Este módulo construye mensajes Protobuf internos
(`Detection.remote_id`) como los que entregaría un receptor tras decodificar una emisión estándar
(EN 4709-002 por defecto, o ASTM F3411). No produce tramas de radio, ni Wi-Fi ni Bluetooth, no
importa bibliotecas de radio y no contiene ningún camino de transmisión.

Modos de cada amenaza (`remote_id.mode` del escenario):
- `none`: sin observaciones.
- `compliant`: posición declarada = posición real + ruido gaussiano truncado (σ por eje
  `position_sigma_m`, cota `sigma_clip`·σ); ubicación del operador = punto de despegue + ruido.
- `forged`: **datos de entrada incoherentes que la plataforma tendrá que señalar**. La posición
  declarada se desplaza `forged_offset_m` de la real en una dirección que gira al menos
  `forged_min_turn_deg` cada `forged_jump_every` mensajes: el salto entre mensajes supera la
  velocidad máxima de cualquier clase y la posición es incompatible con la acústica. Ningún campo
  de la `Detection` lo revela: solo `GroundTruth.is_forged` (verdad del simulador) lo sabe.

Identificadores sintéticos con prefijo `SIM` (nunca números de operador ni de serie reales). El
texto libre (`self_id_description`) no se rellena: queda fuera de toda salida hasta T1.7b.
Remote ID no informa de las clases C1-C9: `class_scores` es un prior uniforme sobre C1-C7.
Valores por defecto **NO VERIFICADO** (órdenes de magnitud, sin medir).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from random import Random
from typing import Any

from atalaya.sim.v1.ground_truth_pb2 import GroundTruth
from atalaya.v1.common_pb2 import ClassScore
from atalaya.v1.detection_pb2 import (
    REMOTE_ID_STANDARD_ASTM_F3411,
    REMOTE_ID_STANDARD_EN_4709_002,
    SENSOR_TYPE_REMOTE_ID,
    Detection,
    RemoteIdStandard,
)

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
from sim.trajectory import Trajectory, Waypoint

NO_VERIFICADO = "NO VERIFICADO"
RECEIVER_KIND = "remote_id_adsb_receiver"
REMOTE_ID_PERIOD_S = 1.0  # las normas exigen al menos 1 mensaje de posición por segundo
SYNTHETIC_PREFIX = "SIM-"
REMOTE_ID_CONFIDENCE = 0.99  # mensaje decodificado sin errores; NO VERIFICADO
UNMANNED_CLASSES = ("C1", "C2", "C3", "C4", "C5", "C6", "C7")
_MICRO = 1_000_000

STANDARDS: Mapping[str, RemoteIdStandard] = {
    "EN_4709_002": REMOTE_ID_STANDARD_EN_4709_002,
    "ASTM_F3411": REMOTE_ID_STANDARD_ASTM_F3411,
}


@dataclass(frozen=True)
class RemoteIdModel:
    """Parámetros del receptor y de los datos simulados (todos NO VERIFICADO)."""

    position_sigma_m: float = 3.0
    sigma_clip: float = 4.0
    range_m: float = 3000.0
    forged_offset_m: float = 400.0
    forged_jump_every: int = 5
    forged_min_turn_deg: float = 90.0
    forgery_threshold_m: float = 100.0

    def __post_init__(self) -> None:
        check_positive(self.position_sigma_m, "position_sigma_m")
        check_positive(self.sigma_clip, "sigma_clip")
        check_positive(self.range_m, "range_m")
        check_positive(self.forged_offset_m, "forged_offset_m")
        check_positive(self.forgery_threshold_m, "forgery_threshold_m")
        if (
            isinstance(self.forged_jump_every, bool)
            or not isinstance(self.forged_jump_every, int)
            or self.forged_jump_every < 1
        ):
            raise ValueError(f"forged_jump_every: entero ≥ 1 ({self.forged_jump_every!r})")
        turn = check_positive(self.forged_min_turn_deg, "forged_min_turn_deg")
        if turn > 180.0:
            raise ValueError(f"forged_min_turn_deg fuera de (0, 180]: {turn!r}")
        if self.max_error_m >= self.forgery_threshold_m:
            raise ValueError(
                f"el error máximo de un caso conforme ({self.max_error_m:.1f} m) debe quedar "
                f"por debajo del umbral de falsificación ({self.forgery_threshold_m!r} m)"
            )
        if self.forged_offset_m - self.max_error_m <= self.forgery_threshold_m:
            raise ValueError(
                f"forged_offset_m ({self.forged_offset_m!r} m) no supera el umbral de "
                f"falsificación ({self.forgery_threshold_m!r} m) con el ruido máximo"
            )

    @property
    def max_error_m(self) -> float:
        """Cota del error 3D del ruido truncado (√3 · clip · σ)."""
        return math.sqrt(3.0) * self.sigma_clip * self.position_sigma_m


def uniform_prior(classes: Sequence[str]) -> list[tuple[str, float]]:
    """Prior uniforme redondeado hacia abajo (la suma nunca supera 1)."""
    share = math.floor(_MICRO / len(classes)) / _MICRO
    return [(c, share) for c in sorted(classes)]


class ForgedOffset:
    """Desplazamiento incoherente de un caso `forged` (dirección con saltos periódicos)."""

    def __init__(self, model: RemoteIdModel, rng: Random) -> None:
        self.model = model
        self.rng = rng
        self.heading_deg = rng.uniform(0.0, 360.0)
        self.count = 0

    def next(self) -> Vec3:
        if self.count and self.count % self.model.forged_jump_every == 0:
            low = self.model.forged_min_turn_deg
            self.heading_deg = (self.heading_deg + self.rng.uniform(low, 360.0 - low)) % 360.0
        self.count += 1
        rad = math.radians(self.heading_deg)
        r = self.model.forged_offset_m
        return (r * math.sin(rad), r * math.cos(rad), 0.0)


@dataclass(frozen=True)
class Identity:
    uas_id: str
    operator_id: str


def synthetic_identity(rng: Random) -> Identity:
    """Identificadores sintéticos `SIM-…` sacados de la semilla (nunca reales)."""
    return Identity(
        f"{SYNTHETIC_PREFIX}UAS-{rng.getrandbits(40):010X}",
        f"{SYNTHETIC_PREFIX}OP-{rng.getrandbits(40):010X}",
    )


def build_detection(
    *,
    declared: Vec3,
    declared_operator: Vec3,
    center: Mapping[str, float],
    identity: Identity,
    standard: RemoteIdStandard,
    site_id: str,
    node_id: str,
    now_ns: int,
    pps: bool,
    model: RemoteIdModel,
    rng: Random,
    clock_rng: Random,
    drift_offset_ms: float = 0.0,
) -> Detection:
    """`Detection` de Remote ID decodificado, con su incertidumbre (REQ-FUN-062).

    Misma forma para casos conformes y falsificados: solo cambian los valores.
    """
    for value in (identity.uas_id, identity.operator_id):
        if not value.startswith(SYNTHETIC_PREFIX):
            raise ValueError(f"identificador no sintético: {value!r} (prefijo {SYNTHETIC_PREFIX})")
    if standard not in STANDARDS.values():
        raise ValueError(f"norma de Remote ID desconocida: {standard!r}")
    position = geopoint(declared, center)
    det = Detection(
        detection_id=f"{node_id}-rid-{rng.getrandbits(64):016x}",
        site_id=site_id,
        node_id=node_id,
        observed_at=clock.to_timestamp(now_ns),
        sensor_type=SENSOR_TYPE_REMOTE_ID,
        time_quality=time_quality(pps, clock_rng, drift_offset_ms),
        position=position,
        position_covariance=isotropic_covariance(model.position_sigma_m),
        detection_confidence=REMOTE_ID_CONFIDENCE,
    )
    det.class_scores.extend(
        ClassScore(class_id=c, probability=p) for c, p in uniform_prior(UNMANNED_CLASSES)
    )
    rid = det.remote_id
    rid.standard = standard
    rid.aircraft_position.CopyFrom(position)
    rid.message_time.CopyFrom(clock.to_timestamp(now_ns))
    # FCSE_ONLY (REQ-LEG-007): identifican o sitúan al operador y a la aeronave.
    rid.uas_id = identity.uas_id
    rid.operator_id = identity.operator_id
    rid.operator_location.CopyFrom(geopoint(declared_operator, center))
    return det


@dataclass(frozen=True)
class _RidTarget:
    target_id: str
    class_id: str
    site_id: str
    start_s: float
    trajectory: Trajectory
    is_forged: bool
    standard: RemoteIdStandard
    launch_point: Vec3


def _rid_targets(scenario: Scenario) -> list[_RidTarget]:
    out: list[_RidTarget] = []
    for item in scenario.data["threats"]:
        rid = item["remote_id"]
        if rid["mode"] == "none":
            continue
        route = [Waypoint(p["east_m"], p["north_m"], p["up_m"]) for p in item["route"]]
        lp = item["launch_point"]["offset_m"]
        out.append(
            _RidTarget(
                item["id"],
                item["class"],
                item["site"],
                float(item["start_s"]),
                Trajectory(item["class"], route, float(item["speed_mps"])),
                rid["mode"] == "forged",
                STANDARDS[rid["standard"]],
                (float(lp["east_m"]), float(lp["north_m"]), float(lp["up_m"])),
            )
        )
    return sorted(out, key=lambda t: t.target_id)


def receivers(scenario: Scenario) -> list[Mapping[str, Any]]:
    """Nodos receptores de Remote ID y ADS-B del escenario."""
    return [
        f["properties"]
        for f in scenario.geometry["features"]
        if f["properties"]["role"] == "node" and f["properties"]["kind"] == RECEIVER_KIND
    ]


def remote_id_components(
    scenario: Scenario,
    model: RemoteIdModel | None = None,
    period_s: float = REMOTE_ID_PERIOD_S,
) -> list[Component]:
    """Un componente por amenaza con Remote ID: cada `period_s` registra la verdad terreno y
    entrega los datos decodificados a los receptores en alcance y en servicio."""
    rid_model = model or RemoteIdModel()
    check_positive(period_s, "periodo")
    centers = {site["id"]: site["center"] for site in scenario.data["sites"]}
    nodes = receivers(scenario)
    schedule = FaultSchedule(scenario.data["faults"])
    period_ns = clock.seconds_to_ns(period_s)
    return [
        _target_component(target, nodes, centers, rid_model, schedule, period_ns)
        for target in _rid_targets(scenario)
    ]


def _target_component(
    target: _RidTarget,
    nodes: Sequence[Mapping[str, Any]],
    centers: Mapping[str, Mapping[str, float]],
    model: RemoteIdModel,
    schedule: FaultSchedule,
    period_ns: int,
) -> Component:
    tid = target.target_id
    home = centers[target.site_id]
    start_ns = clock.seconds_to_ns(target.start_s)
    last_ns = clock.seconds_to_ns(target.start_s + target.trajectory.duration_s)

    def setup(engine: Engine) -> None:
        noise_rng = engine.rng(f"remote-id/ruido/{tid}")
        identity = synthetic_identity(engine.rng(f"remote-id/identidad/{tid}"))
        incoherent = ForgedOffset(model, engine.rng(f"remote-id/incoherencia/{tid}"))

        def tick(e: Engine) -> None:
            nxt = e.now_ns + period_ns
            if nxt <= last_ns and (e.end_ns is None or nxt <= e.end_ns):
                e.schedule(nxt, tick)
            t_s = e.now_ns / clock.NS_PER_S
            true_pos = target.trajectory.state(t_s - target.start_s).position
            e.record_truth(
                GroundTruth(
                    target_id=tid,
                    simulated_at=clock.to_timestamp(e.now_ns),
                    true_position=geopoint(true_pos, home),
                    class_id=target.class_id,
                    is_forged=target.is_forged,
                    launch_point=geopoint(target.launch_point, home),
                )
            )
            declared = add(
                true_pos, truncated_noise(noise_rng, model.position_sigma_m, model.sigma_clip)
            )
            declared_op = add(
                target.launch_point,
                truncated_noise(noise_rng, model.position_sigma_m, model.sigma_clip),
            )
            if target.is_forged:
                shift = incoherent.next()
                declared = add(declared, shift)
                declared_op = add(declared_op, shift)
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
                    declared=to_frame(declared, home, frame),
                    declared_operator=to_frame(declared_op, home, frame),
                    center=frame,
                    identity=identity,
                    standard=target.standard,
                    site_id=site_id,
                    node_id=node_id,
                    now_ns=e.now_ns,
                    pps=pps_now,
                    model=model,
                    rng=e.rng(f"remote-id/receptor/{node_id}"),
                    clock_rng=e.rng(f"remote-id/reloj/{node_id}"),
                    drift_offset_ms=schedule.drift_offset_ms(node_id, t_s, pps_now),
                )
                e.emit(site_id, node_id, det)

        if engine.end_ns is None or start_ns <= engine.end_ns:
            engine.schedule(start_ns, tick)

    return setup

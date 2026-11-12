"""T1.13: red, relojes y fallos de nodo (REQ-FUN-004).

Un test por fenómeno: pérdida empírica dentro del IC al 99 % con 10.000 mensajes; desfase de reloj
lineal con la deriva; un nodo caído deja de publicar `NodeStatus` desde el instante del fallo; un
nodo sin PPS publica `pps_valid=false` y su `TimeQuality` lo refleja; cada duplicado conserva el
mismo `detection_id`. Negativas: magnitudes imposibles rechazadas al cargar el escenario y cero
huecos en la secuencia de `NodeStatus` sin fallos.
"""

from __future__ import annotations

import copy
import itertools
import math
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from random import Random
from typing import Any

import pytest
from atalaya.v1.envelope_pb2 import Envelope
from atalaya.v1.node_status_pb2 import NODE_HEALTH_DEGRADED, NODE_HEALTH_HEALTHY, NodeStatus
from atalaya_contracts.validate import validate
from hypothesis import given, settings
from hypothesis import strategies as st

from sim import clock, faults, network
from sim.engine import NODE_STATUS_PERIOD_S, build_engine
from sim.network import NetworkConfig
from sim.scenario import Scenario, ScenarioError, load_scenario, validate_scenario
from sim.sensors import acoustic

REPO = Path(__file__).resolve().parents[2]
SCENARIOS = REPO / "sim" / "scenarios"
NAMES = ("prision_ceuta", "puerto_ceuta", "aerodromo", "frontera_8km")
Z99 = 2.5758293035489004  # cuantil 0,995 de la normal estándar


def _scenario(name: str, fault_list: Sequence[dict[str, Any]] | None = None) -> Scenario:
    base = load_scenario(SCENARIOS / f"{name}.yaml")
    if fault_list is None:
        return base
    data = copy.deepcopy(base.data)
    data["faults"] = list(fault_list)
    if fault_list:  # el esquema exige ≥ 1 fallo; la lista vacía «desactiva» los fallos
        validate_scenario(data, source="test", geometry=base.geometry)
    return Scenario(name=base.name, data=data, geometry=base.geometry)


def _statuses(scenario: Scenario, node_id: str, **kwargs: Any) -> list[NodeStatus]:
    engine = build_engine(scenario, seed=kwargs.pop("seed", 7), **kwargs)
    return [
        env.node_status
        for env in engine.run_all()
        if env.HasField("node_status") and env.node_id == node_id
    ]


def _t(status: NodeStatus) -> float:
    return clock.from_timestamp(status.observed_at) / clock.NS_PER_S


def _messages(count: int, node_id: str = "n1") -> list[Envelope]:
    out = []
    for i in range(count):
        env = Envelope(site_id="s", node_id=node_id, sequence=i)
        env.emitted_at.CopyFrom(clock.to_timestamp(i * 1_000_000))
        env.node_status.node_id = node_id
        out.append(env)
    return out


# --- red -----------------------------------------------------------------------------------


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize("loss", [0.05, 0.2, 0.5])
def test_tasa_de_perdida_dentro_del_ic_99(loss: float) -> None:
    n = 10_000
    config = NetworkConfig(loss=loss)
    delivered = network.transmit(_messages(n), lambda env: config, Random(3))  # noqa: S311
    observed = 1.0 - len(delivered) / n
    half_width = Z99 * math.sqrt(loss * (1 - loss) / n)
    assert abs(observed - loss) <= half_width


@pytest.mark.req("REQ-FUN-004")
def test_latencia_lognormal_con_la_mediana_configurada() -> None:
    n = 10_000
    config = NetworkConfig(base_latency_ms=150.0, latency_sigma=0.5)
    delivered = network.transmit(_messages(n), lambda env: config, Random(5))  # noqa: S311
    latencies = sorted(d.latency_ms for d in delivered)
    assert len(latencies) == n
    assert min(latencies) > 0.0
    median = latencies[n // 2]
    assert median == pytest.approx(150.0, rel=0.03)
    logs = [math.log(v) for v in latencies]
    mean = sum(logs) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in logs) / (n - 1))
    assert sd == pytest.approx(0.5, rel=0.05)


@pytest.mark.req("REQ-FUN-004")
def test_entrega_ordenada_por_llegada_con_desorden() -> None:
    config = NetworkConfig(base_latency_ms=5.0, latency_sigma=0.0, reorder=0.3)
    delivered = network.transmit(_messages(2000), lambda env: config, Random(9))  # noqa: S311
    arrivals = [d.arrival_ns for d in delivered]
    assert arrivals == sorted(arrivals)
    sequences = [d.envelope.sequence for d in delivered]
    inversions = sum(1 for a, b in itertools.pairwise(sequences) if b < a)
    assert inversions > 0
    calm = network.transmit(
        _messages(2000),
        lambda env: NetworkConfig(base_latency_ms=5.0, latency_sigma=0.0),
        Random(9),  # noqa: S311
    )
    assert [d.envelope.sequence for d in calm] == list(range(2000))


@pytest.mark.req("REQ-FUN-004")
def test_duplicados_conservan_el_mismo_detection_id() -> None:
    scenario = _scenario(
        "prision_ceuta",
        [{"kind": "duplicate", "node": "rc-pps-1", "start_s": 0.0, "duration_s": 600.0,
          "magnitude": 0.5}],
    )  # fmt: skip
    engine = build_engine(scenario, seed=3, extra_components=acoustic.acoustic_components(scenario))
    emitted = engine.run_all()
    delivered = network.transmit_scenario(scenario, emitted, seed=3)
    ids = Counter(
        d.envelope.detection.detection_id for d in delivered if d.envelope.HasField("detection")
    )
    duplicated = {i: c for i, c in ids.items() if c > 1}
    assert duplicated, "ningún duplicado con probabilidad 0,5"
    assert all(i.startswith("rc-pps-1-") for i in duplicated)
    by_id: dict[str, list[bytes]] = {}
    for d in delivered:
        if d.envelope.HasField("detection"):
            by_id.setdefault(d.envelope.detection.detection_id, []).append(
                d.envelope.SerializeToString(deterministic=True)
            )
    assert all(len(set(copies)) == 1 for copies in by_id.values())


@pytest.mark.req("REQ-FUN-004")
def test_enlace_perdido_no_entrega_nada_del_nodo_durante_el_fallo() -> None:
    scenario = _scenario(
        "prision_ceuta",
        [{"kind": "link_down", "node": "rc-and-1", "start_s": 100.0, "duration_s": 200.0}],
    )
    emitted = build_engine(scenario, seed=1).run_all()
    delivered = network.transmit_scenario(scenario, emitted, seed=1)
    lost = [
        d
        for d in delivered
        if d.envelope.node_id == "rc-and-1" and 100.0 <= _t(d.envelope.node_status) < 300.0
    ]
    assert lost == []
    sent = [e for e in emitted if e.node_id == "rc-and-1" and 100.0 <= _t(e.node_status) < 300.0]
    assert len(sent) >= 6  # el nodo sigue vivo y emitiendo; es el enlace el que falla


@pytest.mark.req("REQ-FUN-003", "REQ-FUN-004")
def test_red_reproducible_por_semilla() -> None:
    scenario = load_scenario(SCENARIOS / "puerto_ceuta.yaml")
    emitted = build_engine(scenario, seed=4).run_all()

    def run(seed: int) -> list[tuple[int, bytes]]:
        return [
            (d.arrival_ns, d.envelope.SerializeToString(deterministic=True))
            for d in network.transmit_scenario(scenario, emitted, seed=seed)
        ]

    assert run(4) == run(4)
    assert run(4) != run(5)


# --- relojes -------------------------------------------------------------------------------


@pytest.mark.req("REQ-FUN-004")
@given(drift=st.floats(-500.0, 500.0), t1=st.floats(0.0, 3600.0), t2=st.floats(0.0, 3600.0))
@settings(max_examples=200, derandomize=True)
def test_desfase_lineal_con_la_deriva(drift: float, t1: float, t2: float) -> None:
    a = clock.drift_offset_ms(drift, t1)
    b = clock.drift_offset_ms(drift, t2)
    assert b - a == pytest.approx(drift * 1e-3 * (t2 - t1), abs=1e-9)
    assert clock.drift_offset_ms(drift, 0.0) == 0.0


@pytest.mark.req("REQ-FUN-004")
def test_deriva_del_escenario_se_ve_en_node_status() -> None:
    drift_ppm = 1000.0
    scenario = _scenario(
        "prision_ceuta",
        [{"kind": "clock_drift", "node": "rc-and-1", "start_s": 0.0, "duration_s": 600.0,
          "magnitude": drift_ppm}],
    )  # fmt: skip
    statuses = _statuses(scenario, "rc-and-1")
    points = [(_t(s), s.time_quality.clock_offset_ms) for s in statuses]
    n = len(points)
    mean_t = sum(t for t, _ in points) / n
    mean_o = sum(o for _, o in points) / n
    slope = sum((t - mean_t) * (o - mean_o) for t, o in points) / sum(
        (t - mean_t) ** 2 for t, _ in points
    )
    assert slope == pytest.approx(drift_ppm * 1e-3, rel=0.10)  # ms por segundo


@pytest.mark.req("REQ-FUN-004")
def test_nodo_con_pps_valido_no_acumula_deriva() -> None:
    scenario = _scenario(
        "prision_ceuta",
        [{"kind": "clock_drift", "node": "rc-pps-1", "start_s": 0.0, "duration_s": 600.0,
          "magnitude": 1000.0}],
    )  # fmt: skip
    statuses = _statuses(scenario, "rc-pps-1")
    assert max(abs(s.time_quality.clock_offset_ms) for s in statuses) < 0.01


@pytest.mark.req("REQ-FUN-004")
def test_nodo_sin_pps_lo_publica_en_time_quality() -> None:
    scenario = load_scenario(SCENARIOS / "prision_ceuta.yaml")
    android = _statuses(scenario, "rc-and-1")
    assert android and all(not s.time_quality.pps_valid for s in android)
    assert all(s.time_quality.uncertainty_ms >= 1.0 for s in android)
    with_pps = _statuses(scenario, "rc-pps-1")
    assert with_pps and all(s.time_quality.pps_valid for s in with_pps)
    assert all(s.time_quality.uncertainty_ms < 0.01 for s in with_pps)


@pytest.mark.req("REQ-FUN-004")
def test_pps_perdido_durante_el_fallo() -> None:
    scenario = _scenario(
        "prision_ceuta",
        [{"kind": "pps_invalid", "node": "rc-pps-1", "start_s": 200.0, "duration_s": 100.0}],
    )
    statuses = _statuses(scenario, "rc-pps-1")
    for s in statuses:
        inside = 200.0 <= _t(s) < 300.0
        assert s.time_quality.pps_valid is (not inside)
        assert s.health == (NODE_HEALTH_DEGRADED if inside else NODE_HEALTH_HEALTHY)
        assert (s.time_quality.uncertainty_ms >= 1.0) is inside
        assert validate(s) == []
    assert any(200.0 <= _t(s) < 300.0 for s in statuses)


# --- fallos de nodo ------------------------------------------------------------------------


@pytest.mark.req("REQ-FUN-004")
def test_nodo_caido_deja_de_publicar_desde_el_instante_del_fallo() -> None:
    scenario = load_scenario(SCENARIOS / "prision_ceuta.yaml")  # rc-and-2 caído 300-420 s
    times = [_t(s) for s in _statuses(scenario, "rc-and-2")]
    assert [t for t in times if 300.0 <= t < 420.0] == []
    assert any(t < 300.0 for t in times) and any(t >= 420.0 for t in times)
    before = max(t for t in times if t < 300.0)
    assert 300.0 - before <= NODE_STATUS_PERIOD_S
    assert min(t for t in times if t >= 420.0) - 420.0 <= NODE_STATUS_PERIOD_S


@pytest.mark.req("REQ-FUN-004")
def test_nodo_caido_tampoco_emite_detecciones() -> None:
    scenario = _scenario(
        "prision_ceuta",
        [{"kind": "node_down", "node": "rc-pps-1", "start_s": 0.0, "duration_s": 600.0}],
    )
    engine = build_engine(
        scenario,
        seed=2,
        extra_components=acoustic.acoustic_components(
            scenario, acoustic.DetectionModel(snr50_db=-20.0)
        ),
    )
    envelopes = engine.run_all()
    assert not [e for e in envelopes if e.node_id == "rc-pps-1"]
    assert [e for e in envelopes if e.HasField("detection")]


@pytest.mark.req("REQ-FUN-004")
def test_calendario_de_fallos_por_nodo_y_tiempo() -> None:
    schedule = faults.FaultSchedule(
        [
            {"kind": "packet_loss", "node": "a", "start_s": 10.0, "duration_s": 5.0,
             "magnitude": 0.3},
            {"kind": "latency", "node": "a", "start_s": 0.0, "duration_s": 100.0,
             "magnitude": 80.0},
        ]
    )  # fmt: skip
    assert schedule.network_config("a", 9.999).loss == 0.0
    assert schedule.network_config("a", 10.0).loss == 0.3
    assert schedule.network_config("a", 15.0).loss == 0.0
    assert schedule.network_config("a", 50.0).base_latency_ms == 80.0
    assert schedule.network_config("b", 12.0) == NetworkConfig()


# --- pruebas negativas ---------------------------------------------------------------------


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize(
    ("fault", "fragment"),
    [
        ({"kind": "packet_loss", "magnitude": 1.5}, "[0, 1]"),
        ({"kind": "duplicate", "magnitude": 1.01}, "[0, 1]"),
        ({"kind": "reorder", "magnitude": 2.0}, "[0, 1]"),
        ({"kind": "latency", "magnitude": -5.0}, "magnitude"),
        ({"kind": "clock_drift", "magnitude": math.inf}, "finita"),
        ({"kind": "clock_drift", "magnitude": math.nan}, "finita"),
        ({"kind": "packet_loss"}, "requiere"),
        ({"kind": "latency"}, "requiere"),
    ],
)
def test_negativa_magnitudes_imposibles_rechazadas_al_cargar(
    fault: dict[str, Any], fragment: str
) -> None:
    base = load_scenario(SCENARIOS / "prision_ceuta.yaml")
    data = copy.deepcopy(base.data)
    data["faults"] = [{"node": "rc-and-1", "start_s": 0.0, "duration_s": 10.0, **fault}]
    with pytest.raises(ScenarioError) as info:
        validate_scenario(data, source="test", geometry=base.geometry)
    assert info.value.path.startswith("faults/0")
    assert fragment in str(info.value)


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize(
    "kwargs",
    [
        {"loss": 1.1},
        {"loss": -0.1},
        {"duplicate": math.nan},
        {"base_latency_ms": -1.0},
        {"latency_sigma": math.inf},
    ],
)
def test_negativa_configuracion_de_red_invalida(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        NetworkConfig(**kwargs)


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize("drift", [math.inf, math.nan])
def test_negativa_deriva_no_finita(drift: float) -> None:
    with pytest.raises(ValueError, match="deriva"):
        clock.drift_offset_ms(drift, 1.0)


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize("name", NAMES)
def test_negativa_sin_fallos_cero_huecos_en_node_status(name: str) -> None:
    scenario = _scenario(name, [])
    engine = build_engine(scenario, seed=8)
    emitted = engine.run_all()
    delivered = network.transmit_scenario(scenario, emitted, seed=8)
    assert len(delivered) == len(emitted)
    nodes = {e.node_id for e in emitted}
    for node in sorted(nodes):
        times = sorted(
            _t(d.envelope.node_status)
            for d in delivered
            if d.envelope.node_id == node and d.envelope.HasField("node_status")
        )
        gaps = [b - a for a, b in itertools.pairwise(times)]
        assert gaps and all(g == pytest.approx(NODE_STATUS_PERIOD_S) for g in gaps), node
        assert times[0] < NODE_STATUS_PERIOD_S
        assert scenario.data["duration_s"] - times[-1] <= NODE_STATUS_PERIOD_S


@pytest.mark.req("REQ-FUN-004")
def test_escenarios_reales_cargan_con_sus_fallos() -> None:
    for name in NAMES:
        scenario = load_scenario(SCENARIOS / f"{name}.yaml")
        assert faults.FaultSchedule(scenario.data["faults"]).faults

"""T1.14: Remote ID (conforme y falsificado) y ADS-B simulados (REQ-FUN-004, REQ-LEG-007,
REQ-LEG-001).

Solo datos en memoria: mensajes Protobuf internos como los que entregaría un receptor tras
decodificar. Los casos `forged` son datos de entrada incoherentes que la plataforma tendrá que
señalar; nada en `sim/` genera tramas ni transmite.

- Conformes: posición declarada a < 30 m de la real.
- Falsificados: distancia a la real por encima del umbral configurado y al menos un salto que
  supera la velocidad máxima de la clase.
- Campos de operador y aeronave identificada `FCSE_ONLY`; desaparecen con `redact(…, OPERATOR)`.
- ADS-B solo con identificadores `SIM…`.
- Negativas: ningún campo de la `Detection` falsificada revela que lo es; `sim/` no importa
  bibliotecas de radio, Wi-Fi ni Bluetooth.
"""

from __future__ import annotations

import ast
import copy
import itertools
import math
from collections import defaultdict
from collections.abc import Iterator
from functools import cache
from pathlib import Path
from random import Random
from typing import Any, cast

import pytest
from atalaya.sim.v1.ground_truth_pb2 import GroundTruth
from atalaya.v1 import options_pb2
from atalaya.v1.detection_pb2 import (
    SENSOR_TYPE_ADSB,
    SENSOR_TYPE_REMOTE_ID,
    AdsbObservation,
    Detection,
    RemoteIdObservation,
)
from atalaya_contracts.redact import redact
from atalaya_contracts.validate import validate
from google.protobuf.message import Message

from sim import classes, clock, geo
from sim.engine import Engine, build_engine
from sim.scenario import Scenario, load_scenario
from sim.sensors import adsb, common, remote_id
from sim.sensors.adsb import AdsbModel
from sim.sensors.remote_id import RemoteIdModel

REPO = Path(__file__).resolve().parents[2]
SIM_DIR = REPO / "sim"
SCENARIOS = REPO / "sim" / "scenarios"
NAMES = ("prision_ceuta", "puerto_ceuta", "aerodromo", "frontera_8km")
SEED = 11

COMPLIANT = [
    ("aerodromo", "amenaza-1"),
    ("puerto_ceuta", "amenaza-1"),
    ("frontera_8km", "amenaza-3"),
]
FORGED = [("prision_ceuta", "amenaza-2"), ("aerodromo", "amenaza-2"), ("frontera_8km", "amenaza-2")]


# --- utilidades ----------------------------------------------------------------------------


@cache
def _scenario(name: str) -> Scenario:
    return load_scenario(SCENARIOS / f"{name}.yaml")


def _only_threat(name: str, threat_id: str) -> Scenario:
    base = _scenario(name)
    data = copy.deepcopy(base.data)
    data["threats"] = [t for t in data["threats"] if t["id"] == threat_id]
    data["manned_aircraft"] = []
    return Scenario(name=base.name, data=data, geometry=base.geometry)


def _run(scenario: Scenario, seed: int = SEED, **kwargs: Any) -> Engine:
    rid_model = kwargs.pop("rid_model", None)
    adsb_model = kwargs.pop("adsb_model", None)
    components = [
        *remote_id.remote_id_components(scenario, rid_model),
        *adsb.adsb_components(scenario, adsb_model),
    ]
    engine = build_engine(scenario, seed=seed, extra_components=components, **kwargs)
    engine.run_all()
    return engine


@cache
def _single(name: str, threat_id: str) -> Engine:
    return _run(_only_threat(name, threat_id))


@cache
def _full(name: str) -> Engine:
    return _run(_scenario(name))


def _detections(engine: Engine, sensor: int) -> list[Detection]:
    return [
        env.detection
        for env in engine.envelopes
        if env.HasField("detection") and env.detection.sensor_type == sensor
    ]


def _site_center(scenario: Scenario, site_id: str) -> dict[str, float]:
    return next(s["center"] for s in scenario.data["sites"] if s["id"] == site_id)


def _distance_m(a: Any, b: Any, center: dict[str, float]) -> float:
    pa = geo.geodetic_to_enu(
        a.latitude_deg, a.longitude_deg, a.altitude_m, center["lat_deg"], center["lon_deg"], 0.0
    )
    pb = geo.geodetic_to_enu(
        b.latitude_deg, b.longitude_deg, b.altitude_m, center["lat_deg"], center["lon_deg"], 0.0
    )
    return math.dist(pa, pb)


def _pairs(engine: Engine, sensor: int) -> list[tuple[Detection, GroundTruth]]:
    truth = {
        (gt.target_id, clock.from_timestamp(gt.simulated_at)): gt for gt in engine.ground_truth
    }
    by_time: dict[int, list[GroundTruth]] = defaultdict(list)
    for (_, t_ns), gt in truth.items():
        by_time[t_ns].append(gt)
    out = []
    for det in _detections(engine, sensor):
        candidates = by_time[clock.from_timestamp(det.observed_at)]
        assert len(candidates) == 1, "un solo objetivo por escenario reducido"
        out.append((det, candidates[0]))
    return out


def _field_paths(message: Message, prefix: str = "") -> Iterator[str]:
    for field, value in message.ListFields():
        path = f"{prefix}{field.name}"
        yield path
        if field.message_type is not None and not field.is_repeated:
            yield from _field_paths(value, path + ".")


# --- Remote ID conforme ------------------------------------------------------------------


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize(("name", "threat_id"), COMPLIANT)
def test_remote_id_conforme_a_menos_de_30_m_de_la_real(name: str, threat_id: str) -> None:
    scenario = _only_threat(name, threat_id)
    pairs = _pairs(_single(name, threat_id), SENSOR_TYPE_REMOTE_ID)
    assert len(pairs) >= 20, "el receptor debe oír la amenaza"
    for det, gt in pairs:
        assert gt.is_forged is False
        center = _site_center(scenario, det.site_id)
        assert _distance_m(det.remote_id.aircraft_position, gt.true_position, center) < 30.0
        assert det.position == det.remote_id.aircraft_position


@pytest.mark.req("REQ-FUN-004")
def test_ruido_conforme_acotado_por_debajo_de_30_m() -> None:
    model = RemoteIdModel()
    assert model.max_error_m < 30.0
    rng = Random(3)  # noqa: S311 (simulación)
    clip = model.sigma_clip * model.position_sigma_m
    for _ in range(20_000):
        n = common.truncated_noise(rng, model.position_sigma_m, model.sigma_clip)
        assert all(abs(x) <= clip for x in n)
        assert math.hypot(*n) <= model.max_error_m
    for _ in range(2_000):  # cota estrecha: sin truncado se saldría a menudo
        assert all(abs(x) <= 0.5 * 2.0 for x in common.truncated_noise(rng, 2.0, 0.5))


# --- Remote ID falsificado ---------------------------------------------------------------


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize(("name", "threat_id"), FORGED)
def test_remote_id_falsificado_es_incoherente(name: str, threat_id: str) -> None:
    scenario = _only_threat(name, threat_id)
    model = RemoteIdModel()
    pairs = _pairs(_single(name, threat_id), SENSOR_TYPE_REMOTE_ID)
    assert len(pairs) >= 20
    class_id = pairs[0][1].class_id
    v_max = classes.kinematics(class_id).max_speed_mps.value
    by_node: dict[str, list[Detection]] = defaultdict(list)
    for det, gt in pairs:
        assert gt.is_forged is True
        center = _site_center(scenario, det.site_id)
        assert (
            _distance_m(det.remote_id.aircraft_position, gt.true_position, center)
            > model.forgery_threshold_m
        )
        by_node[det.node_id].append(det)
    fastest = 0.0
    for node_id, dets in by_node.items():
        center = _site_center(scenario, dets[0].site_id)
        for a, b in itertools.pairwise(dets):
            dt = (clock.from_timestamp(b.observed_at) - clock.from_timestamp(a.observed_at)) / 1e9
            assert dt > 0, node_id
            speed = (
                _distance_m(a.remote_id.aircraft_position, b.remote_id.aircraft_position, center)
                / dt
            )
            fastest = max(fastest, speed)
    assert fastest > v_max, f"ningún salto supera {v_max} m/s de {class_id}"


@pytest.mark.req("REQ-FUN-004")
def test_verdad_terreno_marca_los_casos() -> None:
    engine = _full("aerodromo")
    flags = {(gt.target_id, gt.is_forged) for gt in engine.ground_truth}
    assert ("amenaza-1", False) in flags
    assert ("amenaza-2", True) in flags
    assert all(validate(gt) == [] for gt in engine.ground_truth[:200])


# --- privacidad: FCSE_ONLY ---------------------------------------------------------------


def _declared(message: type[Message], field: str) -> int:
    opts = message.DESCRIPTOR.fields_by_name[field].GetOptions()
    return int(opts.Extensions[cast(Any, options_pb2.sensitivity)])


@pytest.mark.req("REQ-LEG-007")
@pytest.mark.parametrize("field", ["operator_id", "operator_location", "uas_id"])
def test_campos_de_operador_declarados_fcse_only(field: str) -> None:
    assert _declared(RemoteIdObservation, field) == options_pb2.FCSE_ONLY


@pytest.mark.req("REQ-LEG-007")
@pytest.mark.parametrize(("name", "threat_id"), COMPLIANT + FORGED)
def test_campos_de_operador_salen_y_desaparecen_con_redact_operator(
    name: str, threat_id: str
) -> None:
    dets = _detections(_single(name, threat_id), SENSOR_TYPE_REMOTE_ID)
    assert dets
    for det in dets:
        rid = det.remote_id
        assert rid.HasField("operator_id") and rid.HasField("operator_location")
        assert rid.HasField("uas_id")
        assert rid.uas_id.startswith("SIM-") and rid.operator_id.startswith("SIM-")
        assert not rid.HasField("self_id_description")  # texto libre: nunca (T1.7b)
        seen = redact(det, options_pb2.OPERATOR)
        assert isinstance(seen, Detection)
        assert seen.HasField("remote_id")
        for field in ("operator_id", "operator_location", "uas_id"):
            assert not seen.remote_id.HasField(field)
        assert seen.remote_id.HasField("aircraft_position")
        public = redact(det, options_pb2.PUBLIC)
        assert b"SIM-OP-" not in public.SerializeToString()
        full = redact(det, options_pb2.FCSE_ONLY)
        assert full == det


@pytest.mark.req("REQ-LEG-007")
def test_verdad_terreno_falsificada_y_origen_desaparecen_con_redact_operator() -> None:
    gt = next(g for g in _full("prision_ceuta").ground_truth if g.is_forged)
    seen = redact(gt, options_pb2.OPERATOR)
    assert isinstance(seen, GroundTruth)
    assert not seen.HasField("is_forged")
    assert not seen.HasField("launch_point")
    assert not seen.HasField("true_position")


# --- validación e incertidumbre ----------------------------------------------------------


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize("name", NAMES)
def test_toda_deteccion_remote_id_y_adsb_pasa_validate(name: str) -> None:
    engine = _full(name)
    dets = _detections(engine, SENSOR_TYPE_REMOTE_ID) + _detections(engine, SENSOR_TYPE_ADSB)
    assert dets
    for det in dets:
        assert validate(det) == [], det.detection_id
        assert det.HasField("position_covariance")


@pytest.mark.req("REQ-FUN-004")
def test_reproducible_por_semilla() -> None:
    scenario = _only_threat("aerodromo", "amenaza-2")
    a = _run(scenario, seed=5, duration_s=400.0)
    b = _run(scenario, seed=5, duration_s=400.0)
    c = _run(scenario, seed=6, duration_s=400.0)
    serial = [e.SerializeToString(deterministic=True) for e in a.envelopes]
    assert serial == [e.SerializeToString(deterministic=True) for e in b.envelopes]
    assert serial != [e.SerializeToString(deterministic=True) for e in c.envelopes]
    assert a.ground_truth == b.ground_truth


@pytest.mark.req("REQ-FUN-004")
def test_receptor_caido_no_entrega_remote_id() -> None:
    base = _only_threat("aerodromo", "amenaza-1")
    receiver = remote_id.receivers(base)[0]["id"]
    data = copy.deepcopy(base.data)
    data["faults"] = [{"kind": "node_down", "node": receiver, "start_s": 0.0, "duration_s": 1e6}]
    engine = _run(Scenario(name=base.name, data=data, geometry=base.geometry))
    assert not [d for d in _detections(engine, SENSOR_TYPE_REMOTE_ID) if d.node_id == receiver]
    assert engine.ground_truth, "la verdad terreno no depende del receptor"


# --- ADS-B ---------------------------------------------------------------------------------


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize("name", NAMES)
def test_adsb_solo_con_identificadores_sim(name: str) -> None:
    dets = _detections(_full(name), SENSOR_TYPE_ADSB)
    assert dets, "cada escenario tiene al menos una aeronave C8"
    for det in dets:
        assert det.adsb.callsign.startswith("SIM")
        assert det.HasField("adsb")
        top = max(det.class_scores, key=lambda s: s.probability)
        assert top.class_id == "C8"


@pytest.mark.req("REQ-FUN-004")
def test_adsb_cerca_de_la_posicion_real() -> None:
    scenario = _scenario("prision_ceuta")
    data = copy.deepcopy(scenario.data)
    data["threats"] = []
    engine = _run(Scenario(name=scenario.name, data=data, geometry=scenario.geometry))
    pairs = _pairs(engine, SENSOR_TYPE_ADSB)
    assert len(pairs) >= 20
    model = AdsbModel()
    for det, gt in pairs:
        assert gt.class_id == "C8" and gt.is_forged is False
        center = _site_center(scenario, det.site_id)
        assert (
            _distance_m(det.adsb.aircraft_position, gt.true_position, center) <= model.max_error_m
        )


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize("callsign", ["IBE1234", "EC-ABC", "sim101", "SIM", "XSIM12", ""])
def test_negativa_adsb_rechaza_identificadores_no_sinteticos(callsign: str) -> None:
    with pytest.raises(ValueError, match="sintético"):
        adsb.check_callsign(callsign)


@pytest.mark.req("REQ-FUN-004")
def test_negativa_constructor_adsb_rechaza_identificador_real() -> None:
    with pytest.raises(ValueError, match="sintético"):
        adsb.build_detection(
            callsign="IBE1234",
            declared=(0.0, 0.0, 900.0),
            center={"lat_deg": 36.2, "lon_deg": -4.1},
            site_id="s",
            node_id="n",
            now_ns=0,
            pps=True,
            model=AdsbModel(),
            rng=Random(1),  # noqa: S311
            clock_rng=Random(2),  # noqa: S311
        )


@pytest.mark.req("REQ-FUN-004")
def test_negativa_escenario_con_identificador_real_rechazado_por_el_sensor() -> None:
    base = _scenario("prision_ceuta")
    data = copy.deepcopy(base.data)
    data["manned_aircraft"][0]["id"] = "IBE1234"
    with pytest.raises(ValueError, match="sintético"):
        adsb.adsb_components(Scenario(name=base.name, data=data, geometry=base.geometry))


# --- pruebas negativas ---------------------------------------------------------------------

_REVEALING = (
    b"forged",
    b"is_forged",
    b"FORGED",
    b"falsif",
    b"fake",
    b"FAKE",
    ("spo" + "of").encode(),
    b"ground_truth",
    b"GroundTruth",
)


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize(("name", "threat_id"), FORGED)
def test_negativa_deteccion_falsificada_no_revela_que_lo_es(name: str, threat_id: str) -> None:
    forged = _detections(_single(name, threat_id), SENSOR_TYPE_REMOTE_ID)
    compliant = _detections(_single(*COMPLIANT[0]), SENSOR_TYPE_REMOTE_ID)
    assert forged and compliant
    compliant_shape = set(_field_paths(compliant[0]))
    for det in forged:
        raw = det.SerializeToString(deterministic=True)
        text = str(det).encode()
        for word in _REVEALING:
            assert word not in raw and word not in text
        assert set(_field_paths(det)) == compliant_shape
        assert det.detection_confidence == compliant[0].detection_confidence
        assert list(det.class_scores) == list(compliant[0].class_scores)
    envelopes = [
        e.SerializeToString(deterministic=True) for e in _single(name, threat_id).envelopes
    ]
    assert not any(word in raw for raw in envelopes for word in _REVEALING)


@pytest.mark.req("REQ-FUN-004")
def test_negativa_campos_de_la_deteccion_sin_nombres_reveladores() -> None:
    for descriptor in (
        Detection.DESCRIPTOR,
        RemoteIdObservation.DESCRIPTOR,
        AdsbObservation.DESCRIPTOR,
    ):
        for field in descriptor.fields:
            assert "forg" not in field.name and "fals" not in field.name


_RADIO_MODULES = frozenset(
    {
        "bleak",
        "bluepy",
        "bluetooth",
        "pybluez",
        "pygatt",
        "btlewrap",
        "scapy",
        "pywifi",
        "wifi",
        "rtlsdr",
        "pyrtlsdr",
        "SoapySDR",
        "soapy",
        "gnuradio",
        "osmosdr",
        "uhd",
        "adi",
        "iio",
        "hackrf",
        "pyhackrf",
        "limesdr",
        "serial",
        "usb",
        "pyudev",
        "esptool",
    }
)


def _imports(source: str) -> list[str]:
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name in {"__import__", "import_module"}:
                found.append("<importación dinámica>")
    return found


@pytest.mark.req("REQ-LEG-001")
def test_negativa_sim_no_importa_bibliotecas_de_radio_wifi_ni_bluetooth() -> None:
    files = sorted(SIM_DIR.rglob("*.py"))
    assert any(f.name == "remote_id.py" for f in files)
    offending = {
        f"{path.relative_to(REPO)}: {name}"
        for path in files
        for name in _imports(path.read_text(encoding="utf-8"))
        if name in _RADIO_MODULES or name == "<importación dinámica>"
    }
    assert offending == set()


@pytest.mark.req("REQ-LEG-001")
def test_negativa_el_detector_de_importaciones_funciona() -> None:
    sample = (
        "import scapy.all\nfrom bleak import BleakScanner\n"
        "import importlib\nimportlib.import_module('x')\n"
    )
    found = _imports(sample)
    assert "scapy" in found and "bleak" in found and "<importación dinámica>" in found


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize(
    "kwargs",
    [
        {"position_sigma_m": 0.0},
        {"position_sigma_m": math.nan},
        {"range_m": -1.0},
        {"forged_offset_m": 50.0},
        {"forged_jump_every": 0},
        {"forged_min_turn_deg": 0.0},
        {"forged_min_turn_deg": 200.0},
        {"forgery_threshold_m": 10.0},
    ],
)
def test_negativa_modelo_remote_id_invalido(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        RemoteIdModel(**kwargs)  # type: ignore[arg-type]


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize("kwargs", [{"position_sigma_m": -1.0}, {"range_m": math.inf}])
def test_negativa_modelo_adsb_invalido(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        AdsbModel(**kwargs)


@pytest.mark.req("REQ-LEG-007")
def test_negativa_identidad_no_sintetica_rechazada() -> None:
    with pytest.raises(ValueError, match="sintético"):
        remote_id.build_detection(
            declared=(0.0, 0.0, 50.0),
            declared_operator=(0.0, 0.0, 0.0),
            center={"lat_deg": 36.2, "lon_deg": -4.1},
            identity=remote_id.Identity("ESP-REAL-0001", "SIM-OP-1"),
            standard=remote_id.STANDARDS["EN_4709_002"],
            site_id="s",
            node_id="n",
            now_ns=0,
            pps=True,
            model=RemoteIdModel(),
            rng=Random(1),  # noqa: S311
            clock_rng=Random(2),  # noqa: S311
        )

"""T1.11: trayectorias C1-C7 (y C8 para ADS-B) con límites cinemáticos por clase (REQ-FUN-004).

Propiedades (`hypothesis`): la velocidad y la aceleración nunca superan el máximo de la clase;
la trayectoria pasa por los puntos de paso dentro de su tolerancia; solo C1-C2 admiten vuelo
estacionario. Cada valor del catálogo lleva su fuente o la marca NO VERIFICADO.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from sim.classes import CATALOG, ClassKinematics, Sourced, catalog_problems, kinematics
from sim.scenario import load_scenario
from sim.trajectory import Trajectory, Waypoint

REPO = Path(__file__).resolve().parents[2]
SCENARIOS = REPO / "sim" / "scenarios"
FLYING = ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8")
SLACK = 1e-6


def _norm(v: tuple[float, float, float]) -> float:
    return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)


def _check_limits(traj: Trajectory, samples: int = 1500) -> None:
    """Comprueba los límites con el estado analítico y con diferencias finitas de la posición."""
    k = kinematics(traj.class_id)
    h = 1e-3
    for i in range(samples + 1):
        t = min(traj.duration_s * i / samples, traj.duration_s)
        state = traj.state(t)
        assert _norm(state.velocity) <= k.max_speed_mps.value * (1 + SLACK)
        assert _norm(state.acceleration) <= k.max_accel_mps2.value * (1 + SLACK)
        if h <= t <= traj.duration_s - h:
            before, after = traj.state(t - h).position, traj.state(t + h).position
            numeric = tuple((a - b) / (2 * h) for a, b in zip(after, before, strict=True))
            assert math.dist(numeric, state.velocity) < 1e-2 * max(1.0, _norm(state.velocity))
            horizontal_rate = _turn_rate_dps(traj, t, h)
            assert horizontal_rate <= k.max_turn_rate_dps.value * (1 + 1e-3) + 1e-6


def _turn_rate_dps(traj: Trajectory, t: float, h: float) -> float:
    v0, v1 = traj.state(t - h).velocity, traj.state(t + h).velocity
    if math.hypot(v0[0], v0[1]) < 0.05 or math.hypot(v1[0], v1[1]) < 0.05:
        return 0.0
    delta = math.atan2(v1[1], v1[0]) - math.atan2(v0[1], v0[0])
    delta = (delta + math.pi) % (2 * math.pi) - math.pi
    return abs(math.degrees(delta)) / (2 * h)


def _min_distance(traj: Trajectory, point: Waypoint, samples: int = 4000) -> float:
    target = (point.east_m, point.north_m, point.up_m)
    best = math.inf
    for i in range(samples + 1):
        best = min(
            best,
            math.dist(
                traj.state(min(traj.duration_s * i / samples, traj.duration_s)).position, target
            ),
        )
    return best


# --- catálogo ------------------------------------------------------------------------------


@pytest.mark.req("REQ-FUN-004")
def test_catalogo_cubre_c1_a_c8_con_fuente_o_no_verificado() -> None:
    assert tuple(sorted(CATALOG)) == FLYING
    assert catalog_problems(CATALOG) == []
    for class_id, entry in CATALOG.items():
        assert entry.class_id == class_id
        assert 0 < entry.cruise_speed_mps.value <= entry.max_speed_mps.value
        assert entry.max_accel_mps2.value > 0
        assert entry.max_turn_rate_dps.value > 0


@pytest.mark.req("REQ-FUN-004")
def test_solo_c1_y_c2_admiten_vuelo_estacionario() -> None:
    assert {c for c, e in CATALOG.items() if e.can_hover} == {"C1", "C2"}


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize("source", ["", "   ", "aproximado"])
def test_negativa_catalogo_sin_fuente_ni_marca(source: str) -> None:
    good = CATALOG["C1"]
    bad = ClassKinematics(
        class_id="C1",
        description=good.description,
        cruise_speed_mps=good.cruise_speed_mps,
        max_speed_mps=Sourced(19.0, source),
        max_accel_mps2=good.max_accel_mps2,
        max_turn_rate_dps=good.max_turn_rate_dps,
        can_hover=True,
    )
    problems = catalog_problems({"C1": bad})
    assert problems
    assert "C1" in problems[0]
    assert "max_speed_mps" in problems[0]


@pytest.mark.req("REQ-FUN-004")
def test_catalogo_detecta_crucero_mayor_que_maximo() -> None:
    good = CATALOG["C5"]
    bad = ClassKinematics(
        class_id="C5",
        description=good.description,
        cruise_speed_mps=Sourced(good.max_speed_mps.value + 1, "NO VERIFICADO: prueba"),
        max_speed_mps=good.max_speed_mps,
        max_accel_mps2=good.max_accel_mps2,
        max_turn_rate_dps=good.max_turn_rate_dps,
        can_hover=False,
    )
    assert catalog_problems({"C5": bad})


@pytest.mark.req("REQ-FUN-004")
def test_clase_desconocida_rechazada() -> None:
    with pytest.raises(ValueError, match="C9"):
        kinematics("C9")


# --- un test por clase ---------------------------------------------------------------------


def _class_route(class_id: str) -> tuple[list[Waypoint], float]:
    k = kinematics(class_id)
    v = k.cruise_speed_mps.value
    r = Trajectory.turn_radius_m(class_id, v)
    leg = 4 * r + 4 * v * v / k.max_accel_mps2.value + 200.0
    return [
        Waypoint(0.0, 0.0, 100.0),
        Waypoint(leg, 0.0, 110.0),
        Waypoint(leg, leg, 100.0),
        Waypoint(2 * leg, leg, 100.0),
    ], v


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize("class_id", FLYING)
def test_trayectoria_por_clase(class_id: str) -> None:
    route, speed = _class_route(class_id)
    traj = Trajectory(class_id, route, speed)
    _check_limits(traj, samples=800)
    start, end = traj.state(0.0), traj.state(traj.duration_s)
    assert math.dist(start.position, (0.0, 0.0, 100.0)) < 1e-6
    assert math.dist(end.position, (route[-1].east_m, route[-1].north_m, route[-1].up_m)) < 1e-6
    for index, point in enumerate(route):
        assert _min_distance(traj, point, samples=2000) <= traj.waypoint_tolerance_m[index] + (
            speed * traj.duration_s / 2000
        )
    if CATALOG[class_id].can_hover:
        assert _norm(start.velocity) == 0.0
        assert _norm(end.velocity) == 0.0
    else:
        assert _norm(start.velocity) == pytest.approx(speed)


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize("class_id", ["C1", "C2"])
def test_vuelo_estacionario_multirrotor(class_id: str) -> None:
    route = [
        Waypoint(0.0, 0.0, 50.0),
        Waypoint(400.0, 0.0, 50.0, hover_s=20.0),
        Waypoint(400.0, 400.0, 60.0),
    ]
    traj = Trajectory(class_id, route, 8.0)
    arrival = traj.waypoint_times_s[1]
    for dt in (0.0, 5.0, 19.9):
        state = traj.state(arrival + dt)
        assert state.position == pytest.approx((400.0, 0.0, 50.0), abs=1e-9)
        assert _norm(state.velocity) == 0.0
    _check_limits(traj)


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize("class_id", ["C3", "C4", "C5", "C6", "C7", "C8"])
def test_negativa_vuelo_estacionario_no_admitido(class_id: str) -> None:
    route = [Waypoint(0.0, 0.0, 50.0), Waypoint(5000.0, 0.0, 50.0, hover_s=5.0)]
    with pytest.raises(ValueError, match=f"{class_id}.*estacionario"):
        Trajectory(class_id, route, kinematics(class_id).cruise_speed_mps.value)


# --- rutas imposibles ----------------------------------------------------------------------


@pytest.mark.req("REQ-FUN-004")
def test_negativa_c1_a_60_mps() -> None:
    with pytest.raises(ValueError, match=r"C1.*60.*máximo.*m/s") as info:
        Trajectory("C1", [Waypoint(0, 0, 50), Waypoint(1000, 0, 50)], 60.0)
    assert f"{kinematics('C1').max_speed_mps.value:g}" in str(info.value)


@pytest.mark.req("REQ-FUN-004")
def test_negativa_c6_giro_de_90_grados_en_1_s() -> None:
    speed = kinematics("C6").cruise_speed_mps.value
    route = [Waypoint(0, 0, 150), Waypoint(5000, 0, 150), Waypoint(5000, speed * 1.0, 150)]
    with pytest.raises(ValueError, match=r"C6.*giro de 90.*°/s") as info:
        Trajectory("C6", route, speed)
    assert f"{kinematics('C6').max_turn_rate_dps.value:g}" in str(info.value)


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize(
    ("route", "speed", "match"),
    [
        ([Waypoint(0, 0, 0)], 10.0, "al menos dos"),
        ([Waypoint(0, 0, 0), Waypoint(0, 0, 0)], 10.0, "horizontal"),
        ([Waypoint(0, 0, 0), Waypoint(100, 0, 0)], 0.0, "velocidad"),
        ([Waypoint(0, 0, 0), Waypoint(100, 0, 0)], math.nan, "velocidad"),
        ([Waypoint(0, 0, 0), Waypoint(100, 0, 500)], 10.0, "vertical"),
        ([Waypoint(0, 0, 0), Waypoint(100, 0, 0), Waypoint(0, 0, 0)], 10.0, "giro"),
        ([Waypoint(0, 0, 0), Waypoint(math.inf, 0, 0)], 10.0, "finit"),
        ([Waypoint(0, 0, 0, hover_s=-1.0), Waypoint(100, 0, 0)], 5.0, "estacionario"),
    ],
)
def test_negativa_rutas_invalidas(route: list[Waypoint], speed: float, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        Trajectory("C2", route, speed)


@pytest.mark.req("REQ-FUN-004")
def test_estado_fuera_de_la_duracion_rechazado() -> None:
    traj = Trajectory("C5", [Waypoint(0, 0, 100), Waypoint(2000, 0, 100)], 20.0)
    assert traj.duration_s == pytest.approx(100.0)
    for t in (-0.1, traj.duration_s + 0.1, math.nan):
        with pytest.raises(ValueError, match="instante"):
            traj.state(t)


# --- propiedades ---------------------------------------------------------------------------


@st.composite
def _routes(draw: st.DrawFn) -> tuple[str, list[Waypoint], float]:
    class_id = draw(st.sampled_from(FLYING))
    k = kinematics(class_id)
    speed = draw(st.floats(0.3, 0.95)) * k.max_speed_mps.value
    radius = Trajectory.turn_radius_m(class_id, speed)
    min_leg = 2 * radius * math.tan(math.radians(60)) + 4 * speed * speed / k.max_accel_mps2.value
    count = draw(st.integers(2, 5))
    heading = draw(st.floats(-math.pi, math.pi))
    east, north, up = 0.0, 0.0, draw(st.floats(20.0, 500.0))
    hover = k.can_hover and draw(st.booleans())
    points = [Waypoint(east, north, up)]
    for index in range(count - 1):
        if index:
            heading += math.radians(draw(st.floats(-120.0, 120.0)))
        leg = min_leg * draw(st.floats(1.05, 3.0)) + 10.0
        east += leg * math.cos(heading)
        north += leg * math.sin(heading)
        up = max(10.0, up + leg * draw(st.floats(-0.05, 0.05)))
        hover_s = draw(st.floats(0.0, 30.0)) if hover and index < count - 2 else 0.0
        points.append(Waypoint(east, north, up, hover_s=hover_s))
    return class_id, points, speed


@pytest.mark.req("REQ-FUN-004")
@settings(max_examples=60, deadline=None, derandomize=True)
@given(case=_routes())
def test_propiedad_limites_de_clase_y_puntos_de_paso(
    case: tuple[str, list[Waypoint], float],
) -> None:
    class_id, route, speed = case
    try:
        traj = Trajectory(class_id, route, speed)
    except ValueError:
        assume(False)
        raise
    _check_limits(traj, samples=600)
    samples = 3000
    slack = speed * traj.duration_s / samples
    for index, point in enumerate(route):
        assert _min_distance(traj, point, samples) <= traj.waypoint_tolerance_m[index] + slack
    times = traj.waypoint_times_s
    assert times == sorted(times)
    for index, point in enumerate(route):
        if point.hover_s > 0:
            assert _norm(traj.state(times[index] + point.hover_s / 2).velocity) == 0.0


# --- escenarios ----------------------------------------------------------------------------


@pytest.mark.req("REQ-FUN-004", "REQ-FUN-005")
@pytest.mark.parametrize("name", ["prision_ceuta", "puerto_ceuta", "aerodromo", "frontera_8km"])
def test_rutas_de_los_escenarios_son_factibles(name: str) -> None:
    scenario = load_scenario(SCENARIOS / f"{name}.yaml")
    for group in ("threats", "manned_aircraft"):
        for item in scenario.data[group]:
            route = [Waypoint(p["east_m"], p["north_m"], p["up_m"]) for p in item["route"]]
            traj = Trajectory(item["class"], route, float(item["speed_mps"]))
            _check_limits(traj, samples=300)


@pytest.mark.req("REQ-FUN-004")
def test_negativa_pendiente_vertical_supera_velocidad_maxima() -> None:
    with pytest.raises(ValueError, match=r"C2: pendiente vertical.*\(máximo 15 m/s\)"):
        Trajectory("C2", [Waypoint(0, 0, 0), Waypoint(1000, 0, 300)], 14.0)


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize("class_id", FLYING)
def test_radio_de_giro_respeta_tasa_y_aceleracion(class_id: str) -> None:
    k = kinematics(class_id)
    omega = math.radians(k.max_turn_rate_dps.value)
    for speed in (0.05, 1.0, k.cruise_speed_mps.value):
        radius = Trajectory.turn_radius_m(class_id, speed)
        assert speed / radius <= omega * (1 + 1e-12)
        assert speed * speed / radius <= k.max_accel_mps2.value / 2 * (1 + 1e-12)
        assert radius == max(speed / omega, 2 * speed * speed / k.max_accel_mps2.value)


@pytest.mark.req("REQ-FUN-004")
def test_giro_a_baja_velocidad_limitado_por_tasa_de_giro() -> None:
    # A 1 m/s, en C1 manda la tasa de giro (no la aceleración): el radio es v/ω.
    route = [Waypoint(0, 0, 10), Waypoint(30, 0, 10), Waypoint(30, 30, 10)]
    traj = Trajectory("C1", route, 1.0)
    assert traj.radius == pytest.approx(1.0 / math.radians(120.0))
    _check_limits(traj, samples=3000)

"""T1.10: núcleo del simulador y reproducibilidad (REQ-FUN-003).

El mismo escenario con la misma semilla, en dos procesos con `PYTHONHASHSEED` distinto, produce
el mismo SHA-256 del flujo sin comprimir y del `.pb.zst`. `geo` conserva la posición en la ida y
vuelta WGS84 → ENU → WGS84 con error < 1 mm a 10 km (propiedades con `hypothesis`).
"""

from __future__ import annotations

import ast
import hashlib
import math
import os
import random
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from atalaya_contracts.validate import validate
from hypothesis import given, settings
from hypothesis import strategies as st

from sim import clock, geo, rng
from sim.engine import Engine, build_engine, compress_stream, encode_stream
from sim.scenario import load_scenario

REPO = Path(__file__).resolve().parents[2]
SCENARIOS = REPO / "sim" / "scenarios"
SCENARIO = SCENARIOS / "prision_ceuta.yaml"
SIM_DIR = REPO / "sim"
PYTHONPATH = os.pathsep.join(
    [str(REPO / "proto/gen/python"), str(REPO / "proto/python"), str(REPO)]
)
DURATION_S = "120"


# --- rng: subsemillas por componente -------------------------------------------------------


@pytest.mark.req("REQ-FUN-003")
def test_subsemilla_es_sha256_de_semilla_y_componente() -> None:
    material = b"atalaya-sim-v1\x00" + b"42" + b"\x00" + b"reloj/rc-and-1"
    expected = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    assert rng.derive_seed(42, "reloj/rc-and-1") == expected
    assert rng.derive_seed(42, "reloj/rc-and-1") != rng.derive_seed(43, "reloj/rc-and-1")
    assert rng.derive_seed(42, "a") != rng.derive_seed(42, "b")


@pytest.mark.req("REQ-FUN-003")
def test_componentes_independientes_entre_si() -> None:
    solo = rng.RngRegistry(7)
    reference = [solo.get("a").random() for _ in range(5)]
    mixed = rng.RngRegistry(7)
    for _ in range(100):
        mixed.get("b").random()
    assert [mixed.get("a").random() for _ in range(5)] == reference
    assert mixed.get("a") is mixed.get("a")


@pytest.mark.req("REQ-FUN-003")
@pytest.mark.parametrize("seed", [-1, 2**64, True, 1.5])
def test_semilla_invalida_rechazada(seed: object) -> None:
    with pytest.raises(ValueError, match="semilla"):
        rng.derive_seed(seed, "a")  # type: ignore[arg-type]


@pytest.mark.req("REQ-FUN-003")
def test_componente_sin_nombre_rechazado() -> None:
    with pytest.raises(ValueError, match="componente"):
        rng.derive_seed(1, "")


# --- engine: cola de eventos determinista --------------------------------------------------


@pytest.mark.req("REQ-FUN-003")
def test_cola_ordena_por_tiempo_y_secuencia() -> None:
    engine = Engine(seed=1)
    order: list[str] = []
    engine.schedule(20, lambda _e: order.append("t20"))
    engine.schedule(10, lambda _e: order.append("t10-a"))
    engine.schedule(10, lambda _e: order.append("t10-b"))
    engine.schedule(0, lambda e: e.schedule(10, lambda _e: order.append("t10-c")))
    engine.run(until_ns=100)
    assert order == ["t10-a", "t10-b", "t10-c", "t20"]
    assert engine.now_ns == 20


@pytest.mark.req("REQ-FUN-003")
def test_cola_no_ejecuta_eventos_despues_del_final() -> None:
    engine = Engine(seed=1)
    order: list[int] = []
    engine.schedule(50, lambda _e: order.append(50))
    engine.schedule(51, lambda _e: order.append(51))
    engine.run(until_ns=50)
    assert order == [50]


@pytest.mark.req("REQ-FUN-003")
@pytest.mark.parametrize("bad", [-1, 1.0, True])
def test_cola_rechaza_tiempo_invalido(bad: object) -> None:
    engine = Engine(seed=1)
    with pytest.raises(ValueError, match="tiempo"):
        engine.schedule(bad, lambda _e: None)  # type: ignore[arg-type]


@pytest.mark.req("REQ-FUN-003")
def test_cola_rechaza_evento_en_el_pasado() -> None:
    engine = Engine(seed=1)
    engine.schedule(10, lambda e: e.schedule(5, lambda _e: None))
    with pytest.raises(ValueError, match="pasado"):
        engine.run(until_ns=100)


# --- clock ---------------------------------------------------------------------------------


@pytest.mark.req("REQ-FUN-003")
def test_reloj_simulado_sin_reloj_del_sistema() -> None:
    start = clock.to_timestamp(0)
    assert (start.seconds, start.nanos) == (clock.SIM_EPOCH_UNIX_S, 0)
    later = clock.to_timestamp(clock.seconds_to_ns(1.5) + 7)
    assert (later.seconds, later.nanos) == (clock.SIM_EPOCH_UNIX_S + 1, 500_000_007)
    assert clock.seconds_to_ns(30.0) == 30_000_000_000
    with pytest.raises(ValueError):
        clock.to_timestamp(-1)
    with pytest.raises(ValueError):
        clock.seconds_to_ns(math.nan)


# --- geo: WGS84 ↔ ENU ----------------------------------------------------------------------


def _distance_m(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.dist(geo.geodetic_to_ecef(*a), geo.geodetic_to_ecef(*b))


@pytest.mark.req("REQ-FUN-003")
def test_geo_valores_conocidos() -> None:
    x, y, z = geo.geodetic_to_ecef(0.0, 0.0, 0.0)
    assert (x, y, z) == pytest.approx((geo.WGS84_A, 0.0, 0.0), abs=1e-6)
    _, _, z_pole = geo.geodetic_to_ecef(90.0, 0.0, 0.0)
    assert z_pole == pytest.approx(geo.WGS84_A * (1 - geo.WGS84_F), abs=1e-6)
    east, north, up = geo.geodetic_to_enu(0.0, 0.001, 0.0, 0.0, 0.0, 0.0)
    assert east == pytest.approx(111.319, abs=1e-3)
    assert abs(north) < 1e-3
    assert abs(up) < 1e-2
    lat, lon, alt = geo.enu_to_geodetic(0.0, 0.0, 0.0, 36.2, -4.1, 0.0)
    assert (lat, lon, alt) == pytest.approx((36.2, -4.1, 0.0), abs=1e-12)


_REF = st.tuples(
    st.floats(min_value=-85.0, max_value=85.0),
    st.floats(min_value=-180.0, max_value=180.0),
    st.floats(min_value=-100.0, max_value=3000.0),
)
_ENU_10KM = st.tuples(
    st.floats(min_value=-10_000.0, max_value=10_000.0),
    st.floats(min_value=-10_000.0, max_value=10_000.0),
    st.floats(min_value=-500.0, max_value=3000.0),
)


@pytest.mark.req("REQ-FUN-003")
@settings(max_examples=300, deadline=None, derandomize=True)
@given(ref=_REF, offset=_ENU_10KM)
def test_geo_ida_y_vuelta_wgs84_enu_wgs84_menos_de_1_mm(
    ref: tuple[float, float, float], offset: tuple[float, float, float]
) -> None:
    point = geo.enu_to_geodetic(*offset, *ref)
    enu = geo.geodetic_to_enu(*point, *ref)
    back = geo.enu_to_geodetic(*enu, *ref)
    assert _distance_m(point, back) < 1e-3
    assert math.dist(enu, offset) < 1e-3


@pytest.mark.req("REQ-FUN-003")
@pytest.mark.parametrize("lat", [90.5, -91.0, math.nan])
def test_geo_rechaza_latitud_invalida(lat: float) -> None:
    with pytest.raises(ValueError, match="latitud"):
        geo.geodetic_to_ecef(lat, 0.0, 0.0)


# --- motor con un escenario ----------------------------------------------------------------


def _run_in_process(seed: int, duration_s: float = 120.0) -> bytes:
    engine = build_engine(load_scenario(SCENARIO), seed=seed, duration_s=duration_s)
    return encode_stream(engine.run_all())


@pytest.mark.req("REQ-FUN-003", "REQ-FUN-062")
def test_escenario_emite_envelopes_validos_y_ordenados() -> None:
    engine = build_engine(load_scenario(SCENARIO), seed=11, duration_s=120.0)
    envelopes = engine.run_all()
    assert envelopes, "el escenario debe emitir mensajes"
    assert [e.sequence for e in envelopes] == list(range(len(envelopes)))
    times = [(e.emitted_at.seconds, e.emitted_at.nanos) for e in envelopes]
    assert times == sorted(times)
    for envelope in envelopes:
        assert validate(envelope) == []
        assert envelope.WhichOneof("payload") == "node_status"


@pytest.mark.req("REQ-FUN-003")
def test_misma_semilla_mismo_flujo_en_el_mismo_proceso() -> None:
    assert _run_in_process(5) == _run_in_process(5)
    assert compress_stream(_run_in_process(5)) == compress_stream(_run_in_process(5))


@pytest.mark.req("REQ-FUN-003")
def test_semilla_por_defecto_del_escenario() -> None:
    scenario = load_scenario(SCENARIO)
    default = scenario.data["seed_policy"]["default_seed"]
    assert build_engine(scenario, seed=None, duration_s=60.0).seed == default


@pytest.mark.req("REQ-FUN-003")
@pytest.mark.parametrize("duration", [0.0, -1.0, math.inf, math.nan])
def test_duracion_invalida_rechazada(duration: float) -> None:
    with pytest.raises(ValueError, match="duración"):
        build_engine(load_scenario(SCENARIO), seed=1, duration_s=duration)


# --- CLI y reproducibilidad entre procesos -------------------------------------------------


def _env(hashseed: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    env["PYTHONHASHSEED"] = hashseed
    env["PYTHONPATH"] = PYTHONPATH
    return env


def _cli(*args: str, hashseed: str = "0") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "sim", *args],
        cwd=REPO,
        env=_env(hashseed),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def _parse_hashes(stdout: str) -> dict[str, str]:
    pairs = (line.split("=", 1) for line in stdout.splitlines() if "=" in line)
    return {key: value for key, value in pairs}


def _run_cli(out: Path, seed: str, hashseed: str) -> dict[str, str]:
    result = _cli(
        "run", "--scenario", str(SCENARIO), "--seed", seed, "--duration", DURATION_S,
        "--out", str(out), hashseed=hashseed,
    )  # fmt: skip
    assert result.returncode == 0, result.stderr
    return _parse_hashes(result.stdout)


@pytest.mark.req("REQ-FUN-003")
@pytest.mark.subproceso
def test_misma_semilla_mismo_sha256_en_dos_procesos_con_hashseed_distinto(
    tmp_path: Path,
) -> None:
    first = _run_cli(tmp_path / "a.pb.zst", "20261111", hashseed="0")
    second = _run_cli(tmp_path / "b.pb.zst", "20261111", hashseed="4242")
    assert set(first) == {"stream_sha256", "file_sha256"}
    assert first == second
    data_a = (tmp_path / "a.pb.zst").read_bytes()
    assert data_a == (tmp_path / "b.pb.zst").read_bytes()
    assert first["file_sha256"] == hashlib.sha256(data_a).hexdigest()
    checked = _cli("hash", str(tmp_path / "a.pb.zst"), hashseed="99")
    assert checked.returncode == 0, checked.stderr
    assert _parse_hashes(checked.stdout) == first


@pytest.mark.req("REQ-FUN-003")
@pytest.mark.subproceso
def test_negativa_semilla_distinta_hash_distinto(tmp_path: Path) -> None:
    first = _run_cli(tmp_path / "a.pb.zst", "1", hashseed="0")
    second = _run_cli(tmp_path / "b.pb.zst", "2", hashseed="0")
    assert first["stream_sha256"] != second["stream_sha256"]
    assert first["file_sha256"] != second["file_sha256"]


@pytest.mark.req("REQ-FUN-003")
@pytest.mark.subproceso
def test_cli_rechaza_entradas_invalidas(tmp_path: Path) -> None:
    bad_seed = _cli(
        "run", "--scenario", str(SCENARIO), "--seed", "-3", "--out", str(tmp_path / "x")
    )
    assert bad_seed.returncode == 2
    assert "semilla" in bad_seed.stderr
    missing = _cli("hash", str(tmp_path / "no-existe.pb.zst"))
    assert missing.returncode == 2
    assert not (tmp_path / "x").exists()


_GLOBAL_RANDOM_SCRIPT = textwrap.dedent(
    """
    import hashlib, random, sys
    from pathlib import Path
    from atalaya.v1.node_status_pb2 import NodeStatus
    from sim.engine import build_engine, encode_stream
    from sim.scenario import load_scenario

    def contaminar(engine):
        # Componente defectuoso inyectado: usa el `random` global (sembrado por el SO).
        def tick(e):
            status = NodeStatus(site_id="recinto", node_id="x", battery_percent=random.random())
            e.emit("recinto", "x", status)
        engine.schedule(0, tick)

    engine = build_engine(load_scenario(Path(sys.argv[1])), seed=7, duration_s=60.0,
                          extra_components=[contaminar])
    print("stream_sha256=" + hashlib.sha256(encode_stream(engine.run_all())).hexdigest())
    """
)


@pytest.mark.req("REQ-FUN-003")
@pytest.mark.subproceso
def test_negativa_random_global_inyectado_rompe_la_igualdad(tmp_path: Path) -> None:
    script = tmp_path / "contaminado.py"
    script.write_text(_GLOBAL_RANDOM_SCRIPT, encoding="utf-8")

    def run(hashseed: str) -> str:
        result = subprocess.run(
            [sys.executable, str(script), str(SCENARIO)],
            cwd=REPO, env=_env(hashseed), capture_output=True, text=True, check=False, timeout=120,
        )  # fmt: skip
        assert result.returncode == 0, result.stderr
        return _parse_hashes(result.stdout)["stream_sha256"]

    # La comprobación de igualdad entre procesos detecta la contaminación.
    assert run("0") != run("0")


# --- análisis estático: sin fuentes de no determinismo en sim/ -------------------------------

_FORBIDDEN_CALLS = {
    ("random", name)
    for name in ("random", "randint", "uniform", "gauss", "choice", "shuffle", "seed", "sample")
} | {
    ("time", "time"),
    ("time", "time_ns"),
    ("time", "monotonic"),
    ("time", "perf_counter"),
    ("datetime", "now"),
    ("datetime", "utcnow"),
    ("datetime", "today"),
    ("uuid", "uuid1"),
    ("uuid", "uuid4"),
    ("os", "urandom"),
}


def nondeterminism(source: str) -> list[str]:
    """Llamadas a fuentes no deterministas (azar global, reloj, `hash`, uuid, `secrets`)."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import | ast.ImportFrom):
            modules = (
                [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module]
            )
            if "secrets" in modules:
                found.append(f"{node.lineno}: secrets")
            if isinstance(node, ast.ImportFrom) and node.module == "random":
                found.extend(
                    f"{node.lineno}: from random import {a.name}"
                    for a in node.names
                    if a.name != "Random"
                )
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "hash":
                found.append(f"{node.lineno}: hash()")
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and (func.value.id, func.attr) in _FORBIDDEN_CALLS
            ):
                found.append(f"{node.lineno}: {func.value.id}.{func.attr}()")
    return found


@pytest.mark.req("REQ-FUN-003")
def test_sim_no_usa_fuentes_no_deterministas() -> None:
    files = sorted(SIM_DIR.rglob("*.py"))
    assert len(files) >= 5
    offenders = {
        str(f.relative_to(REPO)): hits
        for f in files
        if (hits := nondeterminism(f.read_text(encoding="utf-8")))
    }
    assert offenders == {}


@pytest.mark.req("REQ-FUN-003")
@pytest.mark.parametrize(
    "snippet",
    [
        "import random\nx = random.random()",
        "from random import gauss",
        "import time\nt = time.time()",
        "from datetime import datetime\nd = datetime.now()",
        "import uuid\nu = uuid.uuid4()",
        "k = hash('a')",
        "import secrets",
        "import os\nb = os.urandom(4)",
    ],
)
def test_negativa_analisis_estatico_detecta_no_determinismo(snippet: str) -> None:
    assert nondeterminism(snippet)


@pytest.mark.req("REQ-FUN-003")
def test_analisis_estatico_admite_random_instanciado() -> None:
    assert nondeterminism("from random import Random\nr = Random(1)\nx = r.random()") == []
    assert random.Random(3).random() == random.Random(3).random()  # noqa: S311

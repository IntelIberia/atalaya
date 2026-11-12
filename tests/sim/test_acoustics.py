"""T1.12: propagación acústica y modelo de detección (REQ-FUN-004, REQ-FUN-062).

Propiedad exigida por REQ-FUN-004: sin viento, el nivel recibido decrece estrictamente con la
distancia. Además: −6,0 ± 0,1 dB por duplicación sin absorción; la absorción crece con la
frecuencia en las bandas usadas; el viento a favor da más nivel que en contra; la absorción
reproduce una tabla de referencia citada; toda `Detection` generada pasa `validate()`.
El simulador trabaja con niveles por banda y nunca con audio.
"""

from __future__ import annotations

import ast
import itertools
import math
from pathlib import Path
from random import Random

import pytest
from atalaya.v1.detection_pb2 import SENSOR_TYPE_ACOUSTIC, Detection
from atalaya_contracts.validate import validate
from hypothesis import given, settings
from hypothesis import strategies as st

from sim import acoustics
from sim.acoustics import Atmosphere
from sim.engine import build_engine
from sim.scenario import load_scenario
from sim.sensors import acoustic
from sim.sensors.acoustic import DetectionModel

REPO = Path(__file__).resolve().parents[2]
SIM_DIR = REPO / "sim"
SCENARIOS = REPO / "sim" / "scenarios"
NAMES = ("prision_ceuta", "puerto_ceuta", "aerodromo", "frontera_8km")
BANDS = (125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0)
STD = Atmosphere(temperature_c=20.0, relative_humidity_pct=70.0)

atmospheres = st.builds(
    Atmosphere,
    temperature_c=st.floats(-20.0, 50.0),
    relative_humidity_pct=st.floats(0.0, 100.0),
    pressure_kpa=st.floats(80.0, 105.0),
)
distances = st.floats(1.0, 20000.0)


# --- divergencia esférica ------------------------------------------------------------------


@pytest.mark.req("REQ-FUN-004")
@given(r=st.floats(1.0, 10000.0))
@settings(max_examples=200, derandomize=True)
def test_seis_db_por_duplicacion_sin_absorcion(r: float) -> None:
    near = acoustics.received_level_db(90.0, 1000.0, r, STD, include_absorption=False)
    far = acoustics.received_level_db(90.0, 1000.0, 2 * r, STD, include_absorption=False)
    assert far - near == pytest.approx(-6.0, abs=0.1)


@pytest.mark.req("REQ-FUN-004")
def test_nivel_de_referencia_a_un_metro() -> None:
    assert acoustics.spherical_spreading_db(acoustics.REFERENCE_DISTANCE_M) == 0.0
    assert acoustics.spherical_spreading_db(10.0) == pytest.approx(20.0)


# --- propiedad de REQ-FUN-004 ----------------------------------------------------------------


@pytest.mark.req("REQ-FUN-004")
@given(
    atm=atmospheres,
    freq=st.sampled_from(BANDS),
    r1=distances,
    factor=st.floats(1.0001, 50.0),
)
@settings(max_examples=300, derandomize=True)
def test_sin_viento_el_nivel_decrece_estrictamente_con_la_distancia(
    atm: Atmosphere, freq: float, r1: float, factor: float
) -> None:
    r2 = r1 * factor
    near = acoustics.received_level_db(85.0, freq, r1, atm)
    far = acoustics.received_level_db(85.0, freq, r2, atm)
    assert far < near


@pytest.mark.req("REQ-FUN-004")
@given(
    atm=atmospheres,
    along=st.floats(-40.0, 40.0),
    r1=distances,
    factor=st.floats(1.0001, 50.0),
)
@settings(max_examples=300, derandomize=True)
def test_con_viento_constante_el_nivel_tampoco_crece_con_la_distancia(
    atm: Atmosphere, along: float, r1: float, factor: float
) -> None:
    near = acoustics.received_level_db(85.0, 500.0, r1, atm, along_wind_mps=along)
    far = acoustics.received_level_db(85.0, 500.0, r1 * factor, atm, along_wind_mps=along)
    assert far < near


# --- absorción atmosférica -------------------------------------------------------------------


@pytest.mark.req("REQ-FUN-004")
@given(atm=atmospheres)
@settings(max_examples=300, derandomize=True)
def test_absorcion_crece_con_la_frecuencia_en_las_bandas_usadas(atm: Atmosphere) -> None:
    values = [acoustics.absorption_db_per_m(f, atm) for f in BANDS]
    assert all(b > a > 0 for a, b in itertools.pairwise(values))


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize("name", NAMES)
def test_absorcion_crece_con_la_frecuencia_en_cada_escenario(name: str) -> None:
    scenario = load_scenario(SCENARIOS / f"{name}.yaml")
    atm = acoustics.atmosphere_from_scenario(scenario.data["environment"])
    bands = sorted(b["center_hz"] for b in scenario.data["environment"]["background_bands"])
    values = [acoustics.absorption_db_per_m(f, atm) for f in bands]
    assert all(b > a for a, b in itertools.pairwise(values))


# Tabla de referencia (coeficiente de absorción en dB/km a 101,325 kPa, frecuencias de banda
# exactas de base diez 1000·10^(n/10)), tal como la reproduce Wikibooks, «Engineering Acoustics/
# Outdoor Sound Propagation», Tabla 1, citando a Crocker, *Handbook of Acoustics* (Wiley, 1998):
# https://en.wikibooks.org/wiki/Engineering_Acoustics/Outdoor_Sound_Propagation (consultada el
# 2026-11-12). Es una fuente secundaria; el contraste con la Tabla 1 de la propia ISO 9613-1
# (de pago) queda NO VERIFICADO.
_EXACT = tuple(1000.0 * 10 ** (n / 10) for n in (-12, -9, -6, -3, 0, 3, 6, 9))
_REFERENCE_DB_PER_KM = {
    (30.0, 10.0): (0.362, 0.958, 1.82, 3.40, 8.67, 28.5, 96.0, 260.0),
    (20.0, 50.0): (0.123, 0.445, 1.32, 2.73, 4.66, 9.86, 29.4, 104.0),
    (20.0, 70.0): (0.090, 0.339, 1.13, 2.80, 4.98, 9.02, 22.9, 76.6),
    (10.0, 70.0): (0.122, 0.411, 1.04, 1.93, 3.66, 9.66, 32.8, 117.0),
    (0.0, 10.0): (0.424, 1.30, 4.00, 9.25, 14.0, 16.6, 19.0, 26.4),
    (0.0, 90.0): (0.127, 0.367, 0.760, 1.45, 3.66, 12.1, 43.2, 138.0),
}


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize(("conditions", "expected"), sorted(_REFERENCE_DB_PER_KM.items()))
def test_absorcion_frente_a_tabla_de_referencia_citada(
    conditions: tuple[float, float], expected: tuple[float, ...]
) -> None:
    atm = Atmosphere(temperature_c=conditions[0], relative_humidity_pct=conditions[1])
    for freq, value in zip(_EXACT, expected, strict=True):
        got = acoustics.absorption_db_per_m(freq, atm) * 1000.0
        # La tabla tiene tres cifras significativas: tolerancia relativa del 1 %.
        assert got == pytest.approx(value, rel=0.01), (conditions, freq)


@pytest.mark.req("REQ-FUN-004")
def test_coeficientes_iso_9613_1_declaran_su_fuente() -> None:
    assert acoustics.ISO_9613_1_SOURCES
    for source in acoustics.ISO_9613_1_SOURCES:
        assert source.startswith("https://")
    assert "NO VERIFICADO" in acoustics.ISO_9613_1_STATUS


# --- velocidad del sonido y viento -----------------------------------------------------------


@pytest.mark.req("REQ-FUN-004")
def test_velocidad_del_sonido_segun_temperatura() -> None:
    assert acoustics.speed_of_sound_mps(20.0) == pytest.approx(343.2)
    assert acoustics.speed_of_sound_mps(0.0) == pytest.approx(343.2 * math.sqrt(273.15 / 293.15))
    assert acoustics.speed_of_sound_mps(30.0) > acoustics.speed_of_sound_mps(-10.0)


@pytest.mark.req("REQ-FUN-004")
@given(r=st.floats(2.0, 20000.0), wind=st.floats(0.5, 40.0), freq=st.sampled_from(BANDS))
@settings(max_examples=200, derandomize=True)
def test_viento_a_favor_da_mas_nivel_que_en_contra(r: float, wind: float, freq: float) -> None:
    downwind = acoustics.received_level_db(85.0, freq, r, STD, along_wind_mps=wind)
    calm = acoustics.received_level_db(85.0, freq, r, STD, along_wind_mps=0.0)
    upwind = acoustics.received_level_db(85.0, freq, r, STD, along_wind_mps=-wind)
    assert downwind > calm > upwind


@pytest.mark.req("REQ-FUN-004")
def test_componente_del_viento_en_la_direccion_de_propagacion() -> None:
    # Viento DEL oeste (270°) sopla hacia el este: fuente al oeste del receptor → a favor.
    source, receiver = (-500.0, 0.0, 50.0), (0.0, 0.0, 2.0)
    assert acoustics.along_wind_mps(8.0, 270.0, source, receiver) == pytest.approx(8.0)
    assert acoustics.along_wind_mps(8.0, 90.0, source, receiver) == pytest.approx(-8.0)
    assert acoustics.along_wind_mps(8.0, 0.0, source, receiver) == pytest.approx(0.0, abs=1e-9)
    assert acoustics.along_wind_mps(8.0, 0.0, (0.0, 0.0, 50.0), receiver) == 0.0


@pytest.mark.req("REQ-FUN-004")
def test_viento_anade_ruido_de_fondo_dominante_en_graves() -> None:
    bands = [{"center_hz": f, "level_db_spl": 40.0} for f in BANDS]
    calm = [acoustics.background_level_db(f, bands, wind_speed_mps=0.0) for f in BANDS]
    windy = [acoustics.background_level_db(f, bands, wind_speed_mps=12.0) for f in BANDS]
    assert calm == pytest.approx([40.0] * len(BANDS))
    assert all(w > c for w, c in zip(windy, calm, strict=True))
    excess = [w - c for w, c in zip(windy, calm, strict=True)]
    assert excess == sorted(excess, reverse=True)


@pytest.mark.req("REQ-FUN-004")
def test_suma_energetica_de_niveles() -> None:
    assert acoustics.energy_sum_db([40.0, 40.0]) == pytest.approx(43.0103, abs=1e-4)
    assert acoustics.energy_sum_db([40.0, -math.inf]) == pytest.approx(40.0)


# --- modelo de detección ---------------------------------------------------------------------


@pytest.mark.req("REQ-FUN-004")
@given(snr=st.floats(-60.0, 60.0), delta=st.floats(0.01, 30.0))
@settings(max_examples=200, derandomize=True)
def test_probabilidad_de_deteccion_monotona_en_snr(snr: float, delta: float) -> None:
    model = DetectionModel()
    low, high = model.probability(snr), model.probability(snr + delta)
    assert 0.0 <= low <= high <= 1.0


@pytest.mark.req("REQ-FUN-004")
def test_la_deteccion_cae_con_la_distancia() -> None:
    env = {
        "temperature_c": 20.0,
        "relative_humidity_pct": 70.0,
        "wind": {"speed_mps": 0.0, "from_deg": 0.0},
        "background_bands": [{"center_hz": f, "level_db_spl": 40.0} for f in BANDS],
    }
    probs = []
    for r in (50.0, 150.0, 400.0, 1200.0, 4000.0):
        obs = acoustic.observe("C2", (r, 0.0, 30.0), (0.0, 0.0, 2.0), env, DetectionModel())
        probs.append(obs.detection_probability)
    assert probs == sorted(probs, reverse=True)
    assert probs[0] > 0.9 > 0.1 > probs[-1]


@pytest.mark.req("REQ-FUN-004")
def test_espectros_de_fuente_declaran_procedencia() -> None:
    assert acoustic.spectra_problems(acoustic.SOURCE_SPECTRA) == []
    assert set(acoustic.SOURCE_SPECTRA) == {f"C{i}" for i in range(1, 9)}
    bad = {"C1": acoustic.SourceSpectrum({125.0: 70.0}, "aproximado")}
    assert acoustic.spectra_problems(bad)


@pytest.mark.req("REQ-FUN-062")
def test_puntuaciones_de_clase_de_la_matriz_de_confusion() -> None:
    model = DetectionModel()
    rng = Random(7)  # noqa: S311 (simulación)
    for true_class in acoustic.SOURCE_SPECTRA:
        predicted, scores = model.classify(true_class, rng)
        assert predicted in model.confusion
        assert all(0.0 <= p <= 1.0 for _, p in scores)
        assert sum(p for _, p in scores) <= 1.0
        assert max(scores, key=lambda item: item[1])[0] == predicted


@pytest.mark.req("REQ-FUN-062")
def test_matriz_de_confusion_identidad_clasifica_sin_error() -> None:
    classes = ("C1", "C2")
    identity = {a: {b: 1.0 if a == b else 0.0 for b in classes} for a in classes}
    model = DetectionModel(confusion=identity)
    predicted, scores = model.classify("C2", Random(1))  # noqa: S311
    assert predicted == "C2"
    assert dict(scores)["C2"] == pytest.approx(1.0)


def _detections(
    name: str,
    duration_s: float = 600.0,
    seed: int | None = None,
    model: DetectionModel | None = None,
) -> list[Detection]:
    scenario = load_scenario(SCENARIOS / f"{name}.yaml")
    engine = build_engine(
        scenario,
        seed=seed,
        duration_s=duration_s,
        extra_components=acoustic.acoustic_components(scenario, model),
    )
    return [env.detection for env in engine.run_all() if env.HasField("detection")]


# Detector muy sensible: garantiza detecciones en todos los escenarios (incluido el puerto,
# ruidoso y con viento) para comprobar `validate()` sin retocar la física por defecto.
_PERMISSIVE = DetectionModel(snr50_db=-20.0)


@pytest.mark.req("REQ-FUN-004", "REQ-FUN-062")
@pytest.mark.parametrize("permissive", [False, True])
@pytest.mark.parametrize("name", NAMES)
def test_toda_deteccion_generada_pasa_validate(name: str, permissive: bool) -> None:
    detections = _detections(name, model=_PERMISSIVE if permissive else None)
    if permissive:
        assert detections, f"{name}: ninguna detección acústica"
    for det in detections:
        assert validate(det) == [], det
        assert det.sensor_type == SENSOR_TYPE_ACOUSTIC
        assert det.HasField("acoustic")
        assert det.HasField("bearing_deg") and det.HasField("bearing_uncertainty_deg")
        assert 0.0 <= det.detection_confidence <= 1.0
    ids = [d.detection_id for d in detections]
    assert len(ids) == len(set(ids))


@pytest.mark.req("REQ-FUN-004")
def test_modelo_por_defecto_detecta_en_el_recinto_cerrado() -> None:
    assert _detections("prision_ceuta")


@pytest.mark.req("REQ-FUN-003", "REQ-FUN-004")
def test_detecciones_reproducibles_por_semilla() -> None:
    first = _detections("prision_ceuta", 300.0, seed=11)
    second = _detections("prision_ceuta", 300.0, seed=11)
    other = _detections("prision_ceuta", 300.0, seed=12)
    serialize = [d.SerializeToString(deterministic=True) for d in first]
    assert serialize == [d.SerializeToString(deterministic=True) for d in second]
    assert serialize != [d.SerializeToString(deterministic=True) for d in other]


# --- sin audio en ningún punto ---------------------------------------------------------------

_AUDIO_MODULES = {"wave", "audioop", "aifc", "sunau", "sounddevice", "pyaudio", "soundfile"}


def _audio_imports(source: str) -> list[str]:
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found += [a.name for a in node.names if a.name.split(".")[0] in _AUDIO_MODULES]
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.split(".")[0] in _AUDIO_MODULES
        ):
            found.append(node.module)
    return found


@pytest.mark.req("REQ-FUN-004")
def test_sim_no_genera_ni_importa_audio() -> None:
    files = sorted(SIM_DIR.rglob("*.py"))
    assert any(f.name == "acoustic.py" for f in files)
    assert {str(f): hits for f in files if (hits := _audio_imports(f.read_text()))} == {}
    assert _audio_imports("import wave\nfrom sounddevice import rec") == ["wave", "sounddevice"]
    # La observación acústica solo transporta niveles por banda y SNR, nunca muestras.
    acoustic_type = Detection.DESCRIPTOR.fields_by_name["acoustic"].message_type
    assert acoustic_type is not None
    fields = {f.name for f in acoustic_type.fields}
    assert fields == {"band_levels", "signal_to_noise_db"}


# --- pruebas negativas -----------------------------------------------------------------------


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize("distance", [0.0, -1.0, math.nan, math.inf])
def test_negativa_distancia_no_positiva(distance: float) -> None:
    with pytest.raises(ValueError, match="distancia"):
        acoustics.received_level_db(80.0, 1000.0, distance, STD)


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize("humidity", [-0.1, 100.1, math.nan])
def test_negativa_humedad_fuera_de_rango(humidity: float) -> None:
    with pytest.raises(ValueError, match="humedad"):
        Atmosphere(temperature_c=20.0, relative_humidity_pct=humidity)


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize("freq", [0.0, -125.0, math.nan])
def test_negativa_frecuencia_no_positiva(freq: float) -> None:
    with pytest.raises(ValueError, match="frecuencia"):
        acoustics.absorption_db_per_m(freq, STD)


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize(
    "kwargs",
    [{"temperature_c": -274.0}, {"temperature_c": math.inf}, {"pressure_kpa": 0.0}],
)
def test_negativa_atmosfera_invalida(kwargs: dict[str, float]) -> None:
    params = {"temperature_c": 20.0, "relative_humidity_pct": 50.0, **kwargs}
    with pytest.raises(ValueError):
        Atmosphere(**params)


@pytest.mark.req("REQ-FUN-004")
def test_negativa_fondo_mayor_que_la_senal_queda_bajo_el_umbral() -> None:
    model = DetectionModel()
    loud = {
        "temperature_c": 20.0,
        "relative_humidity_pct": 70.0,
        "wind": {"speed_mps": 0.0, "from_deg": 0.0},
        "background_bands": [{"center_hz": f, "level_db_spl": 110.0} for f in BANDS],
    }
    obs = acoustic.observe("C1", (100.0, 0.0, 30.0), (0.0, 0.0, 2.0), loud, model)
    assert max(obs.band_snr_db.values()) < 0.0
    assert obs.detection_probability < model.threshold


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize(
    "confusion",
    [
        {"C1": {"C1": 0.6, "C2": 0.3}},  # fila que no suma 1
        {"C1": {"C1": 1.2, "C2": -0.2}},  # probabilidad fuera de [0, 1]
        {"C1": {"C1": 1.0}, "C2": {"C1": 1.0}},  # columnas distintas de las filas
        {},
    ],
)
def test_negativa_matriz_de_confusion_invalida(confusion: dict[str, dict[str, float]]) -> None:
    with pytest.raises(ValueError, match="confusión"):
        DetectionModel(confusion=confusion)


@pytest.mark.req("REQ-FUN-004")
@pytest.mark.parametrize(
    "kwargs",
    [{"threshold": 0.0}, {"threshold": 1.0}, {"slope_db": 0.0}, {"snr50_db": math.nan}],
)
def test_negativa_parametros_de_deteccion_invalidos(kwargs: dict[str, float]) -> None:
    params = {"snr50_db": 6.0, "slope_db": 2.0, "threshold": 0.5, **kwargs}
    with pytest.raises(ValueError):
        DetectionModel(params["snr50_db"], params["slope_db"], params["threshold"])


@pytest.mark.req("REQ-FUN-004")
def test_negativa_clase_sin_espectro() -> None:
    with pytest.raises(ValueError, match="C9"):
        acoustic.observe("C9", (100.0, 0.0, 30.0), (0.0, 0.0, 2.0), {}, DetectionModel())


@pytest.mark.req("REQ-FUN-004")
def test_no_se_declara_deteccion_bajo_el_umbral() -> None:
    model = DetectionModel(snr50_db=-20.0, threshold=0.99)
    detections = _detections("prision_ceuta", 300.0, model=model)
    assert detections
    assert min(d.detection_confidence for d in detections) >= 0.99 - 1e-6

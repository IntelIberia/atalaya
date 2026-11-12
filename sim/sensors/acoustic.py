"""Sensor acústico simulado: SNR por banda → probabilidad de detección → `Detection` (T1.12).

REQ-FUN-004 (propagación y fondo) y REQ-FUN-062 (toda `Detection` lleva su incertidumbre:
`class_scores`, `detection_confidence`, `time_quality` y, con rumbo, su incertidumbre).

**Sin audio en ningún punto:** el sensor recibe niveles por banda calculados por `sim.acoustics`
y emite niveles, SNR y puntuaciones; no hay muestras, ficheros ni bibliotecas de audio.

Modelo (simplificado y declarado):
1. Nivel de la fuente por banda a 1 m (`SOURCE_SPECTRA`, **todos NO VERIFICADO**: niveles
   *efectivos* de orden de magnitud que ya incluyen la ganancia de procesado del detector).
2. Nivel recibido por banda (`sim.acoustics.received_level_db`) y fondo por banda con ruido de
   viento (`background_level_db`); SNR por banda = señal − fondo; manda la mejor banda.
3. Probabilidad de detección logística en la SNR: p = 1 / (1 + exp(−(SNR − SNR50) / pendiente)).
   Por debajo de `threshold` no se declara detección; por encima se declara con probabilidad p.
4. Clasificación con una matriz de confusión configurable `confusion[real][predicha]`: la clase
   predicha se sortea de la fila de la clase real y `class_scores` es la columna de la predicha
   normalizada (posterior con prior uniforme). La matriz por defecto es sintética (NO VERIFICADO).
5. Rumbo con ruido gaussiano cuya σ decrece con la SNR (NO VERIFICADO); se publica σ como
   `bearing_uncertainty_deg`.

No se simulan falsas alarmas sin objetivo (límite declarado de T1.12).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from random import Random
from typing import Any

from atalaya.v1.common_pb2 import ClassScore
from atalaya.v1.detection_pb2 import SENSOR_TYPE_ACOUSTIC, Detection

from sim import acoustics, clock, geo
from sim.acoustics import Vec3
from sim.engine import Component, Engine
from sim.scenario import Scenario
from sim.trajectory import Trajectory, Waypoint

NO_VERIFICADO = "NO VERIFICADO"
ACOUSTIC_NODE_KINDS = frozenset({"acoustic_android", "acoustic_pps"})
ACOUSTIC_PERIOD_S = 1.0
DB_STEP = 1e-2
DEG_STEP = 1e-3
MS_STEP = 1e-6
_MICRO = 1_000_000

# σ del rumbo: 5° con SNR = SNR50, ×/÷ 10 por cada 20 dB; acotada a [1°, 30°]. NO VERIFICADO.
BEARING_SIGMA_AT_SNR50_DEG = 5.0
BEARING_SIGMA_MIN_DEG = 1.0
BEARING_SIGMA_MAX_DEG = 30.0


@dataclass(frozen=True)
class SourceSpectrum:
    """Nivel efectivo por banda (Hz → dB SPL a 1 m) y su procedencia."""

    levels_db: Mapping[float, float]
    source: str


_SPECTRUM_NOTE = (
    f"{NO_VERIFICADO}: nivel efectivo de orden de magnitud (incluye ganancia de procesado), "
    "sin contrastar con mediciones publicadas"
)
_OCTAVES = (125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0)


def _spectrum(*levels: float) -> SourceSpectrum:
    return SourceSpectrum(dict(zip(_OCTAVES, levels, strict=True)), _SPECTRUM_NOTE)


SOURCE_SPECTRA: Mapping[str, SourceSpectrum] = {
    "C1": _spectrum(84.0, 88.0, 90.0, 88.0, 84.0, 78.0),
    "C2": _spectrum(92.0, 95.0, 96.0, 93.0, 88.0, 82.0),
    "C3": _spectrum(86.0, 90.0, 94.0, 94.0, 90.0, 84.0),
    "C4": _spectrum(86.0, 90.0, 94.0, 94.0, 90.0, 84.0),
    "C5": _spectrum(84.0, 88.0, 88.0, 84.0, 78.0, 72.0),
    "C6": _spectrum(108.0, 106.0, 102.0, 98.0, 92.0, 84.0),
    "C7": _spectrum(118.0, 120.0, 122.0, 122.0, 120.0, 116.0),
    "C8": _spectrum(124.0, 122.0, 118.0, 114.0, 108.0, 100.0),
}


def spectra_problems(spectra: Mapping[str, SourceSpectrum]) -> list[str]:
    """Espectros sin fuente ni marca NO VERIFICADO, vacíos o con valores no finitos."""
    problems: list[str] = []
    for class_id, spectrum in spectra.items():
        text = spectrum.source.strip()
        if not (text.startswith(NO_VERIFICADO) or "https://" in text):
            problems.append(f"{class_id}: sin fuente ni marca {NO_VERIFICADO}")
        if not spectrum.levels_db:
            problems.append(f"{class_id}: espectro vacío")
        for freq, level in spectrum.levels_db.items():
            if not (math.isfinite(freq) and freq > 0 and math.isfinite(level)):
                problems.append(f"{class_id}: banda {freq!r} con nivel {level!r} inválido")
    return problems


def _default_confusion() -> dict[str, dict[str, float]]:
    """Matriz sintética (NO VERIFICADO): 0,70 diagonal, 0,20 a la clase vecina, 0,10 repartido."""
    classes = [f"C{i}" for i in range(1, 10)]
    neighbour = {
        "C1": "C2", "C2": "C1", "C3": "C4", "C4": "C3", "C5": "C6",
        "C6": "C5", "C7": "C8", "C8": "C7", "C9": "C1",
    }  # fmt: skip
    matrix: dict[str, dict[str, float]] = {}
    for real in classes:
        rest = 0.10 / (len(classes) - 2)
        matrix[real] = {
            pred: 0.70 if pred == real else 0.20 if pred == neighbour[real] else rest
            for pred in classes
        }
    return matrix


DEFAULT_CONFUSION_SOURCE = f"{NO_VERIFICADO}: matriz sintética del simulador"


def _probability(value: object, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ValueError(f"{what}: valor no finito {value!r}")
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{what}: probabilidad fuera de [0, 1]: {value!r}")
    return float(value)


def _check_confusion(confusion: Mapping[str, Mapping[str, float]]) -> None:
    if not confusion:
        raise ValueError("matriz de confusión vacía")
    classes = set(confusion)
    for real, row in confusion.items():
        if set(row) != classes:
            raise ValueError(
                f"matriz de confusión: la fila {real} no tiene las mismas clases que las filas"
            )
        total = sum(
            _probability(p, f"matriz de confusión [{real}][{pred}]") for pred, p in row.items()
        )
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"matriz de confusión: la fila {real} suma {total!r}, no 1")


@dataclass(frozen=True)
class DetectionModel:
    """Parámetros del detector: SNR al 50 %, pendiente, umbral de declaración y confusión."""

    snr50_db: float = 6.0
    slope_db: float = 2.0
    threshold: float = 0.5
    confusion: Mapping[str, Mapping[str, float]] = field(default_factory=_default_confusion)

    def __post_init__(self) -> None:
        if not math.isfinite(self.snr50_db):
            raise ValueError(f"SNR50 no finita: {self.snr50_db!r}")
        if not (math.isfinite(self.slope_db) and self.slope_db > 0.0):
            raise ValueError(f"pendiente no positiva: {self.slope_db!r}")
        if not (math.isfinite(self.threshold) and 0.0 < self.threshold < 1.0):
            raise ValueError(f"umbral fuera de (0, 1): {self.threshold!r}")
        _check_confusion(self.confusion)

    def probability(self, snr_db: float) -> float:
        z = (snr_db - self.snr50_db) / self.slope_db
        if z >= 0:
            return 1.0 / (1.0 + math.exp(-z))
        e = math.exp(z)
        return e / (1.0 + e)

    def classify(self, true_class: str, rng: Random) -> tuple[str, list[tuple[str, float]]]:
        """Clase predicha sorteada de la fila real y puntuaciones (columna normalizada)."""
        if true_class not in self.confusion:
            raise ValueError(f"clase sin fila en la matriz de confusión: {true_class!r}")
        classes = sorted(self.confusion)
        u = rng.random()
        acc = 0.0
        predicted = classes[-1]
        for pred in classes:
            acc += self.confusion[true_class][pred]
            if u < acc:
                predicted = pred
                break
        column = {real: self.confusion[real][predicted] for real in classes}
        total = sum(column.values())
        micro = {c: math.floor(p / total * _MICRO) for c, p in column.items() if p > 0.0}
        scores = [(c, m / _MICRO) for c, m in sorted(micro.items()) if m > 0]
        while sum(p for _, p in scores) > 1.0:  # sin margen sobre 1 por redondeo binario
            best = max(range(len(scores)), key=lambda i: scores[i][1])
            scores[best] = (scores[best][0], scores[best][1] - 1.0 / _MICRO)
        return predicted, scores


@dataclass(frozen=True)
class Observation:
    """Resultado físico de observar una fuente desde un nodo (sin azar)."""

    distance_m: float
    bearing_deg: float
    band_signal_db: Mapping[float, float]
    band_background_db: Mapping[float, float]
    band_snr_db: Mapping[float, float]
    snr_db: float
    detection_probability: float


def observe(
    class_id: str,
    source: Vec3,
    receiver: Vec3,
    environment: Mapping[str, Any],
    model: DetectionModel,
) -> Observation:
    """Niveles, SNR y probabilidad de detección de `class_id` en `source` vista desde `receiver`."""
    spectrum = SOURCE_SPECTRA.get(class_id)
    if spectrum is None:
        raise ValueError(f"clase sin espectro acústico en el simulador: {class_id!r}")
    atm = acoustics.atmosphere_from_scenario(environment)
    wind = environment["wind"]
    distance = math.dist(source, receiver)
    along = acoustics.along_wind_mps(
        float(wind["speed_mps"]), float(wind["from_deg"]), source, receiver
    )
    bands = environment["background_bands"]
    signal: dict[float, float] = {}
    background: dict[float, float] = {}
    snr: dict[float, float] = {}
    for band in sorted(bands, key=lambda b: float(b["center_hz"])):
        freq = float(band["center_hz"])
        if freq not in spectrum.levels_db:
            raise ValueError(f"{class_id}: sin nivel de fuente para la banda de {freq:g} Hz")
        signal[freq] = acoustics.received_level_db(
            spectrum.levels_db[freq], freq, distance, atm, along_wind_mps=along
        )
        background[freq] = acoustics.background_level_db(
            freq, bands, wind_speed_mps=float(wind["speed_mps"])
        )
        snr[freq] = signal[freq] - background[freq]
    best = max(snr.values())
    bearing = math.degrees(math.atan2(source[0] - receiver[0], source[1] - receiver[1])) % 360.0
    return Observation(distance, bearing, signal, background, snr, best, model.probability(best))


def bearing_sigma_deg(snr_db: float, model: DetectionModel) -> float:
    sigma = BEARING_SIGMA_AT_SNR50_DEG * float(10.0 ** (-(snr_db - model.snr50_db) / 20.0))
    return min(BEARING_SIGMA_MAX_DEG, max(BEARING_SIGMA_MIN_DEG, sigma))


def _quantize(value: float, step: float) -> float:
    return round(value / step) * step


def build_detection(
    obs: Observation,
    *,
    true_class: str,
    site_id: str,
    node_id: str,
    now_ns: int,
    pps: bool,
    model: DetectionModel,
    rng: Random,
    clock_rng: Random,
) -> Detection:
    """`Detection` acústica con sus incertidumbres (REQ-FUN-062)."""
    _, scores = model.classify(true_class, rng)  # la predicha es la de mayor puntuación
    sigma = bearing_sigma_deg(obs.snr_db, model)
    measured = (obs.bearing_deg + rng.gauss(0.0, sigma)) % 360.0
    det = Detection(
        detection_id=f"{node_id}-ac-{rng.getrandbits(64):016x}",
        site_id=site_id,
        node_id=node_id,
        observed_at=clock.to_timestamp(now_ns),
        sensor_type=SENSOR_TYPE_ACOUSTIC,
        bearing_deg=_quantize(measured, DEG_STEP) % 360.0,
        bearing_uncertainty_deg=_quantize(sigma, DEG_STEP),
        detection_confidence=math.floor(obs.detection_probability * _MICRO) / _MICRO,
    )
    clock_sigma_ms = 0.001 if pps else 20.0
    det.time_quality.pps_valid = pps
    det.time_quality.clock_offset_ms = _quantize(clock_rng.gauss(0.0, clock_sigma_ms), MS_STEP)
    det.time_quality.uncertainty_ms = _quantize(3 * clock_sigma_ms, MS_STEP)
    det.class_scores.extend(ClassScore(class_id=c, probability=p) for c, p in scores)
    for freq in sorted(obs.band_signal_db):
        band = det.acoustic.band_levels.add()
        band.center_frequency_hz = freq
        band.level_db_spl = _quantize(
            acoustics.energy_sum_db((obs.band_signal_db[freq], obs.band_background_db[freq])),
            DB_STEP,
        )
    det.acoustic.signal_to_noise_db = _quantize(obs.snr_db, DB_STEP)
    return det


@dataclass(frozen=True)
class _Target:
    target_id: str
    class_id: str
    site_id: str
    start_s: float
    trajectory: Trajectory


def _targets(scenario: Scenario) -> list[_Target]:
    targets: list[_Target] = []
    for group in ("threats", "manned_aircraft"):
        for item in scenario.data[group]:
            route = [Waypoint(p["east_m"], p["north_m"], p["up_m"]) for p in item["route"]]
            traj = Trajectory(item["class"], route, float(item["speed_mps"]))
            targets.append(
                _Target(item["id"], item["class"], item["site"], float(item["start_s"]), traj)
            )
    return sorted(targets, key=lambda t: t.target_id)


def _to_site_frame(
    point: Vec3, from_center: Mapping[str, float], to_center: Mapping[str, float]
) -> Vec3:
    if from_center == to_center:
        return point
    lat, lon, alt = geo.enu_to_geodetic(*point, from_center["lat_deg"], from_center["lon_deg"], 0.0)
    return geo.geodetic_to_enu(lat, lon, alt, to_center["lat_deg"], to_center["lon_deg"], 0.0)


def _position(target: _Target, t_s: float) -> Vec3 | None:
    tau = t_s - target.start_s
    if not 0.0 <= tau <= target.trajectory.duration_s:
        return None
    return target.trajectory.state(tau).position


def acoustic_components(
    scenario: Scenario,
    model: DetectionModel | None = None,
    period_s: float = ACOUSTIC_PERIOD_S,
) -> list[Component]:
    """Un componente del motor por nodo acústico: cada `period_s` observa cada objetivo activo."""
    detector = model or DetectionModel()
    if not (math.isfinite(period_s) and period_s > 0):
        raise ValueError(f"periodo inválido: {period_s!r}")
    environment = scenario.data["environment"]
    centers = {site["id"]: site["center"] for site in scenario.data["sites"]}
    targets = _targets(scenario)
    speed_of_sound = acoustics.speed_of_sound_mps(float(environment["temperature_c"]))
    period_ns = clock.seconds_to_ns(period_s)
    nodes = [
        f["properties"]
        for f in scenario.geometry["features"]
        if f["properties"]["role"] == "node" and f["properties"]["kind"] in ACOUSTIC_NODE_KINDS
    ]
    components: list[Component] = []
    for node in nodes:
        components.append(
            _node_component(
                node, centers, targets, environment, detector, speed_of_sound, period_ns
            )
        )
    return components


def _node_component(
    node: Mapping[str, Any],
    centers: Mapping[str, Mapping[str, float]],
    targets: Sequence[_Target],
    environment: Mapping[str, Any],
    model: DetectionModel,
    speed_of_sound: float,
    period_ns: int,
) -> Component:
    node_id = node["id"]
    site_id = node["site"]
    off = node["offset_m"]
    receiver: Vec3 = (off["east_m"], off["north_m"], off["up_m"])
    pps = bool(node["pps"])

    def setup(engine: Engine) -> None:
        rng = engine.rng(f"acustica/{node_id}")
        clock_rng = engine.rng(f"reloj-acustica/{node_id}")
        start_ns = int(engine.rng(f"fase-acustica/{node_id}").uniform(0.0, 1.0) * period_ns)

        def tick(e: Engine) -> None:
            t_s = e.now_ns / clock.NS_PER_S
            for target in targets:
                now = _position(target, t_s)
                if now is None:
                    continue
                here = _to_site_frame(now, centers[target.site_id], centers[site_id])
                # Instante de emisión retardado por la propagación (una iteración).
                delay = math.dist(here, receiver) / speed_of_sound
                emitted = _position(target, t_s - delay)
                if emitted is None:
                    continue
                source = _to_site_frame(emitted, centers[target.site_id], centers[site_id])
                if math.dist(source, receiver) <= 0.0:
                    continue
                obs = observe(target.class_id, source, receiver, environment, model)
                if obs.detection_probability < model.threshold:
                    continue
                if rng.random() >= obs.detection_probability:
                    continue
                det = build_detection(
                    obs,
                    true_class=target.class_id,
                    site_id=site_id,
                    node_id=node_id,
                    now_ns=e.now_ns,
                    pps=pps,
                    model=model,
                    rng=rng,
                    clock_rng=clock_rng,
                )
                e.emit(site_id, node_id, det)
            if e.end_ns is None or e.now_ns + period_ns <= e.end_ns:
                e.schedule(e.now_ns + period_ns, tick)

        engine.schedule(start_ns, tick)

    return setup

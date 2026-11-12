"""Propagación acústica simplificada para el simulador (T1.12, REQ-FUN-004).

Física **simplificada y declarada como tal**; el simulador trabaja con niveles por banda (dB SPL),
nunca con audio:

- **Divergencia esférica** respecto a 1 m: −20·log10(r / r0).
- **Absorción atmosférica** con la formulación analítica de ISO 9613-1:1993 (§6, ecuaciones de
  las frecuencias de relajación del oxígeno y del nitrógeno, de la concentración molar de vapor
  de agua y del coeficiente de atenuación de un tono puro). La norma es de pago y no se ha leído:
  las ecuaciones y constantes se tomaron de dos reproducciones públicas independientes que
  coinciden entre sí (`ISO_9613_1_SOURCES`), y los valores resultantes se contrastan en los tests
  con una tabla publicada (Wikibooks, citando a Crocker, *Handbook of Acoustics*, 1998). La
  igualdad con el texto original de la norma queda **NO VERIFICADO** (`ISO_9613_1_STATUS`).
  Validez declarada por esas fuentes: −20…50 °C, 10…100 % HR, 50 Hz…10 kHz; fuera de ese rango
  el cálculo se hace igual, sin garantía.
- **Velocidad del sonido** c = 343,2·√(T / 293,15 K) m/s (misma fuente).
- **Viento:** corrección del nivel ΔL = g·u·log10(r / r0), con u la componente del viento a lo
  largo de la propagación (positiva a favor), acotada a [−20, +6] dB; y ruido de viento en el
  micrófono que se suma en energía al fondo por bandas del escenario. Ambos modelos y sus
  constantes son **NO VERIFICADO** (órdenes de magnitud para un simulador sintético): con
  g·u_max = 10 dB/década < 20 dB/década el nivel nunca crece con la distancia.
- **Fondo** por bandas del escenario (`environment.background_bands`).
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

Vec3 = tuple[float, float, float]

REFERENCE_DISTANCE_M = 1.0
REFERENCE_PRESSURE_KPA = 101.325  # p_r
REFERENCE_TEMPERATURE_K = 293.15  # T_0 (20 °C)
TRIPLE_POINT_K = 273.16  # T_01
KELVIN_OFFSET = 273.15
SPEED_OF_SOUND_REF_MPS = 343.2  # a T_0

ISO_9613_1_SOURCES = (
    "https://sengpielaudio.com/AirdampingFormula.htm",
    "https://gorbatschow.github.io/SonarDocs/sound_absorption_air_iso.en",
)
ISO_9613_1_REFERENCE_TABLE = (
    "https://en.wikibooks.org/wiki/Engineering_Acoustics/Outdoor_Sound_Propagation"
)
ISO_9613_1_STATUS = (
    "Ecuaciones y constantes de ISO 9613-1 contrastadas con dos fuentes públicas secundarias y "
    "con una tabla publicada (consulta 2026-11-12); texto original de la norma NO VERIFICADO"
)

NO_VERIFICADO = "NO VERIFICADO"
# Viento: modelo propio sin fuente (NO VERIFICADO).
WIND_GAIN_DB_PER_MPS_DECADE = 0.25
WIND_MAX_SPEED_MPS = 40.0  # máximo del esquema de escenario
WIND_DOWNWIND_MAX_DB = 6.0
WIND_SHADOW_MAX_DB = 20.0
WIND_NOISE_REF_DB = 45.0  # a 5 m/s en la banda de 125 Hz, con pantalla antiviento
WIND_NOISE_REF_SPEED_MPS = 5.0
WIND_NOISE_SLOPE_DB_PER_OCTAVE = 6.0
WIND_NOISE_MIN_SPEED_MPS = 0.5
_BAND_MATCH_HZ = 1e-6

if WIND_GAIN_DB_PER_MPS_DECADE * WIND_MAX_SPEED_MPS >= 20.0:  # el nivel debe ser monótono
    raise RuntimeError("ganancia de viento incompatible con la monotonía del nivel")


def _finite(value: float, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ValueError(f"{what} no finita: {value!r}")
    return float(value)


@dataclass(frozen=True)
class Atmosphere:
    """Estado de la atmósfera: temperatura (°C), humedad relativa (%) y presión (kPa)."""

    temperature_c: float
    relative_humidity_pct: float
    pressure_kpa: float = REFERENCE_PRESSURE_KPA

    def __post_init__(self) -> None:
        t = _finite(self.temperature_c, "temperatura")
        if t <= -KELVIN_OFFSET:
            raise ValueError(f"temperatura bajo el cero absoluto: {t!r} °C")
        h = self.relative_humidity_pct
        if isinstance(h, bool) or not isinstance(h, int | float) or not 0.0 <= h <= 100.0:
            raise ValueError(f"humedad relativa fuera de [0, 100] %: {h!r}")
        p = _finite(self.pressure_kpa, "presión")
        if p <= 0.0:
            raise ValueError(f"presión no positiva: {p!r} kPa")

    @property
    def temperature_k(self) -> float:
        return self.temperature_c + KELVIN_OFFSET


def atmosphere_from_scenario(environment: Mapping[str, Any]) -> Atmosphere:
    return Atmosphere(
        temperature_c=float(environment["temperature_c"]),
        relative_humidity_pct=float(environment["relative_humidity_pct"]),
    )


def _check_frequency(freq_hz: float) -> float:
    if (
        isinstance(freq_hz, bool)
        or not isinstance(freq_hz, int | float)
        or not math.isfinite(freq_hz)
        or freq_hz <= 0.0
    ):
        raise ValueError(f"frecuencia inválida: {freq_hz!r} (Hz finitos > 0)")
    return float(freq_hz)


def _check_distance(distance_m: float) -> float:
    if (
        isinstance(distance_m, bool)
        or not isinstance(distance_m, int | float)
        or not math.isfinite(distance_m)
        or distance_m <= 0.0
    ):
        raise ValueError(f"distancia inválida: {distance_m!r} (metros finitos > 0)")
    return float(distance_m)


def absorption_db_per_m(freq_hz: float, atm: Atmosphere) -> float:
    """Coeficiente de absorción atmosférica de un tono puro (dB/m), ISO 9613-1 §6."""
    f = _check_frequency(freq_hz)
    t = atm.temperature_k
    t_rel = t / REFERENCE_TEMPERATURE_K
    p_rel = atm.pressure_kpa / REFERENCE_PRESSURE_KPA
    psat_rel = 10.0 ** (-6.8346 * (TRIPLE_POINT_K / t) ** 1.261 + 4.6151)
    h = atm.relative_humidity_pct * psat_rel / p_rel  # concentración molar de vapor (%)
    fr_o = p_rel * (24.0 + 4.04e4 * h * (0.02 + h) / (0.391 + h))
    nitrogen_humidity = 280.0 * h * math.exp(-4.170 * (t_rel ** (-1.0 / 3.0) - 1.0))
    fr_n = p_rel * t_rel**-0.5 * (9.0 + nitrogen_humidity)
    f2 = f * f
    classical = 1.84e-11 / p_rel * t_rel**0.5
    oxygen = 0.01275 * math.exp(-2239.1 / t) / (fr_o + f2 / fr_o)
    nitrogen = 0.1068 * math.exp(-3352.0 / t) / (fr_n + f2 / fr_n)
    return float(8.686 * f2 * (classical + t_rel**-2.5 * (oxygen + nitrogen)))


def speed_of_sound_mps(temperature_c: float) -> float:
    t = Atmosphere(temperature_c, 0.0).temperature_k
    return SPEED_OF_SOUND_REF_MPS * math.sqrt(t / REFERENCE_TEMPERATURE_K)


def spherical_spreading_db(distance_m: float) -> float:
    """Pérdida por divergencia esférica respecto a `REFERENCE_DISTANCE_M` (dB, positiva)."""
    return 20.0 * math.log10(_check_distance(distance_m) / REFERENCE_DISTANCE_M)


def wind_correction_db(distance_m: float, along_wind_mps: float) -> float:
    """Corrección del nivel por viento a favor (+) o en contra (−). NO VERIFICADO."""
    r = _check_distance(distance_m)
    u = _finite(along_wind_mps, "componente del viento")
    if abs(u) > WIND_MAX_SPEED_MPS:
        raise ValueError(f"viento fuera de rango: {u!r} m/s (máximo {WIND_MAX_SPEED_MPS:g})")
    raw = WIND_GAIN_DB_PER_MPS_DECADE * u * math.log10(r / REFERENCE_DISTANCE_M)
    return min(WIND_DOWNWIND_MAX_DB, max(-WIND_SHADOW_MAX_DB, raw))


def received_level_db(
    source_level_db: float,
    freq_hz: float,
    distance_m: float,
    atm: Atmosphere,
    *,
    along_wind_mps: float = 0.0,
    include_absorption: bool = True,
) -> float:
    """Nivel recibido en una banda a `distance_m` de una fuente de nivel `source_level_db` a 1 m."""
    level = _finite(source_level_db, "nivel de fuente") - spherical_spreading_db(distance_m)
    if include_absorption:
        level -= absorption_db_per_m(freq_hz, atm) * distance_m
    else:
        _check_frequency(freq_hz)
    return level + wind_correction_db(distance_m, along_wind_mps)


def along_wind_mps(speed_mps: float, from_deg: float, source: Vec3, receiver: Vec3) -> float:
    """Componente horizontal del viento en la dirección fuente → receptor (+ a favor).

    `from_deg` es la dirección DE la que sopla (convención meteorológica, desde el norte en
    sentido horario); el viento avanza hacia `from_deg + 180°`.
    """
    de = receiver[0] - source[0]
    dn = receiver[1] - source[1]
    norm = math.hypot(de, dn)
    if norm == 0.0:
        return 0.0
    to = math.radians(_finite(from_deg, "dirección del viento") + 180.0)
    return _finite(speed_mps, "velocidad del viento") * (
        math.sin(to) * de / norm + math.cos(to) * dn / norm
    )


def wind_noise_db(freq_hz: float, wind_speed_mps: float) -> float:
    """Ruido de viento en el micrófono por banda (dB SPL); −∞ en calma. NO VERIFICADO."""
    f = _check_frequency(freq_hz)
    u = _finite(wind_speed_mps, "velocidad del viento")
    if u < WIND_NOISE_MIN_SPEED_MPS:
        return -math.inf
    return (
        WIND_NOISE_REF_DB
        + 60.0 * math.log10(u / WIND_NOISE_REF_SPEED_MPS)
        - WIND_NOISE_SLOPE_DB_PER_OCTAVE * math.log2(f / 125.0)
    )


def energy_sum_db(levels: Iterable[float]) -> float:
    """Suma energética de niveles en dB (−∞ no aporta)."""
    total = sum(10.0 ** (level / 10.0) for level in levels if level != -math.inf)
    return 10.0 * math.log10(total) if total > 0.0 else -math.inf


def background_level_db(
    freq_hz: float, bands: Sequence[Mapping[str, Any]], *, wind_speed_mps: float
) -> float:
    """Fondo del escenario en la banda `freq_hz` más el ruido de viento, sumados en energía."""
    f = _check_frequency(freq_hz)
    for band in bands:
        if abs(float(band["center_hz"]) - f) <= _BAND_MATCH_HZ:
            return energy_sum_db((float(band["level_db_spl"]), wind_noise_db(f, wind_speed_mps)))
    raise ValueError(f"el escenario no define fondo para la banda de {f:g} Hz")

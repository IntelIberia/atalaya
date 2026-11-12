"""Utilidades compartidas por los sensores de datos decodificados (Remote ID y ADS-B, T1.14).

Solo geometría, ruido y cuantización en memoria: ningún camino de radio.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from random import Random

from atalaya.v1.common_pb2 import GeoPoint, PositionCovariance, TimeQuality

from sim import clock, geo

Vec3 = tuple[float, float, float]

DEGREE_STEP = 1e-7  # ~1 cm
METRE_STEP = 1e-3
MS_STEP = 1e-6


def quantize(value: float, step: float) -> float:
    return round(value / step) * step


def check_positive(value: object, what: str) -> float:
    """Devuelve `value` si es un número finito > 0; si no, `ValueError`."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{what}: no numérico {value!r}")
    if not (math.isfinite(value) and value > 0.0):
        raise ValueError(f"{what}: debe ser finito y > 0 ({value!r})")
    return float(value)


def add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def truncated_noise(rng: Random, sigma: float, clip: float) -> Vec3:
    """Ruido gaussiano por eje truncado a ±clip·σ (por rechazo; determinista con la semilla)."""

    def one() -> float:
        while True:
            x = rng.gauss(0.0, sigma)
            if abs(x) <= clip * sigma:
                return x

    return (one(), one(), one())


def to_frame(point: Vec3, src: Mapping[str, float], dst: Mapping[str, float]) -> Vec3:
    """Punto ENU respecto al centro `src` → ENU respecto al centro `dst`."""
    if src == dst:
        return point
    lat, lon, alt = geo.enu_to_geodetic(*point, src["lat_deg"], src["lon_deg"], 0.0)
    return geo.geodetic_to_enu(lat, lon, alt, dst["lat_deg"], dst["lon_deg"], 0.0)


def geopoint(point: Vec3, center: Mapping[str, float]) -> GeoPoint:
    """Punto ENU local → `GeoPoint` WGS84 cuantizado."""
    lat, lon, alt = geo.enu_to_geodetic(*point, center["lat_deg"], center["lon_deg"], 0.0)
    return GeoPoint(
        latitude_deg=quantize(lat, DEGREE_STEP),
        longitude_deg=quantize(lon, DEGREE_STEP),
        altitude_m=quantize(alt, METRE_STEP),
    )


def isotropic_covariance(sigma_m: float) -> PositionCovariance:
    var = quantize(sigma_m**2, METRE_STEP)
    return PositionCovariance(
        east_east_m2=var,
        east_north_m2=0.0,
        east_up_m2=0.0,
        north_north_m2=var,
        north_up_m2=0.0,
        up_up_m2=var,
    )


def time_quality(pps: bool, clock_rng: Random, drift_offset_ms: float) -> TimeQuality:
    sigma_ms = clock.clock_sigma_ms(pps)
    return TimeQuality(
        pps_valid=pps,
        clock_offset_ms=quantize(clock_rng.gauss(0.0, sigma_ms) + drift_offset_ms, MS_STEP),
        uncertainty_ms=quantize(3 * sigma_ms, MS_STEP),
    )

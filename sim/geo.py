"""WGS84 ↔ ECEF ↔ ENU local (T1.10, REQ-FUN-003).

Fórmulas estándar del elipsoide WGS84 (NIMA TR8350.2): geodésicas → ECEF en forma cerrada,
ECEF → ENU por rotación respecto al punto de referencia y ECEF → geodésicas por iteración de
Bowring hasta convergencia (error muy inferior al milímetro a las distancias del simulador).
Ángulos en grados, distancias en metros.
"""

from __future__ import annotations

import math

WGS84_A = 6_378_137.0
WGS84_F = 1 / 298.257223563
WGS84_B = WGS84_A * (1 - WGS84_F)
WGS84_E2 = WGS84_F * (2 - WGS84_F)
_MAX_ITER = 10

Vec3 = tuple[float, float, float]


def _check(lat_deg: float, lon_deg: float, alt_m: float) -> None:
    if not -90.0 <= lat_deg <= 90.0:  # también rechaza NaN
        raise ValueError(f"latitud fuera de [-90, 90]: {lat_deg!r}")
    if not -360.0 <= lon_deg <= 360.0:
        raise ValueError(f"longitud fuera de [-360, 360]: {lon_deg!r}")
    if not math.isfinite(alt_m):
        raise ValueError(f"altitud no finita: {alt_m!r}")


def geodetic_to_ecef(lat_deg: float, lon_deg: float, alt_m: float) -> Vec3:
    _check(lat_deg, lon_deg, alt_m)
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    sin_lat, cos_lat = math.sin(lat), math.cos(lat)
    n = WGS84_A / math.sqrt(1 - WGS84_E2 * sin_lat * sin_lat)
    return (
        (n + alt_m) * cos_lat * math.cos(lon),
        (n + alt_m) * cos_lat * math.sin(lon),
        (n * (1 - WGS84_E2) + alt_m) * sin_lat,
    )


def ecef_to_geodetic(x: float, y: float, z: float) -> Vec3:
    for value in (x, y, z):
        if not math.isfinite(value):
            raise ValueError(f"coordenada ECEF no finita: {value!r}")
    lon = math.atan2(y, x)
    p = math.hypot(x, y)
    # Estimación inicial de Bowring y refinado iterativo de la latitud.
    lat = math.atan2(z, p * (1 - WGS84_E2))
    for _ in range(_MAX_ITER):
        sin_lat = math.sin(lat)
        n = WGS84_A / math.sqrt(1 - WGS84_E2 * sin_lat * sin_lat)
        alt = p / math.cos(lat) - n if abs(lat) < math.pi / 4 else z / sin_lat - n * (1 - WGS84_E2)
        new_lat = math.atan2(z, p * (1 - WGS84_E2 * n / (n + alt)))
        if abs(new_lat - lat) < 1e-15:
            lat = new_lat
            break
        lat = new_lat
    sin_lat = math.sin(lat)
    n = WGS84_A / math.sqrt(1 - WGS84_E2 * sin_lat * sin_lat)
    alt = p / math.cos(lat) - n if abs(lat) < math.pi / 4 else z / sin_lat - n * (1 - WGS84_E2)
    return math.degrees(lat), math.degrees(lon), alt


def _rotation(lat0_deg: float, lon0_deg: float) -> tuple[Vec3, Vec3, Vec3]:
    lat, lon = math.radians(lat0_deg), math.radians(lon0_deg)
    sl, cl, so, co = math.sin(lat), math.cos(lat), math.sin(lon), math.cos(lon)
    east = (-so, co, 0.0)
    north = (-sl * co, -sl * so, cl)
    up = (cl * co, cl * so, sl)
    return east, north, up


def geodetic_to_enu(
    lat_deg: float, lon_deg: float, alt_m: float, lat0_deg: float, lon0_deg: float, alt0_m: float
) -> Vec3:
    """Posición geodésica → (este, norte, arriba) respecto a la referencia."""
    x, y, z = geodetic_to_ecef(lat_deg, lon_deg, alt_m)
    x0, y0, z0 = geodetic_to_ecef(lat0_deg, lon0_deg, alt0_m)
    dx, dy, dz = x - x0, y - y0, z - z0
    east, north, up = _rotation(lat0_deg, lon0_deg)
    return (
        east[0] * dx + east[1] * dy + east[2] * dz,
        north[0] * dx + north[1] * dy + north[2] * dz,
        up[0] * dx + up[1] * dy + up[2] * dz,
    )


def enu_to_geodetic(
    east_m: float, north_m: float, up_m: float, lat0_deg: float, lon0_deg: float, alt0_m: float
) -> Vec3:
    """(este, norte, arriba) respecto a la referencia → posición geodésica."""
    for value in (east_m, north_m, up_m):
        if not math.isfinite(value):
            raise ValueError(f"desplazamiento ENU no finito: {value!r}")
    x0, y0, z0 = geodetic_to_ecef(lat0_deg, lon0_deg, alt0_m)
    east, north, up = _rotation(lat0_deg, lon0_deg)
    x = x0 + east[0] * east_m + north[0] * north_m + up[0] * up_m
    y = y0 + east[1] * east_m + north[1] * north_m + up[1] * up_m
    z = z0 + east[2] * east_m + north[2] * north_m + up[2] * up_m
    return ecef_to_geodetic(x, y, z)

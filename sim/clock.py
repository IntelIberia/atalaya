"""Tiempo simulado (T1.10, REQ-FUN-003).

El tiempo del simulador es un entero de nanosegundos desde una época fija (`SIM_EPOCH_UNIX_S`,
2026-01-01T00:00:00Z); nunca se consulta el reloj del sistema. La deriva de reloj y el PPS de
cada nodo (T1.13) se modelan aquí: `drift_offset_ms` y la incertidumbre según el PPS.
"""

from __future__ import annotations

import math

from google.protobuf.timestamp_pb2 import Timestamp

SIM_EPOCH_UNIX_S = 1_767_225_600  # 2026-01-01T00:00:00Z
NS_PER_S = 1_000_000_000
# σ del desfase del reloj del nodo: disciplinado por PPS o sincronizado por red (NO VERIFICADO:
# órdenes de magnitud de GNSS-PPS y NTP en Android, sin medir).
PPS_SIGMA_MS = 0.001
NO_PPS_SIGMA_MS = 20.0


def seconds_to_ns(seconds: float) -> int:
    """Segundos simulados → nanosegundos enteros (redondeo al nanosegundo más cercano)."""
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError(f"tiempo simulado inválido: {seconds!r}")
    return round(seconds * NS_PER_S)


def to_timestamp(t_ns: int) -> Timestamp:
    """Instante simulado → `Timestamp` absoluto a partir de la época fija."""
    if isinstance(t_ns, bool) or not isinstance(t_ns, int) or t_ns < 0:
        raise ValueError(f"tiempo simulado inválido: {t_ns!r}")
    seconds, nanos = divmod(t_ns, NS_PER_S)
    return Timestamp(seconds=SIM_EPOCH_UNIX_S + seconds, nanos=nanos)


def from_timestamp(ts: Timestamp) -> int:
    """`Timestamp` absoluto → instante simulado en ns (inverso de `to_timestamp`)."""
    t_ns = (ts.seconds - SIM_EPOCH_UNIX_S) * NS_PER_S + ts.nanos
    if t_ns < 0:
        raise ValueError(f"marca de tiempo anterior a la época simulada: {ts}")
    return t_ns


def drift_offset_ms(drift_ppm: float, elapsed_s: float) -> float:
    """Desfase acumulado por `drift_ppm` durante `elapsed_s` (lineal; 1 ppm·s = 1 µs)."""
    if isinstance(drift_ppm, bool) or not math.isfinite(drift_ppm):
        raise ValueError(f"deriva de reloj no finita: {drift_ppm!r} ppm")
    if not math.isfinite(elapsed_s):
        raise ValueError(f"tiempo transcurrido no finito: {elapsed_s!r}")
    return drift_ppm * elapsed_s * 1e-3


def clock_sigma_ms(pps_valid: bool) -> float:
    """σ del desfase de reloj según haya PPS válido o no."""
    return PPS_SIGMA_MS if pps_valid else NO_PPS_SIGMA_MS

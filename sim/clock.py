"""Tiempo simulado (T1.10, REQ-FUN-003).

El tiempo del simulador es un entero de nanosegundos desde una época fija (`SIM_EPOCH_UNIX_S`,
2026-01-01T00:00:00Z); nunca se consulta el reloj del sistema. La deriva de reloj y el PPS de
cada nodo se añaden en T1.13.
"""

from __future__ import annotations

import math

from google.protobuf.timestamp_pb2 import Timestamp

SIM_EPOCH_UNIX_S = 1_767_225_600  # 2026-01-01T00:00:00Z
NS_PER_S = 1_000_000_000


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

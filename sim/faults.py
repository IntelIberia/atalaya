"""Fallos programados de nodos y enlaces (T1.13, REQ-FUN-004).

Tipos (`faults[].kind` del escenario), activos en `[start_s, start_s + duration_s)`:

| Tipo | Efecto | `magnitude` |
|---|---|---|
| `node_down` | el nodo no emite nada (ni `NodeStatus` ni detecciones) | — |
| `link_down` | el nodo emite, pero el enlace pierde todo | — |
| `pps_invalid` | PPS perdido: `pps_valid=false`, más incertidumbre, salud degradada | — |
| `clock_drift` | deriva sin PPS: desfase lineal desde el inicio del fallo | ppm (finita) |
| `latency` | mediana de la latencia del enlace | ms (finita, ≥ 0) |
| `packet_loss` / `duplicate` / `reorder` | probabilidad por mensaje | [0, 1] |

Con PPS válido el reloj está disciplinado y la deriva no se acumula (simplificación declarada).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sim import clock
from sim.network import NetworkConfig

FAULT_KINDS = (
    "node_down",
    "link_down",
    "pps_invalid",
    "clock_drift",
    "latency",
    "packet_loss",
    "duplicate",
    "reorder",
)
PROBABILITY_KINDS = frozenset({"packet_loss", "duplicate", "reorder"})
MAGNITUDE_KINDS = PROBABILITY_KINDS | {"latency", "clock_drift"}


def fault_problems(faults: Sequence[Mapping[str, Any]]) -> list[tuple[str, str]]:
    """Problemas semánticos (ruta, mensaje) que el esquema JSON no puede expresar."""
    problems: list[tuple[str, str]] = []
    for index, fault in enumerate(faults):
        kind = fault["kind"]
        path = f"faults/{index}/magnitude"
        if kind not in FAULT_KINDS:
            problems.append((f"faults/{index}/kind", f"tipo de fallo desconocido: {kind!r}"))
            continue
        magnitude = fault.get("magnitude")
        if magnitude is None:
            if kind in MAGNITUDE_KINDS:
                problems.append((path, f"el fallo {kind} requiere magnitude"))
            continue
        if isinstance(magnitude, bool) or not math.isfinite(magnitude):
            problems.append((path, f"magnitude debe ser finita: {magnitude!r}"))
        elif kind in PROBABILITY_KINDS and not 0.0 <= magnitude <= 1.0:
            problems.append((path, f"probabilidad de {kind} fuera de [0, 1]: {magnitude!r}"))
        elif magnitude < 0.0:
            problems.append((path, f"magnitude negativa: {magnitude!r}"))
    return problems


@dataclass(frozen=True)
class Fault:
    kind: str
    node: str
    start_s: float
    duration_s: float
    magnitude: float | None

    def active(self, t_s: float) -> bool:
        return self.start_s <= t_s < self.start_s + self.duration_s


class FaultSchedule:
    """Consulta de los fallos activos por nodo e instante."""

    def __init__(self, faults: Sequence[Mapping[str, Any]]) -> None:
        problems = fault_problems(faults)
        if problems:
            raise ValueError("; ".join(f"{path}: {msg}" for path, msg in problems))
        self.faults = tuple(
            Fault(
                f["kind"],
                f["node"],
                float(f["start_s"]),
                float(f["duration_s"]),
                None if f.get("magnitude") is None else float(f["magnitude"]),
            )
            for f in faults
        )

    def _active(self, node: str, kind: str, t_s: float) -> list[Fault]:
        return [f for f in self.faults if f.node == node and f.kind == kind and f.active(t_s)]

    def is_down(self, node: str, t_s: float) -> bool:
        return bool(self._active(node, "node_down", t_s))

    def pps_valid(self, node: str, t_s: float, nominal: bool) -> bool:
        return nominal and not self._active(node, "pps_invalid", t_s)

    def drift_offset_ms(self, node: str, t_s: float, pps_valid: bool) -> float:
        """Desfase acumulado por las derivas programadas (0 con PPS válido)."""
        if pps_valid:
            return 0.0
        total = 0.0
        for f in self.faults:
            if f.node == node and f.kind == "clock_drift" and t_s >= f.start_s:
                elapsed = min(t_s - f.start_s, f.duration_s)
                total += clock.drift_offset_ms(f.magnitude or 0.0, elapsed)
        return total

    def network_config(self, node: str, t_s: float) -> NetworkConfig:
        base = NetworkConfig()
        latency = [f.magnitude or 0.0 for f in self._active(node, "latency", t_s)]
        loss = [f.magnitude or 0.0 for f in self._active(node, "packet_loss", t_s)]
        if self._active(node, "link_down", t_s):
            loss.append(1.0)
        duplicate = [f.magnitude or 0.0 for f in self._active(node, "duplicate", t_s)]
        reorder = [f.magnitude or 0.0 for f in self._active(node, "reorder", t_s)]
        return NetworkConfig(
            base_latency_ms=max(latency, default=base.base_latency_ms),
            latency_sigma=base.latency_sigma,
            loss=max(loss, default=base.loss),
            duplicate=max(duplicate, default=base.duplicate),
            reorder=max(reorder, default=base.reorder),
        )

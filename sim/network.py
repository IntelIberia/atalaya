"""Red simulada entre nodos y plataforma (T1.13, REQ-FUN-004).

Cada `Envelope` emitido pasa por un enlace con latencia lognormal (mediana `base_latency_ms`,
desviación del logaritmo `latency_sigma`), pérdida, duplicado (la copia es idéntica, con el mismo
`detection_id` y la misma secuencia) y desorden (retraso extra de 1 a 3 veces la mediana). La
salida es la lista de entregas ordenada por instante de llegada. Parámetros por defecto
(20 ms, σ 0,5, sin pérdidas) **NO VERIFICADO**: orden de magnitud de una red local.

El azar sale de un `random.Random` por nodo (`red/<nodo>`) derivado de la semilla del escenario.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from random import Random
from typing import TYPE_CHECKING

from atalaya.v1.envelope_pb2 import Envelope

from sim import clock
from sim.rng import RngRegistry

if TYPE_CHECKING:
    from sim.scenario import Scenario

REORDER_MIN_FACTOR = 1.0
REORDER_MAX_FACTOR = 3.0
REORDER_MIN_DELAY_MS = 1.0


def _number(value: object, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ValueError(f"{what} no finita: {value!r}")
    return float(value)


@dataclass(frozen=True)
class NetworkConfig:
    """Condiciones de un enlace en un instante."""

    base_latency_ms: float = 20.0
    latency_sigma: float = 0.5
    loss: float = 0.0
    duplicate: float = 0.0
    reorder: float = 0.0

    def __post_init__(self) -> None:
        if _number(self.base_latency_ms, "latencia") < 0.0:
            raise ValueError(f"latencia negativa: {self.base_latency_ms!r} ms")
        if _number(self.latency_sigma, "dispersión de latencia") < 0.0:
            raise ValueError(f"dispersión de latencia negativa: {self.latency_sigma!r}")
        for name in ("loss", "duplicate", "reorder"):
            value = _number(getattr(self, name), f"probabilidad {name}")
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"probabilidad {name} fuera de [0, 1]: {value!r}")


@dataclass(frozen=True)
class Delivery:
    """Un `Envelope` entregado: instante de llegada, latencia y número de copia."""

    arrival_ns: int
    latency_ms: float
    envelope: Envelope
    copy: int = 0


def transmit(
    envelopes: Iterable[Envelope], config_for: Callable[[Envelope], NetworkConfig], rng: Random
) -> list[Delivery]:
    """Aplica pérdida, latencia, duplicado y desorden; devuelve las entregas por llegada."""
    items: list[tuple[int, int, Delivery]] = []
    for env in envelopes:
        cfg = config_for(env)
        send_ns = clock.from_timestamp(env.emitted_at)
        if cfg.loss > 0.0 and rng.random() < cfg.loss:
            continue
        copies = 2 if cfg.duplicate > 0.0 and rng.random() < cfg.duplicate else 1
        for copy in range(copies):
            latency = cfg.base_latency_ms
            if cfg.latency_sigma > 0.0:
                latency *= math.exp(cfg.latency_sigma * rng.gauss(0.0, 1.0))
            if cfg.reorder > 0.0 and rng.random() < cfg.reorder:
                latency += rng.uniform(REORDER_MIN_FACTOR, REORDER_MAX_FACTOR) * max(
                    cfg.base_latency_ms, REORDER_MIN_DELAY_MS
                )
            arrival = send_ns + round(latency * 1e6)
            items.append((arrival, len(items), Delivery(arrival, latency, env, copy)))
    items.sort(key=lambda item: (item[0], item[1]))
    return [delivery for _, _, delivery in items]


def merge(deliveries: Sequence[Delivery]) -> list[Delivery]:
    """Ordena entregas de varios enlaces por (llegada, secuencia global, copia)."""
    return sorted(deliveries, key=lambda d: (d.arrival_ns, d.envelope.sequence, d.copy))


def transmit_scenario(
    scenario: Scenario, envelopes: Sequence[Envelope], seed: int
) -> list[Delivery]:
    """Red del escenario: un enlace por nodo con las condiciones de sus fallos programados."""
    from sim.faults import FaultSchedule  # import diferido: faults importa este módulo

    schedule = FaultSchedule(scenario.data["faults"])
    rngs = RngRegistry(seed)
    by_node: dict[str, list[Envelope]] = {}
    for env in envelopes:
        by_node.setdefault(env.node_id, []).append(env)
    out: list[Delivery] = []
    for node_id in sorted(by_node):

        def config_for(env: Envelope, node: str = node_id) -> NetworkConfig:
            t_s = clock.from_timestamp(env.emitted_at) / clock.NS_PER_S
            return schedule.network_config(node, t_s)

        out.extend(transmit(by_node[node_id], config_for, rngs.get(f"red/{node_id}")))
    return merge(out)

"""H2.11: lógica de alerta con persistencia, histéresis y periodo refractario (pura, sin E/S).

ESCUCHANDO → POSIBLE → ALERTA → ESCUCHANDO, más VOZ y DEGRADADO:

- ALERTA si ≥ ``k`` de las últimas ``n`` ventanas puntuadas superan ``theta_on`` y han pasado
  ``refractory_s`` desde el fin de la alerta anterior.
- Fin de ALERTA tras ``off_windows`` ventanas **seguidas** por debajo de ``theta_off``
  (< ``theta_on``): entre ambos umbrales la alerta se mantiene (histéresis).
- Las ventanas VOZ no cuentan ni a favor ni en contra y no muestran puntuación.
- DEGRADADO si la captura lo indica o si pasan más de 2 s sin ninguna ventana; termina una alerta
  en curso y vacía la historia.

Los umbrales vienen del artefacto (``modelo_hito2.json``), no del código.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

NO_INPUT_DEGRADED_S = 2.0


class State(Enum):
    LISTENING = "ESCUCHANDO"
    POSSIBLE = "POSIBLE"
    ALERT = "ALERTA"
    SPEECH = "VOZ"
    DEGRADED = "DEGRADADO"


@dataclass(frozen=True)
class AlertConfig:
    theta_on: float
    theta_off: float
    k: int
    n: int
    off_windows: int
    refractory_s: float

    def __post_init__(self) -> None:
        for name in ("theta_on", "theta_off", "refractory_s"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ValueError(f"{name}: debe ser un número")
            if not math.isfinite(value):
                raise ValueError(f"{name}: no finito")
        for name in ("k", "n", "off_windows"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name}: debe ser un entero ≥ 1")
        if not 0.0 <= self.theta_off < self.theta_on <= 1.0:
            raise ValueError("se exige 0 ≤ theta_off < theta_on ≤ 1")
        if self.k > self.n:
            raise ValueError("se exige k ≤ n")
        if self.refractory_s < 0:
            raise ValueError("refractory_s: debe ser ≥ 0")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> AlertConfig:
        keys = {"theta_on", "theta_off", "k", "n", "off_windows", "refractory_s"}
        if set(data) != keys:
            raise ValueError(f"claves de alerta {sorted(data)} ≠ {sorted(keys)}")
        return cls(**{key: data[key] for key in keys})


@dataclass(frozen=True)
class Decision:
    t: float
    state: State
    probability: float | None  # None en VOZ y DEGRADADO: no se muestra puntuación
    alert_started: bool = False
    alert_ended: bool = False
    alert_active: bool = False


class AlertMachine:
    def __init__(self, config: AlertConfig, *, started_at: float | None = None) -> None:
        self.config = config
        self._hits: deque[bool] = deque(maxlen=config.n)
        self._alert = False
        self._below = 0
        self._last_end: float | None = None
        self._last_t = started_at
        self._last_state = State.LISTENING

    @property
    def alert_active(self) -> bool:
        return self._alert

    def _end_alert(self, t: float) -> bool:
        if not self._alert:
            return False
        self._alert = False
        self._below = 0
        self._last_end = t
        self._hits.clear()
        return True

    def update(
        self,
        t: float,
        *,
        probability: float | None,
        speech: bool = False,
        degraded: bool = False,
    ) -> Decision:
        self._last_t = t
        if degraded:
            ended = self._end_alert(t)
            self._hits.clear()
            return self._emit(Decision(t, State.DEGRADED, None, alert_ended=ended))
        if speech:
            # La ventana se descarta: no cuenta, no muestra puntuación y una alerta en curso
            # sigue activa (``alert_active``) sin acercarse ni alejarse de su fin.
            return self._emit(Decision(t, State.SPEECH, None))
        if probability is None or not math.isfinite(probability):
            raise ValueError("una ventana puntuada necesita una probabilidad finita")
        p = float(probability)
        cfg = self.config
        if self._alert:
            self._below = self._below + 1 if p < cfg.theta_off else 0
            if self._below >= cfg.off_windows:
                self._end_alert(t)
                return self._emit(Decision(t, State.LISTENING, p, alert_ended=True))
            return self._emit(Decision(t, State.ALERT, p))
        self._hits.append(p >= cfg.theta_on)
        hits = sum(self._hits)
        refractory_ok = self._last_end is None or t - self._last_end >= cfg.refractory_s
        if hits >= cfg.k and refractory_ok:
            self._alert = True
            self._below = 0
            return self._emit(Decision(t, State.ALERT, p, alert_started=True))
        state = State.POSSIBLE if hits else State.LISTENING
        return self._emit(Decision(t, state, p))

    def _emit(self, decision: Decision) -> Decision:
        self._last_state = decision.state
        return replace(decision, alert_active=self._alert)

    def state_at(self, now: float) -> State:
        """Estado a mostrar en ``now``: DEGRADADO si no llega nada desde hace más de 2 s."""
        if self._last_t is not None and now - self._last_t > NO_INPUT_DEGRADED_S:
            return State.DEGRADED
        return self._last_state

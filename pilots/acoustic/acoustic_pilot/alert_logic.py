# Lógica de alerta con persistencia e histéresis (hito 2): máquina de estados pura, sin E/S,
# compartida por la sección «Prueba tu audio» del cuaderno y por el Mac (H2.11 puede importarla).
# ESCUCHANDO -> POSIBLE -> ALERTA -> ESCUCHANDO, más VOZ (ventana descartada por la puerta de voz:
# no cuenta ni a favor ni en contra) y DEGRADADO (sin dato). ALERTA si >= k de las últimas n
# ventanas válidas superan theta_on; fin tras fin_ventanas seguidas por debajo de theta_off <
# theta_on; refractario entre el fin de una alerta y el inicio de la siguiente. Los umbrales los
# fija el artefacto (validación de Colab), no el código. Autocontenido (stdlib).
import math
from collections import deque
from collections.abc import Sequence

ALERT_STATES = ("ESCUCHANDO", "POSIBLE", "ALERTA", "VOZ", "DEGRADADO")
ALERT_DEFAULTS = {"k": 3, "n": 5, "fin_ventanas": 4, "refractario_s": 5.0, "salto_s": 0.48}


def validate_alert_config(cfg: dict) -> dict:
    """Comprueba la configuración (fallo cerrado) y devuelve una copia completa."""
    out = {**ALERT_DEFAULTS, **cfg}
    unknown = set(out) - set(ALERT_DEFAULTS) - {"theta_on", "theta_off"}
    if unknown:
        raise ValueError(f"campos desconocidos en la alerta: {sorted(unknown)}")
    for key in ("theta_on", "theta_off"):
        v = out.get(key)
        if not isinstance(v, int | float) or not math.isfinite(v) or not 0 < v < 1:
            raise ValueError(f"{key} debe estar en (0, 1)")
    if out["theta_off"] >= out["theta_on"]:
        raise ValueError("theta_off debe ser menor que theta_on (histéresis)")
    for key in ("k", "n", "fin_ventanas"):
        if not isinstance(out[key], int) or out[key] < 1:
            raise ValueError(f"{key} debe ser un entero >= 1")
    if out["k"] > out["n"]:
        raise ValueError("k no puede ser mayor que n")
    if out["refractario_s"] < 0 or out["salto_s"] <= 0:
        raise ValueError("tiempos no válidos")
    return out


class AlertMachine:
    """Una llamada a step() por ventana (cada salto_s segundos)."""

    def __init__(self, cfg: dict) -> None:
        self.cfg = validate_alert_config(cfg)
        self.recent: deque[bool] = deque(maxlen=self.cfg["n"])
        self.alerting = False
        self.below = 0
        self.t = 0
        self.last_end: float | None = None
        self.events = 0

    def _underlying(self) -> str:
        if self.alerting:
            return "ALERTA"
        return "POSIBLE" if any(self.recent) else "ESCUCHANDO"

    def step(self, prob: float | None, *, speech: bool = False) -> str:
        now = self.t * self.cfg["salto_s"]
        self.t += 1
        if prob is None or not math.isfinite(prob):
            return "DEGRADADO"
        if speech:
            return "VOZ"
        self.recent.append(prob >= self.cfg["theta_on"])
        if self.alerting:
            self.below = self.below + 1 if prob < self.cfg["theta_off"] else 0
            if self.below >= self.cfg["fin_ventanas"]:
                self.alerting, self.below, self.last_end = False, 0, now
                self.recent.clear()
        elif sum(self.recent) >= self.cfg["k"]:
            refractory_ok = (
                self.last_end is None or now - self.last_end >= self.cfg["refractario_s"]
            )
            if refractory_ok:
                self.alerting, self.below = True, 0
                self.events += 1
        return self._underlying()


def run_alert(
    probs: Sequence[float | None], speech: Sequence[bool] | None, cfg: dict
) -> tuple[list[str], int]:
    """Estados por ventana y número de alertas de una secuencia completa."""
    machine = AlertMachine(cfg)
    flags = list(speech) if speech is not None else [False] * len(probs)
    if len(flags) != len(probs):
        raise ValueError("probs y speech deben tener la misma longitud")
    states = [machine.step(p, speech=s) for p, s in zip(probs, flags, strict=True)]
    return states, machine.events


def persistence_score(probs: Sequence[float], k: int = 3, n: int = 5) -> float:
    """Puntuación de clip equivalente a «>= k de n ventanas sobre el umbral»: máximo, sobre los
    tramos de n ventanas, del k-ésimo valor más alto. Clip con m < n ventanas: k_m = ceil(k·m/n)
    (un clip corto no puede acumular k ventanas; se informa como limitación)."""
    p = [float(v) for v in probs]
    if not p:
        raise ValueError("clip sin ventanas")
    if any(not math.isfinite(v) for v in p):
        raise ValueError("probabilidades no finitas")
    if k < 1 or k > n:
        raise ValueError("k debe estar en [1, n]")
    if len(p) < n:
        k_m = max(1, math.ceil(k * len(p) / n))
        return sorted(p, reverse=True)[k_m - 1]
    return max(sorted(p[i : i + n], reverse=True)[k - 1] for i in range(len(p) - n + 1))

# Calibración y curvas (iteración 5): Platt o isotónica ajustadas SOLO en validación, ECE,
# diagrama de fiabilidad, DET y falsas alarmas por hora ESTIMADAS (no verificadas).
# Autocontenido (numpy, scikit-learn): build_colab.py lo incrusta tal cual en el cuaderno.
from collections.abc import Sequence

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import det_curve

ECE_BINS = 15
FA_ESTIMATE_STATUS = "ESTIMACIÓN, NO VERIFICADA como métrica de campo"
FA_ESTIMATE_NOTE = (
    "Alarmas contadas sobre la concatenación de puntuaciones por ventana de clips negativos de "
    "test (fuera de fold); no es una grabación continua de un emplazamiento: no sustituye a la "
    "medida de falsas alarmas por hora en campo"
)


def _logit(p: np.ndarray) -> np.ndarray:
    q = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(q / (1 - q))


def fit_calibrator(y: np.ndarray, p: np.ndarray, method: str) -> dict:
    """Ajusta en VALIDACIÓN: 'platt' (logística sobre el logit) o 'isotonica'."""
    y = np.asarray(y, dtype=int)
    if set(np.unique(y).tolist()) != {0, 1}:
        raise ValueError("la calibración necesita ambas clases en validación")
    if method == "platt":
        lr = LogisticRegression(C=1e4, max_iter=1000).fit(_logit(p)[:, None], y)
        return {"method": "platt", "a": float(lr.coef_[0, 0]), "b": float(lr.intercept_[0])}
    if method == "isotonica":
        iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        iso.fit(np.asarray(p, dtype=float), y)
        return {
            "method": "isotonica",
            "x": iso.X_thresholds_.tolist(),
            "y": iso.y_thresholds_.tolist(),
        }
    raise ValueError(f"método de calibración desconocido: {method}")


def apply_calibration(cal: dict, p: np.ndarray) -> np.ndarray:
    q = np.asarray(p, dtype=float)
    if cal["method"] == "platt":
        return 1 / (1 + np.exp(-(cal["a"] * _logit(q) + cal["b"])))
    if cal["method"] == "isotonica":
        return np.interp(q, cal["x"], cal["y"])
    raise ValueError("calibrador no válido")


def reliability_bins(y: np.ndarray, p: np.ndarray, *, n_bins: int = ECE_BINS) -> list[dict]:
    """Bins de igual anchura en [0, 1] (el último incluye 1,0); solo los no vacíos."""
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    idx = np.minimum((p * n_bins).astype(int), n_bins - 1)
    out = []
    for b in range(n_bins):
        mask = idx == b
        if mask.any():
            out.append(
                {
                    "bin": b,
                    "n": int(mask.sum()),
                    "confianza_media": float(p[mask].mean()),
                    "fraccion_positivos": float(y[mask].mean()),
                }
            )
    return out


def expected_calibration_error(y: np.ndarray, p: np.ndarray, *, n_bins: int = ECE_BINS) -> float:
    bins = reliability_bins(y, p, n_bins=n_bins)
    total = sum(b["n"] for b in bins)
    return sum(b["n"] * abs(b["fraccion_positivos"] - b["confianza_media"]) for b in bins) / total


def brier_score(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((np.asarray(p, dtype=float) - np.asarray(y, dtype=float)) ** 2))


def det_points(y: np.ndarray, p: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Curva DET (tasa de falsas alarmas frente a tasa de fallos) por umbral."""
    return det_curve(np.asarray(y, dtype=int), np.asarray(p, dtype=float))


def alarm_events(scores: np.ndarray, threshold: float, *, hop_s: float, refractory_s: float) -> int:
    """Alarmas = flancos de subida sobre el umbral. Un flanco a menos de refractory_s del fin
    de la alarma anterior se considera la misma alarma."""
    above = np.asarray(scores, dtype=float) >= threshold
    events, last_end = 0, None
    for t in range(len(above)):
        rising = above[t] and (t == 0 or not above[t - 1])
        if rising and (last_end is None or (t - last_end) * hop_s >= refractory_s):
            events += 1
        if above[t]:
            last_end = t
    return events


def false_alarms_per_hour_estimate(
    streams: Sequence[np.ndarray], threshold: float, *, hop_s: float, refractory_s: float
) -> dict:
    """FA/h sobre concatenaciones de negativos: SIEMPRE marcada como estimación no verificada."""
    events = sum(
        alarm_events(s, threshold, hop_s=hop_s, refractory_s=refractory_s) for s in streams
    )
    hours = sum(len(s) for s in streams) * hop_s / 3600
    return {
        "status": FA_ESTIMATE_STATUS,
        "nota": FA_ESTIMATE_NOTE,
        "eventos": int(events),
        "horas": hours,
        "valor": events / hours if hours > 0 else None,
    }

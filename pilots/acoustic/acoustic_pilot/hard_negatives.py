# Negativos difíciles (iteración 5): tipo de cada negativo, matriz de confusión por tipo y
# reponderación de los negativos de entrenamiento con mayor puntuación. Orienta qué grabar en
# Ceuta. Autocontenido (numpy): build_colab.py lo incrusta tal cual en el cuaderno.
import math
from collections.abc import Sequence

import numpy as np

NEGATIVE_TYPES = {
    "Motorcycle": "motos",
    "Boat_and_Water_vehicle": "barcos",
    "Aircraft": "aviones",
    "Fixed-wing_aircraft_and_airplane": "aviones",
    "HELICOPTER": "helicópteros",
    "helicopter": "helicópteros",
    "Insect": "insectos",
    "Wind": "viento",
    "Rain": "lluvia",
    "rain": "lluvia",
    "sea_waves": "mar y oleaje",
    "Engine": "motores y maquinaria",
    "chainsaw": "motores y maquinaria",
    "Bird": "aves",
    "Gull_and_seagull": "aves",
    "rooster": "aves",
    "dog": "perros",
    "crackling_fire": "fuego",
    "clock_tick": "tictac",
    "BACKGROUND": "fondo de campo",
    "ARIS_BACKGROUND": "fondo de campo",
}


def negative_type(source: str, clase: str) -> str:
    """Tipo de negativo legible; 'otros' si la clase no está en la tabla (nunca falla)."""
    return NEGATIVE_TYPES.get(clase, "otros")


def confusion_by_negative_type(
    types: Sequence[str | None],
    labels: Sequence[int],
    scores: Sequence[float],
    thresholds: float | Sequence[float],
) -> list[dict]:
    """Falsas alarmas por tipo de negativo (las filas positivas se ignoran). El umbral puede
    ser único o uno por fila (p. ej. el de cada fold). Orden: FPR desc., n desc., nombre."""
    thr = np.broadcast_to(np.asarray(thresholds, dtype=float), (len(labels),))
    rows: dict[str, list[float]] = {}
    alarms: dict[str, int] = {}
    for t, y, s, h in zip(types, labels, scores, thr, strict=True):
        if int(y) == 1:
            continue
        rows.setdefault(str(t), []).append(float(s))
        alarms[str(t)] = alarms.get(str(t), 0) + int(float(s) >= h)
    table = []
    for t, values in rows.items():
        v = np.asarray(values)
        table.append(
            {
                "tipo": t,
                "n": int(v.size),
                "fp": alarms[t],
                "fpr": alarms[t] / v.size,
                "puntuacion_media": float(v.mean()),
                "puntuacion_p95": float(np.percentile(v, 95)),
            }
        )
    return sorted(table, key=lambda r: (-r["fpr"], -r["n"], r["tipo"]))


def recording_priorities(table: Sequence[dict], *, top: int = 5) -> list[str]:
    """Tipos con más falsas alarmas (fp > 0): qué confusores grabar primero en campo."""
    return [r["tipo"] for r in table if r["fp"] > 0][:top]


def hard_negative_weights(
    weights: np.ndarray,
    labels: Sequence[int],
    train_scores: Sequence[float],
    *,
    fraction: float = 0.1,
    factor: float = 3.0,
) -> tuple[np.ndarray, list[int]]:
    """Multiplica por factor el peso del `fraction` de negativos de ENTRENAMIENTO con mayor
    puntuación (minería de negativos difíciles, segunda ronda). Nunca toca validación ni test."""
    y = np.asarray(labels, dtype=int)
    s = np.asarray(train_scores, dtype=float)
    negatives = np.flatnonzero(y == 0)
    k = math.ceil(len(negatives) * fraction)
    order = negatives[np.lexsort((negatives, -s[negatives]))]
    hard = sorted(int(i) for i in order[:k])
    new = np.array(weights, dtype=float, copy=True)
    new[hard] *= factor
    return new, hard

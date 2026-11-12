# Partición por grupos, umbral elegido en validación y métricas con incertidumbre.
# Autocontenido (stdlib, numpy, scikit-learn): build_colab.py lo incrusta tal cual en el
# cuaderno de Colab, de modo que el código probado es el que se ejecuta allí.
import math
import random
from collections.abc import Sequence

import numpy as np
from sklearn.metrics import average_precision_score

PROVISIONAL_LABEL = "prueba técnica, contaminación entre particiones no descartada"


def split_indices_by_group(
    labels: Sequence[int], groups: Sequence[str], *, seed: int
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    """Train/validación/test por grupos: ningún grupo aparece en dos particiones."""
    if len(labels) != len(groups):
        raise ValueError("labels y groups deben tener la misma longitud")
    unique = sorted(set(groups))
    if len(unique) < 6:
        raise ValueError("se necesitan al menos seis grupos independientes")
    n_test = max(2, round(len(unique) * 0.2))
    n_validation = max(2, round(len(unique) * 0.2))
    if len(unique) - n_test - n_validation < 2:
        raise ValueError("grupos insuficientes para train/validation/test")
    for attempt in range(1000):
        shuffled = unique.copy()
        random.Random(seed + attempt).shuffle(shuffled)
        chosen = (
            set(shuffled[n_test + n_validation :]),
            set(shuffled[n_test : n_test + n_validation]),
            set(shuffled[:n_test]),
        )
        parts = tuple(
            tuple(i for i, group in enumerate(groups) if group in selected) for selected in chosen
        )
        if all({labels[i] for i in part} == {0, 1} for part in parts):
            train, validation, test = parts
            seen = [{groups[i] for i in part} for part in parts]
            if seen[0] & seen[1] or seen[0] & seen[2] or seen[1] & seen[2]:
                raise ValueError("un grupo aparece en varias particiones")
            return train, validation, test
    raise ValueError("no hay partición por grupos con ambas clases en los tres conjuntos")


def choose_threshold(y_validation: np.ndarray, p_validation: np.ndarray) -> float:
    """Umbral que maximiza F1 en validación; en empate, el más alto (menos alarmas)."""
    y = np.asarray(y_validation).astype(int)
    p = np.asarray(p_validation, dtype=float)
    if set(np.unique(y).tolist()) != {0, 1}:
        raise ValueError("la validación necesita ambas clases para fijar el umbral")
    best_threshold, best_f1 = math.nan, -1.0
    for threshold in np.unique(p):
        pred = p >= threshold
        tp = int(np.sum(pred & (y == 1)))
        fp = int(np.sum(pred & (y == 0)))
        fn = int(np.sum(~pred & (y == 1)))
        f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
        if f1 >= best_f1:
            best_threshold, best_f1 = float(threshold), f1
    return best_threshold


def binary_metrics(y_true: np.ndarray, scores: np.ndarray, threshold: float) -> dict:
    """Matriz de confusión, precision, recall y PR-AUC (precisión media)."""
    y = np.asarray(y_true).astype(int)
    p = np.asarray(scores, dtype=float)
    pred = p >= threshold
    tp = int(np.sum(pred & (y == 1)))
    fp = int(np.sum(pred & (y == 0)))
    fn = int(np.sum(~pred & (y == 1)))
    tn = int(np.sum(~pred & (y == 0)))
    both = set(np.unique(y).tolist()) == {0, 1}
    return {
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "precision": tp / (tp + fp) if tp + fp else math.nan,
        "recall": tp / (tp + fn) if tp + fn else math.nan,
        "pr_auc": float(average_precision_score(y, p)) if both else math.nan,
    }


def group_bootstrap(
    y_true: np.ndarray,
    scores: np.ndarray,
    groups: Sequence[str],
    threshold: float,
    *,
    n_boot: int = 2000,
    seed: int = 20261111,
    min_groups: int = 10,
) -> dict:
    """IC 95 % por percentiles remuestreando grupos completos, no clips sueltos."""
    y = np.asarray(y_true).astype(int)
    p = np.asarray(scores, dtype=float)
    unique = sorted(set(groups))
    if len(unique) < min_groups:
        return {"status": "INSUFICIENTE", "n_groups": len(unique), "min_groups": min_groups}
    members = {g: np.array([i for i, h in enumerate(groups) if h == g]) for g in unique}
    rng = np.random.default_rng(seed)
    samples: dict[str, list[float]] = {"precision": [], "recall": [], "pr_auc": []}
    for _ in range(n_boot):
        drawn = rng.choice(len(unique), size=len(unique), replace=True)
        idx = np.concatenate([members[unique[k]] for k in drawn])
        metrics = binary_metrics(y[idx], p[idx], threshold)
        for name in samples:
            samples[name].append(metrics[name])
    intervals = {}
    for name, values in samples.items():
        finite = np.asarray(values, dtype=float)
        finite = finite[np.isfinite(finite)]
        if finite.size < n_boot // 2:
            return {"status": "INSUFICIENTE", "n_groups": len(unique), "min_groups": min_groups}
        intervals[name] = (
            float(np.percentile(finite, 2.5)),
            float(np.percentile(finite, 97.5)),
        )
    return {"status": "OK", "n_groups": len(unique), "n_boot": n_boot, "intervals": intervals}


def false_alarms_per_hour(
    n_false_alarms: int, *, continuous_negative_seconds: float, min_hours: float
) -> dict:
    """Solo hay cifra con duración negativa continua conocida y suficiente."""
    hours = continuous_negative_seconds / 3600
    if hours < min_hours:
        return {"status": "NO VERIFICADA", "value": None, "hours": hours, "min_hours": min_hours}
    return {"status": "OK", "value": n_false_alarms / hours, "hours": hours, "min_hours": min_hours}


def metric_caption(*, provisional: bool) -> str:
    """Rótulo que acompaña a cada métrica según la fiabilidad de los grupos."""
    if provisional:
        return f"[{PROVISIONAL_LABEL}]"
    return "[grupos verificados; generalización limitada a estos grupos]"

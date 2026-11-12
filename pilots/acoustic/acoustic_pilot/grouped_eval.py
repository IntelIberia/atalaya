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
        # Tasa de falsos positivos por clip: la única cifra útil en fuentes solo negativas.
        "fpr": fp / (fp + tn) if fp + tn else math.nan,
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
    samples: dict[str, list[float]] = {"precision": [], "recall": [], "pr_auc": [], "fpr": []}
    for _ in range(n_boot):
        drawn = rng.choice(len(unique), size=len(unique), replace=True)
        idx = np.concatenate([members[unique[k]] for k in drawn])
        metrics = binary_metrics(y[idx], p[idx], threshold)
        for name in samples:
            samples[name].append(metrics[name])
    # Por métrica: None si menos de la mitad de las réplicas dan un valor definido (p. ej.
    # recall en una fuente sin positivos). Nunca se rellena con un valor inventado.
    intervals: dict[str, tuple[float, float] | None] = {}
    for name, values in samples.items():
        finite = np.asarray(values, dtype=float)
        finite = finite[np.isfinite(finite)]
        intervals[name] = (
            None
            if finite.size < n_boot // 2
            else (float(np.percentile(finite, 2.5)), float(np.percentile(finite, 97.5)))
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


def split_with_preassigned(
    labels: Sequence[int],
    groups: Sequence[str],
    preassigned: dict[int, str],
    *,
    seed: int,
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    """Partición única: los índices preasignados ('train'/'val'/'test', p. ej. el split de los
    autores de ITU ARIS) conservan su parte; el resto se reparte por grupos. Un grupo nunca
    cruza particiones ni mezcla índices preasignados y libres."""
    if len(labels) != len(groups):
        raise ValueError("labels y groups deben tener la misma longitud")
    names = ("train", "val", "test")
    fixed_part: dict[str, str] = {}
    for index, part in preassigned.items():
        if part not in names:
            raise ValueError(f"partición desconocida: {part}")
        if fixed_part.setdefault(groups[index], part) != part:
            raise ValueError(f"el grupo {groups[index]} cruza particiones")
    free = [i for i in range(len(labels)) if i not in preassigned]
    if any(groups[i] in fixed_part for i in free):
        raise ValueError("un grupo mezcla segmentos preasignados y libres")
    parts: list[list[int]] = [[], [], []]
    for index, part in preassigned.items():
        parts[names.index(part)].append(index)
    if free:
        sub = split_indices_by_group(
            [labels[i] for i in free], [groups[i] for i in free], seed=seed
        )
        for k, chunk in enumerate(sub):
            parts[k].extend(free[j] for j in chunk)
    train, validation, test = (tuple(sorted(p)) for p in parts)
    seen = [{groups[i] for i in part} for part in (train, validation, test)]
    if seen[0] & seen[1] or seen[0] & seen[2] or seen[1] & seen[2]:
        raise ValueError("un grupo aparece en varias particiones")
    if any({labels[i] for i in part} != {0, 1} for part in (train, validation, test)):
        raise ValueError("cada partición necesita ambas clases")
    return train, validation, test


def group_folds(
    labels: Sequence[int], groups: Sequence[str], *, k: int = 5, seed: int
) -> tuple[int, ...]:
    """Asigna cada grupo entero a uno de k folds (devuelve el fold de cada índice). Los grupos
    se recorren de mayor a menor (desempate barajado con semilla) y cada uno va al fold con
    menos ejemplos de su clase mayoritaria. Todos los folds deben tener ambas clases."""
    if len(labels) != len(groups):
        raise ValueError("labels y groups deben tener la misma longitud")
    if k < 3:
        raise ValueError("se necesitan al menos tres folds")
    members: dict[str, list[int]] = {}
    for i, g in enumerate(groups):
        members.setdefault(g, []).append(i)
    if len(members) < k:
        raise ValueError("menos grupos que folds")
    keys = sorted(members)
    random.Random(seed).shuffle(keys)
    keys.sort(key=lambda g: -len(members[g]))
    load = [[0, 0] for _ in range(k)]  # [negativos, positivos] por fold
    fold_of_group = {}
    for g in keys:
        pos = sum(int(labels[i]) for i in members[g])
        neg = len(members[g]) - pos
        cls = int(pos >= neg)
        target = min(range(k), key=lambda f: (load[f][cls], load[f][0] + load[f][1], f))
        fold_of_group[g] = target
        load[target][0] += neg
        load[target][1] += pos
    if any(n == 0 or p == 0 for n, p in load):
        raise ValueError("algún fold no tiene ambas clases")
    return tuple(fold_of_group[g] for g in groups)


def rotating_folds(
    folds: Sequence[int], k: int
) -> list[tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]]:
    """Validación cruzada por grupos: en la vuelta f, test = fold f, validación = fold f+1
    (módulo k) solo para fijar el umbral, entrenamiento = el resto."""
    if set(folds) != set(range(k)):
        raise ValueError("los folds deben ser exactamente 0..k-1")
    out = []
    for f in range(k):
        v = (f + 1) % k
        test = tuple(i for i, x in enumerate(folds) if x == f)
        validation = tuple(i for i, x in enumerate(folds) if x == v)
        train = tuple(i for i, x in enumerate(folds) if x not in (f, v))
        out.append((train, validation, test))
    return out


def choose_threshold_for_recall(
    y_validation: np.ndarray, p_validation: np.ndarray, *, target_recall: float = 0.9
) -> dict:
    """Umbral MÁS ALTO cuyo recall en validación es >= target_recall: no perder drones con el
    mínimo de alarmas a esa exigencia. Se elige solo en validación, nunca en test."""
    if not 0.0 < target_recall <= 1.0:
        raise ValueError("target_recall debe estar en (0, 1]")
    y = np.asarray(y_validation).astype(int)
    p = np.asarray(p_validation, dtype=float)
    if set(np.unique(y).tolist()) != {0, 1}:
        raise ValueError("la validación necesita ambas clases para fijar el umbral")
    positives = int(np.sum(y == 1))
    for threshold in sorted(np.unique(p).tolist(), reverse=True):
        pred = p >= threshold
        tp = int(np.sum(pred & (y == 1)))
        if tp / positives >= target_recall:
            fp = int(np.sum(pred & (y == 0)))
            return {
                "threshold": float(threshold),
                "target_recall": float(target_recall),
                "validation_recall": tp / positives,
                "validation_precision": tp / (tp + fp),
                "criterion": f"umbral más alto con recall de validación >= {target_recall:.2f}",
            }
    raise ValueError("puntuaciones no válidas")  # el umbral mínimo siempre da recall 1


def metrics_by_source(
    y_true: np.ndarray,
    scores: np.ndarray,
    sources: Sequence[str],
    groups: Sequence[str],
    threshold: float,
    *,
    seed: int = 20261111,
    n_boot: int = 2000,
    min_groups: int = 10,
) -> list[dict]:
    """Métricas por fuente y agregadas (fila TOTAL) con IC 95 % remuestreando grupos."""
    if not len(y_true) == len(scores) == len(sources) == len(groups):
        raise ValueError("longitudes distintas")
    y = np.asarray(y_true).astype(int)
    p = np.asarray(scores, dtype=float)
    rows = []
    for name in [*sorted(set(sources)), "TOTAL"]:
        idx = np.array([i for i, s in enumerate(sources) if name in ("TOTAL", s)], dtype=int)
        metrics = binary_metrics(y[idx], p[idx], threshold)
        boot = group_bootstrap(
            y[idx],
            p[idx],
            [groups[i] for i in idx],
            threshold,
            n_boot=n_boot,
            seed=seed,
            min_groups=min_groups,
        )
        rows.append(
            {
                "fuente": name,
                "n": int(idx.size),
                "positivos": int(y[idx].sum()),
                "grupos": len({groups[i] for i in idx}),
                **metrics,
                "ic95": boot,
            }
        )
    return rows

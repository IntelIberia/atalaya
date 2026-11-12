# Control de fugas y desplazamiento de dominio (iteración 5): StratifiedGroupKFold por grupo y
# leave-one-source-out. Autocontenido: build_colab.py lo incrusta tal cual en el cuaderno.
from collections.abc import Sequence

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold


def stratified_group_folds(
    labels: Sequence[int], groups: Sequence[str], *, k: int = 5, seed: int
) -> tuple[int, ...]:
    """Fold de cada índice con StratifiedGroupKFold: grupos enteros, clases estratificadas.
    Falla (no corrige) si algún fold queda sin una de las dos clases."""
    if len(labels) != len(groups):
        raise ValueError("labels y groups deben tener la misma longitud")
    if len(set(groups)) < k:
        raise ValueError("menos grupos que folds")
    y = np.asarray(labels, dtype=int)
    folds = np.full(len(y), -1, dtype=int)
    splitter = StratifiedGroupKFold(n_splits=k, shuffle=True, random_state=seed)
    for f, (_, test) in enumerate(splitter.split(np.zeros(len(y)), y, np.asarray(groups))):
        folds[test] = f
    for f in range(k):
        if set(y[folds == f].tolist()) != {0, 1}:
            raise ValueError(f"el fold {f} no tiene ambas clases")
    return tuple(int(f) for f in folds)


def leave_one_source_out(
    labels: Sequence[int],
    groups: Sequence[str],
    sources: Sequence[str],
    *,
    seed: int,
    k_inner: int = 5,
) -> list[dict]:
    """Por cada fuente: test = esa fuente entera (nunca vista); con el resto, un fold de
    StratifiedGroupKFold es validación (umbral y calibración) y los demás, entrenamiento."""
    if not len(labels) == len(groups) == len(sources):
        raise ValueError("longitudes distintas")
    out = []
    for source in sorted(set(sources)):
        rest = [i for i, s in enumerate(sources) if s != source]
        test = tuple(i for i, s in enumerate(sources) if s == source)
        inner = stratified_group_folds(
            [labels[i] for i in rest], [groups[i] for i in rest], k=k_inner, seed=seed
        )
        validation = tuple(i for i, f in zip(rest, inner, strict=True) if f == 0)
        train = tuple(i for i, f in zip(rest, inner, strict=True) if f != 0)
        seen = [{groups[i] for i in p} for p in (train, validation, test)]
        if seen[0] & seen[1] or seen[0] & seen[2] or seen[1] & seen[2]:
            raise ValueError("un grupo aparece en varias particiones")
        out.append({"fuente": source, "train": train, "validation": validation, "test": test})
    return out


def assert_no_cross_partition_pairs(
    pairs: Sequence[tuple[int, int, float]], assignment: Sequence[object]
) -> None:
    """Falla si algún par casi duplicado (i, j, sim) cae en particiones distintas."""
    bad = [(i, j, s) for i, j, s in pairs if assignment[i] != assignment[j]]
    if bad:
        raise ValueError(f"casi duplicado a ambos lados de una partición: {bad[:5]}")

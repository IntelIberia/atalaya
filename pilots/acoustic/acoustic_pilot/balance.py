# Desequilibrio (iteración 5): pesos por clase y por fuente y muestreo balanceado.
# Autocontenido (numpy): build_colab.py lo incrusta tal cual en el cuaderno.
from collections.abc import Sequence

import numpy as np


def class_source_weights(labels: Sequence[int], sources: Sequence[str]) -> np.ndarray:
    """Peso por muestra: cada clase suma N/2 y, dentro de una clase, cada fuente que la aporta
    suma lo mismo. Así ninguna fuente (p. ej. ITU ARIS, ~5.500 segmentos) domina la pérdida."""
    y = np.asarray(labels, dtype=int)
    s = np.asarray(sources)
    if len(y) != len(s):
        raise ValueError("longitudes distintas")
    classes = sorted(set(y.tolist()))
    w = np.zeros(len(y), dtype=float)
    for cls in classes:
        cells = sorted(set(s[y == cls].tolist()))
        for src in cells:
            mask = (y == cls) & (s == src)
            w[mask] = len(y) / (len(classes) * len(cells) * mask.sum())
    return w


def balanced_sample(
    labels: Sequence[int], sources: Sequence[str], n: int, *, seed: int
) -> list[int]:
    """n índices con reemplazo y probabilidad proporcional a class_source_weights."""
    w = class_source_weights(labels, sources)
    rng = np.random.default_rng(seed)
    return rng.choice(len(w), size=n, replace=True, p=w / w.sum()).tolist()

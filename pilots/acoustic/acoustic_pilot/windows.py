# Modelado por ventanas (iteración 5): rasgos por ventana YAMNet (0,96 s, salto 0,48 s),
# agregación por clip y suavizado temporal. Autocontenido (numpy): se incrusta en el cuaderno.
from collections.abc import Sequence

import numpy as np

YAMNET_HOP_S = 0.48
SMOOTH_WINDOWS = 3  # ~1,4 s: un pico de una sola ventana no basta para disparar
ATTENTION_TEMPERATURE = 0.1  # agrupación «atención ligera» (softmax sobre la propia puntuación)
AGGREGATIONS = ("media", "max", "top3", "max_suavizado", "atencion")


def pack_frames(blocks: Sequence[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Concatena las ventanas de cada clip (float32) y devuelve (datos, offsets) para cachearlas
    en un único .npz; las ventanas del clip i son datos[offsets[i]:offsets[i+1]]."""
    sizes = [len(b) for b in blocks]
    offsets = np.concatenate([[0], np.cumsum(sizes)]).astype(np.int64)
    data = np.concatenate([np.asarray(b, dtype=np.float32) for b in blocks], axis=0)
    return data, offsets


def unpack_frames(data: np.ndarray, offsets: np.ndarray, i: int) -> np.ndarray:
    return data[offsets[i] : offsets[i + 1]]


def smooth_scores(scores: np.ndarray, k: int = SMOOTH_WINDOWS) -> np.ndarray:
    """Media móvil centrada de k ventanas; en los bordes promedia solo las disponibles."""
    p = np.asarray(scores, dtype=float)
    if k <= 1 or p.size == 0:
        return p.copy()
    half = k // 2
    csum = np.concatenate([[0.0], np.cumsum(p)])
    idx = np.arange(p.size)
    lo = np.maximum(idx - half, 0)
    hi = np.minimum(idx + half + 1, p.size)
    return (csum[hi] - csum[lo]) / (hi - lo)


def aggregate_window_scores(scores: np.ndarray, method: str) -> float:
    """Probabilidad por clip a partir de las probabilidades por ventana."""
    p = np.asarray(scores, dtype=float)
    if p.size == 0:
        raise ValueError("clip sin ventanas")
    if method == "media":
        return float(p.mean())
    if method == "max":
        return float(p.max())
    if method == "top3":
        return float(np.sort(p)[-3:].mean())
    if method == "max_suavizado":
        return float(smooth_scores(p).max())
    if method == "atencion":
        w = np.exp((p - p.max()) / ATTENTION_TEMPERATURE)
        return float(np.sum(w * p) / np.sum(w))
    raise ValueError(f"agregación desconocida: {method}")


def frame_training_set(
    data: np.ndarray,
    offsets: np.ndarray,
    labels: Sequence[int],
    indices: Sequence[int],
    *,
    max_frames: int = 8,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Ventanas de entrenamiento (etiqueta débil: la del clip). Como máximo max_frames por
    clip, equiespaciadas y deterministas, para que los clips largos no dominen."""
    xs, ys, owners = [], [], []
    for i in indices:
        frames = unpack_frames(data, offsets, i)
        if len(frames) > max_frames:
            pick = np.unique(np.linspace(0, len(frames) - 1, max_frames).round().astype(int))
            frames = frames[pick]
        xs.append(frames)
        ys.append(np.full(len(frames), int(labels[i])))
        owners.append(np.full(len(frames), int(i)))
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(owners)

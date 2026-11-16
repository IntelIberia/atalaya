# Calidad de datos (iteración 5): formato, clips defectuosos, sonoridad y duplicados.
# Autocontenido (stdlib, numpy, scipy): build_colab.py lo incrusta tal cual en el cuaderno.
import hashlib
import math
from collections.abc import Sequence

import numpy as np
from scipy.signal import lfilter, resample_poly

TARGET_SR = 16000
# Umbrales documentados (prueba técnica; ver docs/evidence/piloto-acustico):
SILENCE_RMS_DBFS = -60.0  # RMS por debajo => clip silencioso (sin información útil)
SATURATION_LEVEL = 0.999  # |x| >= este valor cuenta como muestra recortada
SATURATION_MAX_FRACTION = 0.01  # > 1 % de muestras recortadas => clip saturado
MIN_SECONDS = 0.5  # más corto => corrupto (YAMNet necesita 0,975 s; se rellena hasta ahí)
# Casi duplicados: coseno de la media de embeddings YAMNet >= 0,995. YAMNet da embeddings no
# negativos (ReLU) y clips distintos de una misma escena llegan a ~0,95-0,98; 0,995 solo une
# copias recortadas, re-codificadas o con ganancia distinta. Heurística: se informa siempre.
NEAR_DUPLICATE_COSINE = 0.995


def normalize_format(signal: np.ndarray, sr: int, *, target_sr: int = TARGET_SR) -> np.ndarray:
    """Mono (media de canales), target_sr Hz y float32. Acepta (n,), (canales, n) o (n, canales)
    y PCM entero (se escala a [-1, 1])."""
    if sr <= 0 or target_sr <= 0:
        raise ValueError("frecuencia de muestreo no válida")
    x = np.asarray(signal)
    if np.issubdtype(x.dtype, np.integer):
        x = x.astype(np.float64) / float(np.iinfo(x.dtype).max)
    x = x.astype(np.float64)
    if x.ndim == 2:
        x = x.mean(axis=0) if x.shape[0] <= x.shape[1] else x.mean(axis=1)
    elif x.ndim != 1:
        raise ValueError("se esperaba señal 1D o 2D")
    if sr != target_sr and x.size:
        g = math.gcd(int(sr), int(target_sr))
        x = resample_poly(x, target_sr // g, int(sr) // g)
    return x.astype(np.float32)


def clip_quality(signal: np.ndarray, sr: int) -> dict:
    """Estado del clip ANTES del remuestreo: 'ok', 'silencioso', 'saturado' o 'corrupto'.
    La saturación se mide en cada canal original (la media mono puede ocultarla)."""
    x = np.asarray(signal, dtype=np.float64)
    channels = x if x.ndim == 2 and x.shape[0] <= x.shape[1] else (x.T if x.ndim == 2 else x[None])
    n = channels.shape[-1] if channels.size else 0
    out = {
        "status": "ok",
        "seconds": n / sr if sr > 0 else 0.0,
        "rms_dbfs": None,
        "clipped_fraction": None,
    }
    if n == 0 or sr <= 0 or not np.isfinite(channels).all():
        out["status"] = "corrupto"
        return out
    if n / sr < MIN_SECONDS:
        out["status"] = "corrupto"
        return out
    mono = channels.mean(axis=0)
    rms = float(np.sqrt(np.mean(mono**2)))
    out["rms_dbfs"] = 20 * math.log10(rms) if rms > 0 else -120.0
    clipped = float(np.max(np.mean(np.abs(channels) >= SATURATION_LEVEL, axis=1)))
    out["clipped_fraction"] = clipped
    channel_rms = float(np.max(np.sqrt(np.mean(channels**2, axis=1))))
    if clipped > SATURATION_MAX_FRACTION:
        out["status"] = "saturado"
    elif channel_rms <= 0 or 20 * math.log10(channel_rms) < SILENCE_RMS_DBFS:
        out["status"] = "silencioso"
    return out


def k_weighting_coefficients(sr: int) -> tuple[tuple[np.ndarray, np.ndarray], ...]:
    """Filtros K de ITU-R BS.1770 (estante alto + paso alto) para cualquier sr, a partir de los
    parámetros analógicos de la norma (formulación de De Man, 2014)."""
    gain_db, q_s, fc_s = 3.99984385397, 0.7071752369554193, 1681.9744509555319
    k = math.tan(math.pi * fc_s / sr)
    vh = 10 ** (gain_db / 20)
    vb = vh**0.499666774155
    a0 = 1 + k / q_s + k * k
    shelf_b = (
        np.array([(vh + vb * k / q_s + k * k), 2 * (k * k - vh), (vh - vb * k / q_s + k * k)]) / a0
    )
    shelf_a = np.array([1.0, 2 * (k * k - 1) / a0, (1 - k / q_s + k * k) / a0])
    q_h, fc_h = 0.5003270373253953, 38.13547087613982
    k = math.tan(math.pi * fc_h / sr)
    a0 = 1 + k / q_h + k * k
    hp_b = np.array([1.0, -2.0, 1.0])
    hp_a = np.array([1.0, 2 * (k * k - 1) / a0, (1 - k / q_h + k * k) / a0])
    return (shelf_b, shelf_a), (hp_b, hp_a)


def approx_lufs(signal: np.ndarray, sr: int) -> float:
    """Sonoridad integrada APROXIMADA (BS.1770 con ponderación K, mono, sin compuertas)."""
    x = np.asarray(signal, dtype=np.float64)
    for b, a in k_weighting_coefficients(sr):
        x = lfilter(b, a, x)
    power = float(np.mean(x**2)) if x.size else 0.0
    return -0.691 + 10 * math.log10(power) if power > 0 else -120.0


def loudness_features(signal: np.ndarray, sr: int = TARGET_SR) -> dict:
    """Rasgos de sonoridad SOLO como característica: la señal que recibe YAMNet no se modifica."""
    x = np.asarray(signal, dtype=np.float64)
    rms = float(np.sqrt(np.mean(x**2))) if x.size else 0.0
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    rms_db = 20 * math.log10(rms) if rms > 0 else -120.0
    peak_db = 20 * math.log10(peak) if peak > 0 else -120.0
    return {
        "rms_dbfs": rms_db,
        "lufs_aprox": approx_lufs(x, sr),
        "pico_dbfs": peak_db,
        "factor_cresta_db": peak_db - rms_db,
    }


def pcm_sha256(signal: np.ndarray) -> str:
    """SHA-256 del audio decodificado y normalizado (float32): detecta la misma señal aunque
    venga en contenedores o codificaciones de fichero distintas."""
    return hashlib.sha256(np.ascontiguousarray(signal, dtype="<f4").tobytes()).hexdigest()


def exact_duplicates(hashes: Sequence[str], names: Sequence[str]) -> dict[int, dict]:
    """Duplicados exactos: por hash se conserva el clip de nombre menor; devuelve
    {índice descartado: {'kept': índice conservado, 'hash': hash}}."""
    if len(hashes) != len(names):
        raise ValueError("longitudes distintas")
    by_hash: dict[str, list[int]] = {}
    for i, h in enumerate(hashes):
        by_hash.setdefault(h, []).append(i)
    dropped = {}
    for h, members in by_hash.items():
        if len(members) > 1:
            keep = min(members, key=lambda i: (names[i], i))
            dropped.update({i: {"kept": keep, "hash": h} for i in members if i != keep})
    return dropped


def near_duplicate_pairs(
    embeddings: np.ndarray,
    *,
    threshold: float = NEAR_DUPLICATE_COSINE,
    block: int = 512,
    groups: Sequence[object] | None = None,
) -> list[tuple[int, int, float]]:
    """Pares (i<j) con similitud coseno >= threshold, por bloques para acotar memoria. Con
    groups, solo pares de grupos (o particiones) distintos: los únicos que pueden filtrar."""
    e = np.asarray(embeddings, dtype=np.float32)
    norms = np.linalg.norm(e, axis=1, keepdims=True)
    e = e / np.where(norms > 0, norms, 1.0)
    codes = None
    if groups is not None:
        if len(groups) != len(e):
            raise ValueError("longitudes distintas")
        codes = np.unique(np.asarray([str(g) for g in groups]), return_inverse=True)[1]
    pairs = []
    for start in range(0, len(e), block):
        sims = e[start : start + block] @ e.T
        mask = sims >= threshold
        if codes is not None:
            mask &= codes[start : start + block, None] != codes[None, :]
        rows, cols = np.nonzero(mask)
        for r, c in zip(rows.tolist(), cols.tolist(), strict=True):
            i = start + r
            if i < c:
                pairs.append((i, c, float(sims[r, c])))
    return sorted(pairs)


def resolve_near_duplicates(
    pairs: Sequence[tuple[int, int, float]], groups: Sequence[str], names: Sequence[str]
) -> dict:
    """Componentes conexas de casi duplicados. Si un componente abarca varios grupos, se
    conservan solo los miembros del grupo que más aporta (desempate por nombre de grupo) y se
    descartan los demás: ningún par casi duplicado queda entre grupos distintos, y por tanto
    tampoco a ambos lados de una partición por grupos."""
    parent: dict[int, int] = {}

    def find(i: int) -> int:
        parent.setdefault(i, i)
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, j, _ in pairs:
        parent[find(i)] = find(j)
    components: dict[int, list[int]] = {}
    for i in list(parent):
        components.setdefault(find(i), []).append(i)
    dropped: dict[int, str] = {}
    cross = 0
    for members in components.values():
        count: dict[str, int] = {}
        for i in members:
            count[groups[i]] = count.get(groups[i], 0) + 1
        if len(count) > 1:
            cross += 1
            rep = min(count, key=lambda g: (-count[g], g))
            dropped.update(
                {i: rep for i in sorted(members, key=lambda i: names[i]) if groups[i] != rep}
            )
    return {
        "dropped": dict(sorted(dropped.items())),
        "clusters": len(components),
        "cross_group_clusters": cross,
    }

# Aumento de datos en forma de onda (iteración 5), SOLO para entrenamiento: drones mezclados
# sobre fondos negativos a SNR controlada, ganancia y desplazamiento temporal.
# Autocontenido (numpy): build_colab.py lo incrusta tal cual en el cuaderno.
from collections.abc import Sequence

import numpy as np

MIX_SNR_RANGE_DB = (-10.0, 20.0)
MIX_GAIN_RANGE_DB = (-6.0, 6.0)
MIX_MAX_SECONDS = 5.0
MIX_PEAK = 0.99
SYNTHETIC_NOTE = (
    "Mezclas sintéticas (synthetic=true): dron grabado + fondo negativo a SNR nominal; solo "
    "entran en entrenamiento, nunca en validación ni test, y no cuentan como rendimiento real"
)


def _power(x: np.ndarray) -> float:
    return float(np.mean(np.asarray(x, dtype=np.float64) ** 2))


def mix_at_snr(
    drone: np.ndarray, background: np.ndarray, snr_db: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Escala el fondo para que 10·log10(P_dron/P_fondo) = snr_db y suma; si el pico pasa de
    MIX_PEAK se escalan ambos por igual (la SNR se conserva). Devuelve (mezcla, dron, fondo).
    La SNR es NOMINAL: el clip de dron ya contiene su propio ruido de fondo."""
    d = np.asarray(drone, dtype=np.float64)
    b = np.asarray(background, dtype=np.float64)[: len(d)]
    if len(b) != len(d) or _power(d) <= 0 or _power(b) <= 0:
        raise ValueError("dron y fondo deben tener la misma longitud y energía no nula")
    b = b * np.sqrt(_power(d) / (_power(b) * 10 ** (snr_db / 10)))
    mix = d + b
    peak = float(np.max(np.abs(mix)))
    if peak > MIX_PEAK:
        scale = MIX_PEAK / peak
        mix, d, b = mix * scale, d * scale, b * scale
    return mix.astype(np.float32), d.astype(np.float32), b.astype(np.float32)


def random_gain(signal: np.ndarray, gain_db: float) -> np.ndarray:
    return (np.asarray(signal, dtype=np.float64) * 10 ** (gain_db / 20)).astype(np.float32)


def time_shift(signal: np.ndarray, samples: int) -> np.ndarray:
    """Desplazamiento circular (el contenido no se pierde)."""
    return np.roll(np.asarray(signal), int(samples))


def plan_mixes(
    positives: Sequence[int],
    negatives: Sequence[int],
    sources: Sequence[str],
    seconds: Sequence[float],
    *,
    n: int,
    seed: int,
) -> list[dict]:
    """Plan determinista de n mezclas. Drones y fondos se eligen equilibrando fuentes (cada
    fuente con la misma probabilidad y, dentro de ella, uniforme)."""
    if not positives or not negatives:
        raise ValueError("hacen falta drones y fondos")
    rng = np.random.default_rng(seed)

    def pick(pool: Sequence[int]) -> int:
        by_src: dict[str, list[int]] = {}
        for i in pool:
            by_src.setdefault(sources[i], []).append(i)
        names = sorted(by_src)
        members = by_src[names[int(rng.integers(len(names)))]]
        return int(members[int(rng.integers(len(members)))])

    plan = []
    for k in range(n):
        d, b = pick(positives), pick(negatives)
        plan.append(
            {
                "id": f"mezcla{k:05d}",
                "drone": d,
                "background": b,
                "snr_db": float(rng.uniform(*MIX_SNR_RANGE_DB)),
                "gain_db": float(rng.uniform(*MIX_GAIN_RANGE_DB)),
                "shift_fraction": float(rng.uniform()),
                "drone_offset": float(rng.uniform()),
                "background_offset": float(rng.uniform()),
                "seconds": float(min(seconds[d], seconds[b], MIX_MAX_SECONDS)),
                "synthetic": True,
                "dron": 1,
            }
        )
    return plan


def plan_cross_mixes(
    positives: Sequence[int],
    negatives: Sequence[int],
    sources: Sequence[str],
    seconds: Sequence[float],
    *,
    n: int,
    seed: int,
) -> list[dict]:
    """Hito 2 (H2.3): mezclas CRUZADAS, el dron de la fuente A sobre fondo de una fuente B != A,
    para que el canal deje de delatar la clase. Fuente de dron y fuente de fondo se eligen
    equilibradas (cada fuente con la misma probabilidad); nunca dos partes de la misma fuente.
    Mismo formato que plan_mixes (se generan con render_mix) más cross/drone_source/
    background_source."""
    by_src: dict[str, dict[str, list[int]]] = {"pos": {}, "neg": {}}
    for kind, pool in (("pos", positives), ("neg", negatives)):
        for i in pool:
            by_src[kind].setdefault(sources[i], []).append(int(i))
    pairs = [(a, b) for a in sorted(by_src["pos"]) for b in sorted(by_src["neg"]) if a != b]
    if not pairs:
        raise ValueError("hacen falta drones y fondos de fuentes distintas")
    drone_sources = sorted({a for a, _ in pairs})
    rng = np.random.default_rng(seed)
    plan = []
    for k in range(n):
        drone_src = drone_sources[int(rng.integers(len(drone_sources)))]
        bg_options = sorted(b for a, b in pairs if a == drone_src)
        bg_src = bg_options[int(rng.integers(len(bg_options)))]
        d = by_src["pos"][drone_src][int(rng.integers(len(by_src["pos"][drone_src])))]
        b = by_src["neg"][bg_src][int(rng.integers(len(by_src["neg"][bg_src])))]
        plan.append(
            {
                "id": f"cruzada{k:05d}",
                "drone": d,
                "background": b,
                "drone_source": drone_src,
                "background_source": bg_src,
                "snr_db": float(rng.uniform(*MIX_SNR_RANGE_DB)),
                "gain_db": float(rng.uniform(*MIX_GAIN_RANGE_DB)),
                "shift_fraction": float(rng.uniform()),
                "drone_offset": float(rng.uniform()),
                "background_offset": float(rng.uniform()),
                "seconds": float(min(seconds[d], seconds[b], MIX_MAX_SECONDS)),
                "synthetic": True,
                "cross": True,
                "dron": 1,
            }
        )
    return plan


def assert_cross_mixes_allowed(
    plan: Sequence[dict], used: Sequence[int], train: Sequence[int], *, held_out: str | None
) -> None:
    """Fallo cerrado: dron y fondo en entrenamiento, fuentes distintas y ninguna es la retenida."""
    allowed = set(train)
    for k in used:
        m = plan[k]
        if m["drone"] not in allowed or m["background"] not in allowed:
            raise ValueError(f"mezcla {m['id']} con audio fuera de entrenamiento")
        if m["drone_source"] == m["background_source"]:
            raise ValueError(f"mezcla {m['id']} con ambas partes de la misma fuente")
        if held_out is not None and held_out in (m["drone_source"], m["background_source"]):
            raise ValueError(f"mezcla {m['id']} usa la fuente retenida {held_out}")


def cross_mixes_for_fold(
    plan: Sequence[dict], train: Sequence[int], *, held_out: str | None
) -> list[int]:
    """Mezclas cruzadas utilizables en un pliegue (LOSO: held_out = fuente retenida)."""
    ids = [
        k
        for k in mixes_for_training(plan, train)
        if held_out not in (plan[k]["drone_source"], plan[k]["background_source"])
    ]
    assert_cross_mixes_allowed(plan, ids, train, held_out=held_out)
    return ids


def _crop(x: np.ndarray, length: int, offset_fraction: float) -> np.ndarray:
    start = int((len(x) - length) * offset_fraction) if len(x) > length else 0
    return np.asarray(x)[start : start + length]


class SilentMixError(ValueError):
    """El dron o el fondo no tienen energía en ninguna ventana: la mezcla se omite."""


def _energetic_crop(x: np.ndarray, length: int, offset_fraction: float) -> np.ndarray:
    """Recorte pedido; si es silencio (p. ej. relleno de ESC-10), la ventana de más energía."""
    crop = _crop(x, length, offset_fraction)
    if _power(crop) > 0:
        return crop
    arr = np.asarray(x, dtype=np.float64)
    if len(arr) <= length or _power(arr) <= 0:
        raise SilentMixError("clip sin energía: mezcla omitida")
    energy = np.concatenate(([0.0], np.cumsum(arr**2)))
    window = energy[length:] - energy[:-length]
    start = int(np.argmax(window))
    return np.asarray(x)[start : start + length]


def render_mix(spec: dict, drone: np.ndarray, background: np.ndarray, sr: int) -> np.ndarray:
    """Genera la mezcla de un plan: recorte, desplazamiento del dron, SNR y ganancia.
    Los recortes evitan el silencio; un clip sin energía lanza SilentMixError (se omite)."""
    length = min(int(spec["seconds"] * sr), len(drone), len(background))
    d = _energetic_crop(drone, length, spec["drone_offset"])
    d = time_shift(d, int(spec["shift_fraction"] * length))
    if _power(d) <= 0:
        raise SilentMixError("dron sin energía tras el desplazamiento: mezcla omitida")
    b = _energetic_crop(background, length, spec["background_offset"])
    mix, _, _ = mix_at_snr(d, b, spec["snr_db"])
    out = random_gain(mix, spec["gain_db"])
    peak = float(np.max(np.abs(out)))
    return (out * (MIX_PEAK / peak) if peak > MIX_PEAK else out).astype(np.float32)


def mixes_for_training(plan: Sequence[dict], train: Sequence[int]) -> list[int]:
    """Posiciones del plan utilizables en un fold: dron Y fondo deben estar en entrenamiento,
    de modo que ningún audio de validación o test entra por una mezcla."""
    allowed = set(train)
    return [k for k, m in enumerate(plan) if m["drone"] in allowed and m["background"] in allowed]

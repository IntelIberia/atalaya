# Aumento de CANAL (hito 2, H2.2), SOLO para entrenamiento en Colab: EQ aleatoria, respuesta de
# micrófono, respuesta de altavoz pequeño, reverberación con respuesta al impulso sintética, códec
# (mu-law de 8 bits y recorte de banda) y ruido de baja amplitud. Objetivo: que el canal de cada
# dataset deje de delatar la clase (atajo de dominio de la iteración 5). Todo se aplica igual a
# drones y a fondos. Sin dependencias nuevas (numpy, scipy); los códecs con pérdidas vía ffmpeg no
# se usan (licencia y versión sin registrar). Autocontenido: build_colab.py lo incrusta tal cual.
from collections.abc import Sequence

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

AUG_SR = 16000
AUG_PEAK = 0.99
EQ_GAIN_RANGE_DB = (-12.0, 12.0)
RT60_RANGE_S = (0.2, 0.8)
CHANNEL_SYNTHETIC_NOTE = (
    "Aumento de canal (synthetic=true): EQ, micrófono, altavoz pequeño, reverberación sintética, "
    "códec y ruido; solo en entrenamiento, nunca en validación ni test, y no cuenta como "
    "rendimiento real"
)
# Probabilidad de cada etapa en random_channel (documentadas; no se ajustan mirando test).
CHANNEL_STAGE_PROB = {
    "altavoz": 0.35,
    "eq": 0.8,
    "reverb": 0.5,
    "microfono": 0.7,
    "codec": 0.3,
    "ruido": 0.7,
}


def _check_signal(x: np.ndarray, sr: int) -> np.ndarray:
    if int(sr) != AUG_SR:
        raise ValueError(f"el aumento de canal trabaja a {AUG_SR} Hz, no a {sr}")
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim != 1 or arr.size == 0 or not np.isfinite(arr).all():
        raise ValueError("se esperaba una señal 1D finita y no vacía")
    return arr


def _biquad(kind: str, f: float, gain_db: float, q: float, sr: int) -> np.ndarray:
    """Biquads del «Audio EQ Cookbook» (R. Bristow-Johnson) como una sección SOS."""
    if not EQ_GAIN_RANGE_DB[0] <= gain_db <= EQ_GAIN_RANGE_DB[1]:
        raise ValueError(f"ganancia fuera de rango: {gain_db} dB")
    if not 0 < f < sr / 2 or q <= 0:
        raise ValueError("frecuencia o Q no válidas")
    a = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f / sr
    cw, alpha = np.cos(w0), np.sin(w0) / (2 * q)
    if kind == "pico":
        b = [1 + alpha * a, -2 * cw, 1 - alpha * a]
        den = [1 + alpha / a, -2 * cw, 1 - alpha / a]
    elif kind in ("grave", "agudo"):
        s = 1 if kind == "grave" else -1
        ra = 2 * np.sqrt(a) * alpha
        b = [
            a * ((a + 1) - s * (a - 1) * cw + ra),
            s * 2 * a * ((a - 1) - s * (a + 1) * cw),
            a * ((a + 1) - s * (a - 1) * cw - ra),
        ]
        den = [
            (a + 1) + s * (a - 1) * cw + ra,
            -s * 2 * ((a - 1) + s * (a + 1) * cw),
            (a + 1) + s * (a - 1) * cw - ra,
        ]
    else:
        raise ValueError(f"tipo de filtro desconocido: {kind}")
    return np.array([[*(np.array(b) / den[0]), 1.0, den[1] / den[0], den[2] / den[0]]])


def eq_sos(bands: Sequence[dict], sr: int = AUG_SR) -> np.ndarray:
    return np.vstack([_biquad(b["tipo"], b["f"], b["ganancia_db"], b["q"], sr) for b in bands])


def apply_eq(x: np.ndarray, bands: Sequence[dict], sr: int = AUG_SR) -> np.ndarray:
    arr = _check_signal(x, sr)
    if not bands:
        return arr.astype(np.float32)
    return sosfilt(eq_sos(bands, sr), arr).astype(np.float32)


def mic_response(
    x: np.ndarray, *, low_hz: float, high_hz: float, order: int, sr: int = AUG_SR
) -> np.ndarray:
    """Micrófono barato: paso alto (80-300 Hz) y paso bajo (6-8 kHz) de pendiente variable."""
    arr = _check_signal(x, sr)
    sos = np.vstack(
        [
            butter(order, low_hz, btype="highpass", fs=sr, output="sos"),
            butter(order, high_hz, btype="lowpass", fs=sr, output="sos"),
        ]
    )
    return sosfilt(sos, arr).astype(np.float32)


def speaker_response(
    x: np.ndarray,
    *,
    low_hz: float,
    resonances: Sequence[tuple[float, float, float]],
    sr: int = AUG_SR,
) -> np.ndarray:
    """Altavoz pequeño (móvil, portátil): sin graves por debajo de low_hz (150-400 Hz, orden 4)
    y resonancias (frecuencia, ganancia dB, Q)."""
    arr = _check_signal(x, sr)
    sos = [butter(4, low_hz, btype="highpass", fs=sr, output="sos")]
    sos += [_biquad("pico", f, g, q, sr) for f, g, q in resonances]
    return sosfilt(np.vstack(sos), arr).astype(np.float32)


def synthetic_rir(rt60: float, rng: np.random.Generator, sr: int = AUG_SR) -> np.ndarray:
    """Respuesta al impulso sintética: ruido gaussiano con caída exponencial de 60 dB en rt60
    segundos (sin datasets de RIR, que necesitarían intake). Energía unitaria."""
    if not rt60 > 0:
        raise ValueError("RT60 debe ser positivo")
    n = int(1.5 * rt60 * sr) + 1
    t = np.arange(n) / sr
    ir = rng.standard_normal(n) * np.exp(-3 * np.log(10) * t / rt60)
    return ir / np.sqrt(np.sum(ir**2))


def estimate_rt60(ir: np.ndarray, sr: int = AUG_SR) -> float:
    """RT60 por integración inversa de Schroeder y ajuste lineal entre -5 y -25 dB (T20 x 3)."""
    energy = np.cumsum(np.asarray(ir, dtype=np.float64)[::-1] ** 2)[::-1]
    edc = 10 * np.log10(energy / energy[0])
    sel = np.flatnonzero((edc <= -5) & (edc >= -25))
    if sel.size < 2:
        raise ValueError("respuesta al impulso demasiado corta para estimar RT60")
    slope = np.polyfit(sel / sr, edc[sel], 1)[0]
    return float(-60 / slope)


def apply_reverb(
    x: np.ndarray, *, rt60: float, wet: float, rir_seed: int, sr: int = AUG_SR
) -> np.ndarray:
    arr = _check_signal(x, sr)
    ir = synthetic_rir(rt60, np.random.default_rng(rir_seed), sr)
    reverberant = fftconvolve(arr, ir)[: len(arr)]
    return ((1 - wet) * arr + wet * reverberant).astype(np.float32)


def mulaw_codec(x: np.ndarray, bits: int = 8) -> np.ndarray:
    """Codifica y decodifica en mu-law de `bits` bits (cuantificación de telefonía)."""
    mu = 2**bits - 1
    arr = np.clip(np.asarray(x, dtype=np.float64), -1, 1)
    y = np.sign(arr) * np.log1p(mu * np.abs(arr)) / np.log1p(mu)
    q = np.round((y + 1) / 2 * mu) / mu * 2 - 1
    return (np.sign(q) * np.expm1(np.abs(q) * np.log1p(mu)) / mu).astype(np.float32)


def add_low_noise(x: np.ndarray, *, snr_db: float, noise_seed: int) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float64)
    power = float(np.mean(arr**2))
    if power <= 0:
        return arr.astype(np.float32)
    noise = np.random.default_rng(noise_seed).standard_normal(arr.size)
    return (arr + noise * np.sqrt(power / 10 ** (snr_db / 10))).astype(np.float32)


def random_channel(seed: int) -> dict:
    """Especificación determinista (por semilla) de un canal aleatorio."""
    rng = np.random.default_rng(seed)
    p = {k: bool(rng.uniform() < v) for k, v in CHANNEL_STAGE_PROB.items()}
    spec: dict = {"seed": int(seed), "synthetic": True}
    if p["altavoz"]:
        spec["altavoz"] = {
            "low_hz": float(rng.uniform(150, 400)),
            "resonancias": [
                [float(rng.uniform(500, 4000)), float(rng.uniform(3, 10)), float(rng.uniform(2, 5))]
                for _ in range(int(rng.integers(1, 3)))
            ],
        }
    if p["eq"]:
        bands = []
        for _ in range(int(rng.integers(3, 6))):
            kind = ("pico", "grave", "agudo")[int(rng.integers(3))]
            bands.append(
                {
                    "tipo": kind,
                    "f": float(np.exp(rng.uniform(np.log(80), np.log(6000)))),
                    "ganancia_db": float(rng.uniform(*EQ_GAIN_RANGE_DB)),
                    "q": 0.7 if kind != "pico" else float(rng.uniform(0.5, 4)),
                }
            )
        spec["eq"] = bands
    if p["reverb"]:
        spec["reverb"] = {
            "rt60": float(rng.uniform(*RT60_RANGE_S)),
            "wet": float(rng.uniform(0.2, 0.7)),
            "rir_seed": int(rng.integers(2**31)),
        }
    if p["microfono"]:
        spec["microfono"] = {
            "low_hz": float(rng.uniform(80, 300)),
            "high_hz": float(rng.uniform(6000, 7800)),
            "order": int(rng.integers(1, 5)),
        }
    if p["codec"]:
        spec["codec"] = {"bits": 8, "corte_hz": float(rng.uniform(3400, 7000))}
    if p["ruido"]:
        spec["ruido"] = {
            "snr_db": float(rng.uniform(25, 50)),
            "noise_seed": int(rng.integers(2**31)),
        }
    return spec


def apply_channel(x: np.ndarray, spec: dict, sr: int = AUG_SR) -> np.ndarray:
    """Altavoz -> EQ -> sala -> micrófono -> códec -> ruido -> limitador. Conserva la longitud."""
    y = _check_signal(x, sr).astype(np.float32)
    if "altavoz" in spec:
        s = spec["altavoz"]
        y = speaker_response(y, low_hz=s["low_hz"], resonances=[tuple(r) for r in s["resonancias"]])
    if "eq" in spec:
        y = apply_eq(y, spec["eq"])
    if "reverb" in spec:
        y = apply_reverb(y, **spec["reverb"])
    if "microfono" in spec:
        y = mic_response(y, **spec["microfono"])
    if "codec" in spec:
        c = spec["codec"]
        peak = float(np.max(np.abs(y)))
        scale = AUG_PEAK / peak if peak > AUG_PEAK else 1.0
        y = mulaw_codec(y * scale, c["bits"])
        y = sosfilt(butter(6, c["corte_hz"], btype="lowpass", fs=sr, output="sos"), y)
    if "ruido" in spec:
        y = add_low_noise(y, **spec["ruido"])
    y = np.asarray(y, dtype=np.float64)
    peak = float(np.max(np.abs(y)))
    if peak > AUG_PEAK:
        y = y * (AUG_PEAK / peak)
    return y.astype(np.float32)


def plan_channel_augment(
    indices: Sequence[int],
    sources: Sequence[str],
    *,
    n: int,
    seed: int,
    labels: Sequence[int] | None = None,
) -> list[dict]:
    """n copias con canal aleatorio; el clip se elige equilibrando celdas (fuente, clase) para
    que el canal aleatorio no se correlacione con la clase. sources/labels se indexan por clip."""
    if not indices:
        raise ValueError("no hay clips que aumentar")
    rng = np.random.default_rng(seed)
    cells: dict[tuple, list[int]] = {}
    for i in indices:
        cells.setdefault((sources[i], None if labels is None else int(labels[i])), []).append(i)
    names = sorted(cells, key=str)
    plan = []
    for k in range(n):
        members = cells[names[int(rng.integers(len(names)))]]
        clip = int(members[int(rng.integers(len(members)))])
        plan.append(
            {
                "id": f"canal{k:05d}",
                "clip": clip,
                "seed": int(rng.integers(2**31)),
                "offset": float(rng.uniform()),
                "synthetic": True,
            }
        )
    return plan


def channel_augs_for_training(plan: Sequence[dict], train: Sequence[int]) -> list[int]:
    """Posiciones del plan cuyo clip de origen está en entrenamiento (las únicas utilizables)."""
    allowed = set(train)
    return [k for k, p in enumerate(plan) if p["clip"] in allowed]


def assert_channel_augs_training_only(
    plan: Sequence[dict], used: Sequence[int], train: Sequence[int]
) -> None:
    """Fallo cerrado: ninguna copia aumentada puede venir de un clip de validación o test."""
    allowed = set(train)
    bad = [plan[k]["id"] for k in used if plan[k]["clip"] not in allowed]
    if bad:
        raise ValueError(f"aumento de canal fuera de entrenamiento: {bad[:5]}")

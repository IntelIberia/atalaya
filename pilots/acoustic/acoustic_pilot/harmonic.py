# Rasgo armónico de hélices (hito 2, H2.4) sobre una ventana YA normalizada (channel_norm) de
# 16 kHz: fundamental del paso de palas (50-1000 Hz) por suma ponderada de armónicos sobre la
# prominencia espectral, armonicidad (fracción de energía en los armónicos detectados), número de
# armónicos, prominencia media, estabilidad de la fundamental dentro de la ventana (4 subtramas),
# modulación de amplitud (profundidad y frecuencia) y flujo del mel con PCEN. Sin estado entre
# ventanas: el Mac y Colab calculan exactamente lo mismo por ventana. Vector de HARMONIC_DIM
# valores en [0, 1] que se concatena al embedding YAMNet. Autocontenido (numpy, scipy): el
# cuaderno lo incrusta después de channel_norm (build_colab.py quita la importación relativa, que
# allí ya está definida) y usa sus mel_power y pcen.
import numpy as np
from scipy.ndimage import maximum_filter1d

from .channel_norm import mel_power, pcen

HARMONIC_SR = 16000
HARMONIC_NAMES = (
    "f0_log",
    "armonicidad",
    "n_armonicos",
    "prominencia",
    "estabilidad_f0",
    "modulacion_am",
    "frecuencia_am",
    "flujo_pcen",
)
HARMONIC_DIM = len(HARMONIC_NAMES)
HARMONIC_CONFIG = {
    "version": "armonico-1",
    "f0_rango_hz": [50.0, 1000.0],
    "f0_paso_hz": 0.25,
    "banda_max_hz": 7500.0,
    "max_armonicos": 20,
    "peso_armonico": 0.84,  # Hermes (1988): peso 0,84^(h-1)
    "n_fft": 32768,
    "tolerancia_hz": 3.0,
    "prominencia_min_db": 10.0,
    "bloque_suelo": 64,
    "rango_dinamico_db": 80.0,  # bins por bloque para el suelo espectral (mediana)
    "banda_energia_hz": 4.0,
    "subtramas": 4,
    "n_fft_subtrama": 8192,
    "envolvente_muestras": 160,  # 10 ms
    "am_rango_hz": [2.0, 40.0],
    "propela_min_armonicos": 3,
    "propela_min_armonicidad": 0.4,
}


def _check_window(window: np.ndarray) -> np.ndarray:
    x = np.asarray(window, dtype=np.float64)
    if x.ndim != 1 or x.size == 0:
        raise ValueError("se esperaba una ventana 1D no vacía")
    if not np.isfinite(x).all():
        raise ValueError("ventana con valores no finitos")
    return x


def _spectrum(x: np.ndarray, n_fft: int) -> tuple[np.ndarray, np.ndarray]:
    n = min(len(x), n_fft)
    mag = np.abs(np.fft.rfft(x[:n] * np.hanning(n), n_fft))
    return mag, np.fft.rfftfreq(n_fft, 1 / HARMONIC_SR)


def _prominence_db(mag: np.ndarray) -> np.ndarray:
    """dB sobre el suelo espectral local (mediana por bloques, interpolada) o sobre el pico menos
    el rango dinámico, lo que sea mayor."""
    level = 20 * np.log10(mag + 1e-12)
    block = HARMONIC_CONFIG["bloque_suelo"]
    n_blocks = len(level) // block
    medians = np.median(level[: n_blocks * block].reshape(n_blocks, block), axis=1)
    centres = np.arange(n_blocks) * block + block / 2
    floor = np.interp(np.arange(len(level)), centres, medians)
    # Rango dinámico útil limitado: lo que está a más de rango_dinamico_db por debajo del pico es
    # ruido numérico (p. ej. la cuantificación float32 de un tono puro genera «armónicos»).
    floor = np.maximum(floor, level.max() - HARMONIC_CONFIG["rango_dinamico_db"])
    return np.maximum(0.0, level - floor)


def _refine(mag: np.ndarray, freqs: np.ndarray, f0: float, harmonics: list[int]) -> float:
    """f0 por mínimos cuadrados (recta por el origen) sobre los picos interpolados."""
    df = freqs[1] - freqs[0]
    num = den = 0.0
    for h in harmonics:
        lo = int(max(1, (h * f0 * 0.97) / df))
        hi = int(min(len(mag) - 2, (h * f0 * 1.03) / df + 1))
        if hi <= lo:
            continue
        k = lo + int(np.argmax(mag[lo : hi + 1]))
        a, b, c = np.log(mag[k - 1 : k + 2] + 1e-12)
        denom = a - 2 * b + c
        offset = 0.5 * (a - c) / denom if denom < 0 else 0.0
        num += h * (k + offset) * df
        den += h * h
    return num / den if den else f0


def harmonic_summary(window: np.ndarray) -> dict:
    """Resumen interpretable de la ventana (f0 en Hz, armonicidad, número de armónicos…)."""
    cfg = HARMONIC_CONFIG
    x = _check_window(window)
    empty = {
        "f0_hz": 0.0,
        "armonicidad": 0.0,
        "n_armonicos": 0,
        "prominencia_db": 0.0,
        "estabilidad": 0.0,
        "am_profundidad": 0.0,
        "am_frecuencia_hz": 0.0,
        "flujo_pcen": 0.0,
    }
    if not np.any(x):
        return empty
    mag, freqs = _spectrum(x, cfg["n_fft"])
    df = freqs[1] - freqs[0]
    prom = _prominence_db(mag)
    peaky = maximum_filter1d(prom, size=2 * int(cfg["tolerancia_hz"] / df) + 1)
    peaky = np.where(peaky >= cfg["prominencia_min_db"], peaky, 0.0)
    lo, hi = cfg["f0_rango_hz"]
    cands = np.arange(lo, hi + cfg["f0_paso_hz"] / 2, cfg["f0_paso_hz"])
    h = np.arange(1, cfg["max_armonicos"] + 1)
    grid = cands[:, None] * h[None, :]
    valid = grid <= cfg["banda_max_hz"]
    idx = np.minimum(np.round(grid / df).astype(int), len(peaky) - 1)
    weights = cfg["peso_armonico"] ** (h - 1)
    salience = np.sum(np.where(valid, peaky[idx], 0.0) * weights, axis=1)
    if salience.max() <= 0:
        return {**empty, **_modulation(x)}
    best = int(np.argmax(salience))
    detected = [int(k) for k in h[valid[best] & (peaky[idx[best]] > 0)]]
    f0 = _refine(mag, freqs, float(cands[best]), detected)
    power = mag**2
    band = (freqs >= lo) & (freqs <= cfg["banda_max_hz"])
    near = np.zeros_like(band)
    for k in detected:
        near |= np.abs(freqs - k * f0) <= cfg["banda_energia_hz"]
    harmonicity = float(power[near & band].sum() / max(power[band].sum(), 1e-30))
    prominence = float(np.mean([peaky[int(round(k * f0 / df))] for k in detected]))
    return {
        "f0_hz": float(f0),
        "armonicidad": harmonicity,
        "n_armonicos": len(detected),
        "prominencia_db": prominence,
        "estabilidad": _stability(x, f0, detected),
        **_modulation(x),
    }


def _stability(x: np.ndarray, f0: float, detected: list[int]) -> float:
    """1 si la f0 refinada en cada subtrama no se aparta (desviación típica) más de un 0 % de
    f0; 0 si se aparta un 5 % o más."""
    cfg = HARMONIC_CONFIG
    parts = np.array_split(x, cfg["subtramas"])
    estimates = []
    for part in parts:
        if not np.any(part):
            continue
        mag, freqs = _spectrum(part, cfg["n_fft_subtrama"])
        estimates.append(_refine(mag, freqs, f0, detected))
    if len(estimates) < 2 or f0 <= 0:
        return 0.0
    return float(np.clip(1 - np.std(estimates) / (0.05 * f0), 0.0, 1.0))


def _modulation(x: np.ndarray) -> dict:
    """Profundidad (coeficiente de variación de la envolvente RMS de 10 ms) y frecuencia
    dominante de modulación de amplitud (2-40 Hz); flujo medio del mel con PCEN."""
    cfg = HARMONIC_CONFIG
    hop = cfg["envolvente_muestras"]
    n = len(x) // hop
    if n < 8:
        return {"am_profundidad": 0.0, "am_frecuencia_hz": 0.0, "flujo_pcen": 0.0}
    env = np.sqrt(np.mean(x[: n * hop].reshape(n, hop) ** 2, axis=1))
    depth = float(env.std() / env.mean()) if env.mean() > 0 else 0.0
    spec = np.abs(np.fft.rfft((env - env.mean()) * np.hanning(n), 1024))
    fr = np.fft.rfftfreq(1024, hop / HARMONIC_SR)
    sel = (fr >= cfg["am_rango_hz"][0]) & (fr <= cfg["am_rango_hz"][1])
    rate = float(fr[sel][int(np.argmax(spec[sel]))]) if depth >= 0.05 else 0.0
    p = pcen(mel_power(x.astype(np.float32)))
    flux = float(np.mean(np.abs(np.diff(p, axis=1)))) if p.shape[1] > 1 else 0.0
    return {"am_profundidad": depth, "am_frecuencia_hz": rate, "flujo_pcen": flux}


def harmonic_features(window: np.ndarray) -> np.ndarray:
    """Vector de HARMONIC_DIM rasgos en [0, 1] (orden de HARMONIC_NAMES)."""
    s = harmonic_summary(window)
    lo, hi = HARMONIC_CONFIG["f0_rango_hz"]
    f0_log = np.log(s["f0_hz"] / lo) / np.log(hi / lo) if s["n_armonicos"] else 0.0
    am_hi = HARMONIC_CONFIG["am_rango_hz"][1]
    v = [
        f0_log,
        s["armonicidad"],
        min(s["n_armonicos"], HARMONIC_CONFIG["max_armonicos"]) / HARMONIC_CONFIG["max_armonicos"],
        s["prominencia_db"] / 40.0,
        s["estabilidad"],
        s["am_profundidad"],
        s["am_frecuencia_hz"] / am_hi,
        s["flujo_pcen"] / (s["flujo_pcen"] + 1.0),
    ]
    return np.clip(np.asarray(v, dtype=np.float64), 0.0, 1.0).astype(np.float32)


def estimate_f0(window: np.ndarray) -> float:
    """Fundamental estimada en Hz (0,0 si no hay armónicos)."""
    return harmonic_summary(window)["f0_hz"]


def is_propeller_harmonic(summary: dict) -> bool:
    """Firma de hélice: >= 3 armónicos de una f0 en 50-1000 Hz con armonicidad suficiente
    (un tono puro aislado o un ruido no la cumplen)."""
    cfg = HARMONIC_CONFIG
    lo, hi = cfg["f0_rango_hz"]
    return bool(
        summary["n_armonicos"] >= cfg["propela_min_armonicos"]
        and summary["armonicidad"] >= cfg["propela_min_armonicidad"]
        and lo <= summary["f0_hz"] <= hi
    )

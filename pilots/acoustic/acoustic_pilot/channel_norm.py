# Normalización de canal compartida (hito 2, H2.1): EL MISMO código se incrusta en el cuaderno de
# Colab (build_colab.py) y se importa en el Mac (acoustic_pilot.live). Autocontenido: numpy, scipy
# y stdlib. Cadena: mono -> 16 kHz (resample_poly) -> paso banda 100-7500 Hz (Butterworth SOS, fase
# cero) -> sonoridad por ventana a un RMS objetivo con ganancia limitada; y mel con PCEN para la
# rama armónica. Cualquier cambio de parámetros cambia norm_config_sha256() y rompe los vectores
# dorados del artefacto (prueba de que Colab y el Mac normalizan igual).
import hashlib
import json
import math

import numpy as np
from scipy.signal import butter, lfilter, resample_poly, sosfiltfilt

NORM_SR = 16000
# Ventana YAMNet: 0,96 s de parche + 15 ms de la STFT = 15 600 muestras a 16 kHz (una ventana).
WINDOW_SAMPLES = 15600
HOP_SAMPLES = 7680  # 0,48 s
# 11 025 Hz y 8 kHz no llegan a 7,5 kHz de banda: se rechazan (fallo cerrado).
SUPPORTED_RATES = (16000, 22050, 24000, 32000, 44100, 48000, 88200, 96000)
PCEN_DEFAULTS = {"gain": 0.98, "bias": 2.0, "power": 0.5, "time_constant_s": 0.4, "eps": 1e-6}
NORM_CONFIG = {
    "version": "canal-1",
    "sr": NORM_SR,
    "ventana_muestras": WINDOW_SAMPLES,
    "salto_muestras": HOP_SAMPLES,
    # Butterworth de orden 4 por flanco, fase cero: -0,5 dB a 100 Hz y ~-59 dB a 30 Hz.
    "banda_hz": [70.0, 7900.0],
    "banda_orden": 4,
    "rms_objetivo_dbfs": -25.0,
    "ganancia_maxima_db": 30.0,
    "suelo_ruido_dbfs": -90.0,  # por debajo: silencio, no se amplifica
    "pico_maximo": 0.99,
    "mel": {"n_fft": 512, "win": 400, "hop": 160, "n_mels": 64, "fmin": 50.0, "fmax": 7500.0},
    "pcen": PCEN_DEFAULTS,
    "pcen_escala": 2.0**31,  # mel de audio en coma flotante escalado como PCM de 32 bits
}


def norm_config_sha256(config: dict | None = None) -> str:
    """SHA-256 del JSON canónico de la configuración de normalización."""
    data = json.dumps(config or NORM_CONFIG, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()


def _finite_float64(signal: np.ndarray) -> np.ndarray:
    x = np.asarray(signal)
    if np.issubdtype(x.dtype, np.integer):
        x = x.astype(np.float64) / float(np.iinfo(x.dtype).max)
    x = x.astype(np.float64)
    if x.size == 0:
        raise ValueError("señal vacía")
    if not np.isfinite(x).all():
        raise ValueError("señal con valores no finitos (NaN o infinito)")
    return x


def to_mono_16k(signal: np.ndarray, sr: int) -> np.ndarray:
    """Mono (media de canales; (n,), (canales, n) o (n, canales)) y 16 kHz con resample_poly."""
    if int(sr) not in SUPPORTED_RATES:
        raise ValueError(f"frecuencia de muestreo no admitida: {sr}")
    x = _finite_float64(signal)
    if x.ndim == 2:
        x = x.mean(axis=0) if x.shape[0] <= x.shape[1] else x.mean(axis=1)
    elif x.ndim != 1:
        raise ValueError("se esperaba señal 1D o 2D")
    if int(sr) != NORM_SR:
        g = math.gcd(int(sr), NORM_SR)
        x = resample_poly(x, NORM_SR // g, int(sr) // g)
    return x.astype(np.float32)


def bandpass_sos(config: dict | None = None) -> np.ndarray:
    cfg = config or NORM_CONFIG
    return butter(cfg["banda_orden"], cfg["banda_hz"], btype="bandpass", fs=cfg["sr"], output="sos")


def bandpass(window: np.ndarray, config: dict | None = None) -> np.ndarray:
    """Paso banda de fase cero (sosfiltfilt) sobre una ventana de 16 kHz."""
    x = _finite_float64(window)
    if x.ndim != 1:
        raise ValueError("se esperaba una ventana 1D")
    sos = bandpass_sos(config)
    if x.size <= 3 * (2 * sos.shape[0] + 1):
        raise ValueError("ventana demasiado corta para el filtro")
    return sosfiltfilt(sos, x).astype(np.float32)


def loudness_normalize(
    window: np.ndarray, config: dict | None = None, *, return_gain: bool = False
) -> np.ndarray | tuple[np.ndarray, float]:
    """Ganancia por ventana hasta el RMS objetivo, limitada a ±ganancia_maxima_db; por debajo del
    suelo de ruido no se aplica ganancia (el silencio no se amplifica); limitador de pico."""
    cfg = config or NORM_CONFIG
    x = _finite_float64(window)
    rms = float(np.sqrt(np.mean(x**2)))
    level = 20 * math.log10(rms) if rms > 0 else -math.inf
    if level < cfg["suelo_ruido_dbfs"]:
        gain_db = 0.0
    else:
        limit = cfg["ganancia_maxima_db"]
        gain_db = float(min(max(cfg["rms_objetivo_dbfs"] - level, -limit), limit))
    y = x * 10 ** (gain_db / 20)
    peak = float(np.max(np.abs(y)))
    if peak > cfg["pico_maximo"]:
        y = y * (cfg["pico_maximo"] / peak)
    out = y.astype(np.float32)
    return (out, gain_db) if return_gain else out


def normalize_window(window: np.ndarray, config: dict | None = None) -> np.ndarray:
    """Ventana de 16 kHz ya en mono -> paso banda -> sonoridad. Determinista."""
    x = np.asarray(window)
    if x.ndim != 1 or x.size == 0:
        raise ValueError("se esperaba una ventana 1D no vacía a 16 kHz")
    return loudness_normalize(bandpass(x, config), config)


def frame_starts(n_samples: int, config: dict | None = None) -> list[int]:
    """Inicios de ventana (salto 0,48 s); un clip más corto que una ventana da una sola ventana
    (se rellena con ceros al extraerla)."""
    cfg = config or NORM_CONFIG
    win, hop = cfg["ventana_muestras"], cfg["salto_muestras"]
    if n_samples <= win:
        return [0]
    return list(range(0, n_samples - win + 1, hop))


def extract_window(signal16k: np.ndarray, start: int, config: dict | None = None) -> np.ndarray:
    cfg = config or NORM_CONFIG
    win = cfg["ventana_muestras"]
    x = np.asarray(signal16k, dtype=np.float32)[start : start + win]
    return np.pad(x, (0, win - len(x))) if len(x) < win else x


def _hz_to_mel(f: np.ndarray) -> np.ndarray:
    return 1127.0 * np.log1p(np.asarray(f, dtype=np.float64) / 700.0)


def _mel_to_hz(m: np.ndarray) -> np.ndarray:
    return 700.0 * np.expm1(np.asarray(m, dtype=np.float64) / 1127.0)


def mel_filterbank(config: dict | None = None) -> np.ndarray:
    """Banco mel triangular (escala HTK), (n_mels, n_fft // 2 + 1)."""
    cfg = (config or NORM_CONFIG)["mel"]
    n_bins = cfg["n_fft"] // 2 + 1
    freqs = np.linspace(0, NORM_SR / 2, n_bins)
    edges = _mel_to_hz(
        np.linspace(_hz_to_mel(cfg["fmin"]), _hz_to_mel(cfg["fmax"]), cfg["n_mels"] + 2)
    )
    fb = np.zeros((cfg["n_mels"], n_bins))
    for m in range(cfg["n_mels"]):
        lo, mid, hi = edges[m], edges[m + 1], edges[m + 2]
        up = (freqs - lo) / (mid - lo)
        down = (hi - freqs) / (hi - mid)
        fb[m] = np.maximum(0.0, np.minimum(up, down))
        if fb[m].sum() == 0:  # banda más estrecha que un bin: el bin más cercano
            fb[m, int(np.argmin(np.abs(freqs - mid)))] = 1.0
    return fb


def mel_power(window: np.ndarray, config: dict | None = None) -> np.ndarray:
    """Espectrograma mel de potencia (n_mels, tramas) con ventana de Hann periódica."""
    cfg = (config or NORM_CONFIG)["mel"]
    x = _finite_float64(window)
    win, hop, n_fft = cfg["win"], cfg["hop"], cfg["n_fft"]
    if x.size < win:
        x = np.pad(x, (0, win - x.size))
    n_frames = 1 + (x.size - win) // hop
    idx = np.arange(win)[None, :] + hop * np.arange(n_frames)[:, None]
    hann = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(win) / win)
    spec = np.abs(np.fft.rfft(x[idx] * hann, n_fft, axis=1)) ** 2
    return (mel_filterbank(config) @ spec.T).astype(np.float64)


def pcen(mel: np.ndarray, config: dict | None = None) -> np.ndarray:
    """Per-Channel Energy Normalization (Wang et al., 2017), con el suavizador en estado
    estacionario sobre la primera trama: atenúa el fondo estacionario y realza los cambios."""
    cfg = config or NORM_CONFIG
    p = cfg["pcen"]
    e = np.asarray(mel, dtype=np.float64) * cfg["pcen_escala"]
    if e.ndim != 2 or not np.isfinite(e).all():
        raise ValueError("mel no válido")
    t_frames = p["time_constant_s"] * NORM_SR / cfg["mel"]["hop"]
    b = (math.sqrt(1 + 4 * t_frames**2) - 1) / (2 * t_frames**2)
    zi = (1 - b) * e[:, :1]
    m, _ = lfilter([b], [1, b - 1], e, axis=1, zi=zi)
    smooth = np.exp(-p["gain"] * (np.log(p["eps"]) + np.log1p(m / p["eps"])))
    return (e * smooth + p["bias"]) ** p["power"] - p["bias"] ** p["power"]

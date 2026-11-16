# «Prueba tu audio» (hito 2, cuaderno de la iteración 6): el usuario sube SU fichero y se analiza
# por la MISMA ruta que el modelo final y el Mac: remuestreo a 16 kHz -> ventanas de 0,96 s con
# salto de 0,48 s -> normalización de canal -> YAMNet -> puerta de voz (ventanas con voz >= umbral
# descartadas y contadas) -> rasgo armónico -> lineal -> Platt -> alerta 3 de 5 con histéresis.
# Nada se guarda: el cuaderno borra el fichero subido tras inferir. Autocontenido salvo las
# importaciones relativas (en el cuaderno ya están definidas y build_colab.py las quita).
import io
import math
import wave
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

from .alert_logic import persistence_score, run_alert
from .channel_norm import NORM_SR, extract_window, frame_starts
from .model_export import score_features, window_features

USER_AUDIO_NOTE = (
    "Sube solo audio propio o con una licencia que permita este uso; no descargues audio de "
    "YouTube ni de otras plataformas. El fichero se analiza en esta sesión de Colab y se borra al "
    "terminar; no se guarda en Drive ni en el repositorio."
)
USER_AUDIO_LABEL = "Reproducción o grabación de prueba, no vuelo real verificado"
USER_AUDIO_SUFFIXES = (".wav", ".mp3", ".m4a", ".ogg", ".flac")
USER_MIN_SR = 8000
USER_MAX_SR = 192000
USER_SILENCE_DBFS = -60.0
USER_CLIP_LEVEL = 0.999
USER_CLIP_FRACTION = 0.01
UNCERTAINTY_MARGIN = 0.05
VERDICT_YES = "DRON DETECTADO"
VERDICT_NO = "NO DETECTADO"
VERDICT_NONE = "SIN DECISIÓN"


class AudioDecodeError(ValueError):
    """El fichero no se puede leer como audio."""


def decode_wav_bytes(data: bytes) -> tuple[np.ndarray, int]:
    """WAV PCM de 8/16/24/32 bits con la biblioteca estándar -> (float32 (n, canales), sr)."""
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            sr, ch, width = wav.getframerate(), wav.getnchannels(), wav.getsampwidth()
            raw = wav.readframes(wav.getnframes())
    except (wave.Error, EOFError, ValueError) as exc:
        raise AudioDecodeError(f"WAV ilegible: {exc}") from exc
    if not raw or ch < 1:
        raise AudioDecodeError("WAV vacío")
    if width == 1:
        x = (np.frombuffer(raw, np.uint8).astype(np.float64) - 128) / 128
    elif width == 2:
        x = np.frombuffer(raw, "<i2").astype(np.float64) / 32768
    elif width == 3:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        x = np.where(v >= 1 << 23, v - (1 << 24), v).astype(np.float64) / (1 << 23)
    elif width == 4:
        x = np.frombuffer(raw, "<i4").astype(np.float64) / 2**31
    else:
        raise AudioDecodeError(f"ancho de muestra no admitido: {width}")
    if x.size % ch:
        raise AudioDecodeError("WAV truncado")
    return x.reshape(-1, ch).astype(np.float32), int(sr)


def load_user_audio(path: str | Path, *, fallback_loader=None) -> tuple[np.ndarray, int]:
    """WAV con la biblioteca estándar; otros formatos (mp3, m4a, ogg, flac) con fallback_loader
    (en Colab, librosa.load(path, sr=None, mono=False), que usa soundfile o ffmpeg del sistema)."""
    p = Path(path)
    if p.suffix.lower() not in USER_AUDIO_SUFFIXES:
        raise AudioDecodeError(f"extensión no admitida: {p.suffix or '(ninguna)'}")
    if p.suffix.lower() == ".wav":
        try:
            return decode_wav_bytes(p.read_bytes())
        except AudioDecodeError:
            if fallback_loader is None:
                raise
    if fallback_loader is None:
        raise AudioDecodeError(f"no hay decodificador para {p.suffix}")
    try:
        signal, sr = fallback_loader(str(p))
    except Exception as exc:  # cualquier fallo del decodificador = fichero ilegible
        raise AudioDecodeError(f"no se pudo decodificar: {type(exc).__name__}") from exc
    x = np.asarray(signal, dtype=np.float32)
    if x.size == 0:
        raise AudioDecodeError("audio vacío")
    return (x.T if x.ndim == 2 else x), int(sr)


def to_16k_any(signal: np.ndarray, sr: int) -> np.ndarray:
    """Mono y 16 kHz desde cualquier frecuencia entera de 8 a 192 kHz (8 kHz: banda estrecha)."""
    if not USER_MIN_SR <= int(sr) <= USER_MAX_SR:
        raise ValueError(f"frecuencia de muestreo no admitida: {sr}")
    x = np.asarray(signal, dtype=np.float64)
    if x.size == 0 or not np.isfinite(x).all():
        raise ValueError("audio vacío o con valores no finitos")
    if x.ndim == 2:
        x = x.mean(axis=1) if x.shape[0] >= x.shape[1] else x.mean(axis=0)
    if int(sr) != NORM_SR:
        g = math.gcd(int(sr), NORM_SR)
        x = resample_poly(x, NORM_SR // g, int(sr) // g)
    return x.astype(np.float32)


def audio_warnings(signal: np.ndarray, sr: int, alert: dict) -> list[str]:
    x = np.asarray(signal, dtype=np.float64)
    out = []
    seconds = (x.shape[0] if x.ndim else 0) / sr
    min_s = 0.96 + (alert["n"] - 1) * alert["salto_s"]
    if seconds < min_s:
        out.append(
            f"Audio muy corto ({seconds:.1f} s): la regla {alert['k']} de {alert['n']} necesita "
            f"al menos {min_s:.1f} s; el veredicto no es fiable."
        )
    rms = float(np.sqrt(np.mean(x**2))) if x.size else 0.0
    if rms <= 0 or 20 * math.log10(rms) < USER_SILENCE_DBFS:
        out.append("Audio casi silencioso (< −60 dBFS): no hay señal suficiente.")
    if x.size and float(np.mean(np.abs(x) >= USER_CLIP_LEVEL)) > USER_CLIP_FRACTION:
        out.append("Audio saturado (> 1 % de muestras recortadas): el resultado puede fallar.")
    if sr < NORM_SR:
        out.append(
            f"Banda estrecha ({sr} Hz): no hay información por encima de {sr // 2} Hz; el modelo "
            "se entrenó con 16 kHz."
        )
    return out


def analyze_audio(signal: np.ndarray, sr: int, *, artifact: dict, yamnet_fn) -> dict:
    """Informe por fichero: veredicto, probabilidades por ventana, estados y avisos."""
    alert = artifact["alerta"]
    voice = artifact["voz"]
    mono = to_16k_any(signal, sr)
    starts = frame_starts(len(mono))
    probs, speech_flags, speech_scores = [], [], []
    for start in starts:
        feats = window_features(extract_window(mono, start), yamnet_fn, voice["indices"])
        is_speech = feats["voz"] >= voice["umbral"]
        speech_flags.append(bool(is_speech))
        speech_scores.append(feats["voz"])
        if is_speech:
            probs.append(None)  # descartada antes del clasificador
        else:
            probs.append(
                score_features(artifact, feats["embedding"], feats["armonico"])["prob_cal"]
            )
    states, events = run_alert([0.0 if p is None else p for p in probs], speech_flags, alert)
    valid = [p for p in probs if p is not None]
    warnings = audio_warnings(signal, sr, alert)
    if not valid:
        verdict = VERDICT_NONE
        warnings.append("Todas las ventanas tenían voz y se descartaron: no hay decisión.")
        persistence = None
    else:
        verdict = VERDICT_YES if events > 0 else VERDICT_NO
        persistence = persistence_score(valid, alert["k"], alert["n"])
        near_on = abs(persistence - alert["theta_on"]) <= UNCERTAINTY_MARGIN
        if alert["theta_off"] <= persistence < alert["theta_on"] or near_on:
            warnings.append(
                "Puntuación en la zona de incertidumbre (cerca del umbral): trátalo como dudoso."
            )
    return {
        "veredicto": verdict,
        "rotulo": USER_AUDIO_LABEL,
        "segundos": len(mono) / NORM_SR,
        "ventanas": len(starts),
        "ventanas_voz_descartadas": int(sum(speech_flags)),
        "tiempos_s": [s / NORM_SR for s in starts],
        "prob_por_ventana": probs,
        "voz_por_ventana": speech_scores,
        "estados": states,
        "alertas": int(events),
        "prob_max": max(valid) if valid else None,
        "prob_media": float(np.mean(valid)) if valid else None,
        "fraccion_sobre_umbral": float(np.mean([p >= alert["theta_on"] for p in valid]))
        if valid
        else None,
        "persistencia": persistence,
        "theta_on": alert["theta_on"],
        "theta_off": alert["theta_off"],
        "avisos": warnings,
    }

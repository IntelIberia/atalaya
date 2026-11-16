"""H2.1 · Normalización de canal compartida por Colab y el Mac (REQ-FUN-027)."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest
from scipy.signal import sosfreqz

from acoustic_pilot.channel_norm import (
    NORM_CONFIG,
    NORM_SR,
    PCEN_DEFAULTS,
    SUPPORTED_RATES,
    WINDOW_SAMPLES,
    bandpass,
    bandpass_sos,
    loudness_normalize,
    mel_filterbank,
    mel_power,
    norm_config_sha256,
    normalize_window,
    pcen,
    to_mono_16k,
)

pytestmark = pytest.mark.req("REQ-FUN-027")
MODULE = Path(__file__).resolve().parents[1] / "acoustic_pilot" / "channel_norm.py"


def _tone(freq: float, sr: int, seconds: float = 1.0, amp: float = 0.5) -> np.ndarray:
    t = np.arange(int(sr * seconds)) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _peak_frequency(x: np.ndarray, sr: int) -> float:
    n = 1 << 20
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)), n))
    k = int(np.argmax(spec))
    a, b, c = np.log(spec[k - 1 : k + 2] + 1e-30)
    return (k + 0.5 * (a - c) / (a - 2 * b + c)) * sr / n


@pytest.mark.parametrize("sr", [48000, 44100])
def test_resampling_keeps_a_1khz_tone_within_1hz(sr: int) -> None:
    y = to_mono_16k(_tone(1000.0, sr), sr)
    assert len(y) == 16000 and y.dtype == np.float32
    assert abs(_peak_frequency(y, NORM_SR) - 1000.0) <= 1.0


def test_mono_mix_of_channels_first_or_last() -> None:
    left, right = _tone(500.0, 48000), _tone(700.0, 48000)
    a = to_mono_16k(np.stack([left, right]), 48000)
    b = to_mono_16k(np.stack([left, right], axis=1), 48000)
    np.testing.assert_allclose(a, b, atol=1e-7)


def test_bandpass_passband_within_1db_and_30hz_attenuated_20db() -> None:
    freqs = np.array([30.0, 100.0, 250.0, 1000.0, 4000.0, 7000.0, 7500.0])
    _, h = sosfreqz(bandpass_sos(), worN=freqs, fs=NORM_SR)
    gain_db = 20 * np.log10(np.abs(h) ** 2)  # fase cero: respuesta al cuadrado
    assert gain_db[0] <= -20.0
    assert np.all(np.abs(gain_db[1:]) <= 1.0), gain_db


def test_bandpass_measured_on_signals() -> None:
    sr = NORM_SR
    for freq, lo, hi in ((100.0, -1.0, 1.0), (7500.0, -1.0, 1.0), (30.0, -200.0, -20.0)):
        x = _tone(freq, sr, seconds=2.0)
        y = bandpass(x)
        mid = slice(sr // 2, 3 * sr // 2)  # sin bordes
        gain = 20 * np.log10(np.std(y[mid]) / np.std(x[mid]))
        assert lo <= gain <= hi, (freq, gain)


def test_loudness_normalization_removes_gain_differences() -> None:
    rng = np.random.default_rng(1)
    base = (0.05 * rng.standard_normal(WINDOW_SAMPLES)).astype(np.float32)
    quiet = (base * 10 ** (-20 / 20)).astype(np.float32)
    loud = (base * 10 ** (6 / 20)).astype(np.float32)
    a, b = normalize_window(quiet), normalize_window(loud)
    assert np.max(np.abs(a - b)) <= 1e-3
    rms_db = 20 * np.log10(np.sqrt(np.mean(a.astype(np.float64) ** 2)))
    assert abs(rms_db - NORM_CONFIG["rms_objetivo_dbfs"]) <= 0.5


def test_output_is_finite_deterministic_and_peak_limited() -> None:
    rng = np.random.default_rng(2)
    x = rng.uniform(-1, 1, WINDOW_SAMPLES).astype(np.float32)
    a, b = normalize_window(x), normalize_window(x.copy())
    assert np.array_equal(a, b) and np.isfinite(a).all() and a.dtype == np.float32
    assert np.max(np.abs(a)) <= NORM_CONFIG["pico_maximo"] + 1e-6


def test_digital_silence_and_near_silence_are_not_amplified() -> None:
    zeros = np.zeros(WINDOW_SAMPLES, dtype=np.float32)
    assert np.array_equal(normalize_window(zeros), zeros)
    rng = np.random.default_rng(3)
    hiss = (1e-6 * rng.standard_normal(WINDOW_SAMPLES)).astype(np.float32)  # −120 dBFS
    y, gain_db = loudness_normalize(hiss, return_gain=True)
    assert gain_db == 0.0 and np.array_equal(y, hiss)
    faint = (10 ** (-70 / 20) * rng.standard_normal(WINDOW_SAMPLES)).astype(np.float32)
    _, gain_db = loudness_normalize(faint, return_gain=True)
    assert gain_db == NORM_CONFIG["ganancia_maxima_db"]  # limitada, no hasta el objetivo


@pytest.mark.parametrize("sr", [11025, 8000, 0, -16000])
def test_unsupported_rate_is_rejected(sr: int) -> None:
    assert 11025 not in SUPPORTED_RATES
    with pytest.raises(ValueError):
        to_mono_16k(np.zeros(1000, dtype=np.float32), sr)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_non_finite_input_is_rejected(bad: float) -> None:
    x = np.zeros(WINDOW_SAMPLES, dtype=np.float32)
    x[10] = bad
    with pytest.raises(ValueError):
        normalize_window(x)
    with pytest.raises(ValueError):
        to_mono_16k(np.concatenate([x, x, x]), 48000)


def test_wrong_window_shape_is_rejected() -> None:
    with pytest.raises(ValueError):
        normalize_window(np.zeros((2, WINDOW_SAMPLES), dtype=np.float32))
    with pytest.raises(ValueError):
        normalize_window(np.zeros(0, dtype=np.float32))


def test_mel_filterbank_and_pcen_shapes_and_behaviour() -> None:
    fb = mel_filterbank()
    assert fb.shape[0] == NORM_CONFIG["mel"]["n_mels"] and np.all(fb >= 0)
    assert np.all(fb.sum(axis=1) > 0)  # ninguna banda vacía
    rng = np.random.default_rng(4)
    noise = (0.1 * rng.standard_normal(WINDOW_SAMPLES)).astype(np.float32)
    mel = mel_power(noise)
    assert mel.shape[0] == fb.shape[0] and np.isfinite(mel).all() and np.all(mel >= 0)
    out = pcen(mel)
    assert out.shape == mel.shape and np.isfinite(out).all()
    # PCEN atenúa el fondo estacionario: un clic sobre el ruido destaca más que en el mel.
    click = noise.copy()
    click[8000:8040] += 0.9
    p_click = pcen(mel_power(click))
    hop = NORM_CONFIG["mel"]["hop"]
    near = p_click.mean(axis=0)[8000 // hop - 3 : 8040 // hop + 1]  # tramas que cubren el clic
    assert near.max() > 3 * np.median(p_click.mean(axis=0))
    assert set(PCEN_DEFAULTS) == {"gain", "bias", "power", "time_constant_s", "eps"}


def test_config_hash_is_stable_and_sensitive() -> None:
    a = norm_config_sha256()
    assert a == norm_config_sha256() and len(a) == 64
    changed = {**NORM_CONFIG, "rms_objetivo_dbfs": NORM_CONFIG["rms_objetivo_dbfs"] - 1}
    assert norm_config_sha256(changed) != a


def test_module_is_self_contained_for_the_mac_and_the_notebook() -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported <= {"hashlib", "json", "math", "numpy", "scipy", "collections"}, imported
    assert "__future__" not in MODULE.read_text(encoding="utf-8")

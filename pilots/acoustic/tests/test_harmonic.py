"""H2.4 · Rasgo armónico de hélices (REQ-FUN-027)."""

from __future__ import annotations

import numpy as np
import pytest

from acoustic_pilot.channel_augment import speaker_response
from acoustic_pilot.channel_norm import WINDOW_SAMPLES, normalize_window
from acoustic_pilot.harmonic import (
    HARMONIC_DIM,
    HARMONIC_NAMES,
    estimate_f0,
    harmonic_features,
    harmonic_summary,
    is_propeller_harmonic,
)

pytestmark = pytest.mark.req("REQ-FUN-027")
SR = 16000


def _comb(f0: float, n_harm: int, seed: int = 0, noise: float = 0.01, am: float = 0.0):
    rng = np.random.default_rng(seed)
    t = np.arange(WINDOW_SAMPLES) / SR
    x = sum(
        np.sin(2 * np.pi * h * f0 * t + rng.uniform(0, 2 * np.pi)) / h**0.3
        for h in range(1, n_harm + 1)
    )
    x = x * (1 + am * np.sin(2 * np.pi * 12 * t))
    x = 0.1 * x / np.std(x) + noise * rng.standard_normal(len(t))
    return normalize_window(x.astype(np.float32))


def _pink(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    spec = np.fft.rfft(rng.standard_normal(WINDOW_SAMPLES))
    f = np.fft.rfftfreq(WINDOW_SAMPLES, 1 / SR)
    spec[1:] /= np.sqrt(f[1:])
    spec[0] = 0
    return normalize_window(np.fft.irfft(spec, WINDOW_SAMPLES).astype(np.float32))


def test_comb_180hz_with_8_harmonics() -> None:
    x = _comb(180.0, 8)
    s = harmonic_summary(x)
    assert abs(s["f0_hz"] - 180.0) <= 3.0
    assert s["armonicidad"] >= 0.8 and s["n_armonicos"] >= 6
    assert is_propeller_harmonic(s)


@pytest.mark.parametrize("f0", [90.0, 240.0, 410.0])
def test_other_fundamentals(f0: float) -> None:
    assert abs(estimate_f0(_comb(f0, 8, seed=int(f0))) - f0) <= 3.0


def test_white_noise_is_not_harmonic() -> None:
    noise = np.random.default_rng(5).standard_normal(WINDOW_SAMPLES).astype(np.float32)
    s = harmonic_summary(normalize_window(noise))
    assert s["armonicidad"] <= 0.2
    assert not is_propeller_harmonic(s)


def test_comb_through_small_speaker_without_fundamental_keeps_f0() -> None:
    t = np.arange(WINDOW_SAMPLES) / SR
    raw = sum(np.sin(2 * np.pi * h * 180.0 * t) / h**0.3 for h in range(1, 9))
    played = speaker_response(
        (0.1 * raw / np.std(raw)).astype(np.float32), low_hz=400.0, resonances=[(1500, 6, 3)]
    )
    x = normalize_window(played)
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1 / SR)
    fund = spec[np.argmin(np.abs(f - 180))]
    second = spec[np.argmin(np.abs(f - 540))]
    assert fund < 0.1 * second  # el altavoz se ha comido la fundamental
    assert abs(estimate_f0(x) - 180.0) <= 5.0
    assert is_propeller_harmonic(harmonic_summary(x))


def test_pink_noise_and_isolated_pure_tone_are_not_propeller_harmonics() -> None:
    for seed in range(3):
        assert not is_propeller_harmonic(harmonic_summary(_pink(seed)))
    t = np.arange(WINDOW_SAMPLES) / SR
    tone = normalize_window((0.2 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32))
    s = harmonic_summary(tone)
    assert s["n_armonicos"] < 3 and not is_propeller_harmonic(s)


def test_feature_vector_shape_range_determinism_and_names() -> None:
    x = _comb(180.0, 8, am=0.5)
    v = harmonic_features(x)
    assert v.shape == (HARMONIC_DIM,) == (len(HARMONIC_NAMES),) and v.dtype == np.float32
    assert np.isfinite(v).all() and np.all(v >= 0) and np.all(v <= 1)
    assert np.array_equal(v, harmonic_features(x.copy()))
    am_index = HARMONIC_NAMES.index("modulacion_am")
    assert v[am_index] > harmonic_features(_comb(180.0, 8))[am_index]
    stab = HARMONIC_NAMES.index("estabilidad_f0")
    assert v[stab] >= 0.8  # f0 estable a lo largo de la ventana


def test_silence_gives_zero_vector() -> None:
    v = harmonic_features(np.zeros(WINDOW_SAMPLES, dtype=np.float32))
    assert np.array_equal(v, np.zeros(HARMONIC_DIM, dtype=np.float32))


@pytest.mark.parametrize(
    "bad",
    [
        np.zeros(0, dtype=np.float32),
        np.array([np.nan] * WINDOW_SAMPLES, dtype=np.float32),
        np.array([np.inf] + [0.0] * (WINDOW_SAMPLES - 1), dtype=np.float32),
        np.zeros((2, WINDOW_SAMPLES), dtype=np.float32),
    ],
)
def test_invalid_input_raises(bad: np.ndarray) -> None:
    with pytest.raises(ValueError):
        harmonic_features(bad)

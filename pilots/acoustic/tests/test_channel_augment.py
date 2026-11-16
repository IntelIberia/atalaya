"""H2.2 · Aumento de canal, solo en entrenamiento (REQ-LEG-009)."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.signal import sosfreqz

from acoustic_pilot.channel_augment import (
    AUG_PEAK,
    AUG_SR,
    CHANNEL_SYNTHETIC_NOTE,
    EQ_GAIN_RANGE_DB,
    RT60_RANGE_S,
    apply_channel,
    apply_eq,
    assert_channel_augs_training_only,
    channel_augs_for_training,
    eq_sos,
    estimate_rt60,
    mic_response,
    mulaw_codec,
    plan_channel_augment,
    random_channel,
    speaker_response,
    synthetic_rir,
)

pytestmark = pytest.mark.req("REQ-LEG-009")


def _noise(seed: int = 0, n: int = 2 * AUG_SR) -> np.ndarray:
    return (0.1 * np.random.default_rng(seed).standard_normal(n)).astype(np.float32)


def test_same_seed_same_output_and_different_seed_differs() -> None:
    x = _noise()
    a = apply_channel(x, random_channel(7))
    b = apply_channel(x, random_channel(7))
    c = apply_channel(x, random_channel(8))
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


@pytest.mark.parametrize("seed", range(25))
def test_length_preserved_peak_limited_finite_and_marked_synthetic(seed: int) -> None:
    x = _noise(seed) * 8  # señal fuerte: el limitador debe actuar
    spec = random_channel(seed)
    y = apply_channel(x, spec)
    assert len(y) == len(x) and y.dtype == np.float32 and np.isfinite(y).all()
    assert np.max(np.abs(y)) <= AUG_PEAK + 1e-6
    assert spec["synthetic"] is True


def test_eq_with_all_gains_zero_is_identity() -> None:
    x = _noise(1)
    bands = [
        {"tipo": "grave", "f": 200.0, "ganancia_db": 0.0, "q": 0.7},
        {"tipo": "pico", "f": 1000.0, "ganancia_db": 0.0, "q": 2.0},
        {"tipo": "pico", "f": 3000.0, "ganancia_db": 0.0, "q": 1.0},
        {"tipo": "agudo", "f": 5000.0, "ganancia_db": 0.0, "q": 0.7},
    ]
    assert np.max(np.abs(apply_eq(x, bands) - x)) <= 1e-6


def test_peaking_filter_has_the_requested_gain_at_its_centre() -> None:
    sos = eq_sos([{"tipo": "pico", "f": 1000.0, "ganancia_db": 9.0, "q": 2.0}])
    _, h = sosfreqz(sos, worN=[1000.0, 60.0], fs=AUG_SR)
    gain = 20 * np.log10(np.abs(h))
    assert abs(gain[0] - 9.0) <= 0.05 and abs(gain[1]) <= 0.3


@pytest.mark.parametrize("rt60", [0.2, 0.4, 0.8])
def test_synthetic_rir_rt60_within_20_percent(rt60: float) -> None:
    ir = synthetic_rir(rt60, np.random.default_rng(3))
    assert abs(estimate_rt60(ir) - rt60) <= 0.2 * rt60


def test_mic_and_speaker_responses_cut_lows() -> None:
    tone = np.sin(2 * np.pi * 60 * np.arange(AUG_SR) / AUG_SR).astype(np.float32)
    mic = mic_response(tone, low_hz=250.0, high_hz=7000.0, order=2)
    spk = speaker_response(tone, low_hz=300.0, resonances=[(1200.0, 6.0, 3.0)])
    mid = slice(AUG_SR // 4, 3 * AUG_SR // 4)
    assert np.std(mic[mid]) < 0.2 * np.std(tone[mid])
    assert np.std(spk[mid]) < 0.05 * np.std(tone[mid])


def test_mulaw_codec_quantizes_to_256_levels() -> None:
    y = mulaw_codec(np.linspace(-1, 1, 5000).astype(np.float32))
    assert len(np.unique(y)) <= 256


def test_invalid_parameters_are_rejected() -> None:
    x = _noise()
    with pytest.raises(ValueError):
        synthetic_rir(0.0, np.random.default_rng(0))
    with pytest.raises(ValueError):
        synthetic_rir(-0.3, np.random.default_rng(0))
    for bad in (EQ_GAIN_RANGE_DB[1] + 0.1, EQ_GAIN_RANGE_DB[0] - 0.1):
        with pytest.raises(ValueError):
            apply_eq(x, [{"tipo": "pico", "f": 1000.0, "ganancia_db": bad, "q": 1.0}])
    with pytest.raises(ValueError):
        apply_channel(x, random_channel(0), sr=44100)
    with pytest.raises(ValueError):
        apply_channel(np.array([np.nan] * 100, dtype=np.float32), random_channel(0))
    assert RT60_RANGE_S == (0.2, 0.8)


def test_plan_is_deterministic_and_training_only_fails_closed() -> None:
    plan = plan_channel_augment(list(range(20)), ["a"] * 10 + ["b"] * 10, n=50, seed=4)
    assert plan == plan_channel_augment(list(range(20)), ["a"] * 10 + ["b"] * 10, n=50, seed=4)
    assert all(p["synthetic"] for p in plan) and len(plan) == 50
    train = list(range(0, 20, 2))
    ids = channel_augs_for_training(plan, train)
    assert ids and all(plan[k]["clip"] in train for k in ids)
    assert_channel_augs_training_only(plan, ids, train)
    leaked = [k for k, p in enumerate(plan) if p["clip"] not in train][:1]
    with pytest.raises(ValueError):  # una ventana aumentada de validación/test: fallo cerrado
        assert_channel_augs_training_only(plan, ids + leaked, train)
    assert "synthetic=true" in CHANNEL_SYNTHETIC_NOTE

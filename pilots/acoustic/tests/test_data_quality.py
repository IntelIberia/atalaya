"""Iteración 5 · calidad de datos: formato, clips defectuosos, sonoridad y duplicados."""

from __future__ import annotations

import numpy as np
import pytest

from acoustic_pilot.data_quality import (
    NEAR_DUPLICATE_COSINE,
    approx_lufs,
    clip_quality,
    exact_duplicates,
    k_weighting_coefficients,
    loudness_features,
    near_duplicate_pairs,
    normalize_format,
    pcm_sha256,
    resolve_near_duplicates,
)


def _sine(freq: float, sr: int, seconds: float, amp: float = 0.5) -> np.ndarray:
    t = np.arange(int(sr * seconds)) / sr
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float64)


# --- Normalización de formato -------------------------------------------------------------


def test_normalize_format_gives_mono_16k_float32() -> None:
    stereo = np.stack([_sine(440, 44100, 1.0), _sine(440, 44100, 1.0)])  # (canales, muestras)
    out = normalize_format(stereo, 44100)
    assert out.dtype == np.float32 and out.ndim == 1
    assert len(out) == 16000
    # la amplitud de un tono por debajo de Nyquist se conserva tras el remuestreo
    assert np.max(np.abs(out[100:-100])) == pytest.approx(0.5, abs=0.02)


def test_normalize_format_scales_integer_pcm_and_accepts_samples_by_channels() -> None:
    pcm = (np.stack([_sine(300, 16000, 0.5), _sine(300, 16000, 0.5)], axis=1) * 32767).astype(
        np.int16
    )  # (muestras, canales)
    out = normalize_format(pcm, 16000)
    assert out.dtype == np.float32 and len(out) == 8000
    assert np.max(np.abs(out)) == pytest.approx(0.5, abs=0.01)


def test_normalize_format_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        normalize_format(np.zeros((3, 4, 5)), 16000)
    with pytest.raises(ValueError):
        normalize_format(np.zeros(10), 0)


# --- Clips silenciosos, saturados y corruptos ---------------------------------------------


def test_clip_quality_flags_ok_silent_saturated_and_corrupt() -> None:
    sr = 16000
    assert clip_quality(_sine(500, sr, 1.0, 0.3), sr)["status"] == "ok"
    assert clip_quality(np.zeros(sr), sr)["status"] == "silencioso"
    assert clip_quality(_sine(500, sr, 1.0, 1e-5), sr)["status"] == "silencioso"
    loud = np.clip(_sine(500, sr, 1.0, 3.0), -1.0, 1.0)
    q = clip_quality(loud, sr)
    assert q["status"] == "saturado" and q["clipped_fraction"] > 0.01
    bad = _sine(500, sr, 1.0)
    bad[10] = np.nan
    assert clip_quality(bad, sr)["status"] == "corrupto"
    assert clip_quality(np.zeros(0), sr)["status"] == "corrupto"
    assert clip_quality(_sine(500, sr, 0.2), sr)["status"] == "corrupto"  # demasiado corto


def test_clip_quality_checks_every_channel_for_saturation() -> None:
    sr = 16000
    left = np.clip(_sine(500, sr, 1.0, 3.0), -1, 1)
    right = -left  # la media mono se anula, pero el clip original está saturado
    assert clip_quality(np.stack([left, right]), sr)["status"] == "saturado"


# --- Sonoridad (solo como característica) -------------------------------------------------


def test_k_weighting_matches_bs1770_table_at_48k() -> None:
    (b_s, a_s), (b_h, a_h) = k_weighting_coefficients(48000)
    np.testing.assert_allclose(
        b_s, [1.53512485958697, -2.69169618940638, 1.19839281085285], atol=1e-6
    )
    np.testing.assert_allclose(a_s, [1.0, -1.69065929318241, 0.73248077421585], atol=1e-6)
    np.testing.assert_allclose(b_h, [1.0, -2.0, 1.0])
    np.testing.assert_allclose(a_h, [1.0, -1.99004745483398, 0.99007225036621], atol=1e-6)


def test_approx_lufs_of_full_scale_1k_sine_is_minus_3() -> None:
    assert approx_lufs(_sine(997, 48000, 5.0, 1.0), 48000) == pytest.approx(-3.01, abs=0.05)
    assert approx_lufs(_sine(997, 16000, 5.0, 1.0), 16000) == pytest.approx(-3.01, abs=0.3)
    # 6 dB menos de amplitud => ~6 LU menos
    quieter = approx_lufs(_sine(997, 16000, 5.0, 0.5), 16000)
    assert quieter == pytest.approx(-9.03, abs=0.3)


def test_loudness_features_do_not_modify_the_signal() -> None:
    x = _sine(997, 16000, 2.0, 0.25).astype(np.float32)
    copy = x.copy()
    feats = loudness_features(x, 16000)
    np.testing.assert_array_equal(x, copy)
    assert set(feats) == {"rms_dbfs", "lufs_aprox", "pico_dbfs", "factor_cresta_db"}
    assert feats["rms_dbfs"] == pytest.approx(20 * np.log10(0.25 / np.sqrt(2)), abs=0.05)
    assert loudness_features(np.zeros(16000, np.float32), 16000)["rms_dbfs"] == -120.0


# --- Duplicados exactos y casi duplicados -------------------------------------------------


def test_pcm_hash_ignores_container_but_not_content() -> None:
    a = _sine(400, 16000, 1.0).astype(np.float32)
    assert pcm_sha256(a) == pcm_sha256(a.astype(np.float64))
    b = a.copy()
    b[0] += 1e-3
    assert pcm_sha256(a) != pcm_sha256(b)


def test_exact_duplicates_keep_first_by_priority() -> None:
    hashes = ["h1", "h2", "h1", "h3", "h1"]
    names = ["c", "a", "b", "d", "a2"]
    dropped = exact_duplicates(hashes, names)
    # se conserva el de nombre menor ("a2" < "b" < "c") y se descartan los demás
    assert sorted(dropped) == [0, 2]
    assert dropped[0]["kept"] == 4


def test_near_duplicate_pairs_by_cosine_with_blocks() -> None:
    rng = np.random.default_rng(0)
    emb = rng.normal(size=(50, 16))
    emb[10] = emb[3] * 2.0 + 1e-6  # misma dirección => coseno 1
    emb[20] = emb[3] + rng.normal(scale=1e-3, size=16)
    pairs = near_duplicate_pairs(emb, threshold=0.999, block=7)
    found = {(i, j) for i, j, _ in pairs}
    assert {(3, 10), (3, 20), (10, 20)} <= found
    assert all(i < j and s >= 0.999 for i, j, s in pairs)
    assert len(found) == 3
    assert 0.9 < NEAR_DUPLICATE_COSINE < 1.0
    # con grupos, los pares dentro de un mismo grupo no cuentan (no pueden filtrar)
    groups = ["x"] * 50
    groups[20] = "y"
    cross = {(i, j) for i, j, _ in near_duplicate_pairs(emb, threshold=0.999, groups=groups)}
    assert cross == {(3, 20), (10, 20)}
    with pytest.raises(ValueError):
        near_duplicate_pairs(emb, groups=["x"])


def test_resolve_near_duplicates_leaves_no_pair_across_groups() -> None:
    groups = ["A", "A", "B", "C", "C", "D"]
    names = [f"c{i}" for i in range(6)]
    # 0~2 (A-B), 2~3 (B-C, cadena), 3~4 dentro de C, 1 sin pareja, 5 sin pareja
    pairs = [(0, 2, 0.999), (2, 3, 0.998), (3, 4, 0.999)]
    out = resolve_near_duplicates(pairs, groups, names)
    kept = set(range(6)) - set(out["dropped"])
    for i, j, _ in pairs:
        if i in kept and j in kept:
            assert groups[i] == groups[j]
    # el grupo representante del componente es el que más miembros aporta (C: 3 y 4)
    assert out["dropped"] == {0: "C", 2: "C"}
    assert out["clusters"] == 1 and out["cross_group_clusters"] == 1


def test_resolve_near_duplicates_within_group_drops_nothing() -> None:
    out = resolve_near_duplicates([(0, 1, 0.999)], ["A", "A"], ["x", "y"])
    assert out["dropped"] == {} and out["cross_group_clusters"] == 0

"""Iteración 5 · control de fugas, desequilibrio y aumento de datos solo en entrenamiento."""

from __future__ import annotations

from collections import Counter

import numpy as np
import pytest

from acoustic_pilot.augment import (
    MIX_SNR_RANGE_DB,
    SYNTHETIC_NOTE,
    mix_at_snr,
    mixes_for_training,
    plan_mixes,
    random_gain,
    render_mix,
    time_shift,
)
from acoustic_pilot.balance import balanced_sample, class_source_weights
from acoustic_pilot.leakage import (
    assert_no_cross_partition_pairs,
    leave_one_source_out,
    stratified_group_folds,
)


def _dataset(seed: int = 0):
    rng = np.random.default_rng(seed)
    labels, groups, sources = [], [], []
    # aris: muy grande (domina), svanstrom: pequeña, fsd50k: solo negativos
    for g in range(60):
        for _ in range(10):
            labels.append(int(g % 2 == 0))
            groups.append(f"aris:{g}")
            sources.append("aris")
    for g in range(20):
        labels.append(int(g % 3 == 0))
        groups.append(f"svan:{g}")
        sources.append("svanstrom")
    for g in range(30):
        for _ in range(int(rng.integers(1, 4))):
            labels.append(0)
            groups.append(f"fsd:{g}")
            sources.append("fsd50k")
    return labels, groups, sources


# --- StratifiedGroupKFold y leave-one-source-out -------------------------------------------


def test_stratified_group_folds_keep_groups_whole_and_both_classes() -> None:
    labels, groups, _ = _dataset()
    folds = stratified_group_folds(labels, groups, k=5, seed=7)
    assert set(folds) == set(range(5))
    fold_of_group: dict[str, int] = {}
    for g, f in zip(groups, folds, strict=True):
        assert fold_of_group.setdefault(g, f) == f
    for f in range(5):
        assert {labels[i] for i in range(len(labels)) if folds[i] == f} == {0, 1}
    assert stratified_group_folds(labels, groups, k=5, seed=7) == folds  # determinista


def test_stratified_group_folds_reject_too_few_groups() -> None:
    with pytest.raises(ValueError):
        stratified_group_folds([0, 1, 0], ["a", "b", "c"], k=5, seed=1)


def test_leave_one_source_out_tests_each_source_unseen() -> None:
    labels, groups, sources = _dataset()
    splits = leave_one_source_out(labels, groups, sources, seed=3)
    assert [s["fuente"] for s in splits] == ["aris", "fsd50k", "svanstrom"]
    for s in splits:
        test_sources = {sources[i] for i in s["test"]}
        assert test_sources == {s["fuente"]}
        for part in ("train", "validation"):
            assert s["fuente"] not in {sources[i] for i in s[part]}
            assert {labels[i] for i in s[part]} == {0, 1}
        seen = [{groups[i] for i in s[p]} for p in ("train", "validation", "test")]
        assert not (seen[0] & seen[1] or seen[0] & seen[2] or seen[1] & seen[2])
        assert len(s["train"]) + len(s["validation"]) + len(s["test"]) == len(labels)


def test_no_near_duplicate_pair_may_cross_partitions() -> None:
    assignment = [0, 0, 1, 1]
    assert_no_cross_partition_pairs([(0, 1, 0.999)], assignment)
    with pytest.raises(ValueError, match="casi duplicado"):
        assert_no_cross_partition_pairs([(1, 2, 0.999)], assignment)


# --- Pesos por clase y por fuente; muestreo balanceado -------------------------------------


def test_class_source_weights_equalize_classes_and_sources() -> None:
    labels, _, sources = _dataset()
    w = class_source_weights(labels, sources)
    y = np.asarray(labels)
    s = np.asarray(sources)
    assert w.sum() == pytest.approx(len(labels))
    assert w[y == 1].sum() == pytest.approx(w[y == 0].sum())
    # dentro de cada clase, cada fuente aporta el mismo peso total: aris no domina
    for cls in (0, 1):
        totals = {src: w[(y == cls) & (s == src)].sum() for src in set(s[y == cls])}
        assert max(totals.values()) == pytest.approx(min(totals.values()))
    assert (w > 0).all()


def test_balanced_sample_draws_sources_evenly() -> None:
    labels, _, sources = _dataset()
    idx = balanced_sample(labels, sources, 6000, seed=1)
    counts = Counter((labels[i], sources[i]) for i in idx)
    # 3 celdas negativas y 2 positivas: cada clase ~50 %, cada fuente ~igual dentro de su clase
    assert sum(v for (c, _), v in counts.items() if c == 1) == pytest.approx(3000, rel=0.06)
    assert counts[(1, "aris")] == pytest.approx(counts[(1, "svanstrom")], rel=0.12)
    assert counts[(0, "fsd50k")] == pytest.approx(counts[(0, "aris")], rel=0.12)
    assert balanced_sample(labels, sources, 100, seed=1) == balanced_sample(
        labels, sources, 100, seed=1
    )


# --- Aumento de forma de onda --------------------------------------------------------------


def _noise(n: int, seed: int, scale: float = 0.1) -> np.ndarray:
    return (np.random.default_rng(seed).normal(scale=scale, size=n)).astype(np.float32)


def test_mix_at_snr_hits_requested_snr() -> None:
    drone, background = _noise(16000, 1), _noise(16000, 2, 0.3)
    for snr in (-10.0, 0.0, 20.0):
        mix, scaled_drone, scaled_bg = mix_at_snr(drone, background, snr)
        measured = 10 * np.log10(np.mean(scaled_drone**2) / np.mean(scaled_bg**2))
        assert measured == pytest.approx(snr, abs=1e-3)
        assert np.max(np.abs(mix)) <= 0.99 + 1e-6
        np.testing.assert_allclose(mix, scaled_drone + scaled_bg, atol=1e-6)


def test_gain_and_shift() -> None:
    x = _noise(1000, 3)
    np.testing.assert_allclose(random_gain(x, 6.0), x * 10 ** (6 / 20), rtol=1e-6)
    shifted = time_shift(x, 100)
    np.testing.assert_array_equal(shifted[100:], x[:-100])
    np.testing.assert_array_equal(shifted[:100], x[-100:])


def test_plan_mixes_uses_only_given_pools_and_documented_ranges() -> None:
    labels, _, sources = _dataset()
    positives = [i for i, y in enumerate(labels) if y == 1]
    negatives = [i for i, y in enumerate(labels) if y == 0]
    seconds = [1.0 if s == "aris" else 10.0 for s in sources]
    plan = plan_mixes(positives, negatives, sources, seconds, n=300, seed=5)
    assert len(plan) == 300
    lo, hi = MIX_SNR_RANGE_DB
    assert (lo, hi) == (-10.0, 20.0)
    for m in plan:
        assert m["drone"] in positives and m["background"] in negatives
        assert lo <= m["snr_db"] <= hi and -6.0 <= m["gain_db"] <= 6.0
        assert m["synthetic"] is True and m["dron"] == 1
        assert 0 < m["seconds"] <= min(seconds[m["drone"]], seconds[m["background"]], 5.0)
    assert len({m["id"] for m in plan}) == 300
    # las fuentes de drones se muestrean equilibradas, no en proporción a su tamaño
    by_src = Counter(sources[m["drone"]] for m in plan)
    assert by_src["svanstrom"] == pytest.approx(by_src["aris"], rel=0.3)
    assert plan == plan_mixes(positives, negatives, sources, seconds, n=300, seed=5)
    assert "no cuentan como rendimiento real" in SYNTHETIC_NOTE


def test_mixes_only_enter_training_when_both_parts_are_in_training() -> None:
    plan = [
        {"id": "m0", "drone": 0, "background": 5},
        {"id": "m1", "drone": 0, "background": 9},
        {"id": "m2", "drone": 8, "background": 5},
    ]
    assert mixes_for_training(plan, train=[0, 1, 5]) == [0]
    assert mixes_for_training(plan, train=[]) == []


def test_render_mix_is_deterministic_and_bounded() -> None:
    drone, bg = _noise(32000, 4), _noise(48000, 5)
    spec = {
        "id": "m0",
        "drone": 0,
        "background": 1,
        "snr_db": 5.0,
        "gain_db": -3.0,
        "shift_fraction": 0.25,
        "drone_offset": 0.5,
        "background_offset": 0.1,
        "seconds": 1.5,
    }
    a = render_mix(spec, drone, bg, 16000)
    assert a.dtype == np.float32 and len(a) == 24000
    np.testing.assert_array_equal(a, render_mix(spec, drone, bg, 16000))
    assert np.max(np.abs(a)) <= 0.99


def _spec(**kw: float) -> dict:
    base = {
        "seconds": 1.0,
        "drone_offset": 0.0,
        "background_offset": 0.0,
        "shift_fraction": 0.0,
        "snr_db": 0.0,
        "gain_db": 0.0,
    }
    base.update(kw)
    return base


def test_render_mix_recorte_en_silencio_usa_la_ventana_con_energia() -> None:
    # Fondo tipo ESC-10: 1 s de sonido seguido de 4 s de silencio de relleno.
    sr = 16000
    rng = np.random.default_rng(0)
    drone = rng.normal(0, 0.1, 5 * sr).astype(np.float32)
    bg = np.zeros(5 * sr, dtype=np.float32)
    bg[:sr] = rng.normal(0, 0.1, sr)
    mix = render_mix(_spec(background_offset=1.0), drone, bg, sr)  # el recorte pedido es silencio
    assert mix.shape == (sr,)
    assert np.isfinite(mix).all() and float(np.mean(mix.astype(np.float64) ** 2)) > 0


def test_render_mix_fondo_totalmente_silencioso_se_omite() -> None:
    import pytest

    from acoustic_pilot.augment import SilentMixError

    sr = 16000
    drone = np.random.default_rng(1).normal(0, 0.1, sr).astype(np.float32)
    with pytest.raises(SilentMixError):
        render_mix(_spec(), drone, np.zeros(sr, dtype=np.float32), sr)
    assert issubclass(SilentMixError, ValueError)

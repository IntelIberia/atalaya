"""H2.3 · Mezclas cruzadas dron/fondo entre fuentes, solo en entrenamiento (REQ-LEG-009)."""

from __future__ import annotations

import numpy as np
import pytest

from acoustic_pilot.augment import (
    MIX_SNR_RANGE_DB,
    assert_cross_mixes_allowed,
    cross_mixes_for_fold,
    plan_cross_mixes,
    render_mix,
)
from acoustic_pilot.leakage import leave_one_source_out

pytestmark = pytest.mark.req("REQ-LEG-009")


def _pool():
    sources = ["aris"] * 40 + ["svanstrom"] * 20 + ["fsd50k"] * 30 + ["esc10"] * 10
    labels = [i % 2 for i in range(40)] + [int(i % 3 == 0) for i in range(20)] + [0] * 40
    groups = [f"{s}:{i // 2}" for i, s in enumerate(sources)]
    seconds = [10.0] * len(sources)
    return sources, labels, groups, seconds


def test_every_cross_mix_has_different_drone_and_background_sources() -> None:
    sources, labels, _, seconds = _pool()
    pos = [i for i, y in enumerate(labels) if y]
    neg = [i for i, y in enumerate(labels) if not y]
    plan = plan_cross_mixes(pos, neg, sources, seconds, n=400, seed=3)
    assert len(plan) == 400
    for m in plan:
        assert sources[m["drone"]] != sources[m["background"]]
        assert m["drone_source"] == sources[m["drone"]]
        assert m["background_source"] == sources[m["background"]]
        assert m["synthetic"] is True and m["cross"] is True and m["dron"] == 1
        assert MIX_SNR_RANGE_DB[0] <= m["snr_db"] <= MIX_SNR_RANGE_DB[1]
    # se equilibran fuentes: ningún fondo de una sola fuente domina
    bg = {s: sum(m["background_source"] == s for m in plan) for s in set(sources)}
    assert max(bg.values()) < 0.6 * len(plan)


def test_plan_is_deterministic_with_seed() -> None:
    sources, labels, _, seconds = _pool()
    pos = [i for i, y in enumerate(labels) if y]
    neg = [i for i, y in enumerate(labels) if not y]
    a = plan_cross_mixes(pos, neg, sources, seconds, n=50, seed=9)
    assert a == plan_cross_mixes(pos, neg, sources, seconds, n=50, seed=9)
    assert a != plan_cross_mixes(pos, neg, sources, seconds, n=50, seed=10)


def test_same_source_pairs_never_appear_and_single_source_fails() -> None:
    sources = ["aris"] * 10
    labels = [1, 0] * 5
    pos = [i for i, y in enumerate(labels) if y]
    neg = [i for i, y in enumerate(labels) if not y]
    with pytest.raises(ValueError):
        plan_cross_mixes(pos, neg, sources, [5.0] * 10, n=10, seed=0)


def test_loso_folds_only_use_mixes_whose_two_sources_are_in_training() -> None:
    sources, labels, groups, seconds = _pool()
    pos = [i for i, y in enumerate(labels) if y]
    neg = [i for i, y in enumerate(labels) if not y]
    plan = plan_cross_mixes(pos, neg, sources, seconds, n=600, seed=1)
    for split in leave_one_source_out(labels, groups, sources, seed=2):
        ids = cross_mixes_for_fold(plan, split["train"], held_out=split["fuente"])
        assert ids
        train = set(split["train"])
        for k in ids:
            assert plan[k]["drone"] in train and plan[k]["background"] in train
            assert split["fuente"] not in (plan[k]["drone_source"], plan[k]["background_source"])
        assert_cross_mixes_allowed(plan, ids, split["train"], held_out=split["fuente"])


def test_a_mix_using_the_held_out_source_is_rejected() -> None:
    sources, labels, _, seconds = _pool()
    pos = [i for i, y in enumerate(labels) if y]
    neg = [i for i, y in enumerate(labels) if not y]
    plan = plan_cross_mixes(pos, neg, sources, seconds, n=200, seed=1)
    everything = list(range(len(sources)))
    bad = [k for k, m in enumerate(plan) if "aris" in (m["drone_source"], m["background_source"])]
    assert bad
    with pytest.raises(ValueError):
        assert_cross_mixes_allowed(plan, bad[:1], everything, held_out="aris")
    outside = [k for k, m in enumerate(plan) if m["drone"] != 0][:1]
    with pytest.raises(ValueError):  # dron o fondo fuera de entrenamiento
        assert_cross_mixes_allowed(plan, outside, [0], held_out=None)


def test_cross_mix_renders_with_the_iteration5_mixer() -> None:
    sources, labels, _, seconds = _pool()
    pos = [i for i, y in enumerate(labels) if y]
    neg = [i for i, y in enumerate(labels) if not y]
    spec = plan_cross_mixes(pos, neg, sources, seconds, n=1, seed=0)[0]
    rng = np.random.default_rng(0)
    drone = (0.2 * np.sin(2 * np.pi * 180 * np.arange(160000) / 16000)).astype(np.float32)
    background = (0.05 * rng.standard_normal(160000)).astype(np.float32)
    mix = render_mix(spec, drone, background, 16000)
    assert len(mix) == int(spec["seconds"] * 16000) and np.max(np.abs(mix)) <= 0.99

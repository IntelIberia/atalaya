"""Iteración 6 · técnicas ligeras contra el atajo de dominio sobre embeddings (REQ-FUN-027)."""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

from acoustic_pilot.domain_robust import (
    apply_centers,
    calibration_centers,
    fit_linear,
    group_dro_fit,
    hysteresis_thresholds,
    inlp_directions,
    linear_logit,
    linear_proba,
    safe_roc_auc,
    worst_source_threshold,
)

pytestmark = pytest.mark.req("REQ-FUN-027")


def _shortcut(seed: int = 0):
    """Fuente A casi solo con dron, B/C solo fondos, E mixta; el «canal» (dims 1-3) delata la
    fuente y por tanto la clase. La fuente de test tiene canales al azar (fuente nueva)."""
    rng = np.random.default_rng(seed)
    spec = {
        "A": (0.9, [3, 0, 0.0]),
        "B": (0.0, [0, 3, 0.0]),
        "C": (0.0, [0, 0, 3.0]),
        "E": (0.5, [-2, -2, 0.0]),
    }
    x, y, s = [], [], []
    for src, (prev, off) in spec.items():
        for _ in range(400):
            label = int(rng.random() < prev)
            v = rng.standard_normal(20)
            v[0] += 1.2 * label
            v[1:4] += np.array(off) + 0.5 * rng.standard_normal(3)
            x.append(v)
            y.append(label)
            s.append(src)
    xt, yt = [], []
    for _ in range(600):
        label = int(rng.random() < 0.5)
        v = rng.standard_normal(20)
        v[0] += 1.2 * label
        v[1:4] += 3 * rng.standard_normal(3)
        xt.append(v)
        yt.append(label)
    return np.array(x), np.array(y), s, np.array(xt), np.array(yt)


def test_folded_linear_model_equals_standardized_logistic_regression() -> None:
    x, y, s, _, _ = _shortcut()
    x = x * np.arange(1, 21) + 5  # escalas y medias distintas por rasgo
    w = np.ones(len(y))
    model = fit_linear(x, y, w, seed=0)
    mu, sd = x.mean(axis=0), x.std(axis=0)
    ref = LogisticRegression(C=1.0, max_iter=3000, random_state=0).fit((x - mu) / sd, y)
    np.testing.assert_allclose(
        linear_logit(model, x), ref.decision_function((x - mu) / sd), atol=1e-8
    )
    assert np.all((linear_proba(model, x) > 0) & (linear_proba(model, x) < 1))


def test_inlp_removes_source_information_within_class_and_helps_a_new_source() -> None:
    x, y, s, xt, yt = _shortcut()
    w = np.ones(len(y))
    erm = fit_linear(x, y, w, seed=0)
    inlp = fit_linear(x, y, w, seed=0, domains=s, inlp_rounds=2)
    assert inlp["inlp_direcciones"] > 0
    auc_erm = safe_roc_auc(yt, linear_logit(erm, xt))
    auc_inlp = safe_roc_auc(yt, linear_logit(inlp, xt))
    assert auc_inlp > auc_erm + 0.05, (auc_erm, auc_inlp)
    # la proyección es ortonormal y deja sin información de fuente a los negativos
    z = (x - x.mean(axis=0)) / x.std(axis=0)
    basis = inlp_directions(z, y, s, rounds=2, seed=0)
    np.testing.assert_allclose(basis.T @ basis, np.eye(basis.shape[1]), atol=1e-8)
    neg = y == 0
    proj = z - (z @ basis) @ basis.T
    clf = LogisticRegression(max_iter=1000).fit(proj[neg], np.asarray(s)[neg])
    chance = max(np.mean(np.asarray(s)[neg] == v) for v in set(np.asarray(s)[neg].tolist()))
    assert clf.score(proj[neg], np.asarray(s)[neg]) < chance + 0.15


def test_inlp_needs_domains() -> None:
    x, y, _, _, _ = _shortcut()
    with pytest.raises(ValueError):
        fit_linear(x, y, np.ones(len(y)), seed=0, inlp_rounds=1)


def test_group_dro_lowers_the_worst_group_loss() -> None:
    x, y, s, _, _ = _shortcut()
    groups = [f"{a}|{b}" for a, b in zip(s, y, strict=True)]
    _, history = group_dro_fit(x, y, groups, seed=0, rounds=4, eta=1.0)
    assert max(history[-1]["perdida"].values()) < max(history[0]["perdida"].values())
    q = history[-1]["q"]
    assert abs(sum(q.values()) - 1) < 1e-6


def test_worst_source_threshold_caps_the_fpr_of_every_source() -> None:
    rng = np.random.default_rng(3)
    y = np.array([0] * 300 + [1] * 100)
    s = ["fsd"] * 100 + ["esc"] * 200 + ["aris"] * 100
    p = np.concatenate(
        [rng.uniform(0.3, 0.9, 100), rng.uniform(0, 0.5, 200), rng.uniform(0.5, 1, 100)]
    )
    rule = worst_source_threshold(y, p, s, max_fpr=0.05)
    assert rule["fuente_limitante"] == "fsd"
    for src, fpr in rule["fpr_validacion"].items():
        assert fpr <= 0.05, src
    assert set(rule["recall_validacion"]) == {"aris"}
    with pytest.raises(ValueError):
        worst_source_threshold([1, 1], [0.2, 0.3], ["a", "b"], max_fpr=0.1)


def test_hysteresis_thresholds_are_ordered() -> None:
    rng = np.random.default_rng(4)
    y = np.array([0] * 200 + [1] * 50)
    p = np.concatenate([rng.uniform(0, 0.7, 200), rng.uniform(0.4, 1, 50)])
    s = ["a"] * 100 + ["b"] * 100 + ["c"] * 50
    th = hysteresis_thresholds(y, p, s, max_fpr_on=0.02, max_fpr_off=0.10)
    assert 0 < th["theta_off"] < th["theta_on"] < 1
    with pytest.raises(ValueError):
        hysteresis_thresholds(y, p, s, max_fpr_on=0.1, max_fpr_off=0.05)


def test_calibration_centering_by_source() -> None:
    x = np.array([[1.0, 1.0], [3.0, 3.0], [10.0, 0.0], [12.0, 2.0]])
    s = ["a", "a", "b", "b"]
    centers = calibration_centers(x, s, [True, False, True, False])
    np.testing.assert_allclose(apply_centers(x, s, centers)[[0, 2]], 0.0)
    with pytest.raises(ValueError):
        calibration_centers(x, s, [True, True, False, False])
    assert safe_roc_auc([1, 1], [0.1, 0.2]) is None

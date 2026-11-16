"""Iteración 5 · modelado por ventanas, calibración, curvas, FA/h estimada y negativos difíciles."""

from __future__ import annotations

import math

import numpy as np
import pytest
from sklearn.metrics import det_curve

from acoustic_pilot.calibration import (
    FA_ESTIMATE_STATUS,
    alarm_events,
    apply_calibration,
    brier_score,
    det_points,
    expected_calibration_error,
    false_alarms_per_hour_estimate,
    fit_calibrator,
    reliability_bins,
)
from acoustic_pilot.hard_negatives import (
    NEGATIVE_TYPES,
    confusion_by_negative_type,
    hard_negative_weights,
    negative_type,
    recording_priorities,
)
from acoustic_pilot.windows import (
    AGGREGATIONS,
    aggregate_window_scores,
    frame_training_set,
    pack_frames,
    smooth_scores,
    unpack_frames,
)

# --- Ventanas ------------------------------------------------------------------------------


def test_pack_and_unpack_frames_round_trip() -> None:
    blocks = [np.ones((3, 4)), np.zeros((1, 4)), np.full((5, 4), 2.0)]
    data, offsets = pack_frames(blocks)
    assert data.shape == (9, 4) and data.dtype == np.float32
    assert offsets.tolist() == [0, 3, 4, 9]
    for i, b in enumerate(blocks):
        np.testing.assert_array_equal(unpack_frames(data, offsets, i), b)


def test_smoothing_is_a_centred_moving_average() -> None:
    p = np.array([0.0, 0.0, 1.0, 0.0, 0.0])
    np.testing.assert_allclose(smooth_scores(p, 3), [0, 1 / 3, 1 / 3, 1 / 3, 0])
    np.testing.assert_allclose(smooth_scores(p, 1), p)
    np.testing.assert_allclose(smooth_scores(np.array([0.2, 0.4]), 5), [0.3, 0.3])


def test_aggregations() -> None:
    p = np.array([0.1, 0.9, 0.2, 0.8, 0.3])
    out = {m: aggregate_window_scores(p, m) for m in AGGREGATIONS}
    assert out["media"] == pytest.approx(0.46)
    assert out["max"] == pytest.approx(0.9)
    assert out["top3"] == pytest.approx((0.9 + 0.8 + 0.3) / 3)
    assert out["max_suavizado"] == pytest.approx(max(smooth_scores(p, 3)))
    assert out["media"] < out["atencion"] < out["max"]
    # un pico aislado pesa menos tras suavizar que en el máximo puro
    spike = np.array([0.0, 0.0, 1.0, 0.0, 0.0])
    assert aggregate_window_scores(spike, "max_suavizado") < aggregate_window_scores(spike, "max")
    with pytest.raises(ValueError):
        aggregate_window_scores(p, "mediana")
    with pytest.raises(ValueError):
        aggregate_window_scores(np.array([]), "max")


def test_frame_training_set_subsamples_and_only_uses_given_clips() -> None:
    blocks = [np.full((n, 2), float(i)) for i, n in enumerate([20, 3, 8])]
    data, offsets = pack_frames(blocks)
    x, y, owner = frame_training_set(data, offsets, [1, 0, 1], [0, 2], max_frames=4)
    assert set(owner.tolist()) == {0, 2}
    assert (owner == 0).sum() == 4 and (owner == 2).sum() == 4
    np.testing.assert_array_equal(x[:, 0], owner.astype(float))
    np.testing.assert_array_equal(y, [1 if o == 0 else 1 for o in owner])
    x2, _, owner2 = frame_training_set(data, offsets, [1, 0, 1], [1], max_frames=4)
    assert len(owner2) == 3  # clip con menos ventanas que el máximo: todas


# --- Calibración y curvas ----------------------------------------------------------------


def _miscalibrated(n: int = 4000, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    true_p = rng.uniform(0.02, 0.98, n)
    y = (rng.uniform(size=n) < true_p).astype(int)
    over = 1 / (1 + np.exp(-3 * np.log(true_p / (1 - true_p))))  # sobreconfiado
    return y, over


@pytest.mark.parametrize("method", ["platt", "isotonica"])
def test_calibration_reduces_ece(method: str) -> None:
    y, p = _miscalibrated()
    cal = fit_calibrator(y[:2000], p[:2000], method)
    before = expected_calibration_error(y[2000:], p[2000:])
    after = expected_calibration_error(y[2000:], apply_calibration(cal, p[2000:]))
    assert after < before / 2
    q = apply_calibration(cal, np.linspace(0, 1, 50))
    assert np.all(np.diff(q) >= -1e-12) and q.min() >= 0 and q.max() <= 1


def test_calibration_rejects_unknown_method_and_single_class() -> None:
    with pytest.raises(ValueError):
        fit_calibrator(np.array([0, 1]), np.array([0.2, 0.8]), "beta")
    with pytest.raises(ValueError):
        fit_calibrator(np.array([0, 0]), np.array([0.2, 0.8]), "platt")


def test_ece_and_reliability_bins_by_hand() -> None:
    y = np.array([0, 1, 1, 1])
    p = np.array([0.1, 0.9, 0.9, 0.6])
    bins = reliability_bins(y, p, n_bins=2)
    assert [b["n"] for b in bins] == [1, 3]
    assert bins[1]["confianza_media"] == pytest.approx(0.8)
    assert bins[1]["fraccion_positivos"] == pytest.approx(1.0)
    assert expected_calibration_error(y, p, n_bins=2) == pytest.approx((1 * 0.1 + 3 * 0.2) / 4)
    assert brier_score(y, p) == pytest.approx((0.01 + 0.01 + 0.01 + 0.16) / 4)


def test_det_points_match_sklearn() -> None:
    y, p = _miscalibrated(300, 2)
    fpr, fnr, thr = det_points(y, p)
    ref = det_curve(y, p)
    np.testing.assert_allclose(fpr, ref[0])
    np.testing.assert_allclose(fnr, ref[1])
    np.testing.assert_allclose(thr, ref[2])


def test_alarm_events_count_rising_edges_with_refractory() -> None:
    s = np.array([0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1], dtype=float)
    assert alarm_events(s, 0.5, hop_s=1.0, refractory_s=0.0) == 3
    # dentro del periodo refractario (2 s) el segundo flanco no cuenta como alarma nueva
    assert alarm_events(s, 0.5, hop_s=1.0, refractory_s=3.0) == 2
    assert alarm_events(np.zeros(5), 0.5, hop_s=1.0, refractory_s=0.0) == 0


def test_fa_per_hour_is_always_an_unverified_estimate() -> None:
    streams = [np.array([0, 1, 0, 0] * 900, dtype=float)]  # 3600 ventanas de 0,5 s = 0,5 h
    est = false_alarms_per_hour_estimate(streams, 0.5, hop_s=0.5, refractory_s=0.0)
    assert est["status"] == FA_ESTIMATE_STATUS
    assert "NO VERIFICADA" in est["status"] and "concatenación" in est["nota"]
    assert est["horas"] == pytest.approx(0.5)
    assert est["eventos"] == 900 and est["valor"] == pytest.approx(1800)
    empty = false_alarms_per_hour_estimate([], 0.5, hop_s=0.5, refractory_s=0.0)
    assert empty["valor"] is None


# --- Negativos difíciles por tipo ---------------------------------------------------------


def test_negative_types_cover_known_classes() -> None:
    assert negative_type("fsd50k", "Motorcycle") == "motos"
    assert negative_type("fsd50k", "Boat_and_Water_vehicle") == "barcos"
    assert negative_type("fsd50k", "Fixed-wing_aircraft_and_airplane") == "aviones"
    assert negative_type("fsd50k", "Aircraft") == "aviones"
    assert negative_type("svanstrom", "HELICOPTER") == "helicópteros"
    assert negative_type("esc10", "helicopter") == "helicópteros"
    assert negative_type("fsd50k", "Insect") == "insectos"
    assert negative_type("fsd50k", "Wind") == "viento"
    assert negative_type("esc10", "chainsaw") == "motores y maquinaria"
    assert negative_type("aris", "ARIS_BACKGROUND") == "fondo de campo"
    assert negative_type("fsd50k", "Desconocida") == "otros"
    assert "motos" in NEGATIVE_TYPES.values()


def test_confusion_by_negative_type_and_priorities() -> None:
    types = ["motos", "motos", "viento", "viento", "aves", None]
    y = [0, 0, 0, 0, 0, 1]
    scores = [0.9, 0.8, 0.1, 0.6, 0.2, 0.95]
    table = confusion_by_negative_type(types, y, scores, 0.5)
    by = {r["tipo"]: r for r in table}
    assert by["motos"]["fp"] == 2 and by["motos"]["fpr"] == 1.0
    assert by["viento"]["fp"] == 1 and by["viento"]["fpr"] == 0.5
    assert by["aves"]["fp"] == 0
    assert [r["tipo"] for r in table] == ["motos", "viento", "aves"]
    assert recording_priorities(table, top=2) == ["motos", "viento"]
    per_row = confusion_by_negative_type(types, y, scores, [0.95, 0.5, 0.5, 0.5, 0.5, 0.5])
    assert {r["tipo"]: r for r in per_row}["motos"]["fp"] == 1


def test_hard_negative_weights_upweight_top_scoring_training_negatives() -> None:
    y = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1])
    scores = np.array([0.1, 0.9, 0.2, 0.3, 0.8, 0.0, 0.1, 0.2, 0.4, 0.5, 0.9, 0.2])
    w = np.ones(12)
    new, hard = hard_negative_weights(w, y, scores, fraction=0.2, factor=3.0)
    assert hard == [1, 4]
    assert new[1] == new[4] == 3.0 and new[0] == 1.0 and new[10] == 1.0
    assert new is not w and w[1] == 1.0
    assert math.isclose(new.sum(), 16.0)

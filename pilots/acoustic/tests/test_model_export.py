"""H2.5 · Artefacto modelo_hito2.json: esquema, hash propio y vectores dorados (REQ-FUN-027)."""

from __future__ import annotations

import copy
import json

import numpy as np
import pytest

from acoustic_pilot.calibration import apply_calibration
from acoustic_pilot.channel_norm import WINDOW_SAMPLES
from acoustic_pilot.harmonic import HARMONIC_DIM
from acoustic_pilot.model_export import (
    EMBEDDING_DIM,
    GOLDEN_KINDS,
    artifact_sha256,
    build_artifact,
    check_golden,
    golden_input,
    platt_from_logit,
    score_features,
    validate_artifact,
    window_features,
)

pytestmark = pytest.mark.req("REQ-FUN-027", "REQ-LEG-009")


def fake_yamnet(window: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Sustituto determinista de YAMNet (sin TensorFlow): rasgos espectrales simples."""
    spec = np.abs(np.fft.rfft(np.asarray(window, dtype=np.float64), 2046))[:EMBEDDING_DIM]
    emb = spec / (1 + spec.max())
    scores = 1 / (1 + np.exp(-np.linspace(-3, 3, 521) * emb[:521].mean()))
    return scores[None, :], emb[None, :].astype(np.float32)


def _artifact(**over) -> dict:
    rng = np.random.default_rng(0)
    kw = {
        "model": {
            "nombre": "iter6 principal",
            "coef": rng.normal(0, 0.01, EMBEDDING_DIM + HARMONIC_DIM),
            "intercept": -0.3,
            "inlp_direcciones": 12,
        },
        "platt": {"method": "platt", "a": 1.2, "b": -0.4},
        "alert": {"theta_on": 0.7, "theta_off": 0.5},
        "yamnet_info": {"onnx_sha256": "0" * 64, "paridad_max_abs": 3e-6},
        "speech_indices": [0, 1, 2, 3],
        "speech_names": ["Speech", "Child speech, kid speaking", "Conversation", "Narration"],
        "speech_threshold": 0.30,
        "criteria": {"c_loso": {"cumple": False}},
        "predictions_sha256": "a" * 64,
        "record_sha256": "b" * 64,
        "yamnet_fn": fake_yamnet,
    }
    kw.update(over)
    return build_artifact(**kw)


def test_artifact_roundtrips_through_json_and_is_small() -> None:
    art = _artifact()
    data = json.dumps(art, ensure_ascii=False).encode()
    assert len(data) <= 200_000
    back = json.loads(data)
    validate_artifact(back)
    assert check_golden(back, fake_yamnet) <= 1e-9
    assert [g["tipo"] for g in back["vectores_dorados"]] == list(GOLDEN_KINDS)


def test_platt_matches_the_notebook_calibrator() -> None:
    logits = np.linspace(-20, 20, 101)
    raw = 1 / (1 + np.exp(-logits))
    cal = {"method": "platt", "a": 1.3, "b": -0.2}
    np.testing.assert_allclose(
        platt_from_logit(logits, 1.3, -0.2), apply_calibration(cal, raw), atol=1e-12
    )


def test_window_features_pads_and_scores() -> None:
    art = _artifact()
    feats = window_features(np.ones(1000, dtype=np.float32) * 0.01, fake_yamnet, [0, 1])
    assert feats["normalizada"].shape == (WINDOW_SAMPLES,) and feats["armonico"].shape == (8,)
    s = score_features(art, feats["embedding"], feats["armonico"])
    assert 0 < s["prob"] < 1 and 0 < s["prob_cal"] < 1
    with pytest.raises(ValueError):
        window_features(np.zeros(WINDOW_SAMPLES + 1, dtype=np.float32), fake_yamnet, [0])


def test_golden_inputs_are_deterministic() -> None:
    for kind in GOLDEN_KINDS:
        a, b = golden_input(5, kind), golden_input(5, kind)
        assert np.array_equal(a, b) and a.dtype == np.float32 and np.isfinite(a).all()
    with pytest.raises(ValueError):
        golden_input(5, "otro")


def test_reordered_features_or_altered_normalization_break_the_golden_vectors() -> None:
    art = _artifact()
    swapped = copy.deepcopy(art)
    coef = swapped["modelo"]["coef"]
    coef[-1], coef[-2] = coef[-2] + 1.0, coef[-1] - 1.0  # orden de rasgos alterado
    with pytest.raises(ValueError):
        check_golden(swapped, fake_yamnet)

    def shifted_yamnet(window):  # otra «normalización» antes de YAMNet
        return fake_yamnet(np.asarray(window) * 1.5)

    with pytest.raises(ValueError):
        check_golden(art, shifted_yamnet)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda a: a.update(extra=1),
        lambda a: a.pop("vectores_dorados"),
        lambda a: a["modelo"]["coef"].pop(),
        lambda a: a["modelo"].update(intercept=float("nan")),
        lambda a: a["normalizacion"].update(sha256="f" * 64),
        lambda a: a["alerta"].update(theta_off=0.9),
        lambda a: a["calibracion"].update(a=-1.0),
        lambda a: a["voz"].update(indices=[600]),
        lambda a: a["modelo"].update(intercept=0.123),  # el hash propio deja de cuadrar
    ],
)
def test_tampered_artifacts_are_rejected(mutate) -> None:
    art = _artifact()
    mutate(art)
    if "artefacto_sha256" in art and art["artefacto_sha256"] == artifact_sha256(art):
        pytest.fail("la mutación no cambió el contenido")
    with pytest.raises(ValueError):
        validate_artifact(art)

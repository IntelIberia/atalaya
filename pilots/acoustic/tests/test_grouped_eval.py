"""Partición por grupos, umbral en validación y métricas del cuaderno Colab.

El cuaderno incrusta el código de ``acoustic_pilot.grouped_eval``: estos tests cubren
exactamente la lógica que se ejecuta en Colab.
"""

from __future__ import annotations

import ast
import json
import math
from pathlib import Path

import numpy as np
import pytest

from acoustic_pilot import grouped_eval
from acoustic_pilot.grouped_eval import (
    PROVISIONAL_LABEL,
    binary_metrics,
    choose_threshold,
    false_alarms_per_hour,
    group_bootstrap,
    metric_caption,
    split_indices_by_group,
)

PILOT_DIR = Path(__file__).resolve().parents[1]


def _labels_groups(n_groups: int = 24, per_group: int = 1) -> tuple[list[int], list[str]]:
    labels, groups = [], []
    for g in range(n_groups):
        for _ in range(per_group):
            labels.append(int(g % 3 == 0))
            groups.append(f"g{g:02}")
    return labels, groups


# --- Partición -------------------------------------------------------------------------


def test_split_is_deterministic_disjoint_by_group_and_complete() -> None:
    labels, groups = _labels_groups(n_groups=12, per_group=3)
    split = split_indices_by_group(labels, groups, seed=5)
    assert split == split_indices_by_group(labels, groups, seed=5)
    train, validation, test = split
    assert set(train + validation + test) == set(range(len(labels)))
    group_sets = [{groups[i] for i in part} for part in split]
    assert group_sets[0].isdisjoint(group_sets[1])
    assert group_sets[0].isdisjoint(group_sets[2])
    assert group_sets[1].isdisjoint(group_sets[2])
    for part in split:
        assert {labels[i] for i in part} == {0, 1}


def test_split_keeps_shared_group_together() -> None:
    labels, groups = _labels_groups(n_groups=12)
    groups[5] = groups[4]  # p. ej. duplicado exacto con grupo compartido
    labels[5] = labels[4]
    for seed in range(20):
        parts = split_indices_by_group(labels, groups, seed=seed)
        owner = [k for k, part in enumerate(parts) if 4 in part]
        assert owner and 5 in parts[owner[0]]


def test_split_rejects_too_few_groups() -> None:
    with pytest.raises(ValueError, match="seis grupos"):
        split_indices_by_group([0, 1, 0, 1, 0], ["a", "b", "c", "d", "e"], seed=1)


def test_split_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError, match="misma longitud"):
        split_indices_by_group([0, 1], ["a"], seed=1)


# --- Umbral en validación --------------------------------------------------------------


def test_threshold_maximizes_validation_f1_and_prefers_higher_on_tie() -> None:
    y = np.array([0, 0, 1, 1])
    p = np.array([0.1, 0.4, 0.35, 0.8])
    # 0.35 -> F1 0.8 (tp 2, fp 1); 0.8 -> F1 0.667; 0.4 -> F1 0.5.
    assert choose_threshold(y, p) == pytest.approx(0.35)
    separable = choose_threshold(np.array([0, 1, 1]), np.array([0.2, 0.6, 0.9]))
    assert separable == pytest.approx(0.6)


def test_threshold_requires_both_classes() -> None:
    with pytest.raises(ValueError, match="ambas clases"):
        choose_threshold(np.array([1, 1]), np.array([0.2, 0.9]))


# --- Métricas --------------------------------------------------------------------------


def test_binary_metrics_confusion_precision_recall_prauc() -> None:
    y = np.array([0, 0, 1, 1, 1])
    p = np.array([0.9, 0.1, 0.8, 0.7, 0.2])
    m = binary_metrics(y, p, threshold=0.5)
    assert (m["tn"], m["fp"], m["fn"], m["tp"]) == (1, 1, 1, 2)
    assert m["precision"] == pytest.approx(2 / 3)
    assert m["recall"] == pytest.approx(2 / 3)
    # AP: orden 0.9(neg) 0.8(pos) 0.7(pos) 0.2(pos) -> (1/2 + 2/3 + 3/4) / 3
    assert m["pr_auc"] == pytest.approx((1 / 2 + 2 / 3 + 3 / 4) / 3)


def test_binary_metrics_precision_is_nan_without_positive_predictions() -> None:
    m = binary_metrics(np.array([0, 1]), np.array([0.1, 0.2]), threshold=0.5)
    assert math.isnan(m["precision"]) and m["recall"] == 0.0


def test_bootstrap_marks_insufficient_groups() -> None:
    y = np.array([0, 1, 0, 1, 0])
    p = np.array([0.1, 0.9, 0.2, 0.8, 0.3])
    result = group_bootstrap(y, p, ["a", "b", "c", "d", "e"], 0.5, min_groups=10)
    assert result["status"] == "INSUFICIENTE"
    assert result["n_groups"] == 5 and "intervals" not in result


def test_bootstrap_resamples_groups_deterministically() -> None:
    rng = np.random.default_rng(0)
    groups = [f"g{i}" for i in range(30) for _ in range(2)]
    y = np.array([i % 2 for i in range(30) for _ in range(2)])
    p = np.clip(y * 0.6 + rng.uniform(0, 0.5, size=y.size), 0, 1)
    a = group_bootstrap(y, p, groups, 0.5, n_boot=200, seed=3, min_groups=10)
    b = group_bootstrap(y, p, groups, 0.5, n_boot=200, seed=3, min_groups=10)
    assert a == b and a["status"] == "OK" and a["n_groups"] == 30
    point = binary_metrics(y, p, 0.5)
    for name in ("precision", "recall", "pr_auc"):
        lo, hi = a["intervals"][name]
        assert 0.0 <= lo <= hi <= 1.0
        assert lo <= point[name] <= hi


def test_false_alarms_per_hour_not_verified_without_continuous_negative_time() -> None:
    result = false_alarms_per_hour(1, continuous_negative_seconds=10.0, min_hours=24.0)
    assert result["status"] == "NO VERIFICADA" and result["value"] is None
    ok = false_alarms_per_hour(3, continuous_negative_seconds=48 * 3600, min_hours=24.0)
    assert ok["status"] == "OK" and ok["value"] == pytest.approx(3 / 48)


def test_metric_caption_flags_provisional_groups() -> None:
    assert PROVISIONAL_LABEL == "prueba técnica, contaminación entre particiones no descartada"
    assert PROVISIONAL_LABEL in metric_caption(provisional=True)
    assert PROVISIONAL_LABEL not in metric_caption(provisional=False)


# --- Integración con el resto del piloto y con el cuaderno -----------------------------


def test_module_is_self_contained_for_colab_embedding() -> None:
    tree = ast.parse(Path(grouped_eval.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported <= {"__future__", "collections", "math", "random", "numpy", "sklearn"}


def _notebook_code() -> str:
    notebook = json.loads((PILOT_DIR / "Atalaya_YAMNet_Colab.ipynb").read_text(encoding="utf-8"))
    return "\n".join(
        "".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"
    )


def test_notebook_embeds_tested_module_and_drops_clip_split() -> None:
    code = _notebook_code()
    assert Path(grouped_eval.__file__).read_text(encoding="utf-8") in code
    assert "train_test_split" not in code
    assert "import librosa.display" in code
    assert "choose_threshold(y[validation_idx]" in code


def test_notebook_gates_open_only_for_documented_technical_test() -> None:
    # Autorización explícita del usuario 2026-11-11 (DECISIONES-USUARIO.md): puertas abiertas SOLO
    # para la prueba técnica aislada en Colab, con la decisión escrita junto a cada puerta.
    code = _notebook_code()
    for gate in ("SOURCE_INTAKE_DOWNLOAD_APPROVED = True", "TRAINING_ALLOWED = True"):
        assert gate in code
        previas = code.split(gate)[0].splitlines()[-3:]
        assert any("Decisión del usuario 2026-11-11" in ln for ln in previas), gate
    assert "SOLO prueba técnica" in code
    assert "DADS_ENABLED = False" in code
    assert "drive.mount" not in code and "/Users/" not in code

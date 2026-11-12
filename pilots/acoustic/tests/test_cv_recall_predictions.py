"""Iteración 4: partición con split de autores, CV por grupos, umbral por recall, métricas
por fuente y exportación de predicciones con hash recalculable por script independiente."""

from __future__ import annotations

import ast
import hashlib
import math
from pathlib import Path

import numpy as np
import pytest

import recompute_metrics
from acoustic_pilot import predictions
from acoustic_pilot.grouped_eval import (
    binary_metrics,
    choose_threshold_for_recall,
    group_bootstrap,
    group_folds,
    metrics_by_source,
    rotating_folds,
    split_with_preassigned,
)
from acoustic_pilot.predictions import PREDICTION_COLUMNS, predictions_csv


def _data(n_groups: int = 30, per_group: int = 3) -> tuple[list[int], list[str]]:
    labels, groups = [], []
    for g in range(n_groups):
        for _ in range(per_group):
            labels.append(int(g % 3 == 0))
            groups.append(f"g{g:02}")
    return labels, groups


# --- Partición con split preasignado ------------------------------------------------------


def test_preassigned_indices_keep_their_part_and_rest_split_by_group() -> None:
    labels, groups = _data(n_groups=18)
    labels += [1, 1, 0, 1, 0]
    groups += ["aris:d0", "aris:d0", "aris:b0", "aris:d1", "aris:b1"]
    base = len(labels) - 5
    pre = {base: "train", base + 1: "train", base + 2: "train", base + 3: "test", base + 4: "val"}
    train, validation, test = split_with_preassigned(labels, groups, pre, seed=3)
    assert {base, base + 1, base + 2} <= set(train) and base + 3 in test and base + 4 in validation
    assert sorted(train + validation + test) == list(range(len(labels)))
    seen = [{groups[i] for i in part} for part in (train, validation, test)]
    assert not (seen[0] & seen[1] or seen[0] & seen[2] or seen[1] & seen[2])
    assert split_with_preassigned(labels, groups, pre, seed=3) == (train, validation, test)


def test_preassigned_group_cannot_cross_parts_or_mix_with_free_indices() -> None:
    labels, groups = _data(n_groups=12)
    with pytest.raises(ValueError, match="cruza"):
        split_with_preassigned(labels, groups, {0: "train", 1: "test"}, seed=1)
    with pytest.raises(ValueError, match="mezcla"):
        split_with_preassigned(labels, groups, {0: "train"}, seed=1)
    with pytest.raises(ValueError, match="desconocida"):
        split_with_preassigned(labels, groups, {0: "holdout", 1: "holdout", 2: "holdout"}, seed=1)


# --- Validación cruzada por grupos ---------------------------------------------------------


def test_group_folds_keep_groups_whole_balanced_and_deterministic() -> None:
    labels, groups = _data(n_groups=40)
    groups[0:3] = ["big"] * 3
    folds = group_folds(labels, groups, k=5, seed=7)
    assert folds == group_folds(labels, groups, k=5, seed=7)
    assert set(folds) == set(range(5))
    for g in set(groups):
        assert len({folds[i] for i, h in enumerate(groups) if h == g}) == 1
    for f in range(5):
        assert {labels[i] for i, x in enumerate(folds) if x == f} == {0, 1}
    sizes = [folds.count(f) for f in range(5)]
    assert max(sizes) - min(sizes) <= 6


def test_group_folds_rejects_too_few_groups_or_folds_without_both_classes() -> None:
    with pytest.raises(ValueError, match="menos grupos"):
        group_folds([0, 1, 0, 1], ["a", "b", "c", "d"], k=5, seed=0)
    with pytest.raises(ValueError, match="ambas clases"):
        group_folds([0, 0, 0, 0, 0, 1], list("abcdef"), k=5, seed=0)
    with pytest.raises(ValueError, match="tres folds"):
        group_folds([0, 1], ["a", "b"], k=2, seed=0)


def test_rotating_folds_partition_and_never_share_groups() -> None:
    labels, groups = _data(n_groups=25)
    folds = group_folds(labels, groups, k=5, seed=1)
    rounds = rotating_folds(folds, 5)
    assert len(rounds) == 5
    tested = []
    for train, validation, test in rounds:
        assert sorted(train + validation + test) == list(range(len(labels)))
        g = [{groups[i] for i in part} for part in (train, validation, test)]
        assert not (g[0] & g[1] or g[0] & g[2] or g[1] & g[2])
        tested += test
    assert sorted(tested) == list(range(len(labels)))  # cada clip se prueba una sola vez
    with pytest.raises(ValueError):
        rotating_folds((0, 1, 1), 3)


# --- Umbral orientado a recall -------------------------------------------------------------


def test_recall_threshold_is_highest_meeting_target() -> None:
    y = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0])
    p = np.array([0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.2, 0.5, 0.1])
    r = choose_threshold_for_recall(y, p, target_recall=0.9)
    assert r["threshold"] == pytest.approx(0.55)  # 9/10 positivos, sin la falsa alarma de 0.5
    assert r["validation_recall"] == pytest.approx(0.9)
    assert r["validation_precision"] == pytest.approx(1.0)
    full = choose_threshold_for_recall(y, p, target_recall=1.0)
    assert full["threshold"] == pytest.approx(0.2)
    assert full["validation_precision"] == pytest.approx(10 / 11)
    assert "0.90" in r["criterion"]


def test_recall_threshold_validates_inputs() -> None:
    with pytest.raises(ValueError, match="ambas clases"):
        choose_threshold_for_recall(np.array([1, 1]), np.array([0.1, 0.2]))
    with pytest.raises(ValueError, match="target_recall"):
        choose_threshold_for_recall(np.array([0, 1]), np.array([0.1, 0.2]), target_recall=0)


# --- Métricas por fuente con IC por grupos -------------------------------------------------


def test_metrics_by_source_and_total_with_fpr_for_negative_only_sources() -> None:
    rng = np.random.default_rng(0)
    n = 60
    y = np.array([1 if i < 20 else 0 for i in range(n)])
    p = np.clip(y * 0.6 + rng.uniform(0, 0.5, size=n), 0, 1)
    sources = ["aris" if i < 30 else "fsd50k" for i in range(n)]
    groups = [f"{sources[i]}:{i // 2}" for i in range(n)]
    rows = metrics_by_source(y, p, sources, groups, 0.5, n_boot=200, seed=1)
    by = {r["fuente"]: r for r in rows}
    assert list(by) == ["aris", "fsd50k", "TOTAL"]
    assert by["TOTAL"]["n"] == n and by["aris"]["n"] + by["fsd50k"]["n"] == n
    assert math.isnan(by["fsd50k"]["recall"])  # solo negativos
    assert by["fsd50k"]["ic95"]["intervals"]["recall"] is None
    assert by["fsd50k"]["ic95"]["intervals"]["fpr"] is not None
    total = binary_metrics(y, p, 0.5)
    for k in ("tn", "fp", "fn", "tp"):
        assert by["TOTAL"][k] == total[k]
    with pytest.raises(ValueError):
        metrics_by_source(y, p, sources[:-1], groups, 0.5)


def test_bootstrap_interval_per_metric_and_fpr() -> None:
    y = np.zeros(20, dtype=int)
    p = np.linspace(0, 1, 20)
    boot = group_bootstrap(y, p, [f"g{i}" for i in range(20)], 0.5, n_boot=100)
    assert boot["status"] == "OK" and boot["intervals"]["precision"] is not None
    assert boot["intervals"]["recall"] is None
    lo, hi = boot["intervals"]["fpr"]
    assert 0.0 <= lo <= binary_metrics(y, p, 0.5)["fpr"] <= hi <= 1.0


# --- Predicciones exportadas y recálculo independiente ---------------------------------------


def _rows() -> list[dict]:
    rng = np.random.default_rng(3)
    rows = []
    for model in ("yamnet", "mfcc"):
        for i in range(40):
            rows.append(
                {
                    "modelo": model,
                    "esquema": "split",
                    "particion": "test",
                    "fuente": ["aris", "esc10", "fsd50k", "svanstrom"][i % 4],
                    "clip": f"c{i:03}",
                    "grupo": f"g{i // 2}",
                    "dron": int(i % 4 in (0, 3) and i % 3 != 0),
                    "puntuacion": float(rng.uniform()),
                    "umbral": 0.5 if model == "yamnet" else 0.4,
                }
            )
    return rows


def test_predictions_csv_is_deterministic_and_hashed() -> None:
    rows = _rows()
    data, digest = predictions_csv(rows)
    assert digest == hashlib.sha256(data).hexdigest()
    assert predictions_csv(list(reversed(rows))) == (data, digest)
    assert data.decode().splitlines()[0] == ",".join(PREDICTION_COLUMNS)


def test_predictions_csv_rejects_bad_rows() -> None:
    row = _rows()[0]
    with pytest.raises(ValueError, match="columnas"):
        predictions_csv([{**row, "extra": 1}])
    with pytest.raises(ValueError, match="repetida"):
        predictions_csv([row, dict(row)])
    with pytest.raises(ValueError, match="no válidas"):
        predictions_csv([{**row, "puntuacion": float("nan")}])
    with pytest.raises(ValueError, match="no válidas"):
        predictions_csv([{**row, "dron": 2}])
    with pytest.raises(ValueError, match="salto"):
        predictions_csv([{**row, "clip": "a\nb"}])


def test_independent_recompute_matches_notebook_metrics(tmp_path: Path) -> None:
    rows = _rows()
    data, digest = predictions_csv(rows)
    table = recompute_metrics.recompute(data, digest)
    for model in ("yamnet", "mfcc"):
        mine = [r for r in rows if r["modelo"] == model]
        # el CSV guarda 9 decimales: se compara con las mismas puntuaciones redondeadas
        y = np.array([r["dron"] for r in mine])
        p = np.array([round(r["puntuacion"], 9) for r in mine])
        expected = binary_metrics(y, p, mine[0]["umbral"])
        (total,) = [t for t in table if t["modelo"] == model and t["fuente"] == "TOTAL"]
        for k in ("tn", "fp", "fn", "tp"):
            assert total[k] == expected[k]
        assert total["recall"] == pytest.approx(expected["recall"])
        assert total["fpr"] == pytest.approx(expected["fpr"])
    csv_path = tmp_path / "pred.csv"
    csv_path.write_bytes(data)
    out = tmp_path / "m.json"
    assert recompute_metrics.main([str(csv_path), "--sha256", digest, "--json", str(out)]) == 0
    assert out.exists()


def test_recompute_rejects_tampered_csv() -> None:
    data, digest = predictions_csv(_rows())
    tampered = data.replace(b"yamnet", b"yamneT", 1)
    with pytest.raises(ValueError, match="SHA-256"):
        recompute_metrics.recompute(tampered, digest)
    bad = b"a,b\n1,2\n"
    with pytest.raises(ValueError, match="columnas"):
        recompute_metrics.recompute(bad, hashlib.sha256(bad).hexdigest())


def test_recompute_script_is_independent_of_notebook_code() -> None:
    tree = ast.parse(Path(recompute_metrics.__file__).read_text(encoding="utf-8"))
    modules = {
        (n.module or "") if isinstance(n, ast.ImportFrom) else a.name
        for n in ast.walk(tree)
        if isinstance(n, ast.Import | ast.ImportFrom)
        for a in (n.names if isinstance(n, ast.Import) else [n])
    }
    assert not any("acoustic_pilot" in m or m.startswith("numpy") for m in modules)
    src = Path(predictions.__file__).read_text(encoding="utf-8")
    assert "__future__" not in src

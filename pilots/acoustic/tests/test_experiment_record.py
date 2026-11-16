"""Iteración 5 · registro del experimento, predicciones ampliadas y recálculo independiente."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from sklearn.metrics import average_precision_score

import recompute_metrics
from acoustic_pilot.calibration import brier_score, expected_calibration_error
from acoustic_pilot.experiment import (
    canonical_json,
    dependency_versions,
    embedding_cache_key,
    experiment_record,
    inventory_sha256,
    verify_record,
)
from acoustic_pilot.grouped_eval import binary_metrics
from acoustic_pilot.hard_negatives import confusion_by_negative_type
from acoustic_pilot.predictions import EXTENDED_COLUMNS, PREDICTION_COLUMNS, predictions_csv


def test_canonical_json_is_order_independent() -> None:
    a, ha = canonical_json({"b": 1, "a": [1, 2], "c": "ñ"})
    b, hb = canonical_json({"c": "ñ", "a": [1, 2], "b": 1})
    assert a == b and ha == hb == hashlib.sha256(a).hexdigest()


def test_inventory_hash_depends_on_content_not_order() -> None:
    rows = [("aris/x.wav", "a" * 64), ("esc10/y.wav", "b" * 64)]
    assert inventory_sha256(rows) == inventory_sha256(list(reversed(rows)))
    assert inventory_sha256(rows) != inventory_sha256([rows[0], ("esc10/y.wav", "c" * 64)])


def test_dependency_versions_reports_missing_packages() -> None:
    v = dependency_versions(["numpy", "paquete-que-no-existe-atalaya"])
    assert v["numpy"] == np.__version__
    assert v["paquete-que-no-existe-atalaya"] == "no instalado"


def test_cache_key_changes_with_any_input() -> None:
    base = embedding_cache_key("i" * 64, "https://tfhub.dev/google/yamnet/1", 16000, "v5")
    assert len(base) == 16
    assert base != embedding_cache_key("j" * 64, "https://tfhub.dev/google/yamnet/1", 16000, "v5")
    assert base != embedding_cache_key("i" * 64, "https://tfhub.dev/google/yamnet/1", 16000, "v6")


def test_experiment_record_is_self_verifying() -> None:
    rec = experiment_record(
        config={"seed": 1, "near_dup": 0.995},
        data={"inventario_sha256": "a" * 64},
        dependencies={"numpy": "1.26.4"},
        predictions_sha256="p" * 64,
        notebook_code_sha256="n" * 64,
    )
    assert verify_record(rec)
    rec["config"]["seed"] = 2
    assert not verify_record(rec)


# --- Predicciones ampliadas y recálculo independiente -------------------------------------


def _rows(n: int = 120) -> list[dict]:
    rng = np.random.default_rng(11)
    types = ["motos", "viento", "aves"]
    rows = []
    for model in ("ventanas·max_suavizado", "media"):
        for i in range(n):
            y = int(i % 3 == 0)
            raw = float(np.clip(rng.normal(0.65 if y else 0.35, 0.2), 0, 1))
            rows.append(
                {
                    "modelo": model,
                    "esquema": "sgkf5",
                    "particion": f"fold{i % 5}",
                    "fuente": ["aris", "fsd50k", "svanstrom"][i % 3],
                    "clip": f"c{i:03}",
                    "grupo": f"g{i // 3}",
                    "tipo": "dron" if y else types[i % 3 - 1],
                    "dron": y,
                    "puntuacion": raw**1.3,
                    "puntuacion_cruda": raw,
                    "puntuacion_isotonica": round(raw, 1),
                    "umbral": 0.3 + 0.02 * (i % 5),
                }
            )
    return rows


def test_extended_columns_extend_the_base_ones() -> None:
    assert EXTENDED_COLUMNS[: len(PREDICTION_COLUMNS) - 3] == PREDICTION_COLUMNS[:-3]
    assert {"tipo", "puntuacion_cruda", "puntuacion_isotonica"} <= set(EXTENDED_COLUMNS)
    data, _ = predictions_csv(_rows(), columns=EXTENDED_COLUMNS)
    assert data.decode().splitlines()[0] == ",".join(EXTENDED_COLUMNS)
    with pytest.raises(ValueError, match="columnas"):
        predictions_csv(_rows())  # sin columns= se exige el formato base


def test_recompute_extended_matches_tested_functions(tmp_path: Path) -> None:
    rows = _rows()
    data, digest = predictions_csv(rows, columns=EXTENDED_COLUMNS)
    table = recompute_metrics.recompute(data, digest)
    pooled = recompute_metrics.recompute_pooled(data, digest)
    for model in ("ventanas·max_suavizado", "media"):
        mine = [r for r in rows if r["modelo"] == model]
        y = np.array([r["dron"] for r in mine])
        p = np.array([r["puntuacion"] for r in mine])
        raw = np.array([r["puntuacion_cruda"] for r in mine])
        thr = np.array([r["umbral"] for r in mine])
        (tot,) = [t for t in pooled if t["modelo"] == model and t["fuente"] == "TOTAL"]
        pred = p >= thr
        assert tot["tp"] == int(np.sum(pred & (y == 1)))
        assert tot["fp"] == int(np.sum(pred & (y == 0)))
        assert tot["pr_auc"] == pytest.approx(average_precision_score(y, p), abs=1e-9)
        assert tot["ece"] == pytest.approx(expected_calibration_error(y, p), abs=1e-9)
        assert tot["ece_cruda"] == pytest.approx(expected_calibration_error(y, raw), abs=1e-9)
        assert tot["brier"] == pytest.approx(brier_score(y, p), abs=1e-9)
        f0 = [r for r in mine if r["particion"] == "fold0"]
        exp = binary_metrics(
            np.array([r["dron"] for r in f0]),
            np.array([r["puntuacion"] for r in f0]),
            f0[0]["umbral"],
        )
        (row,) = [
            t
            for t in table
            if t["modelo"] == model and t["particion"] == "fold0" and t["fuente"] == "TOTAL"
        ]
        assert (row["tn"], row["fp"], row["fn"], row["tp"]) == tuple(
            exp[k] for k in ("tn", "fp", "fn", "tp")
        )
        by_type = recompute_metrics.recompute_by_type(data, digest)
        expected = confusion_by_negative_type(
            [r["tipo"] for r in mine], y.tolist(), p.tolist(), thr.tolist()
        )
        got = {(t["tipo"], t["fp"], t["n"]) for t in by_type if t["modelo"] == model}
        assert got == {(e["tipo"], e["fp"], e["n"]) for e in expected}


def test_extended_csv_keeps_decisions_of_saturated_scores() -> None:
    """Regresión del ensayo en seco: puntuación 1-1.3e-10 frente a umbral 1-0.9e-10 NO es alarma;
    con 9 decimales ambos valían 1.000000000 y el recálculo contaba una falsa alarma."""
    row = {**_rows(1)[0], "dron": 0, "puntuacion": 1 - 1.3e-10, "umbral": 1 - 0.9e-10}
    data, digest = predictions_csv([row], columns=EXTENDED_COLUMNS)
    (total,) = [t for t in recompute_metrics.recompute(data, digest) if t["fuente"] == "TOTAL"]
    assert (total["tn"], total["fp"]) == (1, 0)


def test_recompute_cli_checks_record(tmp_path: Path) -> None:
    data, digest = predictions_csv(_rows(), columns=EXTENDED_COLUMNS)
    csv_path = tmp_path / "p.csv"
    csv_path.write_bytes(data)
    rec = experiment_record(
        config={"seed": 1},
        data={},
        dependencies={},
        predictions_sha256=digest,
        notebook_code_sha256="n" * 64,
    )
    rec_path = tmp_path / "r.json"
    rec_path.write_text(json.dumps(rec))
    out = tmp_path / "m.json"
    args = [str(csv_path), "--sha256", digest, "--record", str(rec_path), "--json", str(out)]
    assert recompute_metrics.main(args) == 0
    result = json.loads(out.read_text())
    assert {"por_particion", "agregado", "por_tipo"} <= set(result)
    rec["predicciones_csv_sha256"] = "x" * 64
    rec_path.write_text(json.dumps(rec))
    with pytest.raises(ValueError, match="registro"):
        recompute_metrics.main(args)

"""Recálculo independiente de la iteración 6: criterio C-LOSO (ADR 0018), D-6 de referencia y
comprobación de modelo_hito2.json (REQ-FUN-027)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from sklearn.metrics import average_precision_score, roc_auc_score

import recompute_metrics as rm
from acoustic_pilot.experiment import experiment_record
from acoustic_pilot.predictions import EXTENDED_COLUMNS, predictions_csv

pytestmark = pytest.mark.req("REQ-FUN-027")
MODEL = "iter6 · principal"


def _rows(seed: int = 0, *, good: bool = True, sources=("aris", "svanstrom", "salford")):
    rng = np.random.default_rng(seed)
    rows = []
    plan = {s: (200, 0.8 if s == "aris" else 0.5) for s in sources}
    plan.update({"esc10": (100, 0.0), "fsd50k": (150, 0.0)})
    for source, (n, prev) in plan.items():
        for i in range(n):
            y = int(rng.random() < prev)
            score = float(np.clip(rng.normal(0.75 if y else 0.2, 0.15 if good else 0.4), 0, 1))
            rows.append(
                {
                    "modelo": MODEL,
                    "esquema": "loso",
                    "particion": f"sin_{source}",
                    "fuente": source,
                    "clip": f"{source}/{i}.wav",
                    "grupo": f"{source}:{i // 3}",
                    "tipo": "dron" if y else "otro",
                    "dron": y,
                    "puntuacion": score,
                    "puntuacion_cruda": score,
                    "puntuacion_isotonica": score,
                    "umbral": 0.5,
                }
            )
    return rows


def test_roc_auc_matches_sklearn_with_ties() -> None:
    rng = np.random.default_rng(3)
    y = rng.integers(0, 2, 300).tolist()
    p = np.round(rng.random(300), 1).tolist()  # muchos empates
    assert abs(rm._roc_auc(y, p) - roc_auc_score(y, p)) < 1e-12
    assert rm._roc_auc([1, 1], [0.1, 0.2]) is None


def test_c_loso_passes_with_good_scores_and_reports_d6() -> None:
    data, digest = predictions_csv(_rows(), columns=EXTENDED_COLUMNS)
    out = rm.criterion_c_loso(data, digest, MODEL)
    assert out["c_loso"] == "CUMPLE"
    by = {e["fuente_retenida"]: e for e in out["por_fuente"]}
    assert by["aris"]["fuentes_dron_entrenando"] == ["salford", "svanstrom"]
    aris = [r for r in _rows() if r["fuente"] == "aris"]
    ys = [r["dron"] for r in aris]
    ps = [r["puntuacion"] for r in aris]
    assert abs(by["aris"]["roc_auc"] - roc_auc_score(ys, ps)) < 1e-12
    assert abs(out["d6_referencia"]["pr_auc_aris"] - average_precision_score(ys, ps)) < 1e-9
    assert by["fsd50k"]["roc_auc"] is None and by["fsd50k"]["fpr"] <= 0.10


def test_c_loso_fails_with_poor_ordering_even_if_d6_pr_auc_looks_fine() -> None:
    """Con prevalencia 0,8 y puntuaciones casi aleatorias el PR-AUC ronda 0,8 (D-6 «casi»)
    pero el ROC-AUC delata el azar: C-LOSO no se cumple."""
    rows = _rows(good=False)
    rng = np.random.default_rng(11)  # determinista (hash() de str cambia entre procesos)
    for r in rows:
        if r["fuente"] == "aris":
            score = float(rng.random())
            r["puntuacion"] = r["puntuacion_cruda"] = r["puntuacion_isotonica"] = score
    data, digest = predictions_csv(rows, columns=EXTENDED_COLUMNS)
    out = rm.criterion_c_loso(data, digest, MODEL)
    by = {e["fuente_retenida"]: e for e in out["por_fuente"]}
    assert by["aris"]["roc_auc"] < 0.6 and by["aris"]["pr_auc"] > 0.7
    assert by["aris"]["estado"] == "NO CUMPLE" and out["c_loso"] == "NO CUMPLE"


def test_drone_only_source_is_judged_by_recall() -> None:
    rows = _rows()
    for r in rows:
        if r["fuente"] == "salford":
            r["dron"], r["tipo"] = 1, "dron"
            r["puntuacion"] = r["puntuacion_cruda"] = r["puntuacion_isotonica"] = 0.9
    data, digest = predictions_csv(rows, columns=EXTENDED_COLUMNS)
    by = {e["fuente_retenida"]: e for e in rm.criterion_c_loso(data, digest, MODEL)["por_fuente"]}
    assert by["salford"]["roc_auc"] is None and by["salford"]["fpr"] is None
    assert by["salford"]["recall"] == 1.0 and by["salford"]["estado"] == "CUMPLE"
    for r in rows:
        if r["fuente"] == "salford":
            r["puntuacion"] = 0.1
    data, digest = predictions_csv(rows, columns=EXTENDED_COLUMNS)
    by = {e["fuente_retenida"]: e for e in rm.criterion_c_loso(data, digest, MODEL)["por_fuente"]}
    assert by["salford"]["estado"] == "NO CUMPLE"


def test_fold_without_two_drone_sources_is_not_evaluable() -> None:
    data, digest = predictions_csv(_rows(sources=("aris", "svanstrom")), columns=EXTENDED_COLUMNS)
    out = rm.criterion_c_loso(data, digest, MODEL)
    by = {e["fuente_retenida"]: e for e in out["por_fuente"]}
    assert by["aris"]["estado"] == "NO EVALUABLE" and out["c_loso"] == "NO EVALUABLE"


def test_rows_in_a_wrong_fold_or_unknown_model_are_rejected() -> None:
    rows = _rows()
    rows[0]["particion"] = "sin_otra"
    data, digest = predictions_csv(rows, columns=EXTENDED_COLUMNS)
    with pytest.raises(ValueError):
        rm.criterion_c_loso(data, digest, MODEL)
    data, digest = predictions_csv(_rows(), columns=EXTENDED_COLUMNS)
    with pytest.raises(ValueError):
        rm.criterion_c_loso(data, digest, "otro modelo")


def test_cli_checks_record_and_artifact(tmp_path: Path) -> None:
    data, digest = predictions_csv(_rows(), columns=EXTENDED_COLUMNS)
    csv_path = tmp_path / "predicciones.csv"
    csv_path.write_bytes(data)
    record = experiment_record(
        config={},
        data={},
        dependencies={},
        predictions_sha256=digest,
        notebook_code_sha256="0" * 64,
        extra={"modelo_principal": MODEL},
    )
    rec_path = tmp_path / "registro.json"
    rec_path.write_text(json.dumps(record))
    art = {
        "predicciones_csv_sha256": digest,
        "registro_experimento_sha256": record["registro_sha256"],
    }
    body = json.dumps(art, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    import hashlib

    art["artefacto_sha256"] = hashlib.sha256(body).hexdigest()
    art_path = tmp_path / "modelo_hito2.json"
    art_path.write_text(json.dumps(art))
    out = tmp_path / "out.json"
    argv = [
        str(csv_path),
        "--sha256",
        digest,
        "--record",
        str(rec_path),
        "--artifact",
        str(art_path),
        "--criterio",
        "c-loso",
        "--json",
        str(out),
    ]
    assert rm.main(argv) == 0
    assert json.loads(out.read_text())["criterio"]["c_loso"] == "CUMPLE"
    art["predicciones_csv_sha256"] = "f" * 64
    art_path.write_text(json.dumps(art))
    with pytest.raises(ValueError):
        rm.main(argv)

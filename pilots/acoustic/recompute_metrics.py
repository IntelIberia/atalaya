"""Recalcula las métricas del cuaderno desde el CSV de predicciones exportado (ADR 0016).

Implementación independiente (solo stdlib; no importa ``acoustic_pilot`` ni numpy): verifica el
SHA-256 del CSV (y, si se da, el registro del experimento ``modelo_piloto.json``), aplica el
umbral de cada fila y calcula:

- por modelo, esquema, partición y fuente (más TOTAL): matriz de confusión, precision, recall, FPR;
- agregado fuera de fold por modelo y esquema (formato de la iteración 5): además PR-AUC
  (precisión media), ECE (15 bins de igual anchura) de las puntuaciones calibrada, cruda e
  isotónica, y Brier;
- falsas alarmas por tipo de negativo (formato de la iteración 5).

- iteración 6: criterio C-LOSO del ADR 0018 (ROC-AUC por rangos, recall y FPR por fuente
  retenida) con D-6 como referencia, y comprobación del artefacto ``modelo_hito2.json``.

Uso:  uv run python recompute_metrics.py predicciones.csv --sha256 <hash>
          [--record modelo_piloto.json] [--json salida.json]
      uv run python recompute_metrics.py predicciones.csv --sha256 <hash>
          --record registro_iter6.json --artifact modelo_hito2.json --criterio c-loso
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

EXPECTED_COLUMNS = [
    "modelo",
    "esquema",
    "particion",
    "fuente",
    "clip",
    "grupo",
    "dron",
    "puntuacion",
    "umbral",
]
EXTENDED_COLUMNS = [
    "modelo",
    "esquema",
    "particion",
    "fuente",
    "clip",
    "grupo",
    "tipo",
    "dron",
    "puntuacion",
    "puntuacion_cruda",
    "puntuacion_isotonica",
    "umbral",
]
ECE_BINS = 15


def _ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def _rows(data: bytes, expected_sha256: str) -> tuple[list[str], list[dict[str, str]]]:
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha256.strip().lower():
        raise ValueError(f"SHA-256 del CSV distinto: {digest}")
    reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
    if reader.fieldnames not in (EXPECTED_COLUMNS, EXTENDED_COLUMNS):
        raise ValueError(f"columnas inesperadas: {reader.fieldnames}")
    return list(reader.fieldnames), list(reader)


def _counts(rows: list[dict[str, str]]) -> list[int]:
    tn = fp = fn = tp = 0
    for row in rows:
        positive = int(row["dron"]) == 1
        alarm = float(row["puntuacion"]) >= float(row["umbral"])
        if positive and alarm:
            tp += 1
        elif positive:
            fn += 1
        elif alarm:
            fp += 1
        else:
            tn += 1
    return [tn, fp, fn, tp]


def _confusion(key: dict[str, str], counts: list[int]) -> dict[str, Any]:
    tn, fp, fn, tp = counts
    return {
        **key,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "precision": _ratio(tp, tp + fp),
        "recall": _ratio(tp, tp + fn),
        "fpr": _ratio(fp, fp + tn),
    }


def recompute(data: bytes, expected_sha256: str) -> list[dict[str, Any]]:
    """Confusión por modelo, esquema, partición y fuente (más TOTAL)."""
    _, rows = _rows(data, expected_sha256)
    cells: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        for source in (row["fuente"], "TOTAL"):
            cells[(row["modelo"], row["esquema"], row["particion"], source)].append(row)
    names = ("modelo", "esquema", "particion", "fuente")
    return [_confusion(dict(zip(names, k, strict=True)), _counts(cells[k])) for k in sorted(cells)]


def _average_precision(labels: list[int], scores: list[float]) -> float | None:
    """Σ (R_k − R_{k−1}) · P_k sobre umbrales distintos en orden descendente."""
    positives = sum(labels)
    if positives == 0 or positives == len(labels):
        return None
    order = sorted(zip(scores, labels, strict=True), key=lambda t: -t[0])
    ap, tp, fp, k, prev_recall = 0.0, 0, 0, 0, 0.0
    while k < len(order):
        threshold = order[k][0]
        while k < len(order) and order[k][0] == threshold:
            tp += order[k][1]
            fp += 1 - order[k][1]
            k += 1
        recall = tp / positives
        ap += (recall - prev_recall) * tp / (tp + fp)
        prev_recall = recall
    return ap


def _ece(labels: list[int], scores: list[float]) -> float:
    bins: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for y, p in zip(labels, scores, strict=True):
        bins[min(int(p * ECE_BINS), ECE_BINS - 1)].append((y, p))
    total = len(labels)
    err = 0.0
    for members in bins.values():
        acc = sum(y for y, _ in members) / len(members)
        conf = sum(p for _, p in members) / len(members)
        err += len(members) * abs(acc - conf)
    return err / total


def recompute_pooled(data: bytes, expected_sha256: str) -> list[dict[str, Any]]:
    """Predicciones fuera de fold agregadas por modelo y esquema (cada fila con su umbral)."""
    columns, rows = _rows(data, expected_sha256)
    cells: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        for source in (row["fuente"], "TOTAL"):
            cells[(row["modelo"], row["esquema"], source)].append(row)
    out = []
    for key in sorted(cells):
        members = cells[key]
        labels = [int(r["dron"]) for r in members]
        scores = [float(r["puntuacion"]) for r in members]
        entry = _confusion(
            dict(zip(("modelo", "esquema", "fuente"), key, strict=True)), _counts(members)
        )
        entry["pr_auc"] = _average_precision(labels, scores)
        entry["ece"] = _ece(labels, scores)
        entry["brier"] = sum((p - y) ** 2 for y, p in zip(labels, scores, strict=True)) / len(
            labels
        )
        if "puntuacion_cruda" in columns:
            for col, name in (
                ("puntuacion_cruda", "ece_cruda"),
                ("puntuacion_isotonica", "ece_isotonica"),
            ):
                entry[name] = _ece(labels, [float(r[col]) for r in members])
        out.append(entry)
    return out


def recompute_by_type(data: bytes, expected_sha256: str) -> list[dict[str, Any]]:
    """Falsas alarmas por tipo de negativo, por modelo y esquema (iteración 5)."""
    columns, rows = _rows(data, expected_sha256)
    if "tipo" not in columns:
        return []
    cells: dict[tuple[str, str, str], list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        if int(row["dron"]) == 1:
            continue
        cell = cells[(row["modelo"], row["esquema"], row["tipo"])]
        cell[0] += 1
        cell[1] += int(float(row["puntuacion"]) >= float(row["umbral"]))
    return [
        {"modelo": k[0], "esquema": k[1], "tipo": k[2], "n": n, "fp": fp, "fpr": fp / n}
        for k, (n, fp) in sorted(cells.items())
    ]


def check_record(record: dict[str, Any], csv_sha256: str) -> None:
    """El registro debe citar este CSV y su propio hash debe cuadrar (JSON canónico)."""
    body = {k: v for k, v in record.items() if k != "registro_sha256"}
    canon = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canon).hexdigest() != record.get("registro_sha256"):
        raise ValueError("el hash del registro del experimento no cuadra")
    if record.get("predicciones_csv_sha256") != csv_sha256.strip().lower():
        raise ValueError("el registro del experimento cita otro CSV de predicciones")


def _roc_auc(labels: list[int], scores: list[float]) -> float | None:
    """ROC-AUC por rangos (Mann-Whitney), con empates a media de rango."""
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return None
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(scores)
    k = 0
    while k < len(order):
        j = k
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[k]]:
            j += 1
        for t in range(k, j + 1):
            ranks[order[t]] = (k + j) / 2 + 1
        k = j + 1
    rank_sum = sum(r for r, y in zip(ranks, labels, strict=True) if y == 1)
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


# Criterio C-LOSO (ADR 0018) y, como referencia, D-6 (DECISIONES-USUARIO, 2026-11-16).
C_LOSO = {"roc_auc_min": 0.85, "recall_min": 0.50, "fpr_max": 0.10, "fuentes_dron_min": 2}
D6 = {"pr_auc_min": 0.85, "recall_min": 0.50, "fpr_max": 0.10}


def criterion_c_loso(data: bytes, expected_sha256: str, model: str) -> dict[str, Any]:
    """C-LOSO del modelo indicado, solo con el CSV: las fuentes con dron de cada pliegue de
    entrenamiento son las fuentes del CSV con alguna fila dron=1 distintas de la retenida."""
    _, rows = _rows(data, expected_sha256)
    loso = [r for r in rows if r["esquema"] == "loso" and r["modelo"] == model]
    if not loso:
        raise ValueError(f"no hay filas LOSO del modelo {model!r}")
    drone_sources = sorted({r["fuente"] for r in rows if int(r["dron"]) == 1})
    folds: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in loso:
        folds[r["fuente"]].append(r)
    out = []
    for source in sorted(folds):
        members = folds[source]
        partitions = {r["particion"] for r in members}
        if partitions != {f"sin_{source}"}:
            raise ValueError(f"filas de {source} fuera de su pliegue: {sorted(partitions)}")
        labels = [int(r["dron"]) for r in members]
        scores = [float(r["puntuacion"]) for r in members]
        tn, fp, fn, tp = _counts(members)
        entry: dict[str, Any] = {
            "fuente_retenida": source,
            "n": len(members),
            "positivos": tp + fn,
            "fuentes_dron_entrenando": [s for s in drone_sources if s != source],
            "roc_auc": _roc_auc(labels, scores),
            "pr_auc": _average_precision(labels, scores),
            "recall": _ratio(tp, tp + fn),
            "fpr": _ratio(fp, fp + tn),
        }
        checks = []
        if entry["positivos"]:
            if len(entry["fuentes_dron_entrenando"]) < C_LOSO["fuentes_dron_min"]:
                entry["estado"] = "NO EVALUABLE"
            else:
                checks.append(
                    entry["recall"] is not None and entry["recall"] >= C_LOSO["recall_min"]
                )
                # ROC-AUC solo se define si la fuente retenida también tiene negativos; una fuente
                # solo de dron (Salford, DroneAudioSet, Yi-KAIST) se juzga por recall.
                if entry["fpr"] is not None:
                    checks.append(
                        entry["roc_auc"] is not None and entry["roc_auc"] >= C_LOSO["roc_auc_min"]
                    )
        if entry["fpr"] is not None:
            checks.append(entry["fpr"] <= C_LOSO["fpr_max"])
        entry.setdefault("estado", "CUMPLE" if all(checks) else "NO CUMPLE")
        out.append(entry)
    states = {e["estado"] for e in out}
    overall = (
        "CUMPLE"
        if states == {"CUMPLE"}
        else (
            "NO EVALUABLE"
            if "NO EVALUABLE" in states and "NO CUMPLE" not in states
            else "NO CUMPLE"
        )
    )
    by_source = {e["fuente_retenida"]: e for e in out}
    aris, fsd = by_source.get("aris"), by_source.get("fsd50k")
    d6 = None
    if aris and fsd:
        d6 = {
            "pr_auc_aris": aris["pr_auc"],
            "recall_aris": aris["recall"],
            "fpr_fsd50k": fsd["fpr"],
        }
        d6["cumple"] = bool(
            d6["pr_auc_aris"] is not None
            and d6["pr_auc_aris"] >= D6["pr_auc_min"]
            and (d6["recall_aris"] or 0) >= D6["recall_min"]
            and d6["fpr_fsd50k"] is not None
            and d6["fpr_fsd50k"] <= D6["fpr_max"]
        )
    return {"modelo": model, "c_loso": overall, "por_fuente": out, "d6_referencia": d6}


def check_artifact(artifact: dict[str, Any], csv_sha256: str, record: dict | None) -> None:
    """modelo_hito2.json: hash propio y referencias al CSV y al registro del experimento."""
    body = {k: v for k, v in artifact.items() if k != "artefacto_sha256"}
    canon = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canon).hexdigest() != artifact.get("artefacto_sha256"):
        raise ValueError("el hash propio del artefacto no cuadra")
    if artifact.get("predicciones_csv_sha256") != csv_sha256.strip().lower():
        raise ValueError("el artefacto cita otro CSV de predicciones")
    if record is not None and artifact.get("registro_experimento_sha256") != record.get(
        "registro_sha256"
    ):
        raise ValueError("el artefacto cita otro registro del experimento")


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--artifact", type=Path, help="modelo_hito2.json (iteración 6)")
    parser.add_argument("--criterio", choices=["c-loso"], help="criterio del ADR 0018")
    parser.add_argument("--modelo", help="modelo al que se aplica el criterio (principal)")
    args = parser.parse_args(argv)
    data = args.csv.read_bytes()
    record = None
    if args.record:
        record = json.loads(args.record.read_text(encoding="utf-8"))
        check_record(record, args.sha256)
    if args.artifact:
        check_artifact(json.loads(args.artifact.read_text(encoding="utf-8")), args.sha256, record)
    criterion = None
    if args.criterio:
        model = args.modelo or (record or {}).get("modelo_principal")
        if not model:
            parser.error("--criterio necesita --modelo o un registro con modelo_principal")
        criterion = criterion_c_loso(data, args.sha256, model)
    table = recompute(data, args.sha256)
    pooled = recompute_pooled(data, args.sha256)
    by_type = recompute_by_type(data, args.sha256)
    header = "| modelo | esquema | fuente | tn | fp | fn | tp | precision | recall | FPR"
    print(header + " | PR-AUC | ECE |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in pooled:
        print(
            f"| {r['modelo']} | {r['esquema']} | {r['fuente']} | {r['tn']} | {r['fp']} "
            f"| {r['fn']} | {r['tp']} | {_fmt(r['precision'])} | {_fmt(r['recall'])} "
            f"| {_fmt(r['fpr'])} | {_fmt(r['pr_auc'])} | {_fmt(r['ece'])} |"
        )
    if by_type:
        print("\n| modelo | esquema | tipo de negativo | n | fp | FPR |")
        print("|---|---|---|---|---|---|")
        for r in by_type:
            print(
                f"| {r['modelo']} | {r['esquema']} | {r['tipo']} | {r['n']} | {r['fp']} "
                f"| {r['fpr']:.3f} |"
            )
    if criterion:
        print(f"\nCriterio C-LOSO (ADR 0018) · modelo {criterion['modelo']}: {criterion['c_loso']}")
        print(
            "| fuente retenida | n | dron | fuentes de dron entrenando | ROC-AUC | recall | FPR "
            "| estado |"
        )
        print("|---|---|---|---|---|---|---|---|")
        for e in criterion["por_fuente"]:
            print(
                f"| {e['fuente_retenida']} | {e['n']} | {e['positivos']} "
                f"| {', '.join(e['fuentes_dron_entrenando']) or '—'} | {_fmt(e['roc_auc'])} "
                f"| {_fmt(e['recall'])} | {_fmt(e['fpr'])} | {e['estado']} |"
            )
        d6 = criterion["d6_referencia"]
        if d6:
            print(
                f"Referencia D-6: PR-AUC ARIS {_fmt(d6['pr_auc_aris'])}, recall ARIS "
                f"{_fmt(d6['recall_aris'])}, FPR FSD50K {_fmt(d6['fpr_fsd50k'])} -> "
                f"{'cumple' if d6['cumple'] else 'no cumple'} (dependiente de la prevalencia)"
            )
    if args.json:
        result = {"por_particion": table, "agregado": pooled, "por_tipo": by_type}
        if criterion:
            result["criterio"] = criterion
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

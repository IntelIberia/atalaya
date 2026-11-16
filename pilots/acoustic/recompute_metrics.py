"""Recalcula las métricas del cuaderno desde el CSV de predicciones exportado (ADR 0016).

Implementación independiente (solo stdlib; no importa ``acoustic_pilot`` ni numpy): verifica el
SHA-256 del CSV (y, si se da, el registro del experimento ``modelo_piloto.json``), aplica el
umbral de cada fila y calcula:

- por modelo, esquema, partición y fuente (más TOTAL): matriz de confusión, precision, recall, FPR;
- agregado fuera de fold por modelo y esquema (formato de la iteración 5): además PR-AUC
  (precisión media), ECE (15 bins de igual anchura) de las puntuaciones calibrada, cruda e
  isotónica, y Brier;
- falsas alarmas por tipo de negativo (formato de la iteración 5).

Uso:  uv run python recompute_metrics.py predicciones.csv --sha256 <hash>
          [--record modelo_piloto.json] [--json salida.json]
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


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    data = args.csv.read_bytes()
    if args.record:
        check_record(json.loads(args.record.read_text(encoding="utf-8")), args.sha256)
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
    if args.json:
        result = {"por_particion": table, "agregado": pooled, "por_tipo": by_type}
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

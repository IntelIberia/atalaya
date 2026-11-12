"""Recalcula las métricas del cuaderno desde el CSV de predicciones exportado (ADR 0016).

Implementación independiente (solo stdlib; no importa ``acoustic_pilot``): verifica el SHA-256
del CSV, aplica el umbral de cada fila y calcula la matriz de confusión, precision, recall y
tasa de falsos positivos por modelo, esquema, partición y fuente (más TOTAL).

Uso:  uv run python recompute_metrics.py predicciones.csv --sha256 <hash> [--json salida.json]
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


def _ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def recompute(data: bytes, expected_sha256: str) -> list[dict[str, Any]]:
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha256.strip().lower():
        raise ValueError(f"SHA-256 del CSV distinto: {digest}")
    reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
    if reader.fieldnames != EXPECTED_COLUMNS:
        raise ValueError(f"columnas inesperadas: {reader.fieldnames}")
    counts: dict[tuple[str, str, str, str], list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    for row in reader:
        label = int(row["dron"])
        alarm = float(row["puntuacion"]) >= float(row["umbral"])
        cell = (1 if label else 0, 1 if alarm else 0)
        position = {(0, 0): 0, (0, 1): 1, (1, 0): 2, (1, 1): 3}[cell]  # tn, fp, fn, tp
        for source in (row["fuente"], "TOTAL"):
            counts[(row["modelo"], row["esquema"], row["particion"], source)][position] += 1
    table = []
    for key in sorted(counts):
        tn, fp, fn, tp = counts[key]
        table.append(
            {
                "modelo": key[0],
                "esquema": key[1],
                "particion": key[2],
                "fuente": key[3],
                "tn": tn,
                "fp": fp,
                "fn": fn,
                "tp": tp,
                "precision": _ratio(tp, tp + fp),
                "recall": _ratio(tp, tp + fn),
                "fpr": _ratio(fp, fp + tn),
            }
        )
    return table


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    table = recompute(args.csv.read_bytes(), args.sha256)
    print(
        "| modelo | esquema | partición | fuente | tn | fp | fn | tp | precision | recall | FPR |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in table:
        print(
            f"| {r['modelo']} | {r['esquema']} | {r['particion']} | {r['fuente']} | {r['tn']} "
            f"| {r['fp']} | {r['fn']} | {r['tp']} | {_fmt(r['precision'])} "
            f"| {_fmt(r['recall'])} | {_fmt(r['fpr'])} |"
        )
    if args.json:
        args.json.write_text(json.dumps(table, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

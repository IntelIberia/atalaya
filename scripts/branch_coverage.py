"""Puerta de cobertura exclusiva de ramas del código crítico (ADR 0006)."""

import argparse
import json
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("minimum", type=float)
    args = parser.parse_args(argv)
    totals = json.loads(args.report.read_text())["totals"]
    total = totals["num_branches"]
    covered = totals["covered_branches"]
    if not total or not 0 <= covered <= total:
        print("cobertura: informe sin ramas o con contadores inválidos")
        return 1
    percent = covered / total * 100
    print(f"cobertura de ramas: {covered}/{total} = {percent:.2f} %")
    return 0 if percent >= args.minimum else 1


if __name__ == "__main__":
    raise SystemExit(main())

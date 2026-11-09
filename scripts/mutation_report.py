#!/usr/bin/env python3
"""Resume los resultados de mutmut (mutants/<fichero>.meta) en JSON, con el SHA-256 del
fuente para que la evidencia caduque si el código cambia (REQ-NFR-018).

Uso: mutation_report.py --out docs/evidence/FASE-N/mutacion.json scripts/guardrails.py [...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
KILLED, SURVIVED = 1, 0


def tests_digest(root: Path, tests_dir: str = "tests/guardrails") -> str:
    """SHA-256 conjunto de los tests de mutación: si se debilitan, la evidencia caduca."""
    h = hashlib.sha256()
    for f in sorted((root / tests_dir).rglob("*.py")):
        h.update(f.relative_to(root).as_posix().encode() + b"\0" + f.read_bytes())
    return h.hexdigest()


def report(root: Path, rel: str) -> dict[str, Any]:
    meta = json.loads((root / "mutants" / f"{rel}.meta").read_text(encoding="utf-8"))
    codes: dict[str, int | None] = meta["exit_code_by_key"]
    run = {k: v for k, v in codes.items() if v is not None}
    killed = sum(1 for v in run.values() if v == KILLED)
    survivors = sorted(k for k, v in run.items() if v == SURVIVED)
    total = len(run)
    return {
        "sha256": hashlib.sha256((root / rel).read_bytes()).hexdigest(),
        "tests_sha256": tests_digest(root),
        "total": total,
        "killed": killed,
        "survived": len(survivors),
        "other": total - killed - len(survivors),
        "score": killed / total if total else 0.0,
        "survivors": survivors,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("files", nargs="+")
    args = ap.parse_args(argv)
    data = {rel: report(ROOT, rel) for rel in args.files}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for rel, r in data.items():
        print(f"mutación {rel}: {r['killed']}/{r['total']} = {r['score']:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

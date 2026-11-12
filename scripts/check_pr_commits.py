#!/usr/bin/env python3
"""Higiene de historia de los PR: ningún commit WIP ni «sin verificar» llega a main.

Lee los asuntos (`git log --format=%s RANGO`) y falla (exit 1) si alguno contiene «wip»
(sin distinguir mayúsculas) o «sin verificar». Un error al leer el rango también falla
(exit 2): fallo cerrado. Los PR se fusionan con squash o con commits limpios (CLAUDE.md, Flujo).

Uso: python3 -I scripts/check_pr_commits.py --range "origin/main..HEAD"
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

PROHIBIDO = re.compile(r"wip|sin verificar", re.IGNORECASE)


def offending(subjects: list[str]) -> list[str]:
    """Asuntos de commit que delatan trabajo en curso o sin verificar."""
    return [s for s in subjects if PROHIBIDO.search(s)]


def subjects_in_range(rango: str) -> list[str]:
    """Asuntos de los commits del rango (falla si git no puede resolverlo)."""
    out = subprocess.run(
        ["git", "log", "--format=%s", rango, "--"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in out.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--range", required=True, dest="rango", help="p. ej. origin/main..HEAD")
    args = ap.parse_args(argv)
    try:
        subjects = subjects_in_range(args.rango)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"check_pr_commits: no se pudo leer el rango {args.rango!r}: {exc}", file=sys.stderr)
        return 2
    malos = offending(subjects)
    if malos:
        print("check_pr_commits: commits WIP o sin verificar en el PR (squash o commits limpios):")
        for s in malos:
            print(f"  - {s}")
        return 1
    print(f"check_pr_commits: OK ({len(subjects)} commits)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

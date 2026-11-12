#!/usr/bin/env python3
"""Higiene de historia de los PR: ningún commit WIP ni «sin verificar» llega a main.

Lee los asuntos (`git log --format=%s RANGO`) y falla (exit 1) si alguno lleva la marca «wip»
(palabra suelta) o «sin verificar» como marca, no como mención. Un error al leer el rango falla
(exit 2): fallo cerrado. Los PR se fusionan con squash o con commits limpios (CLAUDE.md, Flujo).

Uso: python3 -I scripts/check_pr_commits.py --range "origin/main..HEAD"
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

# Se buscan MARCAS, no menciones: el commit que introduce esta regla habla de commits
# «sin verificar» y no debe bloquearse a sí mismo.
MARCAS = (
    re.compile(r"\bwip\b", re.IGNORECASE),  # «wip:», «WIP(fase1)», «[Wip]»; no «swipe»
    re.compile(r"[(\[]\s*sin verificar\s*[)\]]", re.IGNORECASE),  # «(sin verificar)»
    re.compile(r"^[^:]*:\s*sin verificar\b", re.IGNORECASE),  # «fix: sin verificar…»
    re.compile(r"SIN VERIFICAR"),  # en mayúsculas es siempre una marca
)


def offending(subjects: list[str]) -> list[str]:
    """Asuntos de commit marcados como trabajo en curso o sin verificar."""
    return [s for s in subjects if any(m.search(s) for m in MARCAS)]


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

#!/usr/bin/env python3
"""Licencias de dependencias (REQ-LEG-016, G-12). Producto propietario: las dependencias de
EJECUCIÓN (las que se distribuyen) no pueden tener copyleft fuerte (GPL/AGPL) ni licencia
desconocida, salvo ADR. Las de desarrollo se informan pero no bloquean.

Uso: uv run python -m scripts.license_check
"""

from __future__ import annotations

import importlib.metadata as md
import re
import subprocess
import sys
from collections.abc import Callable

STRONG = re.compile(r"\bA?GPL\b|\bA?GPLv\d|GNU (?:Affero )?General Public License", re.IGNORECASE)
WEAK = re.compile(r"\bLGPL|Lesser General Public", re.IGNORECASE)


def is_strong_copyleft(text: str) -> bool:
    return bool(STRONG.search(text)) and not WEAK.search(text)


def parse_requirements(text: str) -> list[str]:
    names = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "-", "--")):
            continue
        name = re.split(r"[=<>!~;\[ \\]", line, maxsplit=1)[0]
        if name:
            names.append(name.lower().replace("_", "-"))
    return names


NOT_INSTALLED = "(no instalado en esta plataforma)"


def license_of(name: str) -> str:
    try:
        meta = md.metadata(name)
    except md.PackageNotFoundError:
        return NOT_INSTALLED
    parts = [meta.get("License-Expression") or "", meta.get("License") or ""]
    parts += [c for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
    return " | ".join(p for p in parts if p and p.strip() not in {"UNKNOWN"})


def evaluate(names: list[str], lookup: Callable[[str], str]) -> list[tuple[str, str]]:
    blocked = []
    for n in names:
        lic = lookup(n)
        if not lic.strip():
            blocked.append((n, "(desconocida)"))
        elif is_strong_copyleft(lic):
            blocked.append((n, lic))
    return blocked


def _export(dev: bool) -> list[str]:
    args = ["uv", "export", "--frozen", "--no-hashes", "--no-emit-project"]
    args += ["--only-dev"] if dev else ["--no-dev"]
    out = subprocess.run(args, capture_output=True, text=True, check=True).stdout
    return parse_requirements(out)


def main() -> int:
    runtime, dev = _export(dev=False), _export(dev=True)
    blocked = evaluate(runtime, license_of)
    print(f"licencias: {len(runtime)} dependencias de ejecución, {len(dev)} de desarrollo")
    for n in dev:
        lic = license_of(n)
        if not lic or lic == NOT_INSTALLED or is_strong_copyleft(lic):
            print(f"  aviso (desarrollo, no se distribuye): {n}: {lic or '(desconocida)'}")
    for n, lic in blocked:
        print(f"  BLOQUEADA (ejecución): {n}: {lic}", file=sys.stderr)
    print("licencias: OK" if not blocked else "licencias: FALLO")
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())

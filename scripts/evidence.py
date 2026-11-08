#!/usr/bin/env python3
"""Paquete de evidencias de una fase (MEGAPROMPT <verificacion_exhaustiva> §5).

  evidence.py --fase N            ejecuta las verificaciones de cierre, guarda sus salidas en
                                  docs/evidence/FASE-N/ y escribe MANIFEST.sha256
  evidence.py --manifest DIR      solo (re)escribe el manifiesto de DIR
  evidence.py --verify DIR        comprueba el manifiesto (exit 1 si algo no cuadra)

El manifiesto incluye el commit exacto y si el árbol de trabajo estaba limpio.
"""

from __future__ import annotations

import argparse
import hashlib
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = "MANIFEST.sha256"


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return r.stdout.strip()


def _header(repo: Path) -> str:
    when = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"# commit: {_git(repo, 'rev-parse', 'HEAD')} · fecha UTC: {when}"


def _files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*") if p.is_file() and p.name != MANIFEST)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(directory: Path, repo: Path = ROOT) -> Path:
    clean = _git(repo, "status", "--porcelain") == ""
    lines = [
        _header(repo),
        f"# árbol de trabajo limpio: {'sí' if clean else 'no'}",
    ]
    lines += [f"{_sha256(p)}  {p.relative_to(directory).as_posix()}" for p in _files(directory)]
    out = directory / MANIFEST
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def verify_manifest(directory: Path) -> list[str]:
    path = directory / MANIFEST
    if not path.exists():
        return [f"no existe {MANIFEST}"]
    listed: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            digest, name = line.split("  ", 1)
            listed[name] = digest
    problems = []
    present = {p.relative_to(directory).as_posix(): p for p in _files(directory)}
    for name, digest in listed.items():
        if name not in present:
            problems.append(f"falta: {name}")
        elif _sha256(present[name]) != digest:
            problems.append(f"modificado: {name}")
    problems += [f"no listado: {n}" for n in sorted(set(present) - set(listed))]
    return problems


def capture(argv: list[str], out: Path, repo: Path = ROOT) -> int:
    """Ejecuta argv SIN shell y guarda cabecera, comando, salida y código de salida."""
    r = subprocess.run(argv, cwd=repo, capture_output=True, text=True, check=False)
    out.write_text(
        f"{_header(repo)}\n$ {shlex.join(argv)}\n{r.stdout}{r.stderr}exit={r.returncode}\n",
        encoding="utf-8",
    )
    return r.returncode


def closing_commands(fase: str) -> dict[str, list[str]]:
    trace_out = f"docs/evidence/FASE-{fase}/TRAZABILIDAD.md"
    return {
        "make-check.txt": ["make", "check"],
        "make-regress.txt": ["make", "regress"],
        "trazabilidad.txt": [
            *("uv", "run", "--frozen", "python", "-m", "scripts.traceability"),
            *("--fase", fase, "--out", trace_out),
        ],
        "clon-limpio.txt": ["scripts/verify_clean_clone.sh"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Paquete de evidencias")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--fase")
    g.add_argument("--manifest", type=Path)
    g.add_argument("--verify", type=Path)
    args = ap.parse_args(argv)

    if args.verify is not None:
        problems = verify_manifest(args.verify)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print(f"evidence: manifiesto {'OK' if not problems else 'con problemas'}")
        return 1 if problems else 0
    if args.manifest is not None:
        print(f"evidence: {write_manifest(args.manifest)}")
        return 0

    directory = ROOT / "docs" / "evidence" / f"FASE-{args.fase}"
    directory.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name, command in closing_commands(args.fase).items():
        rc = capture(command, directory / name)
        print(f"evidence: {name:<18} exit={rc}")
        failures += rc != 0
    write_manifest(directory)
    print(f"evidence: manifiesto escrito; verificaciones con fallo: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

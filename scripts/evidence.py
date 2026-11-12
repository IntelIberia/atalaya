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
import re
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = "MANIFEST.sha256"


def _closed_phase_directories(repo: Path) -> set[Path]:
    registry = repo / "docs" / "requirements" / "FASES-CERRADAS.txt"
    directories: set[Path] = set()
    for raw_line in registry.read_text(encoding="utf-8").splitlines():
        phase = raw_line.split("#", 1)[0].strip()
        if not phase:
            continue
        if not re.fullmatch(r"-?\d+", phase):
            raise ValueError(f"fase cerrada inválida en {registry}: {phase!r}")
        directories.add((repo / "docs" / "evidence" / f"FASE-{phase}").resolve())
    return directories


def _write_allowed(directory: Path, repo: Path) -> bool:
    try:
        closed = _closed_phase_directories(repo)
    except (OSError, ValueError) as exc:
        print(f"evidence: registro de fases cerradas no válido: {exc}", file=sys.stderr)
        return False
    target = directory.resolve()
    if any(target == phase_dir or phase_dir in target.parents for phase_dir in closed):
        print(f"evidence: fase cerrada, paquete inmutable: {directory}", file=sys.stderr)
        return False
    return True


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return r.stdout.strip()


def _header(repo: Path) -> str:
    when = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"# commit: {_git(repo, 'rev-parse', 'HEAD')} · fecha UTC: {when}"


def _files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*") if p.is_file() and p != directory / MANIFEST)


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
    problems = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line and not line.startswith("#"):
            match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
            if match is None:
                problems.append(f"línea {number}: formato de manifiesto inválido")
                continue
            digest, name = match.groups()
            if Path(name).is_absolute() or ".." in Path(name).parts:
                problems.append(f"línea {number}: ruta fuera del paquete")
                continue
            if name in listed:
                problems.append(f"duplicado: {name}")
            listed[name] = digest
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
            *("--fase", fase, "--out", trace_out, "--require-integration"),
            *("--junit", "reports/junit.xml", "--junit", "reports/junit-integracion.xml"),
        ],
        "clon-limpio.txt": ["scripts/verify_clean_clone.sh"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Paquete de evidencias")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--fase", type=int)
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
        if not _write_allowed(args.manifest, ROOT):
            return 1
        print(f"evidence: {write_manifest(args.manifest)}")
        return 0

    directory = ROOT / "docs" / "evidence" / f"FASE-{args.fase}"
    if not _write_allowed(directory, ROOT):
        return 1
    directory.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name, command in closing_commands(str(args.fase)).items():
        rc = capture(command, directory / name)
        print(f"evidence: {name:<18} exit={rc}")
        failures += rc != 0
    write_manifest(directory)
    print(f"evidence: manifiesto escrito; verificaciones con fallo: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

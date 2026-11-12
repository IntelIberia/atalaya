"""Valida el destino de una medición nueva para no reescribir fases cerradas."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLOSED = ROOT / "docs/requirements/FASES-CERRADAS.txt"


def closed_phases(closed_path: Path = CLOSED) -> set[int]:
    result: set[int] = set()
    for raw in closed_path.read_text(encoding="utf-8").splitlines():
        phase = raw.partition("#")[0].strip()
        if not phase:
            continue
        if not re.fullmatch(r"-1|0|[1-9][0-9]*", phase):
            raise ValueError(f"fase cerrada inválida: {phase!r}")
        result.add(int(phase))
    return result


def active_phase(closed_path: Path = CLOSED) -> str:
    """Siguiente fase tras la última cerrada, también después de cerrar FASE-1."""
    return str(max(closed_phases(closed_path) | {-1}) + 1)


def validate_target(phase: str, legacy_phase: str, closed_path: Path = CLOSED) -> str:
    if legacy_phase:
        raise ValueError("FASE= ya no selecciona mutación; usa MUTATION_FASE=N")
    if not re.fullmatch(r"0|[1-9][0-9]*", phase):
        raise ValueError("MUTATION_FASE debe ser un número de fase no negativo")
    if int(phase) in closed_phases(closed_path):
        raise ValueError(f"fase {phase} cerrada; evidencia inmutable")
    current = active_phase(closed_path)
    if phase != current:
        raise ValueError(f"fase activa {current}; no se puede escribir mutación en FASE-{phase}")
    return phase


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--fase")
    target.add_argument("--current", action="store_true")
    parser.add_argument("--legacy-fase", default="")
    args = parser.parse_args(argv)
    try:
        if args.current:
            print(active_phase())
            return 0
        phase = validate_target(args.fase, args.legacy_fase)
    except (OSError, ValueError) as exc:
        print(f"mutación: destino no válido: {exc}", file=sys.stderr)
        return 1
    print(f"mutación: destino FASE-{phase} abierto")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

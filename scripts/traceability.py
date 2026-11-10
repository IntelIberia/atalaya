#!/usr/bin/env python3
"""Trazabilidad requisito → tests → resultado (REQ-NFR-014, REQ-SEC-003).

Cruza docs/requirements/REQUIREMENTS.md con el JUnit XML de pytest (propiedades
`req` añadidas por tests/conftest.py desde @pytest.mark.req) y con
docs/requirements/FASES-CERRADAS.txt. Genera docs/requirements/TRAZABILIDAD.md.

Falla (exit 1) si:
  - un requisito MUST de una fase cerrada no tiene ningún test en verde, o tiene alguno en
    rojo (salvo bloqueo **B** aprobado en la especificación, sin tests);
  - un test cita un ID de requisito que no existe;
  - falta el JUnit XML.

La fase de un requisito es la PRIMERA que menciona su columna Fase (p. ej. «9 (guardarraíles: 0)»
→ 0): desde que se cierra esa fase, el requisito necesita al menos un test en verde.

Uso: traceability.py [--fase N ...] (trata N como cerrada; para comprobar antes de cerrar)
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from defusedxml import ElementTree as ET

from scripts import integration_evidence

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REQS = ROOT / "docs/requirements/REQUIREMENTS.md"
DEFAULT_JUNIT = ROOT / "reports/junit.xml"
INTEGRATION_JUNIT = ROOT / "reports/junit-integracion.xml"
DEFAULT_CLOSED = ROOT / "docs/requirements/FASES-CERRADAS.txt"
DEFAULT_OUT = ROOT / "docs/requirements/TRAZABILIDAD.md"

ROW_RE = re.compile(r"^\| (REQ-(?:FUN|NFR|LEG|SEC|PRIV)-\d{3}) \|")
NUM_RE = re.compile(r"(?<![\d-])-?\d+")


@dataclass(frozen=True)
class Requirement:
    rid: str
    priority: str
    phase: int | None
    blocked: bool


@dataclass
class Result:
    requirements: list[Requirement]
    closed: set[int]
    passed: dict[str, int] = field(default_factory=dict)
    failed: dict[str, int] = field(default_factory=dict)
    unknown_ids: set[str] = field(default_factory=set)
    gaps: list[str] = field(default_factory=list)

    @property
    def failing(self) -> set[str]:
        return set(self.failed)

    @property
    def ok(self) -> bool:
        return not self.gaps and not self.unknown_ids


def first_phase(cell: str) -> int | None:
    nums = [int(n) for n in NUM_RE.findall(cell)]
    return min(nums) if nums else None


def parse_requirements(path: Path) -> list[Requirement]:
    reqs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not ROW_RE.match(line):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        reqs.append(Requirement(cols[0], cols[1], first_phase(cols[5]), "**B**" in line))
    return reqs


def parse_closed(path: Path) -> set[int]:
    closed = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        token = raw.split("#", 1)[0].strip()
        if token:
            closed.add(int(token))
    return closed


def parse_junit(paths: Path | list[Path]) -> tuple[dict[str, int], dict[str, int]]:
    passed: dict[str, int] = {}
    failed: dict[str, int] = {}
    for path in [paths] if isinstance(paths, Path) else paths:
        _parse_one(path, passed, failed)
    return passed, failed


def _parse_one(path: Path, passed: dict[str, int], failed: dict[str, int]) -> None:
    root = ET.parse(path).getroot()
    if root is None:
        raise ValueError(f"JUnit XML vacío: {path}")
    for case in root.iter("testcase"):
        ids = [p.get("value", "") for p in case.iter("property") if p.get("name") == "req"]
        if case.find("skipped") is not None:
            continue
        bad = case.find("failure") is not None or case.find("error") is not None
        target = failed if bad else passed
        for rid in ids:
            target[rid] = target.get(rid, 0) + 1


def evaluate(
    req_path: Path,
    junit_path: Path | list[Path],
    closed_path: Path,
    extra_closed: list[int] | None = None,
) -> Result:
    reqs = parse_requirements(req_path)
    closed = parse_closed(closed_path) | set(extra_closed or [])
    passed, failed = parse_junit(junit_path)
    res = Result(reqs, closed, passed, failed)
    known = {r.rid for r in reqs}
    res.unknown_ids = (set(passed) | set(failed)) - known
    for r in reqs:
        if r.priority != "MUST" or r.phase is None or r.phase not in closed:
            continue
        if r.rid in failed or (r.rid not in passed and not r.blocked):
            res.gaps.append(r.rid)
    return res


def _status(res: Result, r: Requirement) -> tuple[str, str]:
    n_ok, n_bad = res.passed.get(r.rid, 0), res.failed.get(r.rid, 0)
    result = "rojo" if n_bad else ("verde" if n_ok else "sin tests")
    if r.rid in res.gaps:
        state = "HUECO"
    elif r.phase is not None and r.phase in res.closed and r.priority == "MUST":
        state = "BLOQUEADO (B)" if result == "sin tests" else "OK"
    else:
        state = "pendiente (fase abierta)" if result == "sin tests" else "en curso"
    return result, state


def render(res: Result) -> str:
    lines = [
        "# Trazabilidad requisito → tests",
        "",
        "Generado por `scripts/traceability.py` (no editar a mano). "
        f"Fases tratadas como cerradas: {sorted(res.closed)}.",
        "",
        "| Requisito | Prio | Fase | Tests | Resultado | Estado |",
        "|---|---|---|---|---|---|",
    ]
    for r in res.requirements:
        n = res.passed.get(r.rid, 0) + res.failed.get(r.rid, 0)
        result, state = _status(res, r)
        phase = "" if r.phase is None else str(r.phase)
        lines.append(f"| {r.rid} | {r.priority} | {phase} | {n} | {result} | {state} |")
    lines += ["", f"Huecos: {len(res.gaps)} · IDs desconocidos en tests: {len(res.unknown_ids)}"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Trazabilidad requisito → tests")
    ap.add_argument("--requirements", type=Path, default=DEFAULT_REQS)
    ap.add_argument("--junit", type=Path, action="append", default=None)
    ap.add_argument("--closed", type=Path, default=DEFAULT_CLOSED)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--fase", type=int, action="append", default=[])
    ap.add_argument("--require-integration", action="store_true")
    args = ap.parse_args(argv)

    junits = args.junit or [DEFAULT_JUNIT] + (
        [INTEGRATION_JUNIT] if INTEGRATION_JUNIT.exists() else []
    )
    missing = [j for j in junits if not j.exists()]
    if missing:
        print(f"traceability: no existe {missing[0]}; ejecuta antes los tests", file=sys.stderr)
        return 1
    integration = [p for p in junits if p.name == INTEGRATION_JUNIT.name]
    if args.require_integration and not integration:
        print("traceability: falta evidencia de integración", file=sys.stderr)
        return 1
    for path in integration:
        if not integration_evidence.verify(path):
            print("traceability: integración ausente, fallida u obsoleta", file=sys.stderr)
            return 1
    res = evaluate(args.requirements, junits, args.closed, args.fase)
    print(f"traceability: informes JUnit: {[j.name for j in junits]}")
    out = args.out if args.out is not None else DEFAULT_OUT
    out.write_text(render(res), encoding="utf-8")
    must_closed = [r for r in res.requirements if r.priority == "MUST" and r.phase in res.closed]
    print(
        f"traceability: fases cerradas {sorted(res.closed)}; MUST en ellas: {len(must_closed)}; "
        f"huecos: {len(res.gaps)}; IDs desconocidos: {len(res.unknown_ids)}"
    )
    for g in res.gaps:
        print(f"  HUECO {g}", file=sys.stderr)
    for u in sorted(res.unknown_ids):
        print(f"  ID DESCONOCIDO en tests: {u}", file=sys.stderr)
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())

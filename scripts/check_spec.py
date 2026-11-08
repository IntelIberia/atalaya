#!/usr/bin/env python3
"""Verificación de la especificación (FASE -1).

Comprueba:
  1. Requisitos: IDs únicos y bien formados, prioridad válida; todo MUST con
     criterio de aceptación, método (T/A/I/D) y fase; al menos un MUST por categoría.
  2. Casos de uso: cada CU de docs/SPEC.md referencia >= 1 requisito existente.
  3. Cobertura: todo requisito está referenciado por algún caso de uso.
  4. Referencias: todo REQ-… citado en cualquier documento existe.
  5. Correspondencia con el MEGAPROMPT: las 7 restricciones legales, los 6 principios
     y los 9 requisitos no funcionales iniciales tienen fila y requisitos existentes.
  6. Estructura: secciones obligatorias de la SPEC, los siete roles y las categorías
     de riesgo exigidas.
  7. Legal: toda línea que mencione un término sensible (capacidad ofensiva, TX,
     demodulación, persistencia de audio, atribución, datos de pilotos) tiene que
     estar en la lista blanca revisada por una persona (scripts/legal_allowlist.txt).
     Una mención nueva o modificada hace fallar la verificación hasta que se revise.

Uso:
  python3 -I scripts/check_spec.py            # verificación
  python3 -I scripts/check_spec.py --propose  # imprime las menciones no revisadas en
                                              # formato de lista blanca (para revisar
                                              # a mano; nunca se añaden solas)

Solo biblioteca estándar. Sale con código 1 si alguna comprobación falla.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent

REQ_REL = "docs/requirements/REQUIREMENTS.md"
SPEC_REL = "docs/SPEC.md"
RISK_REL = "docs/RIESGOS.md"
ALLOWLIST_REL = "scripts/legal_allowlist.txt"
SCANNED_REL = [
    SPEC_REL,
    REQ_REL,
    "docs/PLAN-MAESTRO-DE-PRUEBAS.md",
    RISK_REL,
    "docs/requirements/ENTREVISTA-FASE--1.md",
]

ID_RE = re.compile(r"^REQ-(FUN|NFR|LEG|SEC|PRIV)-\d{3}$")
REF_RE = re.compile(r"REQ-(?:FUN|NFR|LEG|SEC|PRIV)-\d{3}")
METHOD_RE = re.compile(r"^[TAID](\+[TAID])*$")
PRIORITIES = {"MUST", "SHOULD", "COULD"}
CATEGORIES = ("FUN", "NFR", "LEG", "SEC", "PRIV")

REQUIRED_ORIGINS = (
    [f"LEGAL-{i}" for i in range(1, 8)]
    + [f"PRINCIPIO-{i}" for i in range(1, 7)]
    + [
        "NFR-LATENCIA",
        "NFR-NODO-CAIDO",
        "NFR-DETECCION",
        "NFR-LOCALIZACION",
        "NFR-PREDICCION",
        "NFR-DISPONIBILIDAD",
        "NFR-SIN-CONEXION",
        "NFR-RETENCION",
        "NFR-ACCESIBILIDAD",
    ]
)
REQUIRED_SPEC_SECTIONS = (
    "Visión",
    "Alcance",
    "Fuera de alcance",
    "Actores y roles",
    "Casos de uso",
    "Estimación por fases",
)
REQUIRED_ROLES = (
    "Vigilante",
    "Supervisor",
    "Operador SOC",
    "FCSE",
    "Analista",
    "Administrador",
    "Auditor",
)
REQUIRED_RISK_CATEGORIES = ("Legal", "Técnico", "Datos", "Hardware", "Negocio", "Reputación")

SENSITIVE = re.compile(
    r"neutrali[zc]|inhib|interf(?:er|ier|ir)|jamm|suplant|desautentic|deauth|"
    r"toma\w* (?:de|el) control|takeover|spoof|armamento|"
    r"transmi|\bTX\b|emisi[oó]n|\bemit|demodul|droneid|"
    r"persist\w* (?:el |de |del )?audio|audio\w* (?:a|en) disco|"
    r"atribuci[oó]n autom|nacionalidad|datos de (?:los )?pilotos|posici[oó]n del piloto",
    re.IGNORECASE,
)


def line_key(rel: str, line: str) -> str:
    norm = " ".join(line.split())
    return hashlib.sha256(f"{rel}\n{norm}".encode()).hexdigest()


def load_allowlist(root: Path) -> set[str]:
    path = root / ALLOWLIST_REL
    if not path.exists():
        return set()
    keys = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw and not raw.startswith("#"):
            keys.add(raw.split()[0])
    return keys


def parse_requirements(root: Path, errors: list[str]) -> dict[str, list[str]]:
    reqs: dict[str, list[str]] = {}
    for n, line in enumerate((root / REQ_REL).read_text(encoding="utf-8").splitlines(), 1):
        if not line.startswith("| REQ-"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) != 7:
            errors.append(f"REQUIREMENTS.md:{n}: {len(cols)} columnas (se esperaban 7)")
            continue
        rid, prio, desc, criterio, metodo, fase, _just = cols
        if not ID_RE.match(rid):
            errors.append(f"REQUIREMENTS.md:{n}: ID mal formado: {rid}")
        if rid in reqs:
            errors.append(f"REQUIREMENTS.md:{n}: ID duplicado: {rid}")
        if prio not in PRIORITIES:
            errors.append(f"{rid}: prioridad no válida: {prio}")
        if not desc:
            errors.append(f"{rid}: sin descripción")
        if prio == "MUST":
            if not criterio:
                errors.append(f"{rid}: MUST sin criterio de aceptación")
            if not METHOD_RE.match(metodo):
                errors.append(f"{rid}: MUST sin método válido (T/A/I/D): '{metodo}'")
            if not fase:
                errors.append(f"{rid}: MUST sin fase")
        reqs[rid] = cols
    for cat in CATEGORIES:
        if not any(r.split("-")[1] == cat and c[1] == "MUST" for r, c in reqs.items()):
            errors.append(f"Categoría {cat} sin ningún requisito MUST")
    return reqs


def parse_use_cases(root: Path, reqs: dict[str, list[str]], errors: list[str]) -> dict[str, set[str]]:
    cus: dict[str, set[str]] = {}
    current: str | None = None
    for line in (root / SPEC_REL).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\*\*(CU-\d{2})\b", line)
        if m:
            current = m.group(1)
            if current in cus:
                errors.append(f"SPEC.md: caso de uso duplicado {current}")
            cus[current] = set()
            continue
        if current and line.startswith("**Requisitos:**"):
            cus[current] = set(REF_RE.findall(line))
            current = None
    if not cus:
        errors.append("SPEC.md: no hay casos de uso")
    for cu, refs in sorted(cus.items()):
        if not refs:
            errors.append(f"{cu}: sin requisitos")
        for r in sorted(refs - reqs.keys()):
            errors.append(f"{cu}: referencia un requisito inexistente {r}")
    return cus


def check_references(root: Path, reqs: dict[str, list[str]], errors: list[str]) -> None:
    for rel in SCANNED_REL:
        for n, line in enumerate((root / rel).read_text(encoding="utf-8").splitlines(), 1):
            for r in REF_RE.findall(line):
                if r not in reqs:
                    errors.append(f"{rel}:{n}: cita un requisito inexistente {r}")


def check_mapping(root: Path, reqs: dict[str, list[str]], errors: list[str]) -> int:
    rows: dict[str, set[str]] = {}
    for line in (root / REQ_REL).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| ((?:LEGAL|PRINCIPIO|NFR)-[A-Z0-9-]+) \|", line)
        if m:
            rows[m.group(1)] = set(REF_RE.findall(line))
    for origin in REQUIRED_ORIGINS:
        if origin not in rows:
            errors.append(f"Correspondencia MEGAPROMPT: falta la fila {origin}")
        elif not rows[origin]:
            errors.append(f"Correspondencia MEGAPROMPT: {origin} sin requisitos")
        else:
            for r in sorted(rows[origin] - reqs.keys()):
                errors.append(f"Correspondencia MEGAPROMPT: {origin} cita {r}, que no existe")
    return len(rows)


def check_structure(root: Path, errors: list[str]) -> None:
    spec = (root / SPEC_REL).read_text(encoding="utf-8")
    headings = [h.lower() for h in re.findall(r"^#{2,3} .*$", spec, re.MULTILINE)]
    for sec in REQUIRED_SPEC_SECTIONS:
        if not any(sec.lower() in h for h in headings):
            errors.append(f"SPEC.md: falta la sección «{sec}»")
    role_rows = {m.group(1).strip() for m in re.finditer(r"^\| ([^|]+?) \|", spec, re.MULTILINE)}
    for role in REQUIRED_ROLES:
        if role not in role_rows:
            errors.append(f"SPEC.md: falta el rol «{role}» en la tabla de actores")
    risks = (root / RISK_REL).read_text(encoding="utf-8")
    cats = " ".join(
        m.group(1) for m in re.finditer(r"^\| R-\d{2} \| ([^|]+) \|", risks, re.MULTILINE)
    )
    for cat in REQUIRED_RISK_CATEGORIES:
        if cat.lower() not in cats.lower():
            errors.append(f"RIESGOS.md: ningún riesgo de categoría «{cat}»")


def scan_legal(root: Path, errors: list[str]) -> tuple[int, list[str]]:
    allow = load_allowlist(root)
    hits = 0
    proposals: list[str] = []
    for rel in SCANNED_REL:
        for n, line in enumerate((root / rel).read_text(encoding="utf-8").splitlines(), 1):
            if not SENSITIVE.search(line):
                continue
            hits += 1
            key = line_key(rel, line)
            if key not in allow:
                snippet = " ".join(line.split())[:110]
                errors.append(f"{rel}:{n}: mención sensible no revisada: {snippet}")
                proposals.append(f"{key}  {rel}  # {snippet}")
    return hits, proposals


def run(root: Path = DEFAULT_ROOT, propose: bool = False, out=print) -> int:
    errors: list[str] = []
    reqs = parse_requirements(root, errors)
    cus = parse_use_cases(root, reqs, errors)
    referenced = set().union(*cus.values()) if cus else set()
    orphans = sorted(reqs.keys() - referenced)
    for r in orphans:
        errors.append(f"{r}: no lo referencia ningún caso de uso")
    check_references(root, reqs, errors)
    n_map = check_mapping(root, reqs, errors)
    check_structure(root, errors)
    legal_hits, proposals = scan_legal(root, errors)

    if propose:
        for p in proposals:
            out(p)
        return 0

    by_cat = {c: {"MUST": 0, "SHOULD": 0, "COULD": 0} for c in CATEGORIES}
    for rid, cols in reqs.items():
        cat = rid.split("-")[1]
        if cat in by_cat and cols[1] in PRIORITIES:
            by_cat[cat][cols[1]] += 1
    bloqueados = sorted(r for r, c in reqs.items() if "**B**" in " ".join(c))

    out("== check_spec.py — verificación de la FASE -1 ==")
    out(f"Requisitos: {len(reqs)}")
    for cat in CATEGORIES:
        c = by_cat[cat]
        out(f"  {cat:5} MUST={c['MUST']:3} SHOULD={c['SHOULD']:3} COULD={c['COULD']:3}")
    out(f"Requisitos con bloqueo (**B**): {len(bloqueados)} -> {', '.join(bloqueados)}")
    out(f"Casos de uso: {len(cus)}")
    out(f"Requisitos sin caso de uso: {len(orphans)}")
    out(f"Filas de correspondencia con el MEGAPROMPT: {n_map} (exigidas {len(REQUIRED_ORIGINS)})")
    out(f"Menciones sensibles: {legal_hits} (todas deben estar en {ALLOWLIST_REL})")
    if errors:
        out(f"\nRESULTADO: FALLO ({len(errors)} errores)")
        for e in errors:
            out(f"  - {e}")
        return 1
    out("\nRESULTADO: OK")
    return 0


if __name__ == "__main__":
    sys.exit(run(propose="--propose" in sys.argv[1:]))

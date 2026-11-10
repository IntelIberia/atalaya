#!/usr/bin/env python3
"""Detector de datos personales en logs, evidencias y salidas (REQ-PRIV-003).

Busca correos, teléfonos españoles, DNI/NIE con letra de control válida, IBAN e IPv4
públicas. Excepciones explícitas: direcciones técnicas (noreply, example.invalid) e IP
privadas/loopback. Uso: python -m scripts.pii_scan RUTA [RUTA...]  (exit 1 si hay hallazgos)
"""

from __future__ import annotations

import ipaddress
import re
import sys
from dataclasses import dataclass
from pathlib import Path

DNI_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
EMAIL_OK = re.compile(
    r"(?i)^(?:noreply|no-reply)@|@example\.(invalid|com|org)$|@users\.noreply\.github\.com$"
)
PHONE = re.compile(r"(?<![\w.])(?:\+34[ -]?)?[6789]\d{2}[ -]?\d{3}[ -]?\d{3}(?![\w.])")
DNI = re.compile(r"\b(\d{8})-?([A-Z])\b")
NIE = re.compile(r"\b([XYZ])(\d{7})-?([A-Z])\b")
IBAN = re.compile(r"\bES\d{2}(?: ?\d{4}){5}\b")
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
TEXT_SUFFIXES = {".txt", ".md", ".json", ".log", ".xml", ".csv", ".jsonl", ".yaml", ".yml"}


@dataclass(frozen=True)
class Hit:
    path: str
    line: int
    kind: str


def _dni_ok(num: str, letter: str) -> bool:
    return DNI_LETTERS[int(num) % 23] == letter


def scan_text(text: str, path: str = "<texto>") -> list[Hit]:
    hits: list[Hit] = []
    for n, line in enumerate(text.splitlines(), 1):
        for m in EMAIL.finditer(line):
            if not EMAIL_OK.search(m.group(0)):
                hits.append(Hit(path, n, "email"))
        hits += [
            Hit(path, n, "telefono")
            for m in PHONE.finditer(line)
            if not re.match(r"\s*(?:[kMG]?Hz\b|\([^)]*\b[kMG]?Hz\))", line[m.end() :], re.I)
            and not re.search(r"\bhackrf(?:_transfer)?\b[^\n]*\s-f\s*$", line[: m.start()])
        ]
        hits += [Hit(path, n, "dni") for m in DNI.finditer(line) if _dni_ok(*m.groups())]
        for m in NIE.finditer(line):
            prefix, num, letter = m.groups()
            if _dni_ok(str("XYZ".index(prefix)) + num, letter):
                hits.append(Hit(path, n, "nie"))
        hits += [Hit(path, n, "iban") for _ in IBAN.finditer(line)]
        for m in IPV4.finditer(line):
            try:
                ip = ipaddress.IPv4Address(m.group(0))
            except ValueError:
                continue
            if ip.is_global:
                hits.append(Hit(path, n, "ipv4_publica"))
    return hits


def scan_tree(root: Path) -> list[Hit]:
    hits: list[Hit] = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES:
            hits += scan_text(p.read_text(encoding="utf-8", errors="replace"), str(p))
    return hits


def main(argv: list[str] | None = None) -> int:
    paths = [Path(a) for a in (argv if argv is not None else sys.argv[1:])]
    hits = [
        h for p in paths for h in (scan_tree(p) if p.is_dir() else scan_text(p.read_text(), str(p)))
    ]
    for h in hits:
        print(f"  {h.path}:{h.line}: posible dato personal ({h.kind})", file=sys.stderr)
    print(f"pii_scan: {len(hits)} hallazgos")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())

"""Procedencia del smoke local de FASE 0 (REQ-SEC-005)."""

import hashlib
from pathlib import Path

from defusedxml import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TEST_NAME = "test_stack_rechaza_accesos_sin_credenciales"


def source_digest(root: Path = ROOT) -> str:
    paths = sorted((root / "infra/compose").rglob("*"))
    paths += [
        root / p
        for p in (
            "scripts/smoke_compose.py",
            "scripts/integration_evidence.py",
            "tests/integracion/test_smoke_compose.py",
            "tests/conftest.py",
            "pyproject.toml",
            "uv.lock",
            "Makefile",
        )
    ]
    digest = hashlib.sha256()
    for path in paths:
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def verify(path: Path, root: Path = ROOT) -> bool:
    tree = ET.parse(path)
    for case in tree.iter("testcase"):
        properties = {p.get("name"): p.get("value") for p in case.iter("property")}
        if (
            case.get("name") == TEST_NAME
            and properties.get("integration_source_sha256") == source_digest(root)
            and all(case.find(tag) is None for tag in ("failure", "error", "skipped"))
        ):
            return True
    return False

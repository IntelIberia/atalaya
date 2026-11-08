"""Workflows de CI: acciones fijadas por SHA, permisos mínimos y controles exigidos."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

USES = re.compile(r"uses:\s*([^\s#]+)")
SHA_PIN = re.compile(r"^[\w.-]+/[\w.-]+(?:/[\w./-]+)?@[0-9a-f]{40}$")


def acciones_sin_sha(texto: str) -> list[str]:
    return [u for u in USES.findall(texto) if not SHA_PIN.match(u)]


@pytest.mark.req("REQ-SEC-012")
def test_acciones_fijadas_por_sha(repo: Path) -> None:
    for wf in (repo / ".github" / "workflows").glob("*.yml"):
        assert acciones_sin_sha(wf.read_text()) == [], wf.name


@pytest.mark.req("REQ-SEC-012")
def test_detecta_accion_por_etiqueta() -> None:
    assert acciones_sin_sha("uses: actions/checkout@v4\n") == ["actions/checkout@v4"]


@pytest.mark.req("REQ-SEC-012", "REQ-SEC-003", "REQ-LEG-016")
def test_controles_presentes(repo: Path) -> None:
    ci = (repo / ".github/workflows/ci.yml").read_text()
    sec = (repo / ".github/workflows/security.yml").read_text()
    for wf in (ci, sec):
        assert "permissions:\n  contents: read" in wf
    assert "make check" in ci
    assert "make regress" in ci
    assert "guardrails.sh --range" in ci
    for control in ("gitleaks", "anchore/sbom-action", "anchore/scan-action", "semgrep"):
        assert control in sec
    assert "scripts.license_check" in sec
    assert "severity-cutoff: critical" in sec

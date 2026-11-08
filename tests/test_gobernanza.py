"""CLAUDE.md y reglas por ruta (.claude/rules/) cumplen lo que exige la FASE 0."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

SECCIONES_CLAUDE_MD = (
    "## Antes de empezar",
    "## Comandos",
    "## Restricciones legales",
    "## Flujo de trabajo",
    "## Lo que confunde",
)
REGLAS: dict[str, list[str] | None] = {
    "legal.md": None,  # sin paths: se carga siempre
    "edge.md": ["edge/**"],
    "ml.md": ["ml/**", "evals/**"],
    "rf.md": ["edge/rf-presence/**", "edge/adsb/**", "edge/esp32-remoteid/**"],
}


def frontmatter(texto: str) -> dict[str, object]:
    m = re.match(r"^---\n(.*?)\n---\n", texto, re.DOTALL)
    if not m:
        return {}
    data = yaml.safe_load(m.group(1))
    return data if isinstance(data, dict) else {}


def problemas_claude_md(texto: str) -> list[str]:
    p: list[str] = []
    if len(texto.splitlines()) >= 150:
        p.append("CLAUDE.md tiene 150 líneas o más")
    p += [f"falta {s}" for s in SECCIONES_CLAUDE_MD if s not in texto]
    if "docs/MEGAPROMPT.md" not in texto:
        p.append("falta el puntero al MEGAPROMPT")
    return p


@pytest.mark.req("REQ-LEG-017")
def test_claude_md(repo: Path) -> None:
    assert problemas_claude_md((repo / "CLAUDE.md").read_text()) == []


@pytest.mark.req("REQ-LEG-017")
def test_claude_md_detecta_exceso_y_seccion_ausente(repo: Path) -> None:
    texto = (repo / "CLAUDE.md").read_text().replace("## Restricciones legales", "## Otra")
    texto += "\n" * 200
    p = problemas_claude_md(texto)
    assert "CLAUDE.md tiene 150 líneas o más" in p
    assert "falta ## Restricciones legales" in p


@pytest.mark.req("REQ-LEG-017", "REQ-LEG-001")
@pytest.mark.parametrize(("nombre", "paths"), list(REGLAS.items()))
def test_reglas_por_ruta(repo: Path, nombre: str, paths: list[str] | None) -> None:
    texto = (repo / ".claude" / "rules" / nombre).read_text()
    fm = frontmatter(texto)
    assert fm.get("paths") == paths
    assert len(texto.splitlines()) > 5


@pytest.mark.req("REQ-LEG-017")
def test_regla_legal_incluye_detenerse(repo: Path) -> None:
    texto = (repo / ".claude" / "rules" / "legal.md").read_text().lower()
    assert "detente" in texto
    assert "alternativa defensiva" in texto

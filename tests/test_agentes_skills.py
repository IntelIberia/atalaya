"""Subagentes revisores (solo lectura) y skills del proceso por fases."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_gobernanza import frontmatter

AGENTES = (
    "independent-reviewer",
    "security-reviewer",
    "legal-guardrail-reviewer",
    "test-auditor",
    "ml-eval-reviewer",
    "sapient-conformance",
    "privacy-reviewer",
)
CON_BASH = {"independent-reviewer", "test-auditor"}
SKILLS = ("phase-plan", "phase-close", "new-adr", "dataset-intake", "release")
ESCRITURA = {"Write", "Edit", "NotebookEdit", "MultiEdit"}


def _lista(valor: object) -> set[str]:
    if isinstance(valor, str):
        return {t.strip() for t in valor.split(",") if t.strip()}
    if isinstance(valor, list):
        return {str(t).strip() for t in valor}
    return set()


def problemas_agente(nombre: str, texto: str) -> list[str]:
    fm = frontmatter(texto)
    p: list[str] = []
    if fm.get("name") != nombre:
        p.append("name incorrecto")
    if not fm.get("description"):
        p.append("sin description")
    tools = _lista(fm.get("tools"))
    if not tools:
        p.append("sin lista explícita de tools (heredaría todas)")
    if tools & ESCRITURA:
        p.append(f"herramientas de escritura: {sorted(tools & ESCRITURA)}")
    if "Bash" in tools and not ESCRITURA - {"MultiEdit"} <= _lista(fm.get("disallowedTools")):
        p.append("con Bash debe declarar disallowedTools de escritura")
    if "Bash" in tools and nombre not in CON_BASH:
        p.append("Bash no autorizado para este revisor")
    return p


@pytest.mark.req("REQ-SEC-003")
@pytest.mark.parametrize("nombre", AGENTES)
def test_agente_solo_lectura(repo: Path, nombre: str) -> None:
    texto = (repo / ".claude" / "agents" / f"{nombre}.md").read_text()
    assert problemas_agente(nombre, texto) == []
    assert len(texto.splitlines()) > 10


@pytest.mark.req("REQ-SEC-003")
def test_agente_con_write_se_detecta(repo: Path) -> None:
    texto = (repo / ".claude" / "agents" / "security-reviewer.md").read_text()
    texto = texto.replace("tools: Read, Grep, Glob", "tools: Read, Grep, Glob, Write", 1)
    assert any("escritura" in p for p in problemas_agente("security-reviewer", texto))


@pytest.mark.req("REQ-SEC-003")
@pytest.mark.parametrize("nombre", SKILLS)
def test_skill(repo: Path, nombre: str) -> None:
    texto = (repo / ".claude" / "skills" / nombre / "SKILL.md").read_text()
    fm = frontmatter(texto)
    assert fm.get("description")
    assert (fm.get("disable-model-invocation") is True) is (nombre == "release")

"""El Makefile no puede ocultar fallos: GNU Make 3.81 (macOS) ignora .SHELLFLAGS y no hay
pipefail, así que `cmd | tail` devolvería el código de `tail` (siempre 0)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

FILTROS = re.compile(r"\|\s*(?:tail|head|grep|sed|awk|tee|cat|sort)\b")


def recetas_con_tuberia(makefile: str) -> list[str]:
    return [
        ln.strip() for ln in makefile.splitlines() if ln.startswith("\t") and FILTROS.search(ln)
    ]


@pytest.mark.req("REQ-NFR-014")
def test_recetas_sin_tuberias_que_oculten_fallos(repo: Path) -> None:
    assert recetas_con_tuberia((repo / "Makefile").read_text()) == []


@pytest.mark.req("REQ-NFR-014")
def test_deteccion_de_tuberia() -> None:
    assert recetas_con_tuberia("x:\n\t@mypy . | tail -1\n") == ["@mypy . | tail -1"]


@pytest.mark.req("REQ-NFR-014")
def test_objetivo_que_falla_hace_fallar_make(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text("SHELL := /bin/bash\nmalo:\n\t@false\n")
    r = subprocess.run(["make", "-C", str(tmp_path), "malo"], capture_output=True)
    assert r.returncode != 0


@pytest.mark.req("REQ-NFR-014")
def test_objetivos_de_claude_md_existen(repo: Path) -> None:
    objetivos = set(re.findall(r"^([a-z-]+):", (repo / "Makefile").read_text(), re.MULTILINE))
    citados = set(re.findall(r"`make ([a-z-]+)", (repo / "CLAUDE.md").read_text()))
    assert citados - objetivos == set()

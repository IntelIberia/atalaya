"""Riesgo H2-R11: el piloto no se filtra al producto.

Ningún fichero Python fuera de ``pilots/`` puede importar ``pilots``, ``acoustic_pilot`` ni el
subpaquete ``live``, ni añadir ``pilots`` a ``sys.path``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Riesgo del plan, no requisito: el marcador lleva su identificador.
pytestmark = pytest.mark.req("H2-R11")

REPO = Path(__file__).resolve().parents[4]
PILOT_MODULES = frozenset({"pilots", "acoustic_pilot", "live"})
SKIP_DIRS = frozenset(
    {".git", ".venv", "venv", ".claude", "node_modules", "third_party", "mutants", "pilots"}
)


def _python_files_outside_pilots(root: Path) -> list[Path]:
    files: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        for entry in current.iterdir():
            if entry.is_dir():
                if entry.name not in SKIP_DIRS and not entry.name.startswith("."):
                    stack.append(entry)
            elif entry.suffix == ".py":
                files.append(entry)
    return files


def pilot_leaks(source: str, filename: str) -> list[str]:
    tree = ast.parse(source, filename=filename)
    leaks: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        elif (
            isinstance(node, ast.Call)
            and any(isinstance(a, ast.Constant) and a.value == "pilots" for a in node.args)
        ) or (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and "pilots/acoustic" in node.value
        ):
            leaks.append(f"{filename}:{node.lineno}: referencia a pilots")
            continue
        else:
            continue
        leaks += [
            f"{filename}:{node.lineno}: import {n}"
            for n in names
            if n.split(".")[0] in PILOT_MODULES
        ]
    return leaks


def test_repo_root_is_the_atalaya_root() -> None:
    assert (REPO / "pilots" / "acoustic" / "pyproject.toml").is_file()
    assert (REPO / "Makefile").is_file()


def test_nothing_outside_pilots_imports_the_pilot() -> None:
    files = _python_files_outside_pilots(REPO)
    assert len(files) > 50  # analiza de verdad el resto del repositorio
    leaks: list[str] = []
    for path in files:
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        leaks += pilot_leaks(source, str(path.relative_to(REPO)))
    assert leaks == [], "\n".join(leaks)


@pytest.mark.parametrize(
    "snippet",
    [
        "import acoustic_pilot",
        "from acoustic_pilot.speech_gate import apply_speech_gate",
        "from live.artifact import load_artifact",
        "import pilots.acoustic",
        "import sys\nsys.path.insert(0, 'pilots/acoustic')",
        "p = Path('x') / 'pilots'\nsys.path.append(str(Path('x').joinpath('pilots')))",
    ],
)
def test_detector_catches_injected_imports(snippet: str) -> None:
    assert pilot_leaks(snippet, "services/x.py"), snippet


def test_detector_ignores_unrelated_code() -> None:
    assert pilot_leaks("import json\nfrom scripts import guardrails\nlive = 1\n", "x.py") == []

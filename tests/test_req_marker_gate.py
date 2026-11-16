"""Barrera de fallo cerrado: ningún test sin @pytest.mark.req llega a ejecutarse (trazabilidad)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.req("REQ-NFR-014", "REQ-SEC-003"), pytest.mark.subproceso]

INI = """[pytest]
addopts = --strict-markers
markers =
    req(id): requisitos que verifica el test
"""


def recoger(tmp_path: Path, repo: Path, cuerpo: str) -> subprocess.CompletedProcess[str]:
    """Recoge (--co) un proyecto temporal que usa el conftest real del repositorio."""
    shutil.copy(repo / "tests/conftest.py", tmp_path / "conftest.py")
    (tmp_path / "pytest.ini").write_text(INI)
    (tmp_path / "test_muestra.py").write_text(cuerpo)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--co",
            "-q",
            "-p",
            "no:cacheprovider",
            "-c",
            str(tmp_path / "pytest.ini"),
            "--rootdir",
            str(tmp_path),
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )


def test_test_sin_marcador_req_hace_fallar_la_recogida(tmp_path: Path, repo: Path) -> None:
    cuerpo = (
        "import pytest\n\n"
        "@pytest.mark.req('REQ-FUN-001')\n"
        "def test_marcado() -> None:\n    pass\n\n"
        "def test_huerfano() -> None:\n    pass\n"
    )
    proc = recoger(tmp_path, repo, cuerpo)
    salida = proc.stdout + proc.stderr
    assert proc.returncode != 0, salida
    assert "sin marcador req" in salida
    assert "test_muestra.py::test_huerfano" in salida
    assert "test_muestra.py::test_marcado" not in salida.split("sin marcador req")[1]


def test_marcador_de_modulo_y_de_clase_cuentan(tmp_path: Path, repo: Path) -> None:
    cuerpo = (
        "import pytest\n\n"
        "pytestmark = pytest.mark.req('REQ-FUN-001')\n\n"
        "def test_por_modulo() -> None:\n    pass\n\n"
        "class TestClase:\n    def test_por_clase(self) -> None:\n        pass\n"
    )
    proc = recoger(tmp_path, repo, cuerpo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "2 tests collected" in proc.stdout


def test_marcador_req_sin_ids_no_cuenta(tmp_path: Path, repo: Path) -> None:
    cuerpo = "import pytest\n\n@pytest.mark.req()\ndef test_vacio() -> None:\n    pass\n"
    proc = recoger(tmp_path, repo, cuerpo)
    assert proc.returncode != 0
    assert "test_muestra.py::test_vacio" in proc.stdout + proc.stderr

"""Documentos de gobernanza v0 (FASE 0): ADR, STRIDE, DPIA + RAT, ENS, deuda técnica, coste 0 €."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

ADR_SECCIONES = (
    "- Estado:",
    "## Contexto",
    "## Opciones consideradas",
    "## Decisión",
    "## Consecuencias",
)
ADRS = {
    "0001": "arquitectura",
    "0002": "restricciones-legales",
    "0003": "stack",
    "0004": "presupuesto-cero",
    "0005": "guardarrail-lista-blanca",
    "0006": "hook-stop-y-umbrales",
    "0007": "ci-repo-privado",
}
STRIDE = (
    "Supla" + "ntación",
    "Manipulación",
    "Repudio",
    "Divulgación de información",
    "Denegación de servicio",
    "Elevación de privilegios",
)


def problemas_adr(texto: str) -> list[str]:
    return [f"falta «{s}»" for s in ADR_SECCIONES if s not in texto]


def _adr(repo: Path, num: str) -> str:
    [f] = list((repo / "docs" / "adr").glob(f"{num}-*.md"))
    return f.read_text()


@pytest.mark.req("REQ-SEC-015", "REQ-LEG-001")
@pytest.mark.parametrize(("num", "clave"), list(ADRS.items()))
def test_adr_madr(repo: Path, num: str, clave: str) -> None:
    [f] = list((repo / "docs" / "adr").glob(f"{num}-*.md"))
    assert clave in f.name
    assert problemas_adr(f.read_text()) == []


@pytest.mark.req("REQ-SEC-015")
def test_adr_sin_consecuencias_se_detecta(repo: Path) -> None:
    texto = _adr(repo, "0001").replace("## Consecuencias", "## Otra")
    assert problemas_adr(texto) == ["falta «## Consecuencias»"]


@pytest.mark.req("REQ-NFR-016")
def test_presupuesto_cero_y_runners_gratuitos(repo: Path) -> None:
    assert "0 €" in _adr(repo, "0004")
    for wf in (repo / ".github" / "workflows").glob("*.yml"):
        jobs = yaml.safe_load(wf.read_text())["jobs"]
        assert {j["runs-on"] for j in jobs.values()} <= {"ubuntu-24.04"}, wf.name


def problemas_stride(texto: str) -> list[str]:
    p = [f"falta STRIDE «{c}»" for c in STRIDE if c not in texto]
    for ataque in (
        "nodos supla" + "ntados",
        "detecciones falsas",
        "Remote ID falsificado",
        "denegación",
    ):
        if ataque.lower() not in texto.lower():
            p.append(f"falta ataque a la red de sensores: {ataque}")
    return p


@pytest.mark.req("REQ-SEC-015")
def test_modelo_de_amenazas(repo: Path) -> None:
    assert problemas_stride((repo / "docs/threat-model/v0.md").read_text()) == []


@pytest.mark.req("REQ-SEC-015")
def test_stride_incompleto_se_detecta(repo: Path) -> None:
    texto = (repo / "docs/threat-model/v0.md").read_text().replace("Repudio", "X")
    assert "falta STRIDE «Repudio»" in problemas_stride(texto)


@pytest.mark.req("REQ-PRIV-006", "REQ-PRIV-007")
def test_dpia_y_registro_de_actividades(repo: Path) -> None:
    texto = (repo / "docs/dpia/v0.md").read_text()
    assert "## Registro de actividades de tratamiento" in texto
    filas = [ln for ln in texto.splitlines() if re.match(r"^\| T-\d{2} \|", ln)]
    assert len(filas) >= 4
    for fila in filas:
        celdas = [c.strip() for c in fila.strip("|").split("|")]
        assert all(celdas), f"celda vacía en {celdas[0]}"
        assert re.search(r"RGPD art\. 6\.1\.[a-f]|LOPDGDD|pendiente", fila), celdas[0]


@pytest.mark.req("REQ-SEC-016")
def test_ens(repo: Path) -> None:
    texto = (repo / "docs/ens/v0.md").read_text()
    assert "MEDIA" in texto
    for marco in ("org.", "op.", "mp."):
        assert marco in texto
    assert len([ln for ln in texto.splitlines() if re.match(r"^\| (org|op|mp)\.", ln)]) >= 15


@pytest.mark.req("REQ-NFR-014")
def test_deuda_tecnica_registrada(repo: Path) -> None:
    texto = (repo / "docs/tech-debt.md").read_text()
    for item in ("libcst", "pytest<9", "Make 3.81"):
        assert item in texto


@pytest.mark.req("REQ-NFR-014")
def test_plantillas(repo: Path) -> None:
    plan = (repo / "docs/plans/PLANTILLA-FASE.md").read_text()
    for campo in ("Requisitos", "Verificación", "Resultado esperado", "Prueba negativa"):
        assert campo in plan
    assert (
        "| Prueba negativa |" in (repo / "docs/evidence/PLANTILLA-registro-tareas.md").read_text()
    )


@pytest.mark.req("REQ-NFR-015")
def test_herramientas_disponibles(repo: Path) -> None:
    r = subprocess.run([str(repo / "scripts/doctor.sh")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "grpc-protoc" in r.stdout
    assert "libprotoc" in r.stdout

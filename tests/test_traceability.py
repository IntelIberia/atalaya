"""Tests de scripts/traceability.py (REQ-NFR-014, REQ-SEC-003)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import traceability as t

REQS = """
| ID | Prio | Descripción | Criterio | Método | Fase | Justificación |
|---|---|---|---|---|---|---|
| REQ-FUN-001 | MUST | a | c | T | 0 | j |
| REQ-FUN-002 | MUST | b | c | T | 3 (y 10) | j |
| REQ-FUN-003 | SHOULD | c | c | T | 0 | j |
| REQ-NFR-001 | MUST | d | c **B** | T | 0→ | j |
| REQ-SEC-001 | MUST | e | c | T | 9 (guardarraíles: 0) | j |
"""


def junit(casos: list[tuple[str, list[str], str]]) -> str:
    """casos: (nombre, [req...], resultado) con resultado en {"ok", "fail", "skip"}."""
    partes = ['<?xml version="1.0"?><testsuites><testsuite name="pytest">']
    for nombre, reqs, res in casos:
        props = "".join(f'<property name="req" value="{r}"/>' for r in reqs)
        cuerpo = f"<properties>{props}</properties>"
        if res == "fail":
            cuerpo += '<failure message="x"/>'
        elif res == "skip":
            cuerpo += '<skipped message="x"/>'
        partes.append(f'<testcase classname="tests.x" name="{nombre}">{cuerpo}</testcase>')
    partes.append("</testsuite></testsuites>")
    return "".join(partes)


@pytest.fixture
def entorno(tmp_path: Path) -> Path:
    (tmp_path / "REQUIREMENTS.md").write_text(REQS)
    (tmp_path / "FASES-CERRADAS.txt").write_text("# fases cerradas\n-1\n")
    return tmp_path


def correr(
    d: Path, casos: list[tuple[str, list[str], str]], fases: list[int] | None = None
) -> t.Result:
    (d / "junit.xml").write_text(junit(casos))
    return t.evaluate(
        d / "REQUIREMENTS.md", d / "junit.xml", d / "FASES-CERRADAS.txt", extra_closed=fases or []
    )


@pytest.mark.req("REQ-NFR-014")
def test_fase_de_un_requisito_es_la_primera_mencionada() -> None:
    assert t.first_phase("0→") == 0
    assert t.first_phase("3 (y 10)") == 3
    assert t.first_phase("9 (guardarraíles: 0)") == 0
    assert t.first_phase("1 (esquema), 9-10") == 1
    assert t.first_phase("-1") == -1
    assert t.first_phase("") is None


@pytest.mark.req("REQ-SEC-003")
def test_sin_fases_cerradas_relevantes_no_hay_huecos(entorno: Path) -> None:
    r = correr(entorno, [])
    assert r.gaps == []


@pytest.mark.req("REQ-SEC-003")
def test_must_de_fase_cerrada_sin_test_es_hueco(entorno: Path) -> None:
    r = correr(entorno, [("t1", ["REQ-SEC-001"], "ok")], fases=[0])
    assert r.gaps == ["REQ-FUN-001"]  # NFR-001 tiene **B**; FUN-003 es SHOULD


@pytest.mark.req("REQ-SEC-003")
def test_must_con_test_en_rojo_es_hueco(entorno: Path) -> None:
    casos = [("t1", ["REQ-FUN-001"], "fail"), ("t2", ["REQ-SEC-001"], "ok")]
    r = correr(entorno, casos, fases=[0])
    assert r.gaps == ["REQ-FUN-001"]
    assert r.failing == {"REQ-FUN-001"}


@pytest.mark.req("REQ-SEC-003")
def test_test_omitido_no_cuenta_como_verde(entorno: Path) -> None:
    casos = [("t1", ["REQ-FUN-001"], "skip"), ("t2", ["REQ-SEC-001"], "ok")]
    assert correr(entorno, casos, fases=[0]).gaps == ["REQ-FUN-001"]


@pytest.mark.req("REQ-SEC-003")
def test_basta_un_test_verde_si_no_hay_rojos(entorno: Path) -> None:
    casos = [("t1", ["REQ-FUN-001"], "ok"), ("t2", ["REQ-SEC-001", "REQ-FUN-001"], "ok")]
    assert correr(entorno, casos, fases=[0]).gaps == []


@pytest.mark.req("REQ-SEC-003")
def test_un_rojo_rompe_aunque_haya_verdes(entorno: Path) -> None:
    casos = [("t1", ["REQ-FUN-001"], "ok"), ("t2", ["REQ-FUN-001"], "fail")]
    casos.append(("t3", ["REQ-SEC-001"], "ok"))
    assert correr(entorno, casos, fases=[0]).gaps == ["REQ-FUN-001"]


@pytest.mark.req("REQ-SEC-003")
def test_id_inexistente_en_un_test_es_error(entorno: Path) -> None:
    r = correr(entorno, [("t1", ["REQ-FUN-999"], "ok")])
    assert r.unknown_ids == {"REQ-FUN-999"}
    assert not r.ok


@pytest.mark.req("REQ-SEC-003")
def test_fases_cerradas_se_leen_del_fichero(entorno: Path) -> None:
    (entorno / "FASES-CERRADAS.txt").write_text("-1\n0\n")
    r = correr(entorno, [("t2", ["REQ-SEC-001"], "ok")])
    assert r.gaps == ["REQ-FUN-001"]


@pytest.mark.req("REQ-NFR-014")
def test_informe_markdown(entorno: Path) -> None:
    r = correr(entorno, [("t1", ["REQ-FUN-001"], "ok")], fases=[0])
    md = t.render(r)
    assert "| REQ-FUN-001 | MUST | 0 | 1 | verde |" in md
    assert "| REQ-NFR-001 | MUST | 0 | 0 | sin tests | BLOQUEADO (B) |" in md
    assert "| REQ-SEC-001 | MUST | 0 | 0 | sin tests | HUECO |" in md


@pytest.mark.req("REQ-SEC-003")
def test_cli_exit_1_con_huecos(entorno: Path) -> None:
    (entorno / "junit.xml").write_text(junit([]))
    out = entorno / "T.md"
    args = [
        "--requirements",
        str(entorno / "REQUIREMENTS.md"),
        "--junit",
        str(entorno / "junit.xml"),
        "--closed",
        str(entorno / "FASES-CERRADAS.txt"),
        "--out",
        str(out),
    ]
    assert t.main([*args, "--fase", "0"]) == 1
    assert out.exists()
    assert t.main(args) == 0


@pytest.mark.req("REQ-SEC-003")
def test_cli_junit_ausente_falla(entorno: Path) -> None:
    args = ["--requirements", str(entorno / "REQUIREMENTS.md"), "--junit", str(entorno / "no.xml")]
    assert t.main([*args, "--closed", str(entorno / "FASES-CERRADAS.txt")]) == 1

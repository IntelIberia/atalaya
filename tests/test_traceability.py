"""Tests de scripts/traceability.py (REQ-NFR-014, REQ-SEC-003)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import integration_evidence
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


@pytest.mark.req("REQ-SEC-003")
def test_integration_failure_overrides_unit_success(entorno: Path) -> None:
    unit = entorno / "unit.xml"
    integration = entorno / "integration.xml"
    unit.write_text(junit([("unit", ["REQ-FUN-001", "REQ-SEC-001"], "ok")]))
    integration.write_text(junit([("integration", ["REQ-FUN-001"], "fail")]))
    result = t.evaluate(
        entorno / "REQUIREMENTS.md",
        [unit, integration],
        entorno / "FASES-CERRADAS.txt",
        extra_closed=[0],
    )
    assert result.gaps == ["REQ-FUN-001"]


# --- T1.16: varios JUnit con --junit repetible ----------------------------------------------


def _cli_args(d: Path, *junits: Path) -> list[str]:
    args = ["--requirements", str(d / "REQUIREMENTS.md"), "--closed", str(d / "FASES-CERRADAS.txt")]
    for j in junits:
        args += ["--junit", str(j)]
    return [*args, "--out", str(d / "T.md"), "--fase", "0"]


@pytest.mark.req("REQ-NFR-014", "REQ-SEC-003")
def test_cli_combina_varios_junit(entorno: Path, capsys: pytest.CaptureFixture[str]) -> None:
    a, b = entorno / "a.xml", entorno / "b.xml"
    a.write_text(junit([("u", ["REQ-SEC-001"], "ok")]))
    b.write_text(junit([("m", ["REQ-FUN-001"], "ok")]))
    assert t.main(_cli_args(entorno, a)) == 1
    assert t.main(_cli_args(entorno, a, b)) == 0
    assert "['a.xml', 'b.xml']" in capsys.readouterr().out
    informe = (entorno / "T.md").read_text()
    assert "| REQ-FUN-001 | MUST | 0 | 1 | verde | OK |" in informe
    assert "| REQ-SEC-001 | MUST | 0 | 1 | verde | OK |" in informe


@pytest.mark.req("REQ-SEC-003")
def test_cli_un_rojo_en_el_segundo_junit_falla(entorno: Path) -> None:
    a, b = entorno / "a.xml", entorno / "b.xml"
    a.write_text(junit([("u", ["REQ-SEC-001", "REQ-FUN-001"], "ok")]))
    b.write_text(junit([("m", ["REQ-FUN-001"], "fail")]))
    assert t.main(_cli_args(entorno, a)) == 0
    assert t.main(_cli_args(entorno, a, b)) == 1
    assert "| REQ-FUN-001 | MUST | 0 | 2 | rojo | HUECO |" in (entorno / "T.md").read_text()


@pytest.mark.req("REQ-SEC-003")
def test_cli_segundo_junit_ausente_falla_sin_informe(
    entorno: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    a = entorno / "a.xml"
    a.write_text(junit([("u", ["REQ-SEC-001", "REQ-FUN-001"], "ok")]))
    assert t.main(_cli_args(entorno, a, entorno / "falta.xml")) == 1
    assert "falta.xml" in capsys.readouterr().err
    assert not (entorno / "T.md").exists()


@pytest.mark.req("REQ-SEC-003")
def test_cli_omitido_en_segundo_junit_no_cuenta(entorno: Path) -> None:
    a, b = entorno / "a.xml", entorno / "b.xml"
    a.write_text(junit([("u", ["REQ-SEC-001"], "ok")]))
    b.write_text(junit([("m", ["REQ-FUN-001"], "skip")]))
    assert t.main(_cli_args(entorno, a, b)) == 1


@pytest.mark.req("REQ-SEC-003")
def test_cli_id_desconocido_en_segundo_junit_falla(entorno: Path) -> None:
    a, b = entorno / "a.xml", entorno / "b.xml"
    a.write_text(junit([("u", ["REQ-SEC-001", "REQ-FUN-001"], "ok")]))
    b.write_text(junit([("m", ["REQ-FUN-999"], "ok")]))
    assert t.main(_cli_args(entorno, a, b)) == 1


# --- T1.16: tests añadidos para la mutación de traceability.py (código crítico) -------------

REQS_COMPLETO = """
| ID | Prio | Descripción | Criterio | Método | Fase | Justificación |
|---|---|---|---|---|---|---|
| REQ-FUN-001 | MUST | a | c | T | 0 | j |
| REQ-FUN-002 | MUST | b | c | T | 3 (y 10) | j |
| REQ-FUN-003 | SHOULD | c | c | T | 0 | j |
| REQ-NFR-001 | MUST | d | c **B** | T | 0→ | j |
| REQ-SEC-001 | MUST | e | c | T | 9 (guardarraíles: 0) | j |
| REQ-SEC-002 | MUST | f | c | T | 5 | j |
| REQ-PRIV-001 | MUST | g | c | T | — | j |
"""

INFORME_ESPERADO = """# Trazabilidad requisito → tests

Generado por `scripts/traceability.py` (no editar a mano). Fases tratadas como cerradas: [-1, 0].

| Requisito | Prio | Fase | Tests | Resultado | Estado |
|---|---|---|---|---|---|
| REQ-FUN-001 | MUST | 0 | 2 | verde | OK |
| REQ-FUN-002 | MUST | 3 | 1 | rojo | en curso |
| REQ-FUN-003 | SHOULD | 0 | 0 | sin tests | pendiente (fase abierta) |
| REQ-NFR-001 | MUST | 0 | 0 | sin tests | BLOQUEADO (B) |
| REQ-SEC-001 | MUST | 0 | 0 | sin tests | HUECO |
| REQ-SEC-002 | MUST | 5 | 0 | sin tests | pendiente (fase abierta) |
| REQ-PRIV-001 | MUST |  | 1 | verde | en curso |

Huecos: 1 · IDs desconocidos en tests: 1
"""

CASOS_COMPLETOS = [
    ("t1", ["REQ-FUN-001"], "ok"),
    ("t2", ["REQ-FUN-001"], "ok"),
    ("t3", ["REQ-FUN-002"], "fail"),
    ("t4", ["REQ-PRIV-001"], "ok"),
    ("t5", ["REQ-FUN-999"], "ok"),
]


@pytest.fixture
def completo(tmp_path: Path) -> Path:
    (tmp_path / "REQUIREMENTS.md").write_text(REQS_COMPLETO)
    (tmp_path / "FASES-CERRADAS.txt").write_text("# fases cerradas\n-1 # comentario # otro\n")
    (tmp_path / "junit.xml").write_text(junit(CASOS_COMPLETOS))
    return tmp_path


@pytest.mark.req("REQ-NFR-014")
def test_informe_completo_exacto(completo: Path) -> None:
    r = t.evaluate(
        completo / "REQUIREMENTS.md",
        completo / "junit.xml",
        completo / "FASES-CERRADAS.txt",
        extra_closed=[0],
    )
    assert t.render(r) == INFORME_ESPERADO
    assert r.passed == {"REQ-FUN-001": 2, "REQ-PRIV-001": 1, "REQ-FUN-999": 1}
    assert r.failed == {"REQ-FUN-002": 1}


@pytest.mark.req("REQ-SEC-003")
def test_junit_error_cuenta_como_rojo_y_req_sin_valor_es_desconocido(tmp_path: Path) -> None:
    xml = (
        '<?xml version="1.0"?><testsuites><testsuite name="pytest">'
        '<testcase name="a"><properties><property name="req" value="REQ-FUN-001"/>'
        '</properties><error message="x"/></testcase>'
        '<testcase name="b"><properties><property name="req"/>'
        '<property name="otra" value="REQ-SEC-001"/></properties></testcase>'
        "</testsuite></testsuites>"
    )
    (tmp_path / "j.xml").write_text(xml)
    passed, failed = t.parse_junit(tmp_path / "j.xml")
    assert failed == {"REQ-FUN-001": 1}
    assert passed == {"": 1}


def _defaults(monkeypatch: pytest.MonkeyPatch, d: Path) -> Path:
    monkeypatch.setattr(t, "DEFAULT_REQS", d / "REQUIREMENTS.md")
    monkeypatch.setattr(t, "DEFAULT_CLOSED", d / "FASES-CERRADAS.txt")
    monkeypatch.setattr(t, "DEFAULT_JUNIT", d / "junit.xml")
    monkeypatch.setattr(t, "INTEGRATION_JUNIT", d / "junit-integracion.xml")
    out = d / "TRAZABILIDAD.md"
    monkeypatch.setattr(t, "DEFAULT_OUT", out)
    return out


@pytest.mark.req("REQ-SEC-003")
def test_cli_rutas_por_defecto_y_salida(
    completo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out = _defaults(monkeypatch, completo)
    assert t.main([]) == 1
    cap = capsys.readouterr()
    assert "traceability: informes JUnit: ['junit.xml']" in cap.out
    assert "fases cerradas [-1]; MUST en ellas: 0; huecos: 0; IDs desconocidos: 1" in cap.out
    assert "  ID DESCONOCIDO en tests: REQ-FUN-999" in cap.err
    assert out.read_text(encoding="utf-8").startswith("# Trazabilidad requisito → tests\n")
    assert t.main(["--fase", "0"]) == 1
    cap = capsys.readouterr()
    assert "fases cerradas [-1, 0]; MUST en ellas: 3; huecos: 1; IDs desconocidos: 1" in cap.out
    assert "  HUECO REQ-SEC-001" in cap.err
    assert "HUECO" not in cap.out


@pytest.mark.req("REQ-SEC-003")
def test_cli_junit_por_defecto_ausente(
    completo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _defaults(monkeypatch, completo)
    (completo / "junit.xml").unlink()
    assert t.main([]) == 1
    assert "junit.xml; ejecuta antes los tests" in capsys.readouterr().err


@pytest.mark.req("REQ-SEC-003", "REQ-SEC-005")
def test_cli_integracion_por_defecto_se_verifica(
    completo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out = _defaults(monkeypatch, completo)
    (completo / "junit.xml").write_text(junit([("t1", ["REQ-FUN-001", "REQ-SEC-001"], "ok")]))
    assert t.main(["--fase", "0", "--require-integration"]) == 1
    assert "falta evidencia de integración" in capsys.readouterr().err
    assert not out.exists()
    (completo / "junit-integracion.xml").write_text(junit([("i", ["REQ-FUN-001"], "ok")]))
    vistos: list[Path] = []

    def verify(path: Path) -> bool:
        vistos.append(path)
        return False

    monkeypatch.setattr(integration_evidence, "verify", verify)
    assert t.main(["--fase", "0", "--require-integration"]) == 1
    assert "integración ausente, fallida u obsoleta" in capsys.readouterr().err
    assert vistos == [completo / "junit-integracion.xml"]
    assert not out.exists()
    monkeypatch.setattr(integration_evidence, "verify", lambda path: True)
    assert t.main(["--fase", "0", "--require-integration"]) == 0
    assert "['junit.xml', 'junit-integracion.xml']" in capsys.readouterr().out
    assert "| REQ-FUN-001 | MUST | 0 | 2 | verde | OK |" in out.read_text()

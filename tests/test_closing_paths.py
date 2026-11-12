"""Regresiones de cierre y fallo de sus herramientas de verificación."""

import subprocess
import sys
from pathlib import Path

import pytest

from scripts import evidence, integration_evidence, traceability


@pytest.mark.req("REQ-NFR-014")
@pytest.mark.parametrize("exit_code", [0, 3])
def test_phase_capture_records_real_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exit_code: int
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.invalid",
            "commit",
            "--allow-empty",
            "-qm",
            "base",
        ],
        cwd=tmp_path,
        check=True,
    )
    closed = tmp_path / "docs" / "requirements" / "FASES-CERRADAS.txt"
    closed.parent.mkdir(parents=True)
    closed.write_text("# ninguna fase cerrada en este fixture\n", encoding="utf-8")
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    monkeypatch.setattr(
        evidence,
        "closing_commands",
        lambda _: {"verification.txt": [sys.executable, "-c", f"raise SystemExit({exit_code})"]},
    )
    assert evidence.main(["--fase", "0"]) == (1 if exit_code else 0)
    directory = tmp_path / "docs/evidence/FASE-0"
    assert f"exit={exit_code}" in (directory / "verification.txt").read_text()
    assert evidence.verify_manifest(directory) == []
    assert evidence.main(["--manifest", str(directory)]) == 0


@pytest.mark.req("REQ-SEC-003", "REQ-SEC-005")
@pytest.mark.parametrize("state", ["missing", "stale", "unknown", "valid"])
def test_traceability_integration_cli(tmp_path: Path, state: str) -> None:
    requirements = tmp_path / "requirements.md"
    requirements.write_text("| REQ-SEC-005 | MUST | stack | integration | T | 0 | security |\n")
    closed = tmp_path / "closed.txt"
    closed.write_text("0\n")
    xml = tmp_path / ("junit.xml" if state == "missing" else "junit-integracion.xml")
    digest = "stale" if state == "stale" else integration_evidence.source_digest()
    rid = "REQ-FUN-999" if state == "unknown" else "REQ-SEC-005"
    xml.write_text(
        f'<testsuite><testcase name="{integration_evidence.TEST_NAME}"><properties>'
        f'<property name="req" value="{rid}"/>'
        f'<property name="integration_source_sha256" value="{digest}"/>'
        "</properties></testcase></testsuite>"
    )
    args = [
        "--requirements",
        str(requirements),
        "--closed",
        str(closed),
        "--junit",
        str(xml),
        "--out",
        str(tmp_path / "trace.md"),
        "--require-integration",
    ]
    assert traceability.main(args) == (0 if state == "valid" else 1)

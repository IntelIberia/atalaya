"""Regresión de evidencia vacía, fallida u obsoleta."""

from pathlib import Path

import pytest

from scripts import integration_evidence as evidence


@pytest.mark.req("REQ-SEC-005")
@pytest.mark.parametrize("state", ["passed", "failure", "error", "skipped", "stale", "empty"])
def test_integration_identity_and_source(tmp_path: Path, state: str) -> None:
    source = tmp_path / "scripts/smoke_compose.py"
    source.parent.mkdir()
    source.write_text("initial")
    digest = evidence.source_digest(tmp_path)
    xml = tmp_path / "integration.xml"
    status = f"<{state}/>" if state in {"failure", "error", "skipped"} else ""
    case = (
        f'<testcase name="{evidence.TEST_NAME}"><properties>'
        f'<property name="integration_source_sha256" value="{digest}"/>'
        f"</properties>{status}</testcase>"
    )
    xml.write_text(f"<testsuite>{case if state != 'empty' else ''}</testsuite>")
    if state == "stale":
        source.write_text("changed")
    assert evidence.verify(xml, tmp_path) == (state == "passed")

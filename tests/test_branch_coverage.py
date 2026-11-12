"""El porcentaje combinado no sustituye la cobertura de ramas."""

import json
from pathlib import Path

import pytest

from scripts import branch_coverage


@pytest.mark.req("REQ-NFR-018")
@pytest.mark.parametrize(("covered", "total", "expected"), [(89, 100, 1), (90, 100, 0), (0, 0, 1)])
def test_branch_gate(tmp_path: Path, covered: int, total: int, expected: int) -> None:
    report = tmp_path / "coverage.json"
    report.write_text(
        json.dumps(
            {
                "totals": {
                    "percent_covered": 99.9,
                    "num_branches": total,
                    "covered_branches": covered,
                }
            }
        )
    )
    assert branch_coverage.main([str(report), "90"]) == expected

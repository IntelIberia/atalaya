"""La orden de mutación no acepta ejecuciones vacías, parciales o bajo umbral."""

import json
from pathlib import Path

import pytest

from scripts import mutation_report


@pytest.mark.req("REQ-NFR-018")
@pytest.mark.parametrize(
    ("codes", "expected"),
    [([], 1), ([1, None], 1), ([0], 1), ([1, 1, 1, 1, 0], 0), ([1, 36], 1)],
)
def test_mutation_cli_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, codes: list[int | None], expected: int
) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/m.py").write_text("x = 1\n")
    meta = tmp_path / "mutants/scripts/m.py.meta"
    meta.parent.mkdir(parents=True)
    meta.write_text(json.dumps({"exit_code_by_key": {str(i): c for i, c in enumerate(codes)}}))
    (tmp_path / "pyproject.toml").write_text("[tool.atalaya]\nmutation_threshold = 0.80\n")
    monkeypatch.setattr(mutation_report, "ROOT", tmp_path)
    assert (
        mutation_report.main(["--out", str(tmp_path / "report.json"), "scripts/m.py"]) == expected
    )

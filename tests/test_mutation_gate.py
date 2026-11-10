"""La orden de mutación no acepta ejecuciones vacías, parciales o bajo umbral."""

import json
import os
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
    (tmp_path / "pyproject.toml").write_text("[tool.atalaya]\nmutation_threshold = 0.80\n")
    monkeypatch.setattr(mutation_report, "ROOT", tmp_path)
    snapshot = tmp_path / "inputs.json"
    assert mutation_report.main(["--snapshot", str(snapshot), "scripts/m.py"]) == 0
    meta.write_text(json.dumps({"exit_code_by_key": {str(i): c for i, c in enumerate(codes)}}))
    assert (
        mutation_report.main(
            ["--out", str(tmp_path / "report.json"), "--inputs", str(snapshot), "scripts/m.py"]
        )
        == expected
    )


@pytest.mark.req("REQ-NFR-018")
@pytest.mark.parametrize(
    "changes",
    [
        {"pending": 464},
        {"other": 1},
        {"total": 0},
        {"score": 1.0},
        {"killed": -1},
        {"total": 999},
    ],
)
def test_stored_mutation_report_rejected(changes: dict[str, int | float]) -> None:
    report = {"total": 5, "killed": 4, "survived": 1, "other": 0, "score": 0.8}
    assert mutation_report.valid_report(report, 0.8)
    report.update(changes)
    assert not mutation_report.valid_report(report, 0.8)


@pytest.fixture
def mutation_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in (
        "scripts/m.py",
        "tests/guardrails/test_m.py",
        "tests/conftest.py",
        "conftest.py",
        "uv.lock",
        "scripts/guardrails_allowlist.txt",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("original\n")
    (tmp_path / "pyproject.toml").write_text("[tool.atalaya]\nmutation_threshold = 0.80\n")
    monkeypatch.setattr(mutation_report, "ROOT", tmp_path)
    assert mutation_report.main(["--snapshot", str(tmp_path / "inputs.json"), "scripts/m.py"]) == 0
    meta = tmp_path / "mutants/scripts/m.py.meta"
    meta.parent.mkdir(parents=True)
    meta.write_text(json.dumps({"exit_code_by_key": {"m": 1}}))
    return tmp_path


def _produce(root: Path) -> int:
    return mutation_report.main(
        [
            "--out",
            str(root / "report.json"),
            "--inputs",
            str(root / "inputs.json"),
            "scripts/m.py",
        ]
    )


@pytest.mark.req("REQ-NFR-018")
@pytest.mark.parametrize(
    "changed",
    [
        "scripts/m.py",
        "tests/guardrails/test_m.py",
        "tests/conftest.py",
        "conftest.py",
        "pyproject.toml",
        "uv.lock",
        "scripts/guardrails_allowlist.txt",
        "tests/new_test.py",
    ],
)
def test_mutation_inputs_change_rejected(mutation_run: Path, changed: str) -> None:
    (mutation_run / changed).write_text("changed\n")
    assert _produce(mutation_run) == 1
    assert not (mutation_run / "report.json").exists()


@pytest.mark.req("REQ-NFR-018")
def test_mutation_snapshot_cannot_revalidate_old_results(mutation_run: Path) -> None:
    assert (
        mutation_report.main(["--snapshot", str(mutation_run / "inputs.json"), "scripts/m.py"]) == 1
    )
    meta = mutation_run / "mutants/scripts/m.py.meta"
    snapshot_time = (mutation_run / "inputs.json").stat().st_mtime_ns
    os.utime(meta, ns=(snapshot_time - 1, snapshot_time - 1))
    assert _produce(mutation_run) == 1


@pytest.mark.req("REQ-NFR-018")
@pytest.mark.parametrize("contents", [None, "invalid JSON", "[]"])
def test_mutation_snapshot_missing_or_invalid(mutation_run: Path, contents: str | None) -> None:
    snapshot = mutation_run / "inputs.json"
    if contents is None:
        snapshot.unlink()
    else:
        snapshot.write_text(contents)
    assert _produce(mutation_run) == 1


@pytest.mark.req("REQ-NFR-018")
def test_mutation_cli_requires_snapshot(mutation_run: Path) -> None:
    assert mutation_report.main(["--out", str(mutation_run / "report.json"), "scripts/m.py"]) == 1


@pytest.mark.req("REQ-NFR-018")
def test_mutation_report_records_complete_input_digest(mutation_run: Path) -> None:
    assert _produce(mutation_run) == 0
    report = json.loads((mutation_run / "report.json").read_text())["scripts/m.py"]
    assert report["inputs_sha256"] == mutation_report.inputs_digest(mutation_run, ["scripts/m.py"])


@pytest.mark.req("REQ-NFR-018")
def test_mutation_report_rejects_inputs_changed_during_generation(
    mutation_run: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_report = mutation_report.report

    def change_input(root: Path, rel: str) -> dict[str, object]:
        result = original_report(root, rel)
        (root / rel).write_text("changed during reporting\n")
        return result

    monkeypatch.setattr(mutation_report, "report", change_input)
    assert _produce(mutation_run) == 1
    assert not (mutation_run / "report.json").exists()

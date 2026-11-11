"""La orden de mutación no acepta ejecuciones vacías, parciales o bajo umbral."""

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mutation_report, mutation_target, run_mutmut


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
    selected_test = tmp_path / "tests/test_selected.py"
    selected_test.parent.mkdir(parents=True)
    selected_test.write_text("assert True\n")
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
        "proto/gen/python/atalaya/v1/options_pb2.py",
        "proto/atalaya/v1/options.proto",
    ],
)
def test_mutation_inputs_change_rejected(mutation_run: Path, changed: str) -> None:
    changed_path = mutation_run / changed
    changed_path.parent.mkdir(parents=True, exist_ok=True)
    changed_path.write_text("changed\n")
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


@pytest.mark.req("REQ-NFR-018")
def test_tests_digest_cubre_seleccion_completa_de_mutmut(tmp_path: Path) -> None:
    selected = tmp_path / "tests/relevant/test_selected.py"
    unrelated = tmp_path / "tests/unrelated/test_unselected.py"
    selected.parent.mkdir(parents=True)
    unrelated.parent.mkdir(parents=True)
    selected.write_text("assert True\n")
    unrelated.write_text("assert True\n")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.mutmut]\npytest_add_cli_args_test_selection = ["tests/relevant/"]\n'
    )

    first = mutation_report.tests_digest(tmp_path)
    unrelated.write_text("assert False\n")
    assert mutation_report.tests_digest(tmp_path) == first
    selected.write_text("assert False\n")
    assert mutation_report.tests_digest(tmp_path) != first


@pytest.mark.req("REQ-NFR-018")
@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        ("[]", "lista no vacía"),
        ('["tests/missing/"]', "ruta de tests de mutmut inexistente"),
    ],
)
def test_tests_digest_rechaza_seleccion_vacia_o_inexistente(
    tmp_path: Path, selection: str, expected: str
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        f"[tool.mutmut]\npytest_add_cli_args_test_selection = {selection}\n"
    )
    with pytest.raises(ValueError, match=expected):
        mutation_report.tests_digest(tmp_path)


@pytest.mark.req("REQ-NFR-018")
def test_mutation_alias_de_contratos_conserva_ruta_de_evidencia(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rel = "proto/python/atalaya_contracts/redact.py"
    source = tmp_path / rel
    source.parent.mkdir(parents=True)
    source.write_text("def redact():\n    return True\n")
    test = tmp_path / "tests/test_selected.py"
    test.parent.mkdir()
    test.write_text("def test_selected():\n    assert True\n")
    (tmp_path / "pyproject.toml").write_text("[tool.atalaya]\nmutation_threshold = 0.80\n")
    monkeypatch.setattr(mutation_report, "ROOT", tmp_path)
    snapshot = tmp_path / "inputs.json"
    assert mutation_report.main(["--snapshot", str(snapshot), rel]) == 0
    meta = mutation_report.mutation_meta_path(tmp_path, rel)
    assert meta == tmp_path / "mutants/src/atalaya_contracts/redact.py.meta"
    meta.parent.mkdir(parents=True)
    meta.write_text(json.dumps({"exit_code_by_key": {"atalaya_contracts.redact.x_redact": 1}}))
    report = tmp_path / "report.json"
    assert mutation_report.main(["--out", str(report), "--inputs", str(snapshot), rel]) == 0
    assert list(json.loads(report.read_text())) == [rel]
    assert mutation_report.main(["--snapshot", str(snapshot), rel]) == 1


@pytest.mark.req("REQ-NFR-018")
@pytest.mark.parametrize(
    ("phase", "legacy", "valid"),
    [("1", "", True), ("0", "", False), ("1", "0", False), ("01", "", False), ("../2", "", False)],
)
def test_mutation_target_rechaza_fases_cerradas_y_legacy(
    tmp_path: Path, phase: str, legacy: str, valid: bool
) -> None:
    closed = tmp_path / "FASES-CERRADAS.txt"
    closed.write_text("# cerradas\n-1\n0\n")
    if valid:
        assert mutation_target.validate_target(phase, legacy, closed) == phase
    else:
        with pytest.raises(ValueError):
            mutation_target.validate_target(phase, legacy, closed)


@pytest.mark.req("REQ-NFR-018")
def test_mutation_target_avanza_tras_cierre_de_fase(tmp_path: Path) -> None:
    closed = tmp_path / "FASES-CERRADAS.txt"
    closed.write_text("# fases cerradas\n-1\n0\n")
    assert mutation_target.active_phase(closed) == "1"
    closed.write_text("# fases cerradas\n-1\n0\n1\n")
    assert mutation_target.active_phase(closed) == "2"
    with pytest.raises(ValueError, match="evidencia inmutable"):
        mutation_target.validate_target("1", "", closed)


@pytest.mark.req("REQ-NFR-018")
def test_runner_recupera_solo_su_alias_temporal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.mutmut]\n")
    (tmp_path / "proto/python/atalaya_contracts").mkdir(parents=True)
    alias = tmp_path / "src/atalaya_contracts"
    alias.parent.mkdir()
    alias.symlink_to("../proto/python/atalaya_contracts", target_is_directory=True)
    monkeypatch.setattr(run_mutmut, "ROOT", tmp_path)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(returncode=0),
    )
    assert run_mutmut.main(["--help"]) == 0
    assert not alias.is_symlink()
    alias.symlink_to("../otro-paquete", target_is_directory=True)
    assert run_mutmut.main(["--help"]) == 2
    assert alias.readlink() == Path("../otro-paquete")

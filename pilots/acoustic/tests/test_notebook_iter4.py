"""Cuaderno de la iteración 4: fuentes nuevas, verificaciones, evaluación y reproducibilidad."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

PILOT_DIR = Path(__file__).resolve().parents[1]
ROOT = PILOT_DIR.parents[1]
NOTEBOOK = PILOT_DIR / "Atalaya_YAMNet_Colab.ipynb"
EMBEDDED = ("grouped_eval", "speech_gate", "remote", "remote_zip", "sources", "predictions")


def _notebook() -> dict:
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def _code() -> str:
    return "\n".join("".join(c["source"]) for c in _notebook()["cells"] if c["cell_type"] == "code")


def _pilot_config() -> dict:
    code = _code()
    start = code.index("PILOT = json.loads('''") + len("PILOT = json.loads('''")
    return json.loads(code[start : code.index("''')", start)])


@pytest.mark.parametrize("module", EMBEDDED)
def test_every_tested_module_is_embedded_verbatim(module: str) -> None:
    source = (PILOT_DIR / "acoustic_pilot" / f"{module}.py").read_text(encoding="utf-8")
    assert source in _code()


def test_notebook_is_valid_nbformat_without_outputs() -> None:
    nb = _notebook()
    assert nb["nbformat"] == 4 and nb["nbformat_minor"] >= 4
    for cell in nb["cells"]:
        assert cell["cell_type"] in {"markdown", "code"}
        if cell["cell_type"] == "code":
            assert cell["outputs"] == [] and cell["execution_count"] is None
            compile("".join(cell["source"]), "<celda>", "exec")


def test_regeneration_is_reproducible(tmp_path: Path) -> None:
    """El cuaderno versionado es exactamente lo que genera build_colab.py (nunca editado a mano)."""
    fresh = tmp_path / "nb.ipynb"
    subprocess.run(  # noqa: S603 - script del propio repositorio
        [sys.executable, str(PILOT_DIR / "build_colab.py"), str(fresh)],
        check=True,
        capture_output=True,
    )
    assert (
        hashlib.sha256(fresh.read_bytes()).hexdigest()
        == hashlib.sha256(NOTEBOOK.read_bytes()).hexdigest()
    )


def test_sources_are_pinned_with_hashes_and_allowed_licenses() -> None:
    cfg = _pilot_config()
    fsd = cfg["fsd50k"]
    assert fsd["record"] == "4060432" and len(fsd["clips"]) >= 500
    allowed = {
        "http://creativecommons.org/publicdomain/zero/1.0/",
        "http://creativecommons.org/licenses/by/3.0/",
        "http://creativecommons.org/licenses/by/4.0/",
    }
    for clip in fsd["clips"]:
        assert clip["license_url"] in allowed
        assert len(clip["sha256"]) == 64 and clip["size"] > 0 and clip["compressed_bytes"] > 0
        assert clip["group_id"].startswith("fsd50k:u-")
    for part in fsd["audio_archives"].values():
        assert len(part["central_directory"]["sha256"]) == 64
    assert all(len(m["sha256"]) == 64 for m in fsd["metadata_archives"])
    aris = cfg["aris"]
    assert aris["record"] == "22682339" and len(aris["archive"]["sha256"]) == 64
    assert {"LICENSE", "SHA256SUMS", "groups.json", aris["split_used"]} <= set(
        aris["inner_files_sha256"]
    )
    esc = cfg["esc10"]
    assert len(esc["files"]) == 318
    total = (
        sum(c["compressed_bytes"] for c in fsd["clips"])
        + aris["archive"]["bytes"]
        + sum(f["bytes"] for f in esc["files"])
        + sum(c["bytes"] for c in cfg["clips"])
    )
    assert total < 2_000_000_000  # límite razonable para Colab gratuito


def test_no_fsd50k_clip_duplicates_an_esc10_freesound_source() -> None:
    cfg = _pilot_config()
    esc_ids = {f["group_id"].split("freesound-")[-1] for f in cfg["esc10"]["files"]}
    assert not esc_ids & {c["fname"] for c in cfg["fsd50k"]["clips"]}


def test_prohibited_sources_are_never_downloaded() -> None:
    code = _code()
    cfg = _pilot_config()
    assert set(cfg["prohibited"]) == {
        "DADS",
        "Al-Emadi",
        "UrbanSound8K",
        "ESC-50 fuera de ESC-10",
        "Sonniss",
        "AeroSonicDB",
    }
    lowered = code.lower()
    for host in ("huggingface.co/datasets", "saraalemadi", "urbansound", "sonniss", "aerosonic"):
        assert f'read_https("https://{host}' not in lowered
    assert "DADS_ENABLED = False" in code
    assert "drive.mount" not in code and "/Users/" not in code


def test_downloads_use_allowed_hosts_and_verify_hashes() -> None:
    code = _code()
    assert 'ZENODO_HOSTS = {"zenodo.org"}' in code
    assert 'SVAN_HOSTS = {"raw.githubusercontent.com", "api.github.com"}' in code
    assert (
        "urllib.request.urlopen" not in code
    )  # todo pasa por read_https (redirecciones comprobadas)
    assert 'verify_fsd50k_pins(FSD["clips"], fsd_gt, fsd_info)' in code
    assert 'hashlib.sha256(data).hexdigest() == clip["sha256"]' in code
    assert 'hashlib.sha256(raw).hexdigest() == cd["sha256"]' in code
    assert 'aris_sums[seg["path"]]' in code
    assert 'aris_record["metadata"]["license"]["id"] == "cc-by-4.0"' in code


def test_evaluation_uses_groups_cv_recall_threshold_and_exports_predictions() -> None:
    code = _code()
    assert "TARGET_RECALL = 0.90" in code and "N_FOLDS = 5" in code
    assert "group_folds(y.tolist(), groups, k=N_FOLDS, seed=SEED)" in code
    assert "rotating_folds(folds, N_FOLDS)" in code
    assert "metrics_by_source(" in code
    assert "predictions_csv(PRED_ROWS)" in code and "recompute_metrics.py" in code
    assert "choose_threshold(" not in code.replace("def choose_threshold(", "")
    # La puerta de voz se aplica a TODAS las fuentes y antes del entrenamiento.
    assert code.index("apply_speech_gate(") < code.index("TRAINING_ALLOWED = True")
    assert '"svanstrom/BACKGROUND_006.wav"' in code


def test_human_cleared_is_kept_with_reviewer_date_and_note() -> None:
    code = _code()
    start = code.index("HUMAN_CLEARED = {")
    block = code[start : code.index("}", start)]
    assert "usuario, 2026-11-11" in block and "no es voz" in block

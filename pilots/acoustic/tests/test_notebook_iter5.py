"""Cuaderno de la iteración 5: fuentes, verificaciones, tratamiento de datos, evaluación y
reproducibilidad (el cuaderno se genera con build_colab.py; nunca se edita a mano)."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

PILOT_DIR = Path(__file__).resolve().parents[1]
ROOT = PILOT_DIR.parents[1]
NOTEBOOK = PILOT_DIR / "Atalaya_YAMNet_Colab.ipynb"
sys.path.insert(0, str(PILOT_DIR))
from build_colab import EMBEDDED  # noqa: E402


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


def test_embedded_modules_cover_iteration5_and_have_unique_top_level_names() -> None:
    assert {
        "data_quality",
        "leakage",
        "balance",
        "augment",
        "windows",
        "calibration",
        "hard_negatives",
        "experiment",
    } <= set(EMBEDDED)
    seen: dict[str, str] = {}
    for module in EMBEDDED:
        tree = ast.parse((PILOT_DIR / "acoustic_pilot" / f"{module}.py").read_text("utf-8"))
        for node in tree.body:
            targets = []
            if isinstance(node, ast.FunctionDef | ast.ClassDef):
                targets = [node.name]
            elif isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            for name in targets:
                # se incrustan en el mismo espacio de nombres: un choque sobrescribiría código
                assert name not in seen, f"{name} en {module} y {seen.get(name)}"
                seen[name] = module


def test_evaluation_uses_sgkf_loso_weights_calibration_and_exports_predictions() -> None:
    code = _code()
    assert "TARGET_RECALL = 0.90" in code and "N_FOLDS = 5" in code
    assert "stratified_group_folds(y.tolist(), groups, k=N_FOLDS, seed=SEED)" in code
    assert "leave_one_source_out(y.tolist(), groups, src, seed=SEED)" in code
    assert "assert_no_cross_partition_pairs(crossing" in code
    assert "class_source_weights(" in code
    assert 'fit_calibrator(yv, pv, "platt"), fit_calibrator(yv, pv, "isotonica")' in code
    assert "choose_threshold_for_recall(yv, apply_calibration(platt, pv)" in code
    assert "predictions_csv(PRED_ROWS, columns=EXTENDED_COLUMNS)" in code
    assert "recompute_metrics.py" in code and "--record modelo_piloto.json" in code
    assert "choose_threshold(" not in code.replace("def choose_threshold(", "")
    # la puerta de voz se aplica a TODAS las fuentes antes del entrenamiento y de la deduplicación
    assert code.index("apply_speech_gate(") < code.index("TRAINING_ALLOWED = True")
    assert code.index("TRAINING_ALLOWED = True") < code.index("exact = exact_duplicates(")
    assert '"svanstrom/BACKGROUND_006.wav"' in code


def test_data_quality_steps_and_discard_report() -> None:
    code = _code()
    for call in (
        "clip_quality(raw, sr)",
        "normalize_format(raw, sr)",
        "loudness_features(signal, TARGET_SR)",
        "exact_duplicates(",
        "near_duplicate_pairs(MEANS, threshold=NEAR_DUPLICATE_COSINE",
        "resolve_near_duplicates(",
        'assert not residual, "quedan casi duplicados entre grupos distintos"',
        '"descartes.csv"',
        "save_shard(path, key, *loaded)",
    ):
        assert call in code, call


def test_augmentation_is_training_only_and_marked_synthetic() -> None:
    code = _code()
    assert "mixes_for_training(MIX_PLAN, train)" in code
    assert "print(SYNTHETIC_NOTE)" in code
    # las mezclas nunca se puntúan: solo se añaden a las matrices de entrenamiento
    assert "MIX_MEANS[mix_ids]" in code
    for line in code.splitlines():
        if "predict_proba" in line:
            assert "MIX_" not in line, line


def test_fa_per_hour_is_labelled_as_unverified_estimate() -> None:
    code = _code()
    assert "false_alarms_per_hour_estimate(" in code and "FA_ESTIMATE_STATUS" in code
    assert "NO VERIFICADA" in code


def test_notebook_embeds_the_hash_of_its_own_code() -> None:
    nb = _notebook()
    code = _code()
    match = re.search(r'NOTEBOOK_CODE_SHA256 = "([0-9a-f]{64})"', code)
    assert match, "falta el hash del código"
    cells = [
        {k: v for k, v in c.items() if k != "id"} for c in nb["cells"]
    ]  # el hash se calcula antes de asignar ids
    for cell in cells:
        cell["source"] = [
            line.replace(match.group(1), "__CODIGO_SHA256__") for line in cell["source"]
        ]
    canon = json.dumps(cells, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canon).hexdigest() == match.group(1)


def test_human_cleared_is_kept_with_reviewer_date_and_note() -> None:
    code = _code()
    start = code.index("HUMAN_CLEARED = {")
    block = code[start : code.index("}", start)]
    assert "usuario, 2026-11-11" in block and "no es voz" in block


def test_speech_discards_are_built_from_the_gate_dicts() -> None:
    """Regresión del ensayo en seco: SPEECH_GATE["excluded"] contiene dicts, no tuplas."""
    from acoustic_pilot.speech_gate import apply_speech_gate

    code = _code()
    start = code.index("SPEECH_DROPPED = [")
    end = code.index('SPEECH_GATE["excluded"]]', start) + len('SPEECH_GATE["excluded"]]')
    statement = code[start:end]
    ns = {
        "SPEECH_GATE": apply_speech_gate(["a.wav", "b.wav", "c.wav"], [0.9, 0.1, float("nan")]),
        "CLIP_SOURCE": {"a.wav": "aris", "b.wav": "esc10", "c.wav": "fsd50k"},
    }
    exec(statement, ns)  # noqa: S102 - código del propio cuaderno generado
    assert ns["SPEECH_DROPPED"] == [
        {
            "clip": "a.wav",
            "fuente": "aris",
            "motivo": "posible voz",
            "detalle": "voz_automatica; max_speech_score=0.9",
        },
        {
            "clip": "c.wav",
            "fuente": "fsd50k",
            "motivo": "posible voz",
            "detalle": "puntuacion_no_valida; max_speech_score=None",  # nunca float(None)
        },
    ]


def test_downloads_are_concurrent_rate_limited_and_checkpointed() -> None:
    code = _code()
    assert "DOWNLOAD_WORKERS = 8" in code
    assert "ZENODO_LIMITER = RateLimiter(120)" in code and "time.sleep(0.45)" not in code
    assert "ZENODO_LIMITER.acquire()" in code
    for fetch in ("fetch_svanstrom", "fetch_esc10", "fetch_fsd50k"):
        assert f"def {fetch}(" in code and "run_concurrent(" in code
    # se reutiliza solo lo verificado por hash; la escritura es atómica
    assert code.count("verified_cached_bytes(") >= 4 and "write_atomic(path, data)" in code
    for label in ("Svanström", "ESC-10", "FSD50K", "ITU ARIS"):
        assert f'Progress("{label}"' in code
    # las verificaciones de licencia y hash siguen ahí
    assert 'hashlib.sha256(data).hexdigest() == clip["sha256"]' in code
    assert 'git_blob_sha1(raw) == f["blob"]' in code


def test_yamnet_runs_in_batches_with_incremental_checkpoints() -> None:
    code = _code()
    assert "YAMNET_SHARD = 256" in code
    assert 'shard_key([(c["clip"], FILE_SHA256[c["clip"]]) for c in items], EMB_CONTEXT)' in code
    assert code.index("loaded = load_shard(path, key)") < code.index(
        "save_shard(path, key, *loaded)"
    )
    assert "drive.mount" not in code

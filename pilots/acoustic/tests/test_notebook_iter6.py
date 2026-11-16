"""H2.5 · Cuaderno de la iteración 6 generado por build_colab.py (nunca editado a mano): módulos
incrustados, fuentes y puertas bloqueadas, LOSO principal, ONNX con fallo cerrado, artefacto y
«Prueba tu audio» (REQ-LEG-009, REQ-NFR-016, REQ-FUN-027)."""

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
NOTEBOOK = PILOT_DIR / "Atalaya_YAMNet_Colab_iter6.ipynb"
sys.path.insert(0, str(PILOT_DIR))
import build_colab  # noqa: E402
from colab_iter6 import COLAB_PINS, ITER6_MODULES, MAIN_VARIANT  # noqa: E402

pytestmark = pytest.mark.req("REQ-LEG-009", "REQ-NFR-016", "REQ-FUN-027")
ALL_MODULES = (*build_colab.EMBEDDED, *ITER6_MODULES)


def _nb() -> dict:
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def _cells() -> list[str]:
    return ["".join(c["source"]) for c in _nb()["cells"] if c["cell_type"] == "code"]


def _code() -> str:
    return "\n".join(_cells())


def _config() -> dict:
    code = _code()
    start = code.index("PILOT = json.loads('''") + len("PILOT = json.loads('''")
    return json.loads(code[start : code.index("''')", start)])


@pytest.mark.parametrize("module", ALL_MODULES)
def test_every_tested_module_is_embedded_verbatim_except_relative_imports(module: str) -> None:
    source = (PILOT_DIR / "acoustic_pilot" / f"{module}.py").read_text(encoding="utf-8")
    stripped = build_colab.RELATIVE_IMPORT.sub("", source)
    assert stripped in _cells(), module
    assert "from ." not in stripped


def test_relative_import_stripping_refuses_unknown_or_late_modules() -> None:
    with pytest.raises(AssertionError):
        build_colab._strip_relative_imports({"a": "from .b import x\n", "b": "x = 1\n"})
    with pytest.raises(AssertionError):
        build_colab._strip_relative_imports({"b": "y = 1\n", "a": "from .b import x\n"})
    out = build_colab._strip_relative_imports(
        {"b": "x = 1\ndef f():\n    pass\n", "a": "from .b import (\n    f,\n    x,\n)\nz = x\n"}
    )
    assert out["a"] == "z = x\n"


def test_embedded_modules_have_unique_top_level_names() -> None:
    seen: dict[str, str] = {}
    for module in ALL_MODULES:
        tree = ast.parse((PILOT_DIR / "acoustic_pilot" / f"{module}.py").read_text("utf-8"))
        for node in tree.body:
            names = []
            if isinstance(node, ast.FunctionDef | ast.ClassDef):
                names = [node.name]
            elif isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            for name in names:
                assert name not in seen, f"{name} en {module} y {seen.get(name)}"
                seen[name] = module


def test_notebook_is_valid_and_regeneration_is_reproducible(tmp_path: Path) -> None:
    nb = _nb()
    assert nb["nbformat"] == 4 and nb["nbformat_minor"] >= 4
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            assert cell["outputs"] == [] and cell["execution_count"] is None
            compile("".join(cell["source"]), "<celda>", "exec")
    fresh = tmp_path / "nb.ipynb"
    subprocess.run(  # noqa: S603 - script del propio repositorio
        [sys.executable, str(PILOT_DIR / "build_colab.py"), "--iter6", str(fresh)],
        check=True,
        capture_output=True,
        cwd=PILOT_DIR,
    )
    assert (
        hashlib.sha256(fresh.read_bytes()).digest()
        == hashlib.sha256(NOTEBOOK.read_bytes()).digest()
    )


def test_notebook_embeds_the_hash_of_its_own_code() -> None:
    code = _code()
    match = re.search(r'NOTEBOOK_CODE_SHA256 = "([0-9a-f]{64})"', code)
    assert match
    cells = [{k: v for k, v in c.items() if k != "id"} for c in _nb()["cells"]]
    for cell in cells:
        cell["source"] = [s.replace(match.group(1), "__CODIGO_SHA256__") for s in cell["source"]]
    canon = json.dumps(cells, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canon).hexdigest() == match.group(1)


def test_prohibited_sources_stay_blocked() -> None:
    code = _code()
    cfg = _config()
    assert set(cfg["prohibited"]) == {
        "DADS",
        "Al-Emadi",
        "UrbanSound8K",
        "ESC-50 fuera de ESC-10",
        "Sonniss",
        "AeroSonicDB",
    }
    lowered = code.lower()
    for host in (
        "huggingface.co/datasets/geronimobasso",
        "saraalemadi",
        "urbansound",
        "sonniss",
        "aerosonic",
        "esc-50/master/audio",
    ):
        assert f'read_https("https://{host}' not in lowered
        assert f'stream_download("https://{host}' not in lowered
    assert "DADS_ENABLED = False" in code and "assert not DADS_ENABLED" in code
    assert (
        'assert set(catalog["fuente"]) <= {"svanstrom", "esc10", "fsd50k", "aris", *EXTRA_ENABLED}'
        in code
    )
    assert "drive.mount" not in code and "/Users/" not in code
    # la configuración no cita ninguna fuente prohibida como descargable
    text = json.dumps({k: v for k, v in cfg.items() if k not in ("prohibited", "dads_card")})
    for name in ("geronimobasso", "DroneAudioDataset", "UrbanSound8K", "sonniss", "aerosonic"):
        assert name.lower() not in text.lower()


def test_extra_drone_sources_enabled_with_recorded_user_authorization() -> None:
    # Decisión del usuario 2026-11-16 (respuesta directa en el chat), registrada en
    # DECISIONES-USUARIO.md: las 3 fuentes extra SOLO para la prueba técnica en Colab.
    quote = "usuario, 2026-11-16: «Sí, las 3 (Recommended)»"
    expected = {"salford": quote, "droneaudioset": quote, "yi_kaist": quote}
    assert expected == build_colab.EXTRA_AUTHORIZATION
    assert quote in build_colab.DECISIONS.read_text(encoding="utf-8")
    code = _code()
    assert f"EXTRA_AUTHORIZATION = {build_colab.EXTRA_AUTHORIZATION!r}" in code
    assert "EXTRA_ENABLED = enabled_extra_sources(EXTRA_AUTHORIZATION)" in code
    for source in ("salford", "droneaudioset", "yi_kaist"):
        assert f'if "{source}" in EXTRA_ENABLED:' in code
    with pytest.raises(AssertionError):  # una autorización inventada no pasa la comprobación
        build_colab._check_authorizations(
            {"salford": "usuario, 2099-01-01: «sí a todo»", "droneaudioset": None, "yi_kaist": None}
        )
    extra = _config()["extra"]
    assert len(extra["salford"]["files"]) == 164
    assert all(len(f["md5"]) == 32 for f in extra["salford"]["files"])
    assert all(len(f["sha256"]) == 64 for f in extra["droneaudioset"]["files"])
    assert extra["yi_kaist"]["file"]["path"] == "drone_A.tar"
    # subconjuntos que caben en Colab gratuito (~100 GB de disco, 12 GB de RAM)
    total = (
        sum(f["bytes"] for f in extra["salford"]["files"])
        + sum(f["bytes"] for f in extra["droneaudioset"]["files"])
        + extra["yi_kaist"]["file"]["bytes"]
    )
    assert total < 5_000_000_000


def test_gates_and_order_of_privacy_steps() -> None:
    code = _code()
    assert code.index("apply_speech_gate(") < code.index("TRAINING_ALLOWED = True")
    assert code.index("TRAINING_ALLOWED = True") < code.index("exact = exact_duplicates(")
    assert "SOURCE_INTAKE_DOWNLOAD_APPROVED = True" in code
    assert "WINDOW_SPEECH = VOZ6 >= SPEECH_EXCLUSION_THRESHOLD" in code
    assert '"svanstrom/BACKGROUND_006.wav"' in code


def test_loso_is_the_main_metric_with_preregistered_model_and_criteria() -> None:
    code = _code()
    assert f"MAIN_VARIANT = {MAIN_VARIANT!r}" in code
    assert "LOSO = leave_one_source_out(y.tolist(), groups, src, seed=SEED)" in code
    assert code.index("LOSO = leave_one_source_out(") < code.index(
        "folds = stratified_group_folds("
    )
    assert "cross_mixes_for_fold(CROSS_PLAN, train, held_out=held_out)" in code
    assert "assert_channel_augs_training_only(CHAN_PLAN, chan, train)" in code
    assert "assert_no_cross_partition_pairs(crossing" in code
    assert "hysteresis_thresholds(" in code and "MAX_FPR_ON = 0.05" in code
    assert "group_dro_fit(" in code and 'inlp_rounds=spec["inlp"]' in code
    assert "persistence_score(" in code
    # criterio C-LOSO (ADR 0018) y D-6 de referencia
    assert ">= 0.85" in code and ">= 0.50" in code and "<= 0.10" in code
    assert "len(training_drone) < 2" in code and '"NO EVALUABLE"' in code
    assert "pr_auc_aris" in code and "modelo que no generaliza" in code
    # las mezclas y copias aumentadas nunca se puntúan
    for line in code.splitlines():
        if "predict_proba" in line or "clip_scores(" in line:
            assert "CROSS_" not in line and "CHAN_" not in line, line


def test_onnx_export_is_pinned_and_fails_closed() -> None:
    code = _code()
    assert COLAB_PINS["tf2onnx"] in code and '"--no-deps"' in code
    assert "PARITY_TOL = 1e-4" in code and "PARITY_WINDOWS = 60" in code
    assert "PARITY_OK = max(diffs_e) <= PARITY_TOL and max(diffs_s) <= PARITY_TOL" in code
    export = code[code.index("# Exportación: predicciones.csv") :]
    guarded = export[export.index("if PARITY_OK:") :]
    assert '(BASE / "modelo_hito2.json").write_bytes(data)' in guarded
    assert '(BASE / "modelo_hito2.json")' not in export[: export.index("if PARITY_OK:")]
    assert "YAMNET_ONNX.unlink(missing_ok=True)" in code
    assert "check_golden(json.loads(data), yamnet_onnx)" in code
    assert "assert len(data) <= 200_000" in code
    # sin reinicio: no se reinstala numpy/protobuf/tensorflow (se fijan a lo instalado)
    deps = _cells()[0]
    assert (
        'keep = [f"{name}=={meta.version(name)}" for name in ("numpy", "protobuf", "tensorflow")]'
        in deps
    )
    assert "Si Colab pide reiniciar" not in deps and "no hace falta reiniciar" in deps


def test_user_audio_section_uses_the_same_route_and_deletes_uploads() -> None:
    code = _code()
    upload = code[code.index("# Prueba tu audio: sube") :]
    assert "files.upload()" in upload and "path.unlink(missing_ok=True)" in upload
    assert "analyze_audio(signal, sr, artifact=ARTIFACT, yamnet_fn=USER_YAMNET)" in upload
    assert "drive" not in upload.lower() and "youtube" not in upload.lower().replace(
        "print(user_audio_note)", ""
    )
    assert "print(USER_AUDIO_NOTE)" in upload
    selfcheck = code[code.index("# Autocomprobación de punta a punta") :]
    assert "FINAL_TEST" in selfcheck and 'assert report["veredicto"] == expected' in selfcheck
    md = "\n".join("".join(c["source"]) for c in _nb()["cells"] if c["cell_type"] == "markdown")
    assert "No descargues audio de YouTube" in md.replace("\n", " ")


def test_downloads_reuse_iteration5_verified_cells() -> None:
    code = _code()
    for fragment in (
        'ZENODO_HOSTS = {"zenodo.org"}',
        'SVAN_HOSTS = {"raw.githubusercontent.com", "api.github.com"}',
        'verify_fsd50k_pins(FSD["clips"], fsd_gt, fsd_info)',
        'aris_record["metadata"]["license"]["id"] == "cc-by-4.0"',
        'assert record["license"]["name"] == "CC BY 4.0"',
        'yi_record["metadata"]["license"]["id"] == "cc-by-4.0"',
    ):
        assert fragment in code, fragment
    assert "urllib.request.urlopen" not in code

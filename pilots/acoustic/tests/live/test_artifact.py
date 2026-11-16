"""H2.6: cargador verificado del artefacto (solo JSON + ONNX, SHA-256 fijados)."""

from __future__ import annotations

import ast
import json
import pickle
import re
import time
from pathlib import Path

import numpy as np
import pytest
from live_helpers import sha256_hex, tiny_onnx, valid_config, write_artifact

from live import artifact
from live.artifact import (
    DEFAULT_HASHES_FILE,
    ArtifactError,
    OnnxEmbeddingModel,
    load_artifact,
    read_pinned_hashes,
)
from live.interfaces import EmbeddingModel

pytestmark = pytest.mark.req("REQ-FUN-027", "REQ-NFR-015")


def test_valid_artifact_loads_and_runs(make_artifact) -> None:
    json_path, hashes = make_artifact()
    t0 = time.perf_counter()
    loaded = load_artifact(json_path, hashes_file=hashes)
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0
    cfg = loaded.config
    assert cfg.window_samples == 15360 and cfg.embedding_dim == 1024 and cfg.num_classes == 521
    assert cfg.coefficients.shape == (1024 + 3,) and cfg.coefficients.dtype == np.float64
    assert cfg.speech_threshold == pytest.approx(0.30)
    model = loaded.model
    assert isinstance(model, EmbeddingModel) and isinstance(model, OnnxEmbeddingModel)
    emb, scores = model.infer(np.zeros(15360, dtype=np.float32))
    assert emb.shape == (1024,) and scores.shape == (521,)


def test_model_rejects_window_of_wrong_length(make_artifact) -> None:
    json_path, hashes = make_artifact()
    model = load_artifact(json_path, hashes_file=hashes).model
    with pytest.raises(ValueError, match="muestras"):
        model.infer(np.zeros(15600, dtype=np.float32))


def test_flipped_byte_in_json_is_rejected_before_loading(make_artifact, monkeypatch) -> None:
    json_path, hashes = make_artifact()
    raw = bytearray(json_path.read_bytes())
    raw[10] ^= 0x01
    json_path.write_bytes(bytes(raw))
    created: list[bytes] = []
    with pytest.raises(ArtifactError, match="SHA-256"):
        load_artifact(json_path, hashes_file=hashes, session_factory=created.append)
    assert created == []  # no se creó ninguna sesión


def test_flipped_byte_in_onnx_is_rejected_before_loading(make_artifact) -> None:
    json_path, hashes = make_artifact()
    onnx_path = json_path.with_name("yamnet.onnx")
    raw = bytearray(onnx_path.read_bytes())
    raw[-1] ^= 0x01
    onnx_path.write_bytes(bytes(raw))
    created: list[bytes] = []
    with pytest.raises(ArtifactError, match="SHA-256"):
        load_artifact(json_path, hashes_file=hashes, session_factory=created.append)
    assert created == []


def test_missing_pinned_hash_fails_closed(make_artifact, tmp_path: Path) -> None:
    json_path, _ = make_artifact()
    empty = tmp_path / "EMPTY_HASHES"
    empty.write_text("# sin entradas\n", encoding="utf-8")
    with pytest.raises(ArtifactError, match="sin hash fijado"):
        load_artifact(json_path, hashes_file=empty)


def test_repo_hashes_file_exists_and_is_well_formed() -> None:
    assert DEFAULT_HASHES_FILE.name == "MODEL_HASHES"
    assert DEFAULT_HASHES_FILE.is_file()
    read_pinned_hashes(DEFAULT_HASHES_FILE)  # no lanza


@pytest.mark.parametrize(
    "line",
    ["zz  modelo_hito2.json", "abc", f"{'0' * 64}  ../fuera.json", f"{'0' * 64}  sub/dir.onnx"],
)
def test_malformed_hash_lines_are_rejected(tmp_path: Path, line: str) -> None:
    path = tmp_path / "H"
    path.write_text(line + "\n", encoding="utf-8")
    with pytest.raises(ArtifactError):
        read_pinned_hashes(path)


def test_duplicate_hash_entries_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "H"
    path.write_text(f"{'0' * 64}  a.json\n{'1' * 64}  a.json\n", encoding="utf-8")
    with pytest.raises(ArtifactError, match="duplicad"):
        read_pinned_hashes(path)


def test_coefficient_dimension_mismatch_is_rejected(make_artifact) -> None:
    json_path, hashes = make_artifact(valid_config(coefficients=[0.0] * 1024))
    with pytest.raises(ArtifactError, match="coefficients"):
        load_artifact(json_path, hashes_file=hashes)


def test_onnx_output_dimension_mismatch_is_rejected(make_artifact) -> None:
    json_path, hashes = make_artifact(onnx_bytes=tiny_onnx(embedding_dim=512))
    with pytest.raises(ArtifactError, match="embeddings"):
        load_artifact(json_path, hashes_file=hashes)


def test_onnx_input_length_mismatch_is_rejected(make_artifact) -> None:
    json_path, hashes = make_artifact(onnx_bytes=tiny_onnx(window_samples=15600))
    with pytest.raises(ArtifactError, match="window_samples"):
        load_artifact(json_path, hashes_file=hashes)


def test_onnx_with_more_than_one_patch_per_window_is_rejected(make_artifact) -> None:
    json_path, hashes = make_artifact(onnx_bytes=tiny_onnx(window_samples="n", patches=2))
    with pytest.raises(ArtifactError, match="parche"):
        load_artifact(json_path, hashes_file=hashes)


def test_onnx_input_name_mismatch_is_rejected(make_artifact) -> None:
    json_path, hashes = make_artifact(onnx_bytes=tiny_onnx(input_name="audio"))
    with pytest.raises(ArtifactError, match="entrada"):
        load_artifact(json_path, hashes_file=hashes)


def test_unknown_field_is_rejected(make_artifact) -> None:
    json_path, hashes = make_artifact(valid_config(extra_field=1))
    with pytest.raises(ArtifactError, match="extra_field"):
        load_artifact(json_path, hashes_file=hashes)


def test_missing_field_is_rejected(make_artifact) -> None:
    cfg = valid_config()
    del cfg["platt"]
    json_path, hashes = make_artifact(cfg)
    with pytest.raises(ArtifactError, match="platt"):
        load_artifact(json_path, hashes_file=hashes)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", 2),
        ("sample_rate", 44100),
        ("window_samples", 16000),
        ("hop_samples", 1000),
        ("speech_threshold", 1.5),
        ("speech_class_indices", [0, 0]),
        ("speech_class_indices", [521]),
        ("speech_class_indices", []),
        ("intercept", True),
        ("onnx_file", "../yamnet.onnx"),
        ("onnx_file", "yamnet.pkl"),
        ("model_id", "con espacio"),
        ("normalization", {"x": [1.0, 2.0]}),
        ("golden_vectors", [{"seed": 1, "expected_probability": 2.0}]),
        ("alert", {"theta_on": 0.5}),
    ],
)
def test_invalid_values_are_rejected(make_artifact, field: str, value: object) -> None:
    json_path, hashes = make_artifact(valid_config(**{field: value}))
    with pytest.raises(ArtifactError):
        load_artifact(json_path, hashes_file=hashes)


def test_non_finite_numbers_are_rejected(make_artifact) -> None:
    raw = json.dumps(valid_config()).replace('"intercept": -0.5', '"intercept": NaN').encode()
    json_path, hashes = make_artifact(json_bytes=raw)
    with pytest.raises(ArtifactError, match="no finito"):
        load_artifact(json_path, hashes_file=hashes)


def test_duplicate_json_keys_are_rejected(make_artifact) -> None:
    raw = json.dumps(valid_config()).replace("{", '{"intercept": 0.0, ', 1).encode()
    json_path, hashes = make_artifact(json_bytes=raw)
    with pytest.raises(ArtifactError, match="duplicad"):
        load_artifact(json_path, hashes_file=hashes)


def test_pickle_file_is_rejected_even_with_matching_hash(tmp_path: Path) -> None:
    directory = tmp_path / "m"
    directory.mkdir()
    payload = pickle.dumps({"coefficients": [0.0]})
    pkl = directory / "modelo_hito2.pkl"
    pkl.write_bytes(payload)
    hashes = tmp_path / "H"
    hashes.write_text(f"{sha256_hex(payload)}  modelo_hito2.pkl\n", encoding="utf-8")
    with pytest.raises(ArtifactError, match="JSON"):
        load_artifact(pkl, hashes_file=hashes)


def test_pickle_bytes_disguised_as_json_are_rejected(make_artifact) -> None:
    json_path, hashes = make_artifact(json_bytes=pickle.dumps({"a": 1}))
    with pytest.raises(ArtifactError, match="pickle"):
        load_artifact(json_path, hashes_file=hashes)


def test_pickle_sibling_in_model_directory_is_rejected(make_artifact) -> None:
    json_path, hashes = make_artifact()
    (json_path.parent / "pesos.pkl").write_bytes(pickle.dumps([1, 2]))
    with pytest.raises(ArtifactError, match="pickle"):
        load_artifact(json_path, hashes_file=hashes)


def test_oversized_json_is_rejected(make_artifact) -> None:
    cfg = valid_config(model_id="x" * 10)
    raw = json.dumps(cfg).encode() + b" " * (artifact.MAX_JSON_BYTES + 1)
    json_path, hashes = make_artifact(json_bytes=raw)
    with pytest.raises(ArtifactError, match="tamaño"):
        load_artifact(json_path, hashes_file=hashes)


def test_loader_never_imports_pickle() -> None:
    tree = ast.parse(Path(artifact.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & {"pickle", "joblib", "dill", "shelve", "marshal"}


def test_artifact_hash_files_written_by_helper_match(tmp_path: Path) -> None:
    # Control del propio ayudante: los hashes que escribe son los de los bytes en disco.
    json_path, hashes = write_artifact(tmp_path / "m")
    pinned = read_pinned_hashes(hashes)
    assert pinned["modelo_hito2.json"] == sha256_hex(json_path.read_bytes())


# --- L1 (revisión legal): la puerta de voz del artefacto no puede relajarse -------------


@pytest.mark.parametrize("threshold", [1.0, 0.5, 0.31, 0.29, 0.0])
def test_speech_threshold_must_equal_pilot_constant(make_artifact, threshold: float) -> None:
    json_path, hashes = make_artifact(valid_config(speech_threshold=threshold))
    with pytest.raises(ArtifactError, match="speech_threshold"):
        load_artifact(json_path, hashes_file=hashes)


@pytest.mark.parametrize("indices", [[10, 11, 12], [0, 1, 2], [1, 2, 3], [500]])
def test_speech_indices_must_cover_canonical_yamnet_speech(make_artifact, indices) -> None:
    json_path, hashes = make_artifact(valid_config(speech_class_indices=indices))
    with pytest.raises(ArtifactError, match="speech_class_indices"):
        load_artifact(json_path, hashes_file=hashes)


def test_speech_indices_superset_is_accepted(make_artifact) -> None:
    json_path, hashes = make_artifact(valid_config(speech_class_indices=[0, 1, 2, 3, 4]))
    cfg = load_artifact(json_path, hashes_file=hashes).config
    assert set(cfg.speech_class_indices) >= {0, 1, 2, 3}


def test_threshold_comes_from_pilot_speech_gate() -> None:
    from acoustic_pilot.speech_gate import SPEECH_EXCLUSION_THRESHOLD

    assert artifact.SPEECH_EXCLUSION_THRESHOLD is SPEECH_EXCLUSION_THRESHOLD


def test_canonical_speech_labels_match_colab_notebook() -> None:
    # build_colab.py (no se modifica) fija las 4 clases de voz por nombre; aquí, por índice.
    source = (Path(artifact.__file__).resolve().parents[1] / "build_colab.py").read_text("utf-8")
    block = source.split("speech_columns = ")[1].split("assert")[0]
    labels = set(re.findall(r'"([^"]+)"', block))
    assert labels == set(artifact.YAMNET_SPEECH_CLASSES.values())

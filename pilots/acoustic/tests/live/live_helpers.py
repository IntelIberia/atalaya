"""Ayudantes de los tests de ``live``: ONNX diminuto y artefactos sintéticos.

El ONNX se codifica a mano en protobuf (sin el paquete ``onnx``) para no añadir dependencias: un
grafo con una entrada de forma ``[window_samples]`` y dos salidas constantes ``scores [1, C]`` y
``embeddings [1, D]``. Basta para probar el cargador con el ``onnxruntime`` real.
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

FLOAT = 1  # TensorProto.FLOAT


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _key(field: int, wire: int) -> bytes:
    return _varint((field << 3) | wire)


def _int(field: int, value: int) -> bytes:
    return _key(field, 0) + _varint(value)


def _bytes(field: int, payload: bytes) -> bytes:
    return _key(field, 2) + _varint(len(payload)) + payload


def _str(field: int, text: str) -> bytes:
    return _bytes(field, text.encode("utf-8"))


def _value_info(name: str, dims: list[int | str]) -> bytes:
    shape = b""
    for dim in dims:
        shape += _bytes(1, _int(1, dim) if isinstance(dim, int) else _str(2, dim))
    tensor_type = _int(1, FLOAT) + _bytes(2, shape)
    return _str(1, name) + _bytes(2, _bytes(1, tensor_type))


def _initializer(name: str, dims: list[int], values: list[float]) -> bytes:
    out = b"".join(_int(1, d) for d in dims) + _int(2, FLOAT) + _str(8, name)
    return out + _bytes(9, struct.pack(f"<{len(values)}f", *values))


def _node(inputs: list[str], outputs: list[str], op: str, name: str) -> bytes:
    out = b"".join(_str(1, i) for i in inputs) + b"".join(_str(2, o) for o in outputs)
    return out + _str(3, name) + _str(4, op)


def tiny_onnx(
    *,
    window_samples: int | str = 15360,
    num_classes: int = 521,
    embedding_dim: int = 1024,
    patches: int = 1,
    input_name: str = "waveform",
) -> bytes:
    """ModelProto mínimo: salidas constantes con la forma de YAMNet para ``patches`` parches."""
    scores = [0.01] * (patches * num_classes)
    emb = [0.5] * (patches * embedding_dim)
    graph = b"".join(
        [
            _bytes(1, _node(["scores_c"], ["scores"], "Identity", "n_scores")),
            _bytes(1, _node(["emb_c"], ["embeddings"], "Identity", "n_emb")),
            _str(2, "tiny_yamnet"),
            _bytes(5, _initializer("scores_c", [patches, num_classes], scores)),
            _bytes(5, _initializer("emb_c", [patches, embedding_dim], emb)),
            _bytes(11, _value_info(input_name, [window_samples])),
            _bytes(12, _value_info("scores", [patches, num_classes])),
            _bytes(12, _value_info("embeddings", [patches, embedding_dim])),
        ]
    )
    opset = _str(1, "") + _int(2, 13)
    return _int(1, 8) + _str(2, "atalaya-tests") + _bytes(7, graph) + _bytes(8, opset)


def valid_config(**overrides: Any) -> dict[str, Any]:
    harmonic = ["f0_hz", "harmonicity", "n_harmonics"]
    config: dict[str, Any] = {
        "schema_version": 1,
        "model_id": "tiny-test-1",
        "onnx_file": "yamnet.onnx",
        "onnx_input": "waveform",
        "onnx_outputs": {"scores": "scores", "embeddings": "embeddings"},
        "sample_rate": 16000,
        "window_samples": 15360,
        "hop_samples": 7680,
        "embedding_dim": 1024,
        "num_classes": 521,
        "harmonic_features": harmonic,
        "coefficients": [0.001] * (1024 + len(harmonic)),
        "intercept": -0.5,
        "platt": {"a": 1.2, "b": -0.1},
        "speech_class_indices": [0, 1, 2, 3],
        "speech_threshold": 0.30,
        "alert": {
            "theta_on": 0.7,
            "theta_off": 0.5,
            "k": 3,
            "n": 5,
            "off_windows": 4,
            "refractory_s": 5.0,
        },
        "normalization": {"target_rms": 0.05, "max_gain_db": 30.0, "band_hz_low": 100.0},
        "golden_vectors": [{"seed": 1, "expected_probability": 0.42}],
    }
    config.update(overrides)
    return config


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_artifact(
    directory: Path,
    config: dict[str, Any] | None = None,
    onnx_bytes: bytes | None = None,
    *,
    json_bytes: bytes | None = None,
) -> tuple[Path, Path]:
    """Escribe JSON + ONNX en ``directory`` y un MODEL_HASHES con sus SHA-256 (en ``tmp``)."""
    directory.mkdir(parents=True, exist_ok=True)
    cfg = valid_config() if config is None else config
    raw_json = json_bytes if json_bytes is not None else json.dumps(cfg).encode("utf-8")
    raw_onnx = tiny_onnx() if onnx_bytes is None else onnx_bytes
    json_path = directory / "modelo_hito2.json"
    json_path.write_bytes(raw_json)
    onnx_name = cfg.get("onnx_file", "yamnet.onnx") if isinstance(cfg, dict) else "yamnet.onnx"
    (directory / str(onnx_name)).write_bytes(raw_onnx)
    hashes = directory.parent / f"{directory.name}_MODEL_HASHES"
    hashes.write_text(
        "# hashes de prueba\n"
        f"{sha256_hex(raw_json)}  modelo_hito2.json\n"
        f"{sha256_hex(raw_onnx)}  {onnx_name}\n",
        encoding="utf-8",
    )
    return json_path, hashes

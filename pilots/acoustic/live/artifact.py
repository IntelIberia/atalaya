"""H2.6: cargador verificado del artefacto del modelo (``modelo_hito2.json`` + ``yamnet.onnx``).

Orden fijo y en fallo cerrado:

1. Solo se acepta un ``.json``; un ``.pkl`` (o cualquier fichero tipo pickle junto al modelo)
   se rechaza. Nunca se usa ``pickle`` ni ``joblib``.
2. Se leen los bytes **una vez**, se calcula su SHA-256 y se compara con el fijado en
   ``live/MODEL_HASHES`` (o el fichero indicado). Sin hash fijado no se carga nada.
3. Se analiza el JSON en modo estricto (sin claves duplicadas, sin NaN/Infinity) y se valida el
   esquema: claves exactas, tipos, rangos y dimensiones.
4. Igual con el ONNX; la sesión se crea **desde esos mismos bytes** (sin segunda lectura).
5. Se comprueban la entrada y las salidas de la sesión y se ejecuta una ventana de ceros: debe
   dar exactamente un parche de ``num_classes`` puntuaciones y ``embedding_dim`` valores.

Los ficheros del modelo viven fuera de Git (decisión D-8); en el repo solo están sus hashes.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from live.alert import AlertConfig

DEFAULT_HASHES_FILE = Path(__file__).resolve().with_name("MODEL_HASHES")
SCHEMA_VERSION = 1
SAMPLE_RATE = 16_000
# YAMNet: 0,96 s por parche. El valor exacto (15 360 o 15 600) lo fija el ONNX real (H2.7).
ALLOWED_WINDOW_SAMPLES = (15_360, 15_600)
MAX_JSON_BYTES = 200 * 1024
MAX_ONNX_BYTES = 64 * 1024 * 1024
PICKLE_SUFFIXES = frozenset({".pkl", ".pickle", ".joblib", ".npy", ".npz", ".dill"})
_HASH_LINE = re.compile(r"^([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9._-]*)$")
_MODEL_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_ONNX_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.onnx$")
_NAME = re.compile(r"^[A-Za-z0-9_:./-]{1,128}$")

_TOP_LEVEL = frozenset(
    {
        "schema_version",
        "model_id",
        "onnx_file",
        "onnx_input",
        "onnx_outputs",
        "sample_rate",
        "window_samples",
        "hop_samples",
        "embedding_dim",
        "num_classes",
        "harmonic_features",
        "coefficients",
        "intercept",
        "platt",
        "speech_class_indices",
        "speech_threshold",
        "alert",
        "normalization",
        "golden_vectors",
    }
)
_ALERT_KEYS = frozenset({"theta_on", "theta_off", "k", "n", "off_windows", "refractory_s"})


class ArtifactError(ValueError):
    """El artefacto no supera la verificación; no se ha cargado nada."""


@dataclass(frozen=True)
class ModelConfig:
    model_id: str
    onnx_file: str
    onnx_input: str
    scores_output: str
    embeddings_output: str
    sample_rate: int
    window_samples: int
    hop_samples: int
    embedding_dim: int
    num_classes: int
    harmonic_features: tuple[str, ...]
    coefficients: NDArray[np.float64]
    intercept: float
    platt_a: float
    platt_b: float
    speech_class_indices: tuple[int, ...]
    speech_threshold: float
    alert: AlertConfig
    normalization: Mapping[str, float | int | str | bool]
    golden_vectors: tuple[Mapping[str, float | int], ...]


class OnnxEmbeddingModel:
    """``EmbeddingModel`` sobre una sesión ONNX ya verificada."""

    def __init__(self, session: Any, config: ModelConfig) -> None:
        self._session = session
        self._config = config
        self.window_samples = config.window_samples

    def infer(self, window: NDArray[np.float32]) -> tuple[NDArray[Any], NDArray[Any]]:
        arr = np.asarray(window, dtype=np.float32)
        if arr.ndim != 1 or arr.shape[0] != self.window_samples:
            raise ValueError(
                f"la ventana debe tener {self.window_samples} muestras mono, no {arr.shape}"
            )
        cfg = self._config
        scores, emb = self._session.run(
            [cfg.scores_output, cfg.embeddings_output], {cfg.onnx_input: arr}
        )
        return np.asarray(emb)[0], np.asarray(scores)[0]


@dataclass(frozen=True)
class LoadedArtifact:
    config: ModelConfig
    model: OnnxEmbeddingModel


SessionFactory = Callable[[bytes], Any]


def _default_session_factory(onnx_bytes: bytes) -> Any:
    import onnxruntime as ort  # importación diferida: solo con el extra live o dev

    options = ort.SessionOptions()
    options.log_severity_level = 3
    options.enable_profiling = False
    options.optimized_model_filepath = ""  # nunca escribir el modelo optimizado a disco
    providers = ["CPUExecutionProvider"]
    return ort.InferenceSession(onnx_bytes, sess_options=options, providers=providers)


def read_pinned_hashes(path: Path) -> dict[str, str]:
    """Lee ``<sha256>  <nombre>`` por línea (formato ``sha256sum``); ``#`` inicia comentario."""
    pinned: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ArtifactError(f"no se puede leer el fichero de hashes {path.name}: {exc}") from exc
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _HASH_LINE.match(line)
        if not match:
            raise ArtifactError(f"{path.name}:{number}: línea de hash mal formada")
        digest, name = match.groups()
        if name in pinned:
            raise ArtifactError(f"{path.name}:{number}: hash duplicado para {name}")
        pinned[name] = digest
    return pinned


def _read_verified(path: Path, pinned: Mapping[str, str], limit: int) -> bytes:
    expected = pinned.get(path.name)
    if expected is None:
        raise ArtifactError(f"{path.name} sin hash fijado: no se carga")
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ArtifactError(f"no se puede leer {path.name}: {exc}") from exc
    if size > limit:
        raise ArtifactError(f"{path.name}: tamaño {size} B supera el límite de {limit} B")
    data = path.read_bytes()
    if len(data) > limit:
        raise ArtifactError(f"{path.name}: tamaño supera el límite de {limit} B")
    actual = hashlib.sha256(data).hexdigest()
    if not hmac.compare_digest(actual, expected):
        raise ArtifactError(f"{path.name}: SHA-256 no coincide con el fijado")
    return data


def _reject_constant(name: str) -> Any:
    raise ArtifactError(f"valor no finito en el JSON: {name}")


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ArtifactError(f"clave duplicada en el JSON: {key}")
        out[key] = value
    return out


def _parse_json(data: bytes) -> dict[str, Any]:
    if data[:1] == b"\x80":
        raise ArtifactError("el fichero parece un pickle; solo se acepta JSON")
    try:
        obj = json.loads(
            data.decode("utf-8"),
            parse_constant=_reject_constant,
            object_pairs_hook=_no_duplicates,
        )
    except ArtifactError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"JSON inválido: {exc}") from exc
    if not isinstance(obj, dict):
        raise ArtifactError("el JSON del modelo debe ser un objeto")
    return obj


def _num(value: Any, field: str, *, lo: float | None = None, hi: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ArtifactError(f"{field}: debe ser un número")
    out = float(value)
    if not math.isfinite(out):
        raise ArtifactError(f"{field}: valor no finito")
    if (lo is not None and out < lo) or (hi is not None and out > hi):
        raise ArtifactError(f"{field}: {out} fuera de [{lo}, {hi}]")
    return out


def _int(value: Any, field: str, *, lo: int = 0, hi: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ArtifactError(f"{field}: debe ser un entero")
    if value < lo or (hi is not None and value > hi):
        raise ArtifactError(f"{field}: {value} fuera de [{lo}, {hi}]")
    return value


def _str(value: Any, field: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.match(value):
        raise ArtifactError(f"{field}: texto no válido")
    return value


def _exact_keys(obj: Any, keys: frozenset[str], field: str) -> Mapping[str, Any]:
    if not isinstance(obj, dict):
        raise ArtifactError(f"{field}: debe ser un objeto")
    unknown = sorted(set(obj) - keys)
    missing = sorted(keys - set(obj))
    if unknown:
        raise ArtifactError(f"{field}: campos desconocidos {unknown}")
    if missing:
        raise ArtifactError(f"{field}: faltan campos {missing}")
    return obj


def _validate(obj: Mapping[str, Any]) -> ModelConfig:
    _exact_keys(obj, _TOP_LEVEL, "modelo")
    if _int(obj["schema_version"], "schema_version") != SCHEMA_VERSION:
        raise ArtifactError(f"schema_version: se esperaba {SCHEMA_VERSION}")
    sample_rate = _int(obj["sample_rate"], "sample_rate")
    if sample_rate != SAMPLE_RATE:
        raise ArtifactError(f"sample_rate: se esperaba {SAMPLE_RATE}")
    window = _int(obj["window_samples"], "window_samples")
    if window not in ALLOWED_WINDOW_SAMPLES:
        raise ArtifactError(f"window_samples: {window} no está en {ALLOWED_WINDOW_SAMPLES}")
    hop = _int(obj["hop_samples"], "hop_samples")
    if hop != window // 2:
        raise ArtifactError("hop_samples: debe ser la mitad de window_samples (salto 0,48 s)")
    embedding_dim = _int(obj["embedding_dim"], "embedding_dim", lo=1, hi=4096)
    num_classes = _int(obj["num_classes"], "num_classes", lo=1, hi=4096)

    harmonic = obj["harmonic_features"]
    if not isinstance(harmonic, list) or len(harmonic) > 32:
        raise ArtifactError("harmonic_features: debe ser una lista de ≤ 32 nombres")
    harmonic_names = tuple(_str(h, "harmonic_features", _NAME) for h in harmonic)
    if len(set(harmonic_names)) != len(harmonic_names):
        raise ArtifactError("harmonic_features: nombres duplicados")

    coefficients = obj["coefficients"]
    expected = embedding_dim + len(harmonic_names)
    if not isinstance(coefficients, list) or len(coefficients) != expected:
        got = len(coefficients) if isinstance(coefficients, list) else type(coefficients).__name__
        raise ArtifactError(
            f"coefficients: dimensión {got} ≠ embedding_dim + rasgos armónicos = {expected}"
        )
    coef = np.array([_num(c, "coefficients") for c in coefficients], dtype=np.float64)

    platt = _exact_keys(obj["platt"], frozenset({"a", "b"}), "platt")
    speech = obj["speech_class_indices"]
    if not isinstance(speech, list) or not speech:
        raise ArtifactError("speech_class_indices: lista no vacía obligatoria")
    speech_idx = tuple(_int(i, "speech_class_indices", lo=0, hi=num_classes - 1) for i in speech)
    if len(set(speech_idx)) != len(speech_idx):
        raise ArtifactError("speech_class_indices: índices duplicados")

    alert = _exact_keys(obj["alert"], _ALERT_KEYS, "alert")
    try:
        alert_cfg = AlertConfig.from_mapping(alert)
    except ValueError as exc:
        raise ArtifactError(f"alert: {exc}") from exc

    normalization = obj["normalization"]
    if not isinstance(normalization, dict) or len(normalization) > 64:
        raise ArtifactError("normalization: debe ser un objeto de ≤ 64 escalares")
    norm: dict[str, float | int | str | bool] = {}
    for key, value in normalization.items():
        _str(key, "normalization", _NAME)
        if isinstance(value, bool | str):
            norm[key] = value
        else:
            norm[key] = _num(value, f"normalization.{key}")

    golden = obj["golden_vectors"]
    if not isinstance(golden, list) or len(golden) > 16:
        raise ArtifactError("golden_vectors: debe ser una lista de ≤ 16 entradas")
    golden_out = []
    for i, item in enumerate(golden):
        entry = _exact_keys(item, frozenset({"seed", "expected_probability"}), f"golden[{i}]")
        golden_out.append(
            {
                "seed": _int(entry["seed"], f"golden[{i}].seed"),
                "expected_probability": _num(
                    entry["expected_probability"], f"golden[{i}].expected_probability", lo=0, hi=1
                ),
            }
        )

    outputs = _exact_keys(obj["onnx_outputs"], frozenset({"scores", "embeddings"}), "onnx_outputs")
    return ModelConfig(
        model_id=_str(obj["model_id"], "model_id", _MODEL_ID),
        onnx_file=_str(obj["onnx_file"], "onnx_file", _ONNX_NAME),
        onnx_input=_str(obj["onnx_input"], "onnx_input", _NAME),
        scores_output=_str(outputs["scores"], "onnx_outputs.scores", _NAME),
        embeddings_output=_str(outputs["embeddings"], "onnx_outputs.embeddings", _NAME),
        sample_rate=sample_rate,
        window_samples=window,
        hop_samples=hop,
        embedding_dim=embedding_dim,
        num_classes=num_classes,
        harmonic_features=harmonic_names,
        coefficients=coef,
        intercept=_num(obj["intercept"], "intercept"),
        platt_a=_num(platt["a"], "platt.a"),
        platt_b=_num(platt["b"], "platt.b"),
        speech_class_indices=speech_idx,
        speech_threshold=_num(obj["speech_threshold"], "speech_threshold", lo=0.0, hi=1.0),
        alert=alert_cfg,
        normalization=norm,
        golden_vectors=tuple(golden_out),
    )


def _check_session(session: Any, cfg: ModelConfig) -> None:
    inputs = session.get_inputs()
    if len(inputs) != 1 or inputs[0].name != cfg.onnx_input:
        names = [i.name for i in inputs]
        raise ArtifactError(f"entrada del ONNX {names} ≠ [{cfg.onnx_input}]")
    shape = list(inputs[0].shape)
    if len(shape) != 1:
        raise ArtifactError(f"entrada del ONNX con forma {shape}: se esperaba 1 dimensión")
    if isinstance(shape[0], int) and shape[0] != cfg.window_samples:
        raise ArtifactError(f"entrada del ONNX de {shape[0]} muestras ≠ window_samples")
    outputs = {o.name for o in session.get_outputs()}
    for name in (cfg.scores_output, cfg.embeddings_output):
        if name not in outputs:
            raise ArtifactError(f"salida {name} ausente en el ONNX")
    probe = np.zeros(cfg.window_samples, dtype=np.float32)
    try:
        scores, emb = session.run(
            [cfg.scores_output, cfg.embeddings_output], {cfg.onnx_input: probe}
        )
    except Exception as exc:  # error del runtime: se traduce y se rechaza
        raise ArtifactError(f"el ONNX no ejecuta una ventana de prueba: {exc}") from exc
    scores, emb = np.asarray(scores), np.asarray(emb)
    if scores.ndim != 2 or emb.ndim != 2 or scores.shape[0] != 1 or emb.shape[0] != 1:
        raise ArtifactError(
            f"una ventana debe dar un único parche; scores {scores.shape}, embeddings {emb.shape}"
        )
    if scores.shape[1] != cfg.num_classes:
        raise ArtifactError(f"scores con {scores.shape[1]} clases ≠ num_classes")
    if emb.shape[1] != cfg.embedding_dim:
        raise ArtifactError(f"embeddings de dimensión {emb.shape[1]} ≠ embedding_dim")
    if not (np.isfinite(scores).all() and np.isfinite(emb).all()):
        raise ArtifactError("el ONNX produce valores no finitos con una ventana de ceros")


def load_artifact(
    json_path: Path,
    *,
    hashes_file: Path = DEFAULT_HASHES_FILE,
    session_factory: SessionFactory | None = None,
) -> LoadedArtifact:
    """Verifica y carga el artefacto. Cualquier fallo lanza ``ArtifactError`` sin cargar nada."""
    json_path = Path(json_path)
    if json_path.suffix != ".json":
        raise ArtifactError(f"{json_path.name}: solo se acepta un fichero JSON (nunca pickle)")
    directory = json_path.parent
    if directory.is_dir():
        suspicious = sorted(
            p.name for p in directory.iterdir() if p.suffix.lower() in PICKLE_SUFFIXES
        )
        if suspicious:
            raise ArtifactError(f"ficheros tipo pickle junto al modelo: {suspicious}")
    pinned = read_pinned_hashes(hashes_file)
    config = _validate(_parse_json(_read_verified(json_path, pinned, MAX_JSON_BYTES)))
    onnx_bytes = _read_verified(directory / config.onnx_file, pinned, MAX_ONNX_BYTES)
    factory = session_factory or _default_session_factory
    session = factory(onnx_bytes)
    _check_session(session, config)
    return LoadedArtifact(config=config, model=OnnxEmbeddingModel(session, config))

# Ruta de inferencia por ventana y artefacto del modelo (hito 2, H2.5). La MISMA función
# window_features/score_features se usa al entrenar en Colab, en «Prueba tu audio» y en el Mac:
# ventana de 16 kHz -> normalización de canal (channel_norm) -> YAMNet (TF en Colab, ONNX en el
# Mac; se inyecta como función) -> rasgo armónico (harmonic) -> lineal -> Platt. El artefacto
# modelo_hito2.json es solo JSON (nunca pickle), pequeño, con hash propio y vectores dorados: tres
# entradas sintéticas regenerables por semilla con su salida esperada, para comprobar en el Mac
# que normalización, rasgos y pesos son los de Colab. Autocontenido salvo las importaciones
# relativas, que build_colab.py quita porque en el cuaderno ya están definidas.
import hashlib
import json
import math
from collections.abc import Callable, Sequence

import numpy as np

from .alert_logic import validate_alert_config
from .channel_norm import NORM_SR, WINDOW_SAMPLES, norm_config_sha256, normalize_window, to_mono_16k
from .harmonic import HARMONIC_CONFIG, HARMONIC_DIM, HARMONIC_NAMES, harmonic_features

ARTIFACT_FORMAT = "atalaya-hito2-modelo/1"
EMBEDDING_DIM = 1024
YAMNET_CLASSES = 521
GOLDEN_KINDS = ("peine", "ruido_rosa", "tono_y_ruido")
GOLDEN_SR = 48000
GOLDEN_TOLERANCE = 1e-4
ARTIFACT_LABEL = "Reproducción en sala, no vuelo real"
ARTIFACT_KEYS = {
    "formato",
    "iteracion",
    "rotulo",
    "modelo",
    "calibracion",
    "alerta",
    "normalizacion",
    "armonico",
    "yamnet",
    "voz",
    "vectores_dorados",
    "criterios",
    "predicciones_csv_sha256",
    "registro_experimento_sha256",
    "artefacto_sha256",
}
# Una función YAMNet recibe una ventana float32 de 16 kHz y devuelve (scores (n, 521),
# embeddings (n, 1024)); con WINDOW_SAMPLES muestras n = 1.
YamnetFn = Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]


def _sigm(z: np.ndarray | float) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(np.asarray(z, dtype=np.float64), -60, 60)))


def platt_from_logit(logit: np.ndarray | float, a: float, b: float) -> np.ndarray:
    """Platt sobre la probabilidad cruda, con el mismo recorte (1e-6) que calibration.py."""
    q = np.clip(_sigm(logit), 1e-6, 1 - 1e-6)
    return _sigm(a * np.log(q / (1 - q)) + b)


def window_features(window16k: np.ndarray, yamnet_fn: YamnetFn, speech_indices: Sequence[int]):
    """Ventana de 16 kHz (WINDOW_SAMPLES; se rellena si es más corta) -> rasgos."""
    x = np.asarray(window16k, dtype=np.float32)
    if x.ndim != 1 or x.size == 0 or x.size > WINDOW_SAMPLES:
        raise ValueError("se esperaba una ventana 1D de hasta WINDOW_SAMPLES muestras")
    if x.size < WINDOW_SAMPLES:
        x = np.pad(x, (0, WINDOW_SAMPLES - x.size))
    norm = normalize_window(x)
    scores, embeddings = yamnet_fn(norm)
    scores = np.asarray(scores, dtype=np.float64).reshape(-1, YAMNET_CLASSES)[0]
    emb = np.asarray(embeddings, dtype=np.float64).reshape(-1, EMBEDDING_DIM)[0]
    return {
        "normalizada": norm,
        "scores": scores,
        "embedding": emb,
        "armonico": harmonic_features(norm).astype(np.float64),
        "voz": float(scores[list(speech_indices)].max()) if len(speech_indices) else 0.0,
    }


def feature_vector(embedding: np.ndarray, harmonic: np.ndarray) -> np.ndarray:
    v = np.concatenate([np.asarray(embedding, np.float64), np.asarray(harmonic, np.float64)])
    if v.shape != (EMBEDDING_DIM + HARMONIC_DIM,):
        raise ValueError("dimensión de rasgos inesperada")
    return v


def score_features(artifact: dict, embedding: np.ndarray, harmonic: np.ndarray) -> dict:
    """Logit lineal, probabilidad cruda y calibrada (Platt) de una ventana."""
    m, cal = artifact["modelo"], artifact["calibracion"]
    logit = float(feature_vector(embedding, harmonic) @ np.asarray(m["coef"]) + m["intercept"])
    return {
        "logit": logit,
        "prob": float(_sigm(logit)),
        "prob_cal": float(platt_from_logit(logit, cal["a"], cal["b"])),
    }


def golden_input(seed: int, kind: str, sr: int = GOLDEN_SR) -> np.ndarray:
    """Entrada sintética determinista (PCG64 de numpy, estable entre plataformas) de una ventana
    a la frecuencia sr; se pasa por to_mono_16k como el audio del micrófono."""
    if kind not in GOLDEN_KINDS:
        raise ValueError(f"tipo dorado desconocido: {kind}")
    rng = np.random.default_rng(seed)
    n = int(math.ceil(WINDOW_SAMPLES * sr / NORM_SR))
    t = np.arange(n) / sr
    if kind == "peine":
        f0 = rng.uniform(100, 300)
        x = sum(np.sin(2 * np.pi * h * f0 * t + rng.uniform(0, 6.28)) / h for h in range(1, 13))
        x = x + 0.05 * rng.standard_normal(n)
    elif kind == "ruido_rosa":
        spec = np.fft.rfft(rng.standard_normal(n))
        f = np.fft.rfftfreq(n, 1 / sr)
        spec[1:] /= np.sqrt(f[1:])
        spec[0] = 0
        x = np.fft.irfft(spec, n)
    else:
        x = np.sin(2 * np.pi * rng.uniform(500, 2000) * t) + 0.3 * rng.standard_normal(n)
    x = 0.1 * x / np.std(x)
    return x.astype(np.float32)


def golden_record(
    artifact: dict, yamnet_fn: YamnetFn, seed: int, kind: str, sr: int = GOLDEN_SR
) -> dict:
    window = to_mono_16k(golden_input(seed, kind, sr), sr)
    feats = window_features(window, yamnet_fn, artifact["voz"]["indices"])
    s = score_features(artifact, feats["embedding"], feats["armonico"])
    return {
        "semilla": int(seed),
        "tipo": kind,
        "sr": int(sr),
        "esperado": {
            "normalizada_rms": float(
                np.sqrt(np.mean(feats["normalizada"].astype(np.float64) ** 2))
            ),
            "normalizada_primeras": [float(v) for v in feats["normalizada"][:8]],
            "armonico": [float(v) for v in feats["armonico"]],
            "embedding_l2": float(np.linalg.norm(feats["embedding"])),
            "embedding_primeros": [float(v) for v in feats["embedding"][:8]],
            "voz": feats["voz"],
            **s,
        },
    }


def _flatten(expected: dict) -> list[float]:
    out = []
    for key in sorted(expected):
        v = expected[key]
        out += [float(x) for x in v] if isinstance(v, list) else [float(v)]
    return out


def check_golden(artifact: dict, yamnet_fn: YamnetFn, *, tol: float = GOLDEN_TOLERANCE) -> float:
    """Reproduce los vectores dorados; devuelve la máxima diferencia y falla si supera tol."""
    worst = 0.0
    for g in artifact["vectores_dorados"]:
        got = golden_record(artifact, yamnet_fn, g["semilla"], g["tipo"], g["sr"])["esperado"]
        if sorted(got) != sorted(g["esperado"]):
            raise ValueError("campos distintos en un vector dorado")
        diff = np.max(np.abs(np.array(_flatten(got)) - np.array(_flatten(g["esperado"]))))
        worst = max(worst, float(diff))
    if not worst <= tol:
        raise ValueError(f"los vectores dorados no se reproducen: diferencia {worst:.3g} > {tol}")
    return worst


def artifact_sha256(artifact: dict) -> str:
    body = {k: v for k, v in artifact.items() if k != "artefacto_sha256"}
    data = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()


def build_artifact(
    *,
    model: dict,
    platt: dict,
    alert: dict,
    yamnet_info: dict,
    speech_indices: Sequence[int],
    speech_names: Sequence[str],
    speech_threshold: float,
    criteria: dict,
    predictions_sha256: str,
    record_sha256: str,
    yamnet_fn: YamnetFn,
    golden_seeds: Sequence[int] = (101, 202, 303),
) -> dict:
    """Arma, firma (hash propio) y valida el artefacto; calcula los vectores dorados con
    yamnet_fn (en Colab, la sesión ONNX que usará el Mac)."""
    artifact = {
        "formato": ARTIFACT_FORMAT,
        "iteracion": 6,
        "rotulo": ARTIFACT_LABEL,
        "modelo": {
            "nombre": str(model["nombre"]),
            "rasgos": {"embedding_dim": EMBEDDING_DIM, "armonico": list(HARMONIC_NAMES)},
            "coef": [float(v) for v in model["coef"]],
            "intercept": float(model["intercept"]),
            "inlp_direcciones": int(model.get("inlp_direcciones", 0)),
        },
        "calibracion": {"metodo": "platt", "a": float(platt["a"]), "b": float(platt["b"])},
        "alerta": validate_alert_config(alert),
        "normalizacion": {"sha256": norm_config_sha256()},
        "armonico": {"config": HARMONIC_CONFIG, "nombres": list(HARMONIC_NAMES)},
        "yamnet": dict(yamnet_info),
        "voz": {
            "indices": [int(i) for i in speech_indices],
            "nombres": list(speech_names),
            "umbral": float(speech_threshold),
        },
        "vectores_dorados": [],
        "criterios": criteria,
        "predicciones_csv_sha256": predictions_sha256,
        "registro_experimento_sha256": record_sha256,
    }
    artifact["vectores_dorados"] = [
        golden_record(artifact, yamnet_fn, seed, kind)
        for seed, kind in zip(golden_seeds, GOLDEN_KINDS, strict=True)
    ]
    artifact["artefacto_sha256"] = artifact_sha256(artifact)
    validate_artifact(artifact)
    return artifact


def validate_artifact(artifact: dict) -> None:
    """Esquema, dimensiones, números finitos, coherencia con el código local y hash propio."""
    if set(artifact) != ARTIFACT_KEYS:
        raise ValueError(f"campos inesperados o ausentes: {sorted(set(artifact) ^ ARTIFACT_KEYS)}")
    if artifact["formato"] != ARTIFACT_FORMAT:
        raise ValueError("formato de artefacto desconocido")
    m = artifact["modelo"]
    if len(m["coef"]) != EMBEDDING_DIM + HARMONIC_DIM:
        raise ValueError("los coeficientes no cuadran con embedding + rasgo armónico")
    if m["rasgos"]["armonico"] != list(HARMONIC_NAMES) or m["rasgos"]["embedding_dim"] != 1024:
        raise ValueError("orden o nombres de rasgos distintos de los del código")
    numbers = [
        *m["coef"],
        m["intercept"],
        artifact["calibracion"]["a"],
        artifact["calibracion"]["b"],
    ]
    if not all(isinstance(v, int | float) and math.isfinite(v) for v in numbers):
        raise ValueError("coeficientes no finitos")
    if artifact["calibracion"]["a"] <= 0:
        raise ValueError("calibración de Platt no creciente")
    if artifact["normalizacion"]["sha256"] != norm_config_sha256():
        raise ValueError("la normalización del artefacto no es la del código local")
    if artifact["armonico"]["config"] != HARMONIC_CONFIG:
        raise ValueError("la configuración del rasgo armónico no es la del código local")
    validate_alert_config(artifact["alerta"])
    voice = artifact["voz"]
    if not voice["indices"] or any(not 0 <= i < YAMNET_CLASSES for i in voice["indices"]):
        raise ValueError("índices de voz no válidos")
    if len(artifact["vectores_dorados"]) != len(GOLDEN_KINDS):
        raise ValueError("faltan vectores dorados")
    if artifact_sha256(artifact) != artifact["artefacto_sha256"]:
        raise ValueError("el hash propio del artefacto no cuadra")

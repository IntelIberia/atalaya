"""Build a self-contained, public-data-only Colab pilot notebook (iteración 5).

The notebook embeds hashes and source references, never audio, repository secrets,
or the private Atalaya repository. Run this after the pinned source manifests exist
(``build_sources.py`` fija FSD50K e ITU ARIS). Salida determinista: mismo repo => mismos bytes.
"""

# ruff: noqa: E501 - the notebook code is kept readable inside embedded cells.

from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from pathlib import Path

from acoustic_pilot.extra_sources import (
    EXTRA_SOURCES,
    droneaudioset_selection,
    salford_selection,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "ml/datasets/svanstrom/manifest.json"
ESC10_MANIFEST = ROOT / "ml/datasets/esc10/manifest.json"
FSD50K_MANIFEST = ROOT / "ml/datasets/fsd50k-subset/manifest.json"
ARIS_MANIFEST = ROOT / "ml/datasets/itu-aris/manifest.json"
OUTPUT = ROOT / "pilots/acoustic/Atalaya_YAMNet_Colab.ipynb"
# Código probado en pilots/acoustic/tests; se incrusta literalmente (Colab no accede al repo).
PILOT_PKG = ROOT / "pilots/acoustic/acoustic_pilot"
EMBEDDED = (
    "grouped_eval",
    "speech_gate",
    "remote",
    "remote_zip",
    "sources",
    "predictions",
    "data_quality",
    "leakage",
    "balance",
    "augment",
    "windows",
    "calibration",
    "hard_negatives",
    "experiment",
    "checkpoints",
)
CODE_SHA_PLACEHOLDER = "__CODIGO_SHA256__"
UPSTREAM_LICENSE_SHA256 = "a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499"
ESC10_COMMIT = "33c8ce9eb2cf0b1c2f8bcf322eb349b6be34dbb6"
# Fuentes prohibidas (licencia incompatible o sin trazabilidad por clip): nunca se descargan.
PROHIBITED = (
    "DADS",
    "Al-Emadi",
    "UrbanSound8K",
    "ESC-50 fuera de ESC-10",
    "Sonniss",
    "AeroSonicDB",
)


def md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(True)}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(True),
    }


def _svanstrom() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["commit"] == "e7a6eaf9760fa3f9ecc37d09cd11a8cd20be90dd"
    assert manifest["license"] == "CC0-1.0"
    assert manifest["license_evidence"]["upstream_sha256"] == UPSTREAM_LICENSE_SHA256
    assert manifest["group_status"] in {"provisional", "verified"}
    clips = [
        {k: c[k] for k in ("path", "sha256", "bytes", "group_id", "training_excluded")}
        for c in manifest["clips"]
    ]
    assert len(clips) == 90
    return {
        "commit": manifest["commit"],
        "license_sha256": UPSTREAM_LICENSE_SHA256,
        "group_status": manifest["group_status"],
        "clips": [dict(c, name=c.pop("path")) for c in clips],
    }


def _esc10() -> dict:
    m = json.loads(ESC10_MANIFEST.read_text())
    assert m["commit"] == ESC10_COMMIT and m["license"] == "CC-BY-3.0"
    admitted = [
        f
        for f in m["files"]
        if not f["training_excluded"] and f["clip_license_upstream_attribution"] in {"CC0", "CC-BY"}
    ]
    assert len(admitted) == m["admitted_file_count"] == 318
    assert not {f["category"] for f in admitted} & {"crying_baby", "sneezing"}
    return {
        "commit": m["commit"],
        "license_git_blob_sha1": m["license_evidence"]["upstream_git_blob_sha1"],
        "metadata_csv_sha256": m["metadata_csv_sha256"],
        "files": [
            {
                "path": f["path"],
                "bytes": f["bytes"],
                "blob": f["upstream_git_blob_sha1"],
                "category": f["category"],
                "group_id": "esc10:" + f["group_id"],
            }
            for f in admitted
        ],
    }


def _fsd50k() -> dict:
    m = json.loads(FSD50K_MANIFEST.read_text())
    assert m["dataset_license"] == "CC-BY-4.0" and m["intake_approved"] is False
    allowed = {"CC0-1.0", "CC-BY-3.0", "CC-BY-4.0"}
    assert all(c["license"] in allowed for c in m["clips"])
    keep = (
        "fname",
        "split",
        "target_label",
        "license_url",
        "uploader",
        "group_id",
        "member",
        "disk",
        "offset",
        "compressed_bytes",
        "size",
        "method",
        "crc32",
        "sha256",
    )
    return {
        "record": m["source"].rsplit("/", 1)[-1],
        "license_sha256": m["license_evidence"]["sha256"],
        "metadata_archives": m["metadata_archives"],
        "audio_archives": m["audio_archives"],
        "clips": [{k: c[k] for k in keep} for c in m["clips"]],
    }


def _aris() -> dict:
    m = json.loads(ARIS_MANIFEST.read_text())
    assert m["license"] == "CC-BY-4.0" and m["intake_approved"] is False
    return {
        "record": m["source"].rsplit("/", 1)[-1],
        "archive": m["archive"],
        "inner_prefix": m["inner_prefix"],
        "inner_files_sha256": m["inner_files_sha256"],
        "split_used": m["split_used"],
        "segment_count": m["segment_count"],
    }


INTRO = """# Atalaya · piloto acústico YAMNet · iteración 5 (tratamiento de datos avanzado)

**Exploración técnica; no es un detector operativo.** Prueba técnica aislada en Colab
(ADR 0016): nada de este cuaderno entra en el producto. Las cifras no son métricas de campo.

| Fuente | Papel | Licencia verificada en la fuente | Verificación por fichero |
|---|---|---|---|
| [DroneDetectionThesis v1.0.0](https://github.com/DroneDetectionThesis/Drone-detection-dataset/releases/tag/v1.0.0) (Svanström et al.) | dron, helicóptero, fondo | CC0 (LICENSE por SHA-256) | SHA-256 por WAV |
| [ESC-10](https://github.com/karolpiczak/ESC-50) (Piczak, commit fijado) | negativos (solo clases admitidas, sin sonidos humanos) | CC BY 3.0 (LICENSE por Git blob) y CC0/CC BY por clip | tamaño + Git blob SHA-1 del commit; SHA-256 calculado |
| [FSD50K](https://zenodo.org/records/4060432) (Fonseca et al.), subconjunto | confusores: motores, motos, barcos, aviones, insectos, viento, lluvia, aves | dataset CC BY 4.0; **por clip solo CC0 y CC BY**, releída en `clips_info` de la fuente | directorio central por SHA-256; tamaño, CRC-32 y SHA-256 por clip |
| [ITU ARIS Lab](https://zenodo.org/records/22682339) (Muhacıroğlu y Akgül) | dron (hasta ~2 km) y fondo de la misma sesión | CC BY 4.0 (API de Zenodo + LICENSE por SHA-256) | ZIP por SHA-256 y `SHA256SUMS` de los autores por WAV |

**Prohibidas** (nunca se descargan): DADS, Al-Emadi, UrbanSound8K, ESC-50 fuera de ESC-10,
Sonniss y AeroSonicDB. Fraunhofer IDMT solo se audita por metadatos (dirección de llegada, fase
posterior). Mismas fuentes que la iteración 4; ninguna dependencia nueva (numpy, SciPy y
scikit-learn, BSD; sin cleanlab, que es AGPL).

**Descarga total ≈ 1,25 GB** (Colab gratuito, CPU, ~12 GB de RAM). Descargas concurrentes
(8 hilos, hosts y redirecciones comprobados, reintentos con `Retry-After`) con un límite global
de 120 peticiones/minuto hacia Zenodo; progreso visible por fuente.

**Puntos de control en `/content` (sin Drive):** cada fichero descargado se reutiliza solo si su
hash coincide, y YAMNet se calcula por lotes que se guardan al terminar (`checkpoints/*.npz` con
hash de entrada). Si el kernel se reinicia o se reconecta a la misma máquina, «Ejecutar todas»
salta lo ya descargado y calculado. Si Colab **recicla la máquina**, `/content` se pierde y hay
que empezar de cero (no se monta Drive por ADR 0016).

**Puerta automática de privacidad:** se excluyen del entrenamiento y la evaluación los clips con
`max_speech_score >= 0,30` en **todas** las fuentes; `HUMAN_CLEARED` registra las escuchas humanas.

**Novedades de la iteración 5 (todo el código probado en `pilots/acoustic/tests`):**
1. **Calidad de datos:** formato normalizado (mono, 16 kHz, float32); clips silenciosos,
   saturados o corruptos detectados y descartados; sonoridad (RMS y LUFS aproximado) **solo como
   característica**; duplicados exactos (hash del PCM) y casi duplicados (coseno de embeddings
   YAMNet ≥ 0,995); informe de todo lo descartado.
2. **Fugas y dominio:** `StratifiedGroupKFold` (5 folds) por grupo y **leave-one-source-out**;
   ningún casi duplicado queda a ambos lados de una partición (se comprueba).
3. **Desequilibrio:** pesos por clase y por fuente (ITU ARIS no domina) y muestreo balanceado.
4. **Aumento** (solo entrenamiento): drones mezclados sobre fondos negativos a SNR −10…+20 dB,
   ganancia y desplazamiento temporal, marcados `synthetic=true`; **no cuentan como rendimiento real**.
5. **Ventanas:** modelo por ventana YAMNet con agregación media, máximo, top-3, máximo suavizado y
   atención ligera, frente a la media de embeddings por clip.
6. **Calibración** Platt e isotónica en validación, ECE, diagrama de fiabilidad, curvas DET y PR;
   umbral con recall ≥ 0,90 en validación; falsas alarmas por hora **estimadas** sobre
   concatenaciones de negativos: **NO VERIFICADAS** como métrica de campo.
7. **Negativos difíciles:** segunda ronda reponderada y falsas alarmas por **tipo** de negativo
   (orienta qué grabar en Ceuta).
8. **Registro:** semillas, configuración, hashes de datos y del código, versiones,
   `predicciones.csv` con SHA-256 y `pilots/acoustic/recompute_metrics.py` para recalcularlo todo.

Svanström sigue con grupos provisionales (sin IDs de vuelo/sesión): las cifras llevan el rótulo
de contaminación no descartada. Pesos de [YAMNet](https://www.kaggle.com/models/google/yamnet)
(Google): Apache 2.0. No se usa micrófono, audio de clientes, acceso al GitHub privado ni montaje
de Drive.
"""


def _embedded_sources(names: tuple[str, ...]) -> dict[str, str]:
    sources_src = {name: (PILOT_PKG / f"{name}.py").read_text(encoding="utf-8") for name in names}
    for name, text in sources_src.items():
        assert "__future__" not in text, name  # se incrusta a mitad de cuaderno
        assert "from acoustic_pilot" not in text, name
    return sources_src


def _base_config() -> dict:
    svan = _svanstrom()
    return {
        "source_commit": svan["commit"],
        "license_sha256": svan["license_sha256"],
        "group_status": svan["group_status"],
        "clips": svan["clips"],
        "esc10": _esc10(),
        "fsd50k": _fsd50k(),
        "aris": _aris(),
        "prohibited": list(PROHIBITED),
        "fraunhofer_record": "https://zenodo.org/api/records/17525811",
        "dads_card": "https://huggingface.co/datasets/geronimobasso/drone-audio-detection-samples",
    }


def _iter5_cells(config: dict, sources_src: dict[str, str]) -> list[dict]:
    """Celdas de la iteración 5 (también fuente de las celdas de descarga de la iteración 6)."""
    cells = [
        md(INTRO),
        code("""# Dependencias para el entorno actual de Colab; se comprueba la versión de TensorFlow.
import importlib.metadata as meta
import subprocess, sys
tf_version = meta.version("tensorflow")
tf_minor = ".".join(tf_version.split(".")[:2])
print("TensorFlow de Colab:", tf_version)
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q",
                       "tensorflow-hub==0.16.1", f"tf-keras=={tf_minor}.*",
                       "librosa>=0.10.2,<0.12", "scikit-learn>=1.4,<2",
                       "soundfile>=0.12,<1"])
print("Dependencias preparadas. Si Colab pide reiniciar el entorno, reinícialo y vuelve a ejecutar.")
"""),
        code(
            """import csv, hashlib, io, json, random, wave, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import librosa
import librosa.display
import tensorflow as tf
import tensorflow_hub as hub
from IPython.display import Audio, display
# Las celdas siguientes definen el código probado en pilots/acoustic/tests (incrustado tal cual):
# grouped_eval, speech_gate, remote (descargas restringidas), remote_zip (ZIP por rangos),
# sources (licencias por clip, selección y grupos), predictions (CSV con hash) y, nuevos en la
# iteración 5, data_quality, leakage, balance, augment, windows, calibration, hard_negatives y
# experiment.

PILOT = json.loads('''"""
            + json.dumps(config, ensure_ascii=False, separators=(",", ":"))
            + """''')
SEED = 20261111
N_PER_CLASS = 30  # todos los WAV inventariados de Svanström por clase; el duplicado excluido sigue fuera.
TARGET_RECALL = 0.90  # criterio del umbral, elegido SOLO en validación
N_FOLDS = 5
# Iteración 5 (valores documentados en docs/evidence/piloto-acustico; no se ajustan mirando test):
N_MIXES = 1500       # mezclas sintéticas dron + fondo (solo entrenamiento)
MAX_FRAMES = 8       # ventanas YAMNet por clip en el entrenamiento del modelo por ventanas
HN_FRACTION = 0.10   # fracción de negativos de entrenamiento reponderados en la segunda ronda
HN_FACTOR = 3.0      # factor de peso de esos negativos difíciles
REFRACTORY_S = 5.0   # dos flancos a menos de 5 s cuentan como una alarma (FA/h estimada)
OPERATING_CALIBRATION = "platt"  # calibración del punto de operación; la isotónica se compara
CODE_VERSION = "iteracion-5"
NOTEBOOK_CODE_SHA256 = "__CODIGO_SHA256__"  # SHA-256 de las celdas (con este marcador), fijado al generar
BASE = Path("/content/atalaya_piloto")
BASE.mkdir(parents=True, exist_ok=True)
COMMIT = PILOT["source_commit"]
PROHIBITED = PILOT["prohibited"]
print("Svanström:", COMMIT[:12], len(PILOT["clips"]), "| ESC-10:", len(PILOT["esc10"]["files"]),
      "| FSD50K:", len(PILOT["fsd50k"]["clips"]), "| ITU ARIS:", PILOT["aris"]["segment_count"])
print("Fuentes prohibidas (no se descargan):", ", ".join(PROHIBITED))
"""
        ),
        *[code(sources_src[name]) for name in EMBEDDED],
        code("""# Svanström: licencia original antes de descargar datos (hosts y redirecciones restringidos).
SVAN_HOSTS = {"raw.githubusercontent.com", "api.github.com"}
def read_source(url):
    return read_https(url, SVAN_HOSTS, timeout=90)

ROOT_URL = f"https://raw.githubusercontent.com/DroneDetectionThesis/Drone-detection-dataset/{COMMIT}"
license_bytes = read_source(ROOT_URL + "/LICENSE")
assert hashlib.sha256(license_bytes).hexdigest() == PILOT["license_sha256"]
assert b"CC0 1.0 Universal" in license_bytes
print("Licencia CC0 original verificada por SHA-256.")
"""),
        code("""# Svanström: selección reproducible y descarga con SHA-256 por archivo. Solo datos públicos.
# Decisión del usuario 2026-11-11 («Pero te lo autorizo, estoy despierto»): SOLO prueba técnica aislada
# en Colab; los WAV y el modelo nunca entran en el producto. Los manifiestos del repo siguen sin aprobar.
SOURCE_INTAKE_DOWNLOAD_APPROVED = True
assert SOURCE_INTAKE_DOWNLOAD_APPROVED, "Procedencia por WAV sin verificar: no repetir la ingesta."
assert 1 <= N_PER_CLASS <= 30
randomizer = random.Random(SEED)
selected = []
for prefix in ("BACKGROUND", "HELICOPTER", "DRONE"):
    candidates = sorted((c for c in PILOT["clips"] if c["name"].startswith(prefix + "_")),
                        key=lambda c: c["name"])
    assert len(candidates) == 30
    candidates = [c for c in candidates if not c["training_excluded"]]
    unique = sorted({c["sha256"]: c for c in candidates}.values(), key=lambda c: c["name"])
    assert len(unique) == len(candidates), "duplicado exacto sin marcar training_excluded"
    selected += randomizer.sample(unique, min(N_PER_CLASS, len(unique)))
assert len({c["sha256"] for c in selected}) == len(selected)

CATALOG = []  # una fila por clip: fuente, id único, ruta local, etiqueta, grupo, partición fijada
(BASE / "svanstrom").mkdir(exist_ok=True)
DOWNLOAD_WORKERS = 8  # descargas concurrentes; cada fichero se verifica por hash antes de usarse

def fetch_svanstrom(item):
    # Punto de control: un WAV ya presente solo se reutiliza si su SHA-256 coincide.
    name = item["name"]
    assert name.replace("_", "").replace(".", "").isalnum() and name.endswith(".wav")
    path = BASE / "svanstrom" / name
    if verified_cached_bytes(path, item["sha256"]) is None:
        raw = read_source(f"{ROOT_URL}/Data/Audio/{name}")
        assert len(raw) == item["bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"], name
        write_atomic(path, raw)
    return path

svan_paths = run_concurrent(selected, fetch_svanstrom, workers=DOWNLOAD_WORKERS,
                            on_done=Progress("Svanström", len(selected), every=30))
for item, path in zip(selected, svan_paths):
    name = item["name"]
    with wave.open(str(path), "rb") as wav:
        assert wav.getframerate() == 44100 and wav.getsampwidth() == 2
        assert wav.getnchannels() in (1, 2) and 9.9 <= wav.getnframes()/44100 <= 10.1
    CATALOG.append({"clip": f"svanstrom/{name}", "fuente": "svanstrom", "path": path,
                    "clase": name.split("_")[0], "dron": int(name.startswith("DRONE_")),
                    "grupo": "svanstrom:" + item["group_id"], "split": None})
print(f"Svanström: {len(selected)} WAV verificados ({sum(c['bytes'] for c in selected)/1e6:.1f} MB).")
"""),
        code("""# ESC-10 (CC BY 3.0) en el commit fijado; nunca ESC-50 completo (CC BY-NC).
# Licencia: Git blob del LICENSE + texto CC BY 3.0 para ESC-10; meta/esc50.csv por SHA-256; cada
# fichero marcado esc10=True. Solo clases admitidas: sin crying_baby ni sneezing (sonidos humanos)
# ni licencias por clip CC Sampling+. Por fichero: tamaño y Git blob SHA-1 publicados en el commit
# (identificador de contenido de git; no es control criptográfico) y SHA-256 calculado e impreso.
ESC = PILOT["esc10"]
ESC_URL = f"https://raw.githubusercontent.com/karolpiczak/ESC-50/{ESC['commit']}"
def git_blob_sha1(data):
    return hashlib.sha1(b"blob %d\\0" % len(data) + data, usedforsecurity=False).hexdigest()  # nosemgrep
esc_license = read_https(ESC_URL + "/LICENSE", SVAN_HOSTS, limit=1 << 21)
assert git_blob_sha1(esc_license) == ESC["license_git_blob_sha1"]
assert b"The ESC-10 subset is licensed as a Creative Commons Attribution 3.0" in esc_license
esc_meta = read_https(ESC_URL + "/meta/esc50.csv", SVAN_HOSTS, limit=1 << 21)
assert hashlib.sha256(esc_meta).hexdigest() == ESC["metadata_csv_sha256"]
esc10_rows = {r["filename"]: r for r in csv.DictReader(io.StringIO(esc_meta.decode("utf-8")))}
assert all(esc10_rows[f["path"].split("/")[-1]]["esc10"] == "True" for f in ESC["files"])
assert not {f["category"] for f in ESC["files"]} & {"crying_baby", "sneezing"}
(BASE / "esc10").mkdir(exist_ok=True)
esc_inventory = hashlib.sha256()

def fetch_esc10(f):
    # Punto de control: se reutiliza solo si tamaño y Git blob coinciden; si no, se descarga.
    path = BASE / "esc10" / f["path"].split("/")[-1]
    raw = path.read_bytes() if path.is_file() else b""
    if len(raw) != f["bytes"] or git_blob_sha1(raw) != f["blob"]:
        raw = read_https(f"{ESC_URL}/{f['path']}", SVAN_HOSTS, limit=1 << 20)
        assert len(raw) == f["bytes"] and git_blob_sha1(raw) == f["blob"], path.name
        write_atomic(path, raw)
    return path, raw

esc_fetched = run_concurrent(ESC["files"], fetch_esc10, workers=DOWNLOAD_WORKERS,
                             on_done=Progress("ESC-10", len(ESC["files"]), every=80))
for f, (path, raw) in zip(ESC["files"], esc_fetched):
    name = path.name
    esc_inventory.update(f"{hashlib.sha256(raw).hexdigest()}  {name}\\n".encode())
    CATALOG.append({"clip": f"esc10/{name}", "fuente": "esc10", "path": path, "clase": f["category"],
                    "dron": 0, "grupo": f["group_id"], "split": None})
print(f"ESC-10: licencia CC BY 3.0 verificada; {len(ESC['files'])} clips admitidos verificados "
      f"({sum(f['bytes'] for f in ESC['files'])/1e6:.1f} MB); SHA-256 del inventario {esc_inventory.hexdigest()}")
"""),
        code("""# FSD50K (Zenodo 4060432): licencia POR CLIP verificada en los metadatos de la fuente original.
# Se descargan doc/ground_truth/metadata (SHA-256 fijado), se relee la licencia de cada clip fijado
# en clips_info (solo CC0 y CC BY), se comprueba que no tenga etiquetas humanas ni de música ni
# mencione drones, y se leen SOLO esos clips del ZIP original por rangos HTTP (directorio central
# por SHA-256; cada clip por tamaño, CRC-32 y SHA-256).
FSD = PILOT["fsd50k"]
ZENODO_HOSTS = {"zenodo.org"}
def zenodo_file(record, key):
    return f"https://zenodo.org/api/records/{record}/files/{key}/content"
fsd_record = json.loads(read_https(f"https://zenodo.org/api/records/{FSD['record']}", ZENODO_HOSTS, limit=1 << 22))
assert fsd_record["doi"] == "10.5281/zenodo.4060432"
remote_sizes = {f["key"]: f["size"] for f in fsd_record["files"]}
fsd_zips = {}
for item in FSD["metadata_archives"]:
    assert remote_sizes[item["key"]] == item["bytes"], item["key"]
    raw = read_https(zenodo_file(FSD["record"], item["key"]), ZENODO_HOSTS, limit=item["bytes"])
    assert len(raw) == item["bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"], item["key"]
    fsd_zips[item["key"]] = zipfile.ZipFile(io.BytesIO(raw))
fsd_license = fsd_zips["FSD50K.doc.zip"].read("FSD50K.doc/LICENSE-DATASET")
assert hashlib.sha256(fsd_license).hexdigest() == FSD["license_sha256"]
assert b"Attribution 4.0 International (CC BY 4.0)" in fsd_license
fsd_gt = {p: read_fsd50k_ground_truth(fsd_zips["FSD50K.ground_truth.zip"].read(
              f"FSD50K.ground_truth/{p}.csv").decode("utf-8"), p) for p in ("dev", "eval")}
fsd_info = {p: json.loads(fsd_zips["FSD50K.metadata.zip"].read(
                f"FSD50K.metadata/{p}_clips_info_FSD50K.json")) for p in ("dev", "eval")}
problems = verify_fsd50k_pins(FSD["clips"], fsd_gt, fsd_info)
assert not problems, problems[:10]
licenses = pd.Series([ALLOWED_CLIP_LICENSES[fsd_info[c["split"]][c["fname"]]["license"]] for c in FSD["clips"]])
print("FSD50K: licencia por clip verificada en la fuente:", licenses.value_counts().to_dict())

cds = {}
for part, info in FSD["audio_archives"].items():
    for vol in info["volumes"]:
        assert remote_sizes[vol["key"]] == vol["bytes"], vol["key"]
    cd = info["central_directory"]
    key = info["volumes"][cd["disk"]]["key"]
    raw = read_https(zenodo_file(FSD["record"], key), ZENODO_HOSTS, byte_range=(cd["offset"], cd["offset"] + cd["bytes"]))
    assert hashlib.sha256(raw).hexdigest() == cd["sha256"], f"directorio central {part}"
    cds[part] = {e["name"]: e for e in parse_central_directory(raw, cd["n_entries"])}
(BASE / "fsd50k").mkdir(exist_ok=True)
# Descarga concurrente (DOWNLOAD_WORKERS hilos) con un límite GLOBAL de 120 peticiones/minuto
# compartido entre hilos (Zenodo admite ~133) y reintentos con Retry-After en read_https. Cada
# clip ya presente se reutiliza solo si su SHA-256 coincide (punto de control en /content).
ZENODO_LIMITER = RateLimiter(120)

def zenodo_range(url, byte_range):
    ZENODO_LIMITER.acquire()
    return read_https(url, ZENODO_HOSTS, byte_range=byte_range)

def fetch_fsd50k(clip):
    part = clip["split"]
    entry = cds[part][clip["member"]]
    assert all(entry[k] == clip[k] for k in ("disk", "offset", "size", "method", "crc32"))
    assert entry["compressed_size"] == clip["compressed_bytes"]
    path = BASE / "fsd50k" / f"{int(clip['fname'])}.wav"
    if verified_cached_bytes(path, clip["sha256"]) is not None:
        return path
    vols = FSD["audio_archives"][part]["volumes"]
    sizes = [v["bytes"] for v in vols]
    span = LOCAL_HEADER_LEN + len(clip["member"].encode()) + 512 + clip["compressed_bytes"]
    span = min(span, sum(sizes[clip["disk"]:]) - clip["offset"])
    raw = b"".join(zenodo_range(zenodo_file(FSD["record"], vols[d]["key"]), (a, b))
                   for d, a, b in volume_ranges(clip["disk"], clip["offset"], span, sizes))
    head = local_header_length(raw, clip["member"])
    data = decode_member(raw[head:head + clip["compressed_bytes"]], method=clip["method"],
                         size=clip["size"], crc32=clip["crc32"])
    assert hashlib.sha256(data).hexdigest() == clip["sha256"], clip["fname"]
    write_atomic(path, data)
    return path

already = sum(verified_cached_bytes(BASE / "fsd50k" / f"{int(c['fname'])}.wav", c["sha256"]) is not None
              for c in FSD["clips"])
print(f"FSD50K: {already}/{len(FSD['clips'])} clips ya verificados en /content; se descargan el resto")
fsd_paths = run_concurrent(FSD["clips"], fetch_fsd50k, workers=DOWNLOAD_WORKERS,
                           on_done=Progress("FSD50K", len(FSD["clips"]), every=50))
for clip, path in zip(FSD["clips"], fsd_paths):
    CATALOG.append({"clip": f"fsd50k/{clip['fname']}.wav", "fuente": "fsd50k", "path": path,
                    "clase": clip["target_label"], "dron": 0, "grupo": clip["group_id"], "split": None})
print(f"FSD50K: {len(FSD['clips'])} clips verificados ({sum(c['compressed_bytes'] for c in FSD['clips'])/1e6:.0f} MB "
      f"descargados); {len({c['group_id'] for c in FSD['clips']})} autores (grupos).")
"""),
        code("""# ITU ARIS Lab (Zenodo 22682339, CC BY 4.0): licencia en la API y en el LICENSE del ZIP; ZIP por
# SHA-256; cada WAV contra el SHA256SUMS de los autores (fijado por SHA-256). Grupos y partición de
# los autores (groups.json, split interval_disjoint): segmentos solapados al 50 %, nunca al azar.
ARIS = PILOT["aris"]
aris_record = json.loads(read_https(f"https://zenodo.org/api/records/{ARIS['record']}", ZENODO_HOSTS, limit=1 << 22))
assert aris_record["metadata"]["license"]["id"] == "cc-by-4.0"
assert aris_record["doi"] == "10.5281/zenodo.22682339"
arch = ARIS["archive"]
assert {f["key"]: f["size"] for f in aris_record["files"]}[arch["key"]] == arch["bytes"]
zip_path = BASE / arch["key"]
if verified_cached_bytes(zip_path, arch["sha256"]) is None:  # punto de control: ZIP verificado
    raw = read_https(zenodo_file(ARIS["record"], arch["key"]), ZENODO_HOSTS, limit=arch["bytes"])
    assert len(raw) == arch["bytes"] and hashlib.sha256(raw).hexdigest() == arch["sha256"]
    write_atomic(zip_path, raw)
    del raw
else:
    print("ITU ARIS: ZIP ya verificado en /content")
aris_zip = zipfile.ZipFile(zip_path)
inner = {}
for name, digest in ARIS["inner_files_sha256"].items():
    inner[name] = aris_zip.read(ARIS["inner_prefix"] + name)
    assert hashlib.sha256(inner[name]).hexdigest() == digest, name
assert b"Creative Commons Attribution 4.0 International (CC BY 4.0)" in inner["LICENSE"]
aris_sums = parse_sha256sums(inner["SHA256SUMS"].decode("utf-8"))
aris_rows = aris_segments(json.loads(inner["groups.json"]), json.loads(inner[ARIS["split_used"]]))
assert len(aris_rows) == ARIS["segment_count"]
(BASE / "aris").mkdir(exist_ok=True)
aris_progress = Progress("ITU ARIS", len(aris_rows), every=1000)
for n, seg in enumerate(aris_rows, 1):
    path = BASE / "aris" / seg["path"].split("/")[-1]
    if verified_cached_bytes(path, aris_sums[seg["path"]]) is None:
        data = aris_zip.read(ARIS["inner_prefix"] + seg["path"])
        assert hashlib.sha256(data).hexdigest() == aris_sums[seg["path"]], seg["path"]
        write_atomic(path, data)
    aris_progress(n, len(aris_rows))
    CATALOG.append({"clip": "aris/" + seg["path"].split("/")[-1], "fuente": "aris", "path": path,
                    "clase": "ARIS_" + ("DRONE" if seg["label"] else "BACKGROUND"), "dron": seg["label"],
                    "grupo": seg["group_id"], "split": seg["split"]})
print(f"ITU ARIS: licencia CC BY 4.0 verificada; {len(aris_rows)} segmentos verificados contra SHA256SUMS; "
      f"{len({s['group_id'] for s in aris_rows})} grupos (intervalos/bloques).")
catalog = pd.DataFrame(CATALOG)
assert catalog["clip"].is_unique
display(catalog.groupby(["fuente", "dron"]).agg(clips=("clip", "size"), grupos=("grupo", "nunique")))
"""),
        md("""## Revisión de privacidad

Escucha al menos una muestra de cada fuente y clase y comprueba que no haya voz identificable u
otros datos personales. Tras YAMNet, una **puerta automática** excluye del entrenamiento y la
evaluación los clips con `max_speech_score >= 0,30` en **todas** las fuentes y los lista; no
sustituye esta escucha. Si la escucha detecta voz en un clip no excluido, no entrenes; documenta
el clip y resuelve su tratamiento antes de seguir. El audio permanece solo en el almacenamiento
temporal de este entorno de Colab.
"""),
        code("""# Reproducción de un clip por fuente y clase para revisión humana.
for (source, label), part in catalog.groupby(["fuente", "dron"]):
    row = part.sort_values("clip").iloc[0]
    audio, sr = librosa.load(row["path"], sr=None, mono=True)
    print(source, "dron" if label else "no dron", row["clip"], f"{len(audio)/sr:.1f} s")
    display(Audio(audio, rate=sr))
"""),
        code("""# Intake pendiente: los manifiestos del repo siguen con intake_approved=false.
# Esta celda documenta el bloqueo; no se desbloquea cambiando una casilla.
# Decisión del usuario 2026-11-11: entrenamiento solo como prueba técnica; revisión de voz automática con
# la puntuación de voz de YAMNet (no sustituye a una escucha humana). Generalización: NO acreditada.
TRAINING_ALLOWED = True
assert TRAINING_ALLOWED, "Intake sin aprobar: derechos por fichero, revisión de voz, data card y agrupación."
"""),
        code("""# YAMNet oficial + calidad de datos (código probado: data_quality). Cada clip se lee en su formato
# original, se comprueba (corrupto, silencioso, saturado) y se normaliza a mono, 16 kHz, float32.
# La sonoridad (RMS, LUFS aproximado) se usa SOLO como característica: la señal que recibe YAMNet
# no se modifica. YAMNet se calcula POR LOTES de YAMNET_SHARD clips y cada lote se guarda al
# terminar en /content/atalaya_piloto/checkpoints (npz con hash de entrada: clips + SHA-256 +
# modelo + código). Si el kernel se reinicia, al reejecutar se cargan los lotes ya hechos y solo
# se calcula lo que falta. Sin Drive: si Colab recicla la máquina, /content se pierde.
MODEL_URL = "https://tfhub.dev/google/yamnet/1"
yamnet = hub.load(MODEL_URL)
class_names = pd.read_csv(yamnet.class_map_path().numpy().decode())["display_name"].tolist()
assert len(class_names) == 521
speech_columns = [i for i, label in enumerate(class_names)
                  if label in {"Speech", "Conversation", "Narration, monologue", "Child speech, kid speaking"}]
assert len(speech_columns) == 4
N_MFCC = 40
LOUDNESS_KEYS = ("rms_dbfs", "lufs_aprox", "pico_dbfs", "factor_cresta_db")
PATHS = {c["clip"]: c["path"] for c in CATALOG}
CLIP_SOURCE = {c["clip"]: c["fuente"] for c in CATALOG}
FILE_SHA256 = {c["clip"]: hashlib.sha256(Path(c["path"]).read_bytes()).hexdigest() for c in CATALOG}
DATA_INVENTORY_SHA256 = inventory_sha256(FILE_SHA256.items())
CHECKPOINTS = BASE / "checkpoints"
CHECKPOINTS.mkdir(exist_ok=True)
EMB_CONTEXT = f"{MODEL_URL}|{TARGET_SR}|{N_MFCC}|{CODE_VERSION}"
YAMNET_SHARD = 256
CACHE_KEY = embedding_cache_key(DATA_INVENTORY_SHA256, MODEL_URL, TARGET_SR, CODE_VERSION)
print("Inventario de datos SHA-256:", DATA_INVENTORY_SHA256)

def yamnet_features(signal):
    padded = signal if len(signal) >= 15600 else np.pad(signal, (0, 15600 - len(signal)))
    scores, embeddings, _ = yamnet(tf.convert_to_tensor(padded, dtype=tf.float32))
    score_array, embedding_array = scores.numpy(), embeddings.numpy()
    assert embedding_array.shape[1] == 1024
    loud = loudness_features(signal, TARGET_SR)
    mfcc = librosa.feature.mfcc(y=padded, sr=TARGET_SR, n_mfcc=N_MFCC).mean(axis=1)
    feats = np.concatenate([mfcc, [loud[k] for k in LOUDNESS_KEYS]]).astype(np.float32)
    return score_array, embedding_array, feats, loud

def load_normalized(clip):
    raw, sr = librosa.load(PATHS[clip], sr=None, mono=False)
    return normalize_format(raw, sr)

def pack_or_empty(blocks):
    return pack_frames(blocks) if blocks else (np.zeros((0, 1024), np.float32), np.zeros(1, np.int64))

def yamnet_shard(items):
    rows, means, mfcc_loud, frame_blocks, quality_dropped = [], [], [], [], []
    for item in items:
        try:
            raw, sr = librosa.load(item["path"], sr=None, mono=False)
            quality = clip_quality(raw, sr)
        except Exception as exc:  # fichero ilegible => corrupto (se informa; nunca se corrige)
            raw, sr = None, 0
            quality = {"status": "corrupto", "error": type(exc).__name__}
        if quality["status"] != "ok":
            quality_dropped.append({"clip": item["clip"], "fuente": item["fuente"],
                                    "motivo": "calidad: " + quality["status"],
                                    "detalle": json.dumps(quality, default=str, sort_keys=True)})
            continue
        signal = normalize_format(raw, sr)
        assert signal.dtype == np.float32 and signal.ndim == 1 and np.isfinite(signal).all()
        score_array, embedding_array, feats, loud = yamnet_features(signal)
        means.append(embedding_array.mean(axis=0))
        frame_blocks.append(embedding_array)
        mfcc_loud.append(feats)
        rows.append({"clip": item["clip"], "fuente": item["fuente"], "clase": item["clase"],
                     "dron": int(item["dron"]), "grupo": item["grupo"],
                     "tipo": "dron" if item["dron"] else negative_type(item["fuente"], item["clase"]),
                     "segundos": round(len(signal) / TARGET_SR, 3), "ventanas": int(len(embedding_array)),
                     "max_speech_score": round(float(score_array[:, speech_columns].max()), 3),
                     "evento_YAMNet": class_names[int(score_array.mean(axis=0).argmax())],
                     "pcm_sha256": pcm_sha256(signal), "file_sha256": FILE_SHA256[item["clip"]],
                     **{key: round(float(v), 2) for key, v in loud.items()}})
    frames, offsets = pack_or_empty(frame_blocks)
    arrays = {"means": np.asarray(means, np.float32).reshape(-1, 1024),
              "mfcc_loud": np.asarray(mfcc_loud, np.float32).reshape(-1, N_MFCC + len(LOUDNESS_KEYS)),
              "frames": frames, "offsets": offsets}
    return arrays, {"rows": rows, "quality": quality_dropped}

rows, QUALITY_DROPPED, shard_arrays = [], [], []
ranges = shard_ranges(len(CATALOG), YAMNET_SHARD)
reused = 0
for n, (a, b) in enumerate(ranges, 1):
    items = CATALOG[a:b]
    key = shard_key([(c["clip"], FILE_SHA256[c["clip"]]) for c in items], EMB_CONTEXT)
    path = CHECKPOINTS / f"yamnet_{a:06d}_{key[:16]}.npz"
    loaded = load_shard(path, key)
    if loaded is None:
        loaded = yamnet_shard(items)
        save_shard(path, key, *loaded)  # guardado incremental: un corte solo pierde el lote en curso
    else:
        reused += 1
    arrays, meta = loaded
    rows += meta["rows"]
    QUALITY_DROPPED += meta["quality"]
    shard_arrays.append(arrays)
    print(f"  YAMNet: lote {n}/{len(ranges)} ({b}/{len(CATALOG)} clips; {reused} lotes reutilizados)")
MEANS = np.vstack([s["means"] for s in shard_arrays])
MFCC_LOUD = np.vstack([s["mfcc_loud"] for s in shard_arrays])
FRAMES, OFFSETS = pack_or_empty([unpack_frames(s["frames"], s["offsets"], i)
                                 for s in shard_arrays for i in range(len(s["offsets"]) - 1)])
del shard_arrays
assert len(MEANS) == len(MFCC_LOUD) == len(rows) == len(OFFSETS) - 1
df = pd.DataFrame(rows)
print(f"Audio procesado: {df['segundos'].sum()/3600:.2f} h en {len(df)} clips; ventanas YAMNet: {len(FRAMES)}")
print("Descartados por calidad (silencioso/saturado/corrupto):", len(QUALITY_DROPPED))
if QUALITY_DROPPED:
    display(pd.DataFrame(QUALITY_DROPPED))
print("Sonoridad por fuente (solo característica; mediana):")
display(df.groupby("fuente")[list(LOUDNESS_KEYS)].median().round(1))
display(df.sort_values("max_speech_score", ascending=False).head(15))
"""),
        code("""# Puerta automática de privacidad (código probado: apply_speech_gate) en TODAS las fuentes.
# Excluye del entrenamiento Y de la evaluación los clips con max_speech_score >= 0,30
# o sin puntuación válida. Revisión AUTOMÁTICA: NO sustituye a la escucha humana.
# Revisiones humanas: clip escuchado por una persona y declarado SIN voz (revisor, fecha, nota).
HUMAN_CLEARED = {
    "svanstrom/BACKGROUND_006.wav": "usuario, 2026-11-11: escuchado; crujido de madera, no es voz",
}
SPEECH_GATE = apply_speech_gate(df["clip"].tolist(), df["max_speech_score"].tolist(),
                                threshold=SPEECH_EXCLUSION_THRESHOLD, human_cleared=HUMAN_CLEARED)
print("Reincorporados por revisión humana:", SPEECH_GATE["human_cleared"])
excluded_speech = pd.DataFrame(SPEECH_GATE["excluded"], columns=["clip", "max_speech_score", "motivo"])
print(f"Excluidos por posible voz (umbral {SPEECH_EXCLUSION_THRESHOLD:.2f}): {len(excluded_speech)}")
print(SPEECH_GATE["note"])
display(excluded_speech.merge(df[["clip", "fuente"]], on="clip").groupby("fuente").size().rename("excluidos"))
display(excluded_speech.sort_values("max_speech_score", ascending=False).head(30))
SPEECH_DROPPED = [{"clip": e["clip"], "fuente": CLIP_SOURCE[e["clip"]], "motivo": "posible voz",
                   "detalle": f"{e['motivo']}; max_speech_score={e['max_speech_score']}"}
                  for e in SPEECH_GATE["excluded"]]
keep = list(SPEECH_GATE["kept_indices"])
df = df.iloc[keep].reset_index(drop=True)
MEANS, MFCC_LOUD = MEANS[keep], MFCC_LOUD[keep]
FRAMES, OFFSETS = pack_frames([unpack_frames(FRAMES, OFFSETS, i) for i in keep])
assert not set(df["clip"]) & set(excluded_speech["clip"])
assert len(MEANS) == len(MFCC_LOUD) == len(df) == len(OFFSETS) - 1
print("Clips que siguen al entrenamiento y la evaluación:", len(df))
"""),
        code("""# Duplicados exactos (hash del PCM normalizado) y casi duplicados (coseno de la media de
# embeddings YAMNet >= NEAR_DUPLICATE_COSINE, solo entre grupos distintos). Un componente de casi
# duplicados que abarca varios grupos conserva solo el grupo que más aporta: así ningún casi
# duplicado puede quedar a ambos lados de una partición por grupos. Informe de TODO lo descartado.
assert TRAINING_ALLOWED, "Entrenamiento bloqueado: intake de derechos, privacidad y grupos pendiente."
exact = exact_duplicates(df["pcm_sha256"].tolist(), df["clip"].tolist())
pairs = [(i, j, s) for i, j, s in near_duplicate_pairs(MEANS, threshold=NEAR_DUPLICATE_COSINE,
                                                        groups=df["grupo"].tolist())
         if i not in exact and j not in exact]
near = resolve_near_duplicates(pairs, df["grupo"].tolist(), df["clip"].tolist())
DUP_DROPPED = [{"clip": df["clip"][i], "fuente": df["fuente"][i], "motivo": "duplicado exacto",
                "detalle": "se conserva " + df["clip"][d["kept"]]} for i, d in exact.items()]
DUP_DROPPED += [{"clip": df["clip"][i], "fuente": df["fuente"][i], "motivo": "casi duplicado entre grupos",
                 "detalle": f"coseno >= {NEAR_DUPLICATE_COSINE}; grupo conservado {g}"}
                for i, g in near["dropped"].items()]
drop = set(exact) | set(near["dropped"])
keep = [i for i in range(len(df)) if i not in drop]
df = df.iloc[keep].reset_index(drop=True)
MEANS, MFCC_LOUD = MEANS[keep], MFCC_LOUD[keep]
FRAMES, OFFSETS = pack_frames([unpack_frames(FRAMES, OFFSETS, i) for i in keep])
residual = near_duplicate_pairs(MEANS, threshold=NEAR_DUPLICATE_COSINE, groups=df["grupo"].tolist())
assert not residual, "quedan casi duplicados entre grupos distintos"
print(f"Pares casi duplicados entre grupos: {len(pairs)} en {near['cross_group_clusters']} componentes")
DISCARDS = pd.DataFrame(QUALITY_DROPPED + SPEECH_DROPPED + DUP_DROPPED,
                        columns=["clip", "fuente", "motivo", "detalle"]).sort_values(["motivo", "clip"])
DISCARDS_CSV = DISCARDS.to_csv(index=False, lineterminator="\\n").encode("utf-8")
DISCARDS_SHA256 = hashlib.sha256(DISCARDS_CSV).hexdigest()
(BASE / "descartes.csv").write_bytes(DISCARDS_CSV)
print("Informe de descartes: descartes.csv · SHA-256", DISCARDS_SHA256)
display(DISCARDS.groupby(["fuente", "motivo"]).size().rename("descartados"))
display(DISCARDS.head(40))
y = df["dron"].to_numpy().astype(int)
groups = df["grupo"].tolist()
src = df["fuente"].tolist()
display(df.groupby(["fuente", "dron"]).agg(clips=("clip", "size"), grupos=("grupo", "nunique"),
                                           horas=("segundos", lambda s: round(s.sum() / 3600, 2))))
"""),
        code("""# Aumento de datos en forma de onda (código probado: augment), SOLO para entrenamiento.
# Plan determinista de N_MIXES mezclas: dron grabado + fondo negativo a SNR nominal -10..+20 dB,
# ganancia -6..+6 dB y desplazamiento temporal; drones y fondos se eligen equilibrando fuentes.
# En cada fold solo se usan las mezclas cuyo dron Y fondo están en el entrenamiento de ese fold
# (mixes_for_training): ningún audio de validación o test entra por una mezcla.
print(SYNTHETIC_NOTE)
positives = [i for i in range(len(y)) if y[i] == 1]
negatives = [i for i in range(len(y)) if y[i] == 0]
MIX_PLAN = plan_mixes(positives, negatives, src, df["segundos"].tolist(), n=N_MIXES, seed=SEED)
_, MIX_PLAN_SHA256 = canonical_json([{**m, "drone": df["clip"][m["drone"]],
                                      "background": df["clip"][m["background"]]} for m in MIX_PLAN])
MIX_SHARD = 250
mix_means, mix_blocks = [], []
mix_ranges = shard_ranges(len(MIX_PLAN), MIX_SHARD)
for n, (a, b) in enumerate(mix_ranges, 1):
    items = [(m["id"], canonical_json({**m, "drone": df["clip"][m["drone"]], "background": df["clip"][m["background"]],
                                        "drone_sha256": df["file_sha256"][m["drone"]],
                                        "background_sha256": df["file_sha256"][m["background"]]})[1])
             for m in MIX_PLAN[a:b]]
    key = shard_key(items, EMB_CONTEXT + "|mezclas")
    path = CHECKPOINTS / f"mezclas_{a:06d}_{key[:16]}.npz"
    loaded = load_shard(path, key)
    if loaded is None:
        means_part, blocks_part = [], []
        for m in MIX_PLAN[a:b]:
            try:
                mix = render_mix(m, load_normalized(df["clip"][m["drone"]]),
                                 load_normalized(df["clip"][m["background"]]), TARGET_SR)
            except SilentMixError:
                # Clip sin energía: la posición se conserva como no válida (NaN) y se excluye.
                means_part.append(np.full(1024, np.nan, dtype=np.float32))
                blocks_part.append(np.zeros((0, 1024), dtype=np.float32))
                continue
            _, embedding_array, _, _ = yamnet_features(mix)
            means_part.append(embedding_array.mean(axis=0))
            blocks_part.append(embedding_array)
        frames, offsets = pack_frames(blocks_part)
        loaded = ({"means": np.asarray(means_part, np.float32), "frames": frames, "offsets": offsets}, {})
        save_shard(path, key, *loaded)
    arrays, _ = loaded
    mix_means.append(arrays["means"])
    mix_blocks += [unpack_frames(arrays["frames"], arrays["offsets"], i) for i in range(len(arrays["offsets"]) - 1)]
    print(f"  Mezclas: lote {n}/{len(mix_ranges)} ({b}/{len(MIX_PLAN)})")
MIX_MEANS = np.vstack(mix_means)
MIX_FRAMES, MIX_OFFSETS = pack_frames(mix_blocks)
assert len(MIX_MEANS) == len(MIX_PLAN) == len(MIX_OFFSETS) - 1
MIX_VALID = np.isfinite(MIX_MEANS).all(axis=1)
print(f"Mezclas omitidas por clip sin energía: {int((~MIX_VALID).sum())} de {len(MIX_PLAN)}")
print("Plan de mezclas SHA-256:", MIX_PLAN_SHA256)
plan_df = pd.DataFrame(MIX_PLAN)
plan_df["fuente_dron"] = [src[i] for i in plan_df["drone"]]
plan_df["tipo_fondo"] = [df["tipo"][i] for i in plan_df["background"]]
display(plan_df[["snr_db", "gain_db", "seconds"]].describe().round(2))
display(plan_df["fuente_dron"].value_counts().rename("mezclas por fuente de dron"))
display(plan_df["tipo_fondo"].value_counts().rename("mezclas por tipo de fondo"))
"""),
        code("""# Evaluación (iteración 5). Dos esquemas:
#  - sgkf5: StratifiedGroupKFold por grupo (5 folds). Vuelta f: test = fold f, validación = fold
#    f+1 (calibración y umbral), entrenamiento = el resto.
#  - loso: leave-one-source-out; cada fuente entera es test nunca vista (generalización entre fuentes).
# En cada partición: grupos disjuntos y comprobación independiente de que ningún casi duplicado
# cruza particiones. Pesos por clase y por fuente (class_source_weights). Calibración Platt e
# isotónica ajustadas en validación; umbral = el más alto con recall >= 0,90 en validación (Platt).
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

assert TRAINING_ALLOWED, "Entrenamiento bloqueado: intake de derechos, privacidad y grupos pendiente."
CAPTION = metric_caption(provisional=PILOT["group_status"] != "verified")  # Svanström sigue provisional
CLIP_VARIANTS = ("YAMNet media", "YAMNet media + aumento",
                 "YAMNet media + aumento + negativos difíciles", "MFCC+sonoridad")
WINDOW_VARIANTS = tuple(f"YAMNet ventanas + aumento · {a}" for a in AGGREGATIONS)
VARIANTS = CLIP_VARIANTS + WINDOW_VARIANTS
FA_VARIANT = "YAMNet ventanas + aumento · max_suavizado"

def fit_lr(X, labels, weights, scale=False):
    lr = LogisticRegression(max_iter=3000, random_state=SEED)
    if scale:
        return make_pipeline(StandardScaler(), lr).fit(X, labels, logisticregression__sample_weight=weights)
    return lr.fit(X, labels, sample_weight=weights)

def raw_scores(train, parts):
    # Puntuaciones sin calibrar de cada variante en cada parte (validación, test).
    train = list(train)
    mix_ids = [i for i in mixes_for_training(MIX_PLAN, train) if MIX_VALID[i]]
    out = {}
    w = class_source_weights(y[train], [src[i] for i in train])
    model = fit_lr(MEANS[train], y[train], w)
    out["YAMNet media"] = [model.predict_proba(MEANS[list(p)])[:, 1] for p in parts]
    Xa = np.vstack([MEANS[train], MIX_MEANS[mix_ids]])
    ya = np.concatenate([y[train], np.ones(len(mix_ids), dtype=int)])
    wa = class_source_weights(ya, [src[i] for i in train] + ["sintetico"] * len(mix_ids))
    model = fit_lr(Xa, ya, wa)
    out["YAMNet media + aumento"] = [model.predict_proba(MEANS[list(p)])[:, 1] for p in parts]
    # Minería de negativos difíciles (2.ª ronda): puntuaciones del propio entrenamiento (sesgo
    # optimista documentado); nunca se mira validación ni test.
    wh, hard = hard_negative_weights(wa, ya, model.predict_proba(Xa)[:, 1],
                                     fraction=HN_FRACTION, factor=HN_FACTOR)
    model = fit_lr(Xa, ya, wh)
    out["YAMNet media + aumento + negativos difíciles"] = [model.predict_proba(MEANS[list(p)])[:, 1] for p in parts]
    model = fit_lr(MFCC_LOUD[train], y[train], w, scale=True)
    out["MFCC+sonoridad"] = [model.predict_proba(MFCC_LOUD[list(p)])[:, 1] for p in parts]
    Xf, yf, owner = frame_training_set(FRAMES, OFFSETS, y, train, max_frames=MAX_FRAMES)
    frame_src = [src[o] for o in owner]
    if mix_ids:
        Xm, ym, _ = frame_training_set(MIX_FRAMES, MIX_OFFSETS, [1] * len(MIX_PLAN), mix_ids,
                                       max_frames=MAX_FRAMES)
        Xf, yf = np.vstack([Xf, Xm]), np.concatenate([yf, ym])
        frame_src += ["sintetico"] * len(ym)
    window_model = fit_lr(Xf, yf, class_source_weights(yf, frame_src))
    frame_probs = window_model.predict_proba(FRAMES)[:, 1]
    def windows_of(i):
        return frame_probs[OFFSETS[i]:OFFSETS[i + 1]]
    for agg in AGGREGATIONS:
        out[f"YAMNet ventanas + aumento · {agg}"] = [
            np.array([aggregate_window_scores(windows_of(i), agg) for i in p]) for p in parts]
    return out, {"mezclas": len(mix_ids), "negativos_dificiles": [train[i] for i in hard],
                 "ventanas": windows_of}

PRED_ROWS, CALIBRATORS, FA_STREAMS, MINED = [], {}, [], []

def evaluate(scheme, partition, train, validation, test):
    assign = np.full(len(y), "fuera", dtype=object)
    for name, part in (("train", train), ("val", validation), ("test", test)):
        assign[list(part)] = name
    seen = [{groups[i] for i in part} for part in (train, validation, test)]
    assert not (seen[0] & seen[1] or seen[0] & seen[2] or seen[1] & seen[2]), "un grupo cruza particiones"
    used = np.flatnonzero(assign != "fuera")
    crossing = near_duplicate_pairs(MEANS[used], threshold=NEAR_DUPLICATE_COSINE, groups=assign[used].tolist())
    assert_no_cross_partition_pairs(crossing, assign[used].tolist())
    scores, info = raw_scores(train, [validation, test])
    yv = y[list(validation)]
    for v in VARIANTS:
        pv, pt = scores[v]
        platt, iso = fit_calibrator(yv, pv, "platt"), fit_calibrator(yv, pv, "isotonica")
        rule = choose_threshold_for_recall(yv, apply_calibration(platt, pv), target_recall=TARGET_RECALL)
        CALIBRATORS[(scheme, partition, v)] = {"platt": platt, "umbral": rule["threshold"],
                                               "recall_validacion": rule["validation_recall"]}
        for i, a, b, c in zip(test, apply_calibration(platt, pt), pt, apply_calibration(iso, pt)):
            PRED_ROWS.append({"modelo": v, "esquema": scheme, "particion": partition, "fuente": src[i],
                              "clip": df["clip"][i], "grupo": groups[i], "tipo": df["tipo"][i],
                              "dron": int(y[i]), "puntuacion": float(a), "puntuacion_cruda": float(b),
                              "puntuacion_isotonica": float(c), "umbral": rule["threshold"]})
    if scheme == "sgkf5":
        rule = CALIBRATORS[(scheme, partition, FA_VARIANT)]
        for i in test:
            if y[i] == 0:  # flujo por ventanas suavizado y calibrado de cada negativo de test
                FA_STREAMS.append((partition, apply_calibration(rule["platt"], smooth_scores(info["ventanas"](i))),
                                   rule["umbral"]))
        MINED.extend(df["tipo"][i] for i in info["negativos_dificiles"])
    print(f"  {scheme} {partition}: train/val/test = {len(train)}/{len(validation)}/{len(test)} clips; "
          f"mezclas en entrenamiento {info['mezclas']}")
    return info

folds = stratified_group_folds(y.tolist(), groups, k=N_FOLDS, seed=SEED)
for f, (tr, va, te) in enumerate(rotating_folds(folds, N_FOLDS)):
    info = evaluate("sgkf5", f"fold{f}", tr, va, te)
    if f == 0:
        WINDOW_DEMO = (te, info["ventanas"], CALIBRATORS[("sgkf5", "fold0", FA_VARIANT)])
LOSO = leave_one_source_out(y.tolist(), groups, src, seed=SEED)
for split in LOSO:
    evaluate("loso", "sin_" + split["fuente"], split["train"], split["validation"], split["test"])
pred = pd.DataFrame(PRED_ROWS)
assert pred.groupby(["modelo", "esquema"])["clip"].apply(lambda c: c.is_unique).all()
print("Predicciones fuera de fold:", len(pred), "filas", CAPTION)
"""),
        code("""# Resumen: cada clip aparece una vez por modelo y esquema (fuera de fold, con el umbral de su
# fold). IC 95 % remuestreando grupos completos sobre las decisiones. PR-AUC y ECE sobre la
# puntuación calibrada (Platt); ECE también sin calibrar y con isotónica.
from sklearn.metrics import average_precision_score

def interval(boot, name):
    if boot["status"] != "OK":
        return f"NO DISPONIBLE ({boot['n_groups']} grupos)"
    iv = boot["intervals"][name]
    return "—" if iv is None else f"[{iv[0]:.3f}, {iv[1]:.3f}]"

def summarize(sub):
    yy = sub["dron"].to_numpy()
    alarm = (sub["puntuacion"] >= sub["umbral"]).to_numpy().astype(float)
    m = binary_metrics(yy, alarm, 0.5)
    boot = group_bootstrap(yy, alarm, sub["grupo"].tolist(), 0.5, n_boot=500, seed=SEED)
    both = len(set(yy.tolist())) == 2
    r = lambda v: None if v is None or np.isnan(v) else round(float(v), 3)
    return {"n": len(sub), "positivos": int(yy.sum()), **{k: m[k] for k in ("tn", "fp", "fn", "tp")},
            "precision": r(m["precision"]), "IC95_precision": interval(boot, "precision"),
            "recall": r(m["recall"]), "IC95_recall": interval(boot, "recall"),
            "fpr": r(m["fpr"]), "IC95_fpr": interval(boot, "fpr"),
            "pr_auc": r(average_precision_score(yy, sub["puntuacion"])) if both else None,
            "ece_cruda": r(expected_calibration_error(yy, sub["puntuacion_cruda"])),
            "ece_platt": r(expected_calibration_error(yy, sub["puntuacion"])),
            "ece_isotonica": r(expected_calibration_error(yy, sub["puntuacion_isotonica"])),
            "brier": r(brier_score(yy, sub["puntuacion"]))}

cv_pred = pred[pred["esquema"] == "sgkf5"]
CV_SUMMARY = pd.DataFrame([{"modelo": v, **summarize(cv_pred[cv_pred["modelo"] == v])} for v in VARIANTS])
print(f"StratifiedGroupKFold ({N_FOLDS} folds), TOTAL fuera de fold", CAPTION)
display(CV_SUMMARY)
per_fold = cv_pred.assign(alarma=cv_pred["puntuacion"] >= cv_pred["umbral"]).groupby(["modelo", "particion"]).apply(
    lambda s: pd.Series({"recall": s.loc[s["dron"] == 1, "alarma"].mean(), "fpr": s.loc[s["dron"] == 0, "alarma"].mean()}))
print("Estabilidad entre folds (media ± desviación):")
display(per_fold.groupby("modelo").agg(["mean", "std"]).round(3))
print("Por fuente (StratifiedGroupKFold):")
display(pd.DataFrame([{"modelo": v, "fuente": s, **summarize(g)} for v in ("YAMNet media", "YAMNet media + aumento", FA_VARIANT)
                      for s, g in cv_pred[cv_pred["modelo"] == v].groupby("fuente")]))
loso_pred = pred[pred["esquema"] == "loso"]
LOSO_SUMMARY = pd.DataFrame([{"modelo": v, "fuente_no_vista": p.replace("sin_", ""), **summarize(g)}
                             for (v, p), g in loso_pred.groupby(["modelo", "particion"])])
print("Leave-one-source-out (generalización a una fuente nunca vista)", CAPTION)
display(LOSO_SUMMARY[["modelo", "fuente_no_vista", "n", "positivos", "recall", "IC95_recall", "fpr",
                      "IC95_fpr", "pr_auc", "ece_platt"]])
print("Comparación de agregaciones por ventana frente a la media por clip (sgkf5):")
display(CV_SUMMARY[CV_SUMMARY["modelo"].isin(("YAMNet media + aumento",) + WINDOW_VARIANTS)][
    ["modelo", "recall", "fpr", "pr_auc", "ece_platt"]])
"""),
        code("""# Calibración (diagrama de fiabilidad), curvas DET y PR sobre las predicciones fuera de fold.
from scipy.stats import norm
from sklearn.metrics import precision_recall_curve

fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))
ax = axes[0]
sub = cv_pred[cv_pred["modelo"] == FA_VARIANT]
for col, label in (("puntuacion_cruda", "sin calibrar"), ("puntuacion", "Platt"), ("puntuacion_isotonica", "isotónica")):
    bins = reliability_bins(sub["dron"].to_numpy(), sub[col].to_numpy())
    ece = expected_calibration_error(sub["dron"].to_numpy(), sub[col].to_numpy())
    ax.plot([b["confianza_media"] for b in bins], [b["fraccion_positivos"] for b in bins], "o-", label=f"{label} (ECE {ece:.3f})")
ax.plot([0, 1], [0, 1], "k--", lw=0.8)
ax.set(xlabel="Probabilidad predicha", ylabel="Fracción de drones", title=f"Fiabilidad · {FA_VARIANT}")
ax.legend(fontsize=8)
clip_ppf = lambda v: norm.ppf(np.clip(v, 1e-4, 1 - 1e-4))
for v in VARIANTS:
    s = cv_pred[cv_pred["modelo"] == v]
    fpr_d, fnr_d, _ = det_points(s["dron"].to_numpy(), s["puntuacion"].to_numpy())
    axes[1].plot(clip_ppf(fpr_d), clip_ppf(fnr_d), label=v, lw=1)
    prec, rec, _ = precision_recall_curve(s["dron"].to_numpy(), s["puntuacion"].to_numpy())
    axes[2].plot(rec, prec, label=v, lw=1)
ticks = [0.001, 0.01, 0.05, 0.2, 0.5]
axes[1].set_xticks(clip_ppf(np.array(ticks)), [str(t) for t in ticks])
axes[1].set_yticks(clip_ppf(np.array(ticks)), [str(t) for t in ticks])
axes[1].set(xlabel="Tasa de falsas alarmas (por clip)", ylabel="Tasa de fallos", title="Curva DET")
axes[2].set(xlabel="Recall", ylabel="Precisión", title="Curva PR")
axes[2].legend(fontsize=6)
fig.suptitle("StratifiedGroupKFold, fuera de fold · " + CAPTION, fontsize=9)
plt.tight_layout(); plt.show()
"""),
        code("""# Punto de operación y falsas alarmas por hora ESTIMADAS.
# Umbral elegido en validación (recall >= 0,90, Platt) para el modelo por ventanas con máximo
# suavizado: equivale a alarmar cuando la probabilidad suavizada de una ventana supera el umbral.
# Los negativos de test de cada fold se concatenan (flujos de puntuación por ventana) y se cuentan
# flancos de alarma con un periodo refractario. ESTIMACIÓN NO VERIFICADA: no es una grabación
# continua de un emplazamiento ni sustituye a la medida en campo.
by_fold = {}
for partition, stream, thr in FA_STREAMS:
    by_fold.setdefault(partition, {"streams": [], "umbral": thr})["streams"].append(stream)
fa_rows = []
for partition, item in sorted(by_fold.items()):
    est = false_alarms_per_hour_estimate(item["streams"], item["umbral"], hop_s=YAMNET_HOP_S,
                                         refractory_s=REFRACTORY_S)
    fa_rows.append({"fold": partition, "umbral": round(item["umbral"], 4), "horas_negativas": round(est["horas"], 2),
                    "alarmas": est["eventos"], "FA_por_hora_estimada": None if est["valor"] is None else round(est["valor"], 2)})
fa_table = pd.DataFrame(fa_rows)
total_hours, total_events = fa_table["horas_negativas"].sum(), int(fa_table["alarmas"].sum())
FA_ESTIMATE = {"modelo": FA_VARIANT, "status": FA_ESTIMATE_STATUS, "nota": FA_ESTIMATE_NOTE,
               "horas": float(total_hours), "alarmas": total_events,
               "valor": float(total_events / total_hours) if total_hours else None,
               "refractario_s": REFRACTORY_S}
display(fa_table)
print(f"FA/h {FA_ESTIMATE_STATUS}: {FA_ESTIMATE['valor']} ({total_events} alarmas en {total_hours:.2f} h de negativos concatenados)")
print(FA_ESTIMATE_NOTE)
fa = false_alarms_per_hour(0, continuous_negative_seconds=30.0, min_hours=24.0)
print("FA/h como métrica de campo:", fa["status"], "(no hay 24 h de negativo continuo conocido)", CAPTION)
"""),
        code("""# Negativos difíciles y matriz de confusión por TIPO de negativo (orienta qué grabar en Ceuta).
TYPE_TABLES = {}
for v in ("YAMNet media + aumento", "YAMNet media + aumento + negativos difíciles", FA_VARIANT):
    s = cv_pred[cv_pred["modelo"] == v]
    TYPE_TABLES[v] = confusion_by_negative_type(s["tipo"].tolist(), s["dron"].tolist(),
                                                s["puntuacion"].tolist(), s["umbral"].tolist())
type_df = pd.concat([pd.DataFrame(t).assign(modelo=v) for v, t in TYPE_TABLES.items()])
display(type_df.pivot(index="tipo", columns="modelo", values="fpr").round(3)
        .join(pd.DataFrame(TYPE_TABLES[FA_VARIANT]).set_index("tipo")[["n"]]).sort_values(FA_VARIANT, ascending=False))
main_types = pd.DataFrame(TYPE_TABLES[FA_VARIANT])
fig, ax = plt.subplots(figsize=(9, 4))
ax.barh(main_types["tipo"][::-1], main_types["fpr"][::-1])
ax.set(xlabel="Tasa de falsas alarmas por clip (fuera de fold)", title=f"Falsas alarmas por tipo de negativo · {FA_VARIANT}")
plt.tight_layout(); plt.show()
PRIORITIES = recording_priorities(TYPE_TABLES[FA_VARIANT], top=5)
print("Qué grabar primero en Ceuta (más falsas alarmas en esta prueba técnica):", ", ".join(PRIORITIES) or "—")
print("Negativos reponderados en la minería (por tipo, sumando folds):")
display(pd.Series(MINED).value_counts().rename("negativos difíciles"))
s = cv_pred[(cv_pred["modelo"] == FA_VARIANT) & (cv_pred["dron"] == 0)]
display(s.nlargest(20, "puntuacion")[["clip", "fuente", "tipo", "puntuacion", "umbral"]])
"""),
        code("""# Exportación de predicciones y registro del experimento (código probado: predictions, experiment).
# Las métricas se recalculan con pilots/acoustic/recompute_metrics.py (script independiente).
csv_bytes, csv_sha256 = predictions_csv(PRED_ROWS, columns=EXTENDED_COLUMNS)
pred_path = BASE / "predicciones.csv"
pred_path.write_bytes(csv_bytes)
DEPENDENCIES = dependency_versions(["tensorflow", "tensorflow-hub", "tf-keras", "librosa", "soundfile",
                                   "scikit-learn", "scipy", "numpy", "pandas", "matplotlib"])
MODEL_RECORD = experiment_record(
    config={"iteracion": 5, "semilla": SEED, "n_folds": N_FOLDS, "target_recall": TARGET_RECALL,
            "yamnet": MODEL_URL, "sr": TARGET_SR, "n_mezclas": N_MIXES, "snr_db": list(MIX_SNR_RANGE_DB),
            "ganancia_db": list(MIX_GAIN_RANGE_DB), "max_frames": MAX_FRAMES, "hn_fraccion": HN_FRACTION,
            "hn_factor": HN_FACTOR, "refractario_s": REFRACTORY_S, "calibracion": OPERATING_CALIBRATION,
            "casi_duplicado_coseno": NEAR_DUPLICATE_COSINE, "silencio_rms_dbfs": SILENCE_RMS_DBFS,
            "saturacion": [SATURATION_LEVEL, SATURATION_MAX_FRACTION], "duracion_minima_s": MIN_SECONDS,
            "voz_umbral": SPEECH_GATE["threshold"], "agregaciones": list(AGGREGATIONS),
            "suavizado_ventanas": SMOOTH_WINDOWS, "variantes": list(VARIANTS)},
    data={"inventario_sha256": DATA_INVENTORY_SHA256, "clave_cache_embeddings": CACHE_KEY, "descartes_csv_sha256": DISCARDS_SHA256,
          "plan_mezclas_sha256": MIX_PLAN_SHA256, "clips_evaluados": len(df),
          "descartados": {k: int(v) for k, v in DISCARDS["motivo"].value_counts().items()},
          "group_status_svanstrom": PILOT["group_status"], "folds": dict(zip(df["clip"], map(int, folds)))},
    dependencies=DEPENDENCIES, predictions_sha256=csv_sha256, notebook_code_sha256=NOTEBOOK_CODE_SHA256,
    extra={"umbrales": {"|".join(k): v["umbral"] for k, v in CALIBRATORS.items()},
           "calibradores_platt": {"|".join(k): v["platt"] for k, v in CALIBRATORS.items()},
           "puerta_voz": {"umbral": SPEECH_GATE["threshold"], "nota": SPEECH_GATE["note"]},
           "excluidos_por_voz": SPEECH_GATE["excluded"], "revisiones_humanas": SPEECH_GATE["human_cleared"],
           "fa_h_estimada": FA_ESTIMATE, "prioridades_grabacion": PRIORITIES,
           "nota_sintetico": SYNTHETIC_NOTE, "filas_predicciones": len(PRED_ROWS)})
assert verify_record(MODEL_RECORD)
(BASE / "modelo_piloto.json").write_text(json.dumps(MODEL_RECORD, ensure_ascii=False, indent=1))
print("predicciones.csv:", len(PRED_ROWS), "filas · SHA-256", csv_sha256)
print("Registro del experimento SHA-256:", MODEL_RECORD["registro_sha256"], "· código del cuaderno", NOTEBOOK_CODE_SHA256)
print("Recalcular: uv run python recompute_metrics.py predicciones.csv --sha256", csv_sha256,
      "--record modelo_piloto.json")
try:
    from google.colab import files  # descarga al navegador del usuario; no monta Drive
    for name in ("predicciones.csv", "modelo_piloto.json", "descartes.csv"):
        files.download(str(BASE / name))
except ImportError:
    pass
"""),
        code("""# Ilustración: un clip de dron de test (fold 0) con su espectrograma y la probabilidad por ventana
# del modelo por ventanas del fold 0 (suavizada y calibrada con Platt) frente al umbral elegido
# en validación. Ahora el modelo SÍ se entrenó por ventanas; la curva sigue siendo de un solo clip.
test0, windows_of0, rule0 = WINDOW_DEMO
candidates = [i for i in test0 if y[i] == 1]
chosen = max(candidates, key=lambda i: (df["ventanas"][i], df["clip"][i])) if candidates else test0[0]
name = df["clip"][chosen]
signal = load_normalized(name)
curve = apply_calibration(rule0["platt"], smooth_scores(windows_of0(chosen)))
db = librosa.power_to_db(librosa.feature.melspectrogram(y=signal, sr=TARGET_SR, n_mels=64), ref=np.max)
fig, (a, b) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
librosa.display.specshow(db, sr=TARGET_SR, x_axis="time", y_axis="mel", ax=a)
a.set_title(f"{name} · espectrograma")
b.plot(np.arange(len(curve)) * YAMNET_HOP_S, curve, label="probabilidad suavizada y calibrada")
b.axhline(rule0["umbral"], color="red", linestyle="--", label="umbral (validación, recall ≥ 0,90)")
b.set(ylim=(0, 1), ylabel="Probabilidad", xlabel="Tiempo (s)")
b.legend()
fig.suptitle(FA_VARIANT + " · " + CAPTION, fontsize=9)
plt.tight_layout(); plt.show()
"""),
        md("""## Fuentes para las siguientes pruebas

- **Fraunhofer IDMT:** [registro original de Zenodo](https://zenodo.org/records/17525811),
  licencia CC BY 4.0; 1,515,112,211 bytes de audio multicanal para dirección de llegada. Queda
  fuera del ensayo de clasificación.
- **Prohibidas:** DADS (la [ficha](https://huggingface.co/datasets/geronimobasso/drone-audio-detection-samples)
  declara MIT pero mezcla [Al-Emadi](https://github.com/saraalemadi/DroneAudioDataset/blob/master/LICENSE.md),
  que prohíbe usos de seguridad y defensa, y UrbanSound8K, no comercial), ESC-50 fuera de ESC-10
  (CC BY-NC), Sonniss (prohíbe entrenar IA) y AeroSonicDB (no comercial en su versión actual).
  `DADS_ENABLED=False`; ninguna se descarga.
"""),
        code("""# Auditoría de metadatos de Fraunhofer; NO descarga su ZIP de 1.5 GB.
FRAUNHOFER = PILOT["fraunhofer_record"]
meta_record = json.loads(read_https(FRAUNHOFER, ZENODO_HOSTS, limit=1 << 22, timeout=30))
assert meta_record["metadata"]["license"]["id"] == "cc-by-4.0"
files_meta = meta_record["files"]
assert len(files_meta) == 1 and files_meta[0]["key"] == "MicArrayData30s.zip"
assert files_meta[0]["size"] == 1515112211
print("Fraunhofer:", meta_record["metadata"]["title"], "| licencia", meta_record["metadata"]["license"]["id"])
DADS_ENABLED = False
assert not DADS_ENABLED
# Ninguna fuente prohibida aparece en las descargadas.
assert set(catalog["fuente"]) == {"svanstrom", "esc10", "fsd50k", "aris"}
print("DADS y demás fuentes prohibidas bloqueadas:", ", ".join(PROHIBITED))
"""),
        md("""**Lectura de resultados:** cualquier acierto o error anterior describe solo estos clips y
estos repartos. ITU ARIS es **una sola sesión** (un día, un lugar): sus intervalos no son
independientes entre sí y no miden generalización a otro emplazamiento. FSD50K y ESC-10 son clips
cortos de Freesound grabados cerca de la fuente. No se ha medido tasa de falsas alarmas por hora,
distancia de detección, nuevos drones ni emplazamientos. Para eso se necesitan grabaciones de
campo independientes, negativos continuos, revisión de privacidad y una evaluación congelada por
vuelo/sitio.
"""),
    ]
    # Orden de ejecución: YAMNet puntúa la voz y la puerta automática excluye clips ANTES de
    # la celda de TRAINING_ALLOWED y del entrenamiento.
    names = [("".join(c["source"])[:60]) for c in cells]
    gate_cell = next(i for i, s in enumerate(names) if s.startswith("# Intake pendiente"))
    yamnet_cell = next(i for i, s in enumerate(names) if s.startswith("# YAMNet oficial"))
    speech_cell = next(
        i
        for i, s in enumerate(names)
        if s.startswith("# Puerta automática de privacidad (código probado")
    )
    assert gate_cell + 1 == yamnet_cell and yamnet_cell + 1 == speech_cell
    cells[gate_cell], cells[yamnet_cell], cells[speech_cell] = (
        cells[yamnet_cell],
        cells[speech_cell],
        cells[gate_cell],
    )
    return cells


def main(output: Path = OUTPUT) -> None:
    sources_src = _embedded_sources(EMBEDDED)
    cells = _iter5_cells(_base_config(), sources_src)
    _finalize(cells, output, OUTPUT.name)


def _finalize(cells: list[dict], output: Path, name: str) -> None:
    # Hash del código del cuaderno: SHA-256 del JSON canónico de las celdas con el marcador; se
    # sustituye después (el cuaderno no puede contener su propio hash final).
    code_sha256 = hashlib.sha256(
        json.dumps(cells, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    marker_cells = [c for c in cells if CODE_SHA_PLACEHOLDER in "".join(c["source"])]
    assert len(marker_cells) == 1
    marker_cells[0]["source"] = [
        line.replace(CODE_SHA_PLACEHOLDER, code_sha256) for line in marker_cells[0]["source"]
    ]
    notebook = {
        # nbformat 4.5 exige un id por celda; ids deterministas para que la salida sea reproducible.
        "cells": [{"id": f"celda-{i:02d}", **cell} for i, cell in enumerate(cells)],
        "metadata": {
            "colab": {"name": name, "provenance": []},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    output.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n")
    print(output)


# --- Iteración 6 (hito 2, H2.5) -------------------------------------------------------------
OUTPUT6 = ROOT / "pilots/acoustic/Atalaya_YAMNet_Colab_iter6.ipynb"
SALFORD_MANIFEST = ROOT / "ml/datasets/salford-dronenoise/manifest.json"
DAS_MANIFEST = ROOT / "ml/datasets/droneaudioset-drone-only/manifest.json"
YI_MANIFEST = ROOT / "ml/datasets/yi-kaist-drone-fault/manifest.json"
DECISIONS = ROOT / "docs/requirements/DECISIONES-USUARIO.md"
# Autorización del usuario para usar cada fuente de dron extra en ESTA prueba técnica (sus
# manifiestos siguen con intake_approved=false). None = desactivada. Para activarla: registrar la
# decisión en DECISIONES-USUARIO.md, poner aquí su cita literal y regenerar el cuaderno.
EXTRA_AUTHORIZATION: dict[str, str | None] = {
    "salford": None,
    "droneaudioset": None,
    "yi_kaist": None,
}
YI_PAIRS = 1200  # pares de segmentos normales de 0,5 s del dron A (subconjunto con semilla)
RELATIVE_IMPORT = re.compile(r"^from \.(\w+) import (\([^)]*\)|[^\n]+)\n", re.MULTILINE)


def _strip_relative_imports(sources_src: dict[str, str]) -> dict[str, str]:
    """Quita las importaciones relativas (en el cuaderno, esos nombres ya los definió un módulo
    incrustado ANTES); comprueba que el módulo y cada nombre existen y van antes."""
    out: dict[str, str] = {}
    for name, text in sources_src.items():
        for match in RELATIVE_IMPORT.finditer(text):
            module = match.group(1)
            assert module in out, f"{name} importa {module}, que no se incrusta antes"
            names = [n.strip() for n in match.group(2).strip("()").split(",") if n.strip()]
            tree = ast.parse(out[module])
            defined = {
                t.id if isinstance(t, ast.Name) else t
                for node in tree.body
                for t in (
                    [node.name]
                    if isinstance(node, ast.FunctionDef | ast.ClassDef)
                    else (node.targets if isinstance(node, ast.Assign) else [])
                )
            }
            missing = set(names) - {d for d in defined if isinstance(d, str)}
            assert not missing, f"{name}: {missing} no están definidos en {module}"
        out[name] = RELATIVE_IMPORT.sub("", text)
        assert "from ." not in out[name], name
    return out


def _extra_config() -> dict:
    sal = json.loads(SALFORD_MANIFEST.read_text())
    assert sal["license"] == "CC-BY-4.0" and sal["intake_approved"] is False
    keep = ("path", "bytes", "md5", "url", "figshare_file_id", "suas_code", "event_id", "group_id")
    salford = {
        "api": "https://api.figshare.com/v2/articles/22133411",
        "files": [{k: f[k] for k in keep} for f in salford_selection(sal["files"])],
    }
    das = json.loads(DAS_MANIFEST.read_text())
    assert das["license"] == "MIT" and das["intake_approved"] is False
    das_sel = droneaudioset_selection(das["files"], seed=20261111)
    row_keep = ("upstream_file_path", "drone", "take", "group_id", "label_status")
    droneaudioset = {
        "info_url": f"https://huggingface.co/api/datasets/ahlab-drone-project/DroneAudioSet/revision/{das['revision']}",
        "revision": das["revision"],
        "files": [
            {
                "path": f["path"],
                "bytes": f["bytes"],
                "sha256": f["sha256"],
                "url": f["url"],
                "rows": [{k: r[k] for k in row_keep} for r in f["rows"]],
            }
            for f in das_sel
        ],
    }
    yi = json.loads(YI_MANIFEST.read_text())
    assert yi["license"] == "CC-BY-4.0" and yi["intake_approved"] is False
    file_a = next(f for f in yi["files"] if f["selected_for_colab"])
    yi_kaist = {
        "api": "https://zenodo.org/api/records/7779574",
        "file": {k: file_a[k] for k in ("path", "bytes", "md5", "url")},
        "n_pairs": YI_PAIRS,
    }
    return {"salford": salford, "droneaudioset": droneaudioset, "yi_kaist": yi_kaist}


def _check_authorizations(auth: dict[str, str | None]) -> None:
    assert set(auth) == set(EXTRA_SOURCES), auth
    text = DECISIONS.read_text(encoding="utf-8")
    for source, quote in auth.items():
        if quote:
            assert quote in text, f"la autorización de {source} no está en DECISIONES-USUARIO.md"


def main_iter6(output: Path = OUTPUT6) -> None:
    from colab_iter6 import ITER6_MODULES, iter6_cells

    _check_authorizations(EXTRA_AUTHORIZATION)
    sources5 = _embedded_sources(EMBEDDED)
    cells5 = _iter5_cells(_base_config(), sources5)
    embedded = _strip_relative_imports({**sources5, **_embedded_sources(ITER6_MODULES)})

    def iter5_cell(prefix: str) -> dict:
        found = [c for c in cells5 if "".join(c["source"]).startswith(prefix)]
        assert len(found) == 1, prefix
        return json.loads(json.dumps(found[0]))

    config = {**_base_config(), "extra": _extra_config()}
    config_json = json.dumps(config, ensure_ascii=False, separators=(",", ":"))
    cells = iter6_cells(config_json, EXTRA_AUTHORIZATION, embedded, iter5_cell, md, code)
    _finalize(cells, output, OUTPUT6.name)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--iter6"]:
        main_iter6(Path(args[1]) if len(args) > 1 else OUTPUT6)
    elif args:
        main(Path(args[0]))
    else:
        main()
        main_iter6()

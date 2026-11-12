"""Build a self-contained, public-data-only Colab pilot notebook (iteración 4).

The notebook embeds hashes and source references, never audio, repository secrets,
or the private Atalaya repository. Run this after the pinned source manifests exist
(``build_sources.py`` fija FSD50K e ITU ARIS). Salida determinista: mismo repo => mismos bytes.
"""

# ruff: noqa: E501 - the notebook code is kept readable inside embedded cells.

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "ml/datasets/svanstrom/manifest.json"
ESC10_MANIFEST = ROOT / "ml/datasets/esc10/manifest.json"
FSD50K_MANIFEST = ROOT / "ml/datasets/fsd50k-subset/manifest.json"
ARIS_MANIFEST = ROOT / "ml/datasets/itu-aris/manifest.json"
OUTPUT = ROOT / "pilots/acoustic/Atalaya_YAMNet_Colab.ipynb"
# Código probado en pilots/acoustic/tests; se incrusta literalmente (Colab no accede al repo).
PILOT_PKG = ROOT / "pilots/acoustic/acoustic_pilot"
EMBEDDED = ("grouped_eval", "speech_gate", "remote", "remote_zip", "sources", "predictions")
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


INTRO = """# Atalaya · piloto acústico YAMNet · iteración 4 (más datos)

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
posterior).

**Descarga total ≈ 1,25 GB** (Colab gratuito, CPU). Todas las peticiones van solo a hosts
permitidos y cada redirección se comprueba antes de seguirla. FSD50K se lee por **rangos HTTP**
del ZIP original (sin bajar sus 24 GB): solo los clips fijados.

**Puerta automática de privacidad:** tras YAMNet se excluyen del entrenamiento y la evaluación
los clips con `max_speech_score >= 0,30` en **todas** las fuentes (ITU ARIS declara voz de sus
operadores en algunos segmentos). No sustituye a la escucha humana; `HUMAN_CLEARED` registra las
revisiones humanas.

**Evaluación:**
- Grupos por fuente/sesión, nunca por segmento solapado: Svanström por clip (provisional),
  ESC-10 por audio original de Freesound, FSD50K por autor de Freesound (seudonimizado) e ITU ARIS
  por intervalo/bloque de `groups.json` (segmentos solapados al 50 %) con el split
  `interval_disjoint` de los autores.
- Partición única train/validación/test **y** validación cruzada por grupos (5 folds).
- **Umbral orientado a recall**: el umbral más alto con recall ≥ 0,90 en validación (nunca en test).
- Métricas por fuente y agregadas con IC 95 % remuestreando grupos; YAMNet frente a MFCC.
- Las predicciones se exportan a `predicciones.csv` con SHA-256 para recalcular las métricas con
  `pilots/acoustic/recompute_metrics.py` (pendiente de ADR 0016).

Svanström sigue con grupos provisionales (sin IDs de vuelo/sesión): las cifras agregadas llevan
el rótulo de contaminación no descartada. Pesos de [YAMNet](https://www.kaggle.com/models/google/yamnet)
(Google): Apache 2.0. No se usa micrófono, audio de clientes, acceso al GitHub privado ni montaje
de Drive.
"""


def main(output: Path = OUTPUT) -> None:
    sources_src = {
        name: (PILOT_PKG / f"{name}.py").read_text(encoding="utf-8") for name in EMBEDDED
    }
    for name, text in sources_src.items():
        assert "__future__" not in text, name  # se incrusta a mitad de cuaderno
        assert "from acoustic_pilot" not in text, name
    svan = _svanstrom()
    config = {
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
# sources (licencias por clip, selección y grupos) y predictions (CSV con hash).

PILOT = json.loads('''"""
            + json.dumps(config, ensure_ascii=False, separators=(",", ":"))
            + """''')
SEED = 20261111
N_PER_CLASS = 30  # todos los WAV inventariados de Svanström por clase; el duplicado excluido sigue fuera.
TARGET_RECALL = 0.90  # criterio del umbral, elegido SOLO en validación
N_FOLDS = 5
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
for item in selected:
    name = item["name"]
    assert name.replace("_", "").replace(".", "").isalnum() and name.endswith(".wav")
    path = BASE / "svanstrom" / name
    raw = path.read_bytes() if path.exists() else read_source(f"{ROOT_URL}/Data/Audio/{name}")
    assert len(raw) == item["bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"], name
    if not path.exists():
        path.write_bytes(raw)
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
for f in ESC["files"]:
    name = f["path"].split("/")[-1]
    path = BASE / "esc10" / name
    raw = path.read_bytes() if path.exists() else read_https(f"{ESC_URL}/{f['path']}", SVAN_HOSTS, limit=1 << 20)
    assert len(raw) == f["bytes"] and git_blob_sha1(raw) == f["blob"], name
    if not path.exists():
        path.write_bytes(raw)
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
for n, clip in enumerate(FSD["clips"], 1):
    part = clip["split"]
    entry = cds[part][clip["member"]]
    assert all(entry[k] == clip[k] for k in ("disk", "offset", "size", "method", "crc32"))
    assert entry["compressed_size"] == clip["compressed_bytes"]
    path = BASE / "fsd50k" / f"{int(clip['fname'])}.wav"
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == clip["sha256"]:
        pass
    else:
        vols = FSD["audio_archives"][part]["volumes"]
        sizes = [v["bytes"] for v in vols]
        span = LOCAL_HEADER_LEN + len(clip["member"].encode()) + 512 + clip["compressed_bytes"]
        span = min(span, sum(sizes[clip["disk"]:]) - clip["offset"])
        raw = b"".join(read_https(zenodo_file(FSD["record"], vols[d]["key"]), ZENODO_HOSTS, byte_range=(a, b))
                       for d, a, b in volume_ranges(clip["disk"], clip["offset"], span, sizes))
        head = local_header_length(raw, clip["member"])
        data = decode_member(raw[head:head + clip["compressed_bytes"]], method=clip["method"],
                             size=clip["size"], crc32=clip["crc32"])
        assert hashlib.sha256(data).hexdigest() == clip["sha256"], clip["fname"]
        path.write_bytes(data)
        time.sleep(0.45)  # límite de Zenodo (~133 peticiones/minuto)
    CATALOG.append({"clip": f"fsd50k/{clip['fname']}.wav", "fuente": "fsd50k", "path": path,
                    "clase": clip["target_label"], "dron": 0, "grupo": clip["group_id"], "split": None})
    if n % 100 == 0:
        print(f"  FSD50K {n}/{len(FSD['clips'])}")
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
raw = zip_path.read_bytes() if zip_path.exists() else read_https(zenodo_file(ARIS["record"], arch["key"]), ZENODO_HOSTS, limit=arch["bytes"])
assert len(raw) == arch["bytes"] and hashlib.sha256(raw).hexdigest() == arch["sha256"]
zip_path.write_bytes(raw)
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
for seg in aris_rows:
    data = aris_zip.read(ARIS["inner_prefix"] + seg["path"])
    assert hashlib.sha256(data).hexdigest() == aris_sums[seg["path"]], seg["path"]
    path = BASE / "aris" / seg["path"].split("/")[-1]
    path.write_bytes(data)
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
        code("""# YAMNet oficial: señal mono float32 a 16 kHz; media de embeddings por clip. Línea base: 40 MFCC.
MODEL_URL = "https://tfhub.dev/google/yamnet/1"
yamnet = hub.load(MODEL_URL)
class_map_path = yamnet.class_map_path().numpy().decode()
class_names = pd.read_csv(class_map_path)["display_name"].tolist()
assert len(class_names) == 521
speech_columns = [i for i, label in enumerate(class_names)
                  if label in {"Speech", "Conversation", "Narration, monologue", "Child speech, kid speaking"}]
assert len(speech_columns) == 4
N_MFCC = 40
rows, vectors, mfcc_vectors = [], [], []
for k, item in enumerate(CATALOG):
    signal, sr = librosa.load(item["path"], sr=16000, mono=True)
    assert sr == 16000 and np.isfinite(signal).all() and len(signal) > 0
    if len(signal) < 15600:  # YAMNet necesita 0,975 s; los segmentos de 1 s pueden quedar justos
        signal = np.pad(signal, (0, 15600 - len(signal)))
    scores, embeddings, _ = yamnet(tf.convert_to_tensor(signal, dtype=tf.float32))
    score_array, embedding_array = scores.numpy(), embeddings.numpy()
    assert embedding_array.shape[1] == 1024
    vectors.append(embedding_array.mean(axis=0))
    mfcc_vectors.append(librosa.feature.mfcc(y=signal, sr=16000, n_mfcc=40).mean(axis=1))
    rows.append({"clip": item["clip"], "fuente": item["fuente"], "clase": item["clase"],
                 "dron": item["dron"], "grupo": item["grupo"], "split": item["split"],
                 "segundos": round(len(signal) / 16000, 2), "ventanas": len(score_array),
                 "max_speech_score": round(float(score_array[:, speech_columns].max()), 3),
                 "evento_YAMNet": class_names[int(score_array.mean(axis=0).argmax())]})
    if (k + 1) % 1000 == 0:
        print(f"  YAMNet {k + 1}/{len(CATALOG)}")
df = pd.DataFrame(rows)
display(df.sort_values("max_speech_score", ascending=False).head(15))
print(f"Audio procesado: {df['segundos'].sum()/3600:.2f} h en {len(df)} clips")
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
keep = list(SPEECH_GATE["kept_indices"])
df = df.iloc[keep].reset_index(drop=True)
vectors = [vectors[i] for i in keep]
mfcc_vectors = [mfcc_vectors[i] for i in keep]
assert not set(df["clip"]) & set(excluded_speech["clip"])
print("Clips que siguen al entrenamiento y la evaluación:", len(df))
display(df.groupby(["fuente", "dron"]).agg(clips=("clip", "size"), grupos=("grupo", "nunique")))
"""),
        code("""# Entrenamiento y evaluación por grupos. El umbral se elige SOLO en validación con criterio de
# recall (el más alto con recall >= TARGET_RECALL); test solo mide.
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import ConfusionMatrixDisplay

assert TRAINING_ALLOWED, "Entrenamiento bloqueado: intake de derechos, privacidad y grupos pendiente."
CAPTION = metric_caption(provisional=PILOT["group_status"] != "verified")  # Svanström sigue provisional
X = {"YAMNet + reg. logística": np.asarray(vectors), "MFCC(40) + reg. logística": np.asarray(mfcc_vectors)}
assert all(len(v) == len(df) for v in X.values()), "la puerta de voz debe aplicarse a ambos rasgos"
y = df["dron"].to_numpy().astype(int)
groups = df["grupo"].tolist()
src = df["fuente"].tolist()

def make_model(name):
    lr = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)
    return make_pipeline(StandardScaler(), lr) if name.startswith("MFCC") else lr

def fit_predict(name, train, validation, test):
    model = make_model(name).fit(X[name][list(train)], y[list(train)])
    rule = choose_threshold_for_recall(y[list(validation)], model.predict_proba(X[name][list(validation)])[:, 1],
                                       target_recall=TARGET_RECALL)
    return model, rule, model.predict_proba(X[name][list(test)])[:, 1]

def ic(row, name):
    if row["ic95"]["status"] != "OK":
        return f"NO DISPONIBLE ({row['ic95']['n_groups']} grupos < {row['ic95']['min_groups']})"
    iv = row["ic95"]["intervals"][name]
    return "—" if iv is None else f"[{iv[0]:.3f}, {iv[1]:.3f}]"

def table(rows, label, threshold):
    out = []
    for r in rows:
        out.append({"modelo": label, "fuente": r["fuente"], "n": r["n"], "positivos": r["positivos"],
                    "grupos": r["grupos"], "umbral": round(threshold, 4),
                    **{k: r[k] for k in ("tn", "fp", "fn", "tp")},
                    **{k: (None if np.isnan(r[k]) else round(r[k], 3)) for k in ("precision", "recall", "fpr", "pr_auc")},
                    **{f"IC95_{k}": ic(r, k) for k in ("precision", "recall", "fpr", "pr_auc")}})
    return out

# 1) Partición única: ITU ARIS con el split interval_disjoint de los autores; el resto por grupos.
preassigned = {i: s for i, s in enumerate(df["split"]) if isinstance(s, str)}
train_idx, validation_idx, test_idx = split_with_preassigned(y.tolist(), groups, preassigned, seed=SEED)
part_groups = [{groups[i] for i in part} for part in (train_idx, validation_idx, test_idx)]
assert not (part_groups[0] & part_groups[1] or part_groups[0] & part_groups[2]
            or part_groups[1] & part_groups[2]), "un grupo aparece en dos particiones"
print("Partición única · clips train/val/test:", len(train_idx), len(validation_idx), len(test_idx),
      "| grupos:", [len(g) for g in part_groups], CAPTION)
PRED_ROWS, SPLIT_TABLE, RULES, MODELS = [], [], {}, {}
for name in X:
    model, rule, proba = fit_predict(name, train_idx, validation_idx, test_idx)
    MODELS[name], RULES[name] = model, rule
    test_rows = metrics_by_source(y[list(test_idx)], proba, [src[i] for i in test_idx],
                                  [groups[i] for i in test_idx], rule["threshold"], seed=SEED)
    SPLIT_TABLE += table(test_rows, name, rule["threshold"])
    for i, p in zip(test_idx, proba):
        PRED_ROWS.append({"modelo": name, "esquema": "split", "particion": "test", "fuente": src[i],
                          "clip": df["clip"][i], "grupo": groups[i], "dron": int(y[i]),
                          "puntuacion": float(p), "umbral": rule["threshold"]})
    print(f"{name}: umbral {rule['threshold']:.4f} ({rule['criterion']}; recall val. "
          f"{rule['validation_recall']:.3f}, precisión val. {rule['validation_precision']:.3f})")
print("Test de la partición única por fuente y TOTAL", CAPTION)
display(pd.DataFrame(SPLIT_TABLE))

# 2) Validación cruzada por grupos (5 folds): test = fold f, validación = fold f+1, train = resto.
folds = group_folds(y.tolist(), groups, k=N_FOLDS, seed=SEED)
CV_TABLE, OOF = [], {name: np.full(len(y), np.nan) for name in X}
for f, (tr, va, te) in enumerate(rotating_folds(folds, N_FOLDS)):
    for name in X:
        _, rule, proba = fit_predict(name, tr, va, te)
        OOF[name][list(te)] = proba
        m = binary_metrics(y[list(te)], proba, rule["threshold"])
        CV_TABLE.append({"modelo": name, "fold": f, "umbral": round(rule["threshold"], 4),
                         "n_test": len(te), "grupos_test": len({groups[i] for i in te}),
                         **{k: m[k] for k in ("tn", "fp", "fn", "tp")},
                         **{k: round(m[k], 3) for k in ("precision", "recall", "fpr", "pr_auc")}})
        for i, p in zip(te, proba):
            PRED_ROWS.append({"modelo": name, "esquema": f"cv{N_FOLDS}", "particion": f"fold{f}",
                              "fuente": src[i], "clip": df["clip"][i], "grupo": groups[i],
                              "dron": int(y[i]), "puntuacion": float(p), "umbral": rule["threshold"]})
cv = pd.DataFrame(CV_TABLE)
display(cv)
print(f"Validación cruzada por grupos ({N_FOLDS} folds): media ± desviación por modelo", CAPTION)
display(cv.groupby("modelo")[["precision", "recall", "fpr", "pr_auc"]].agg(["mean", "std"]).round(3))
"""),
        code("""# Exportación de predicciones con SHA-256: las métricas se recalculan con
# pilots/acoustic/recompute_metrics.py (script independiente) en vez de copiarse de la salida.
csv_bytes, csv_sha256 = predictions_csv(PRED_ROWS)
pred_path = BASE / "predicciones.csv"
pred_path.write_bytes(csv_bytes)
MODEL_RECORD = {
    "iteracion": 4, "yamnet": MODEL_URL, "seed": SEED, "group_status_svanstrom": PILOT["group_status"],
    "criterio_umbral": f"umbral más alto con recall de validación >= {TARGET_RECALL:.2f}",
    "umbrales_particion_unica": {k: v["threshold"] for k, v in RULES.items()},
    "particiones": {k: sorted(df["clip"].iloc[list(v)]) for k, v in
                    (("train", train_idx), ("validacion", validation_idx), ("test", test_idx))},
    "folds": dict(zip(df["clip"], map(int, folds))),
    "coef_sha256": {name: hashlib.sha256((m[-1] if hasattr(m, "steps") else m).coef_.tobytes()).hexdigest()
                    for name, m in MODELS.items()},
    "puerta_voz": {"umbral": SPEECH_GATE["threshold"], "nota": SPEECH_GATE["note"]},
    "excluidos_por_voz": SPEECH_GATE["excluded"], "revisiones_humanas": SPEECH_GATE["human_cleared"],
    "predicciones_csv_sha256": csv_sha256, "filas_predicciones": len(PRED_ROWS),
}
(BASE / "modelo_piloto.json").write_text(json.dumps(MODEL_RECORD, ensure_ascii=False, indent=1))
print("predicciones.csv:", len(PRED_ROWS), "filas · SHA-256", csv_sha256)
print("Recalcular: uv run python recompute_metrics.py predicciones.csv --sha256", csv_sha256)
try:
    from google.colab import files  # descarga al navegador del usuario; no monta Drive
    files.download(str(pred_path))
    files.download(str(BASE / "modelo_piloto.json"))
except ImportError:
    pass
"""),
        code("""# Matrices de confusión de la partición única y FA/h.
FA_MIN_CONTINUOUS_HOURS = 24.0
LONGEST_CONTINUOUS_NEGATIVE_S = 30.0  # el clip negativo continuo más largo (FSD50K ≤ 30 s)
fa = false_alarms_per_hour(0, continuous_negative_seconds=LONGEST_CONTINUOUS_NEGATIVE_S,
                           min_hours=FA_MIN_CONTINUOUS_HOURS)
print("Falsas alarmas por hora:", fa["status"],
      f"(negativo continuo conocido {fa['hours']*3600:.0f} s < {FA_MIN_CONTINUOUS_HOURS:.0f} h)", CAPTION)
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
for ax, name in zip(axes, X):
    p = np.asarray([r["puntuacion"] for r in PRED_ROWS if r["modelo"] == name and r["esquema"] == "split"])
    ConfusionMatrixDisplay.from_predictions(y[list(test_idx)], (p >= RULES[name]["threshold"]).astype(int),
                                            labels=[0, 1], display_labels=["no dron", "dron"], ax=ax, colorbar=False)
    ax.set_title(f"{name}\\numbral {RULES[name]['threshold']:.3f} (recall val. ≥ {TARGET_RECALL:.2f})", fontsize=9)
fig.suptitle("Test de la partición única · " + CAPTION, fontsize=9)
plt.tight_layout(); plt.show()
"""),
        code("""# Ilustración sobre un clip de dron de test: espectrograma y puntuación por ventana.
# AVISO: el clasificador se entrenó con la MEDIA de embeddings por clip. Aplicarlo a ventanas
# sueltas de 0,96 s (salto 0,48 s) queda fuera de su distribución de entrenamiento: la curva
# NO está calibrada y el umbral (fijado por clip en validación) no es un umbral por ventana.
head = MODELS["YAMNet + reg. logística"]
threshold = RULES["YAMNet + reg. logística"]["threshold"]
candidates = [i for i in test_idx if y[i] == 1]
chosen = max(candidates, key=lambda i: (df["segundos"][i], df["clip"][i])) if candidates else test_idx[0]
name = df.iloc[chosen]["clip"]
signal, _ = librosa.load(next(c["path"] for c in CATALOG if c["clip"] == name), sr=16000, mono=True)
_, frames, _ = yamnet(tf.convert_to_tensor(signal, dtype=tf.float32))
window_scores = head.predict_proba(frames.numpy())[:, 1]
db = librosa.power_to_db(librosa.feature.melspectrogram(y=signal, sr=16000, n_mels=64), ref=np.max)
fig, (a, b) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
librosa.display.specshow(db, sr=16000, x_axis="time", y_axis="mel", ax=a)
a.set_title(f"{name} · espectrograma")
b.plot(np.arange(len(window_scores)) * 0.48, window_scores)
b.axhline(threshold, color="red", linestyle="--", label="umbral por clip (validación); no válido por ventana")
b.set(ylim=(0, 1), ylabel="Puntuación sin calibrar", xlabel="Tiempo (s)")
b.legend()
fig.suptitle("Modelo por clip (media de embeddings) aplicado a ventanas: curva NO calibrada, solo ilustrativa\\n" + CAPTION, fontsize=9)
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
    speech_cell = next(i for i, s in enumerate(names) if s.startswith("# Puerta automática"))
    assert gate_cell + 1 == yamnet_cell and yamnet_cell + 1 == speech_cell
    cells[gate_cell], cells[yamnet_cell], cells[speech_cell] = (
        cells[yamnet_cell],
        cells[speech_cell],
        cells[gate_cell],
    )
    notebook = {
        "cells": cells,
        "metadata": {
            "colab": {"name": OUTPUT.name, "provenance": []},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    output.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n")
    print(output)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT)

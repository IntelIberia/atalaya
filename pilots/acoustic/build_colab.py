"""Build a self-contained, public-data-only Colab pilot notebook.

The notebook embeds hashes and source references, never audio, repository secrets,
or the private Atalaya repository. Run this after the pinned source manifest exists.
"""

# ruff: noqa: E501 - the notebook code is kept readable inside embedded cells.

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "ml/datasets/svanstrom/manifest.json"
OUTPUT = ROOT / "pilots/acoustic/Atalaya_YAMNet_Colab.ipynb"
UPSTREAM_LICENSE_SHA256 = "a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499"


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


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["commit"] == "e7a6eaf9760fa3f9ecc37d09cd11a8cd20be90dd"
    assert manifest["license"] == "CC0-1.0"
    assert manifest["license_evidence"]["upstream_sha256"] == UPSTREAM_LICENSE_SHA256
    clips = [
        {"name": c["path"], "sha256": c["sha256"], "bytes": c["bytes"]} for c in manifest["clips"]
    ]
    assert len(clips) == 90
    config = {
        "source_commit": manifest["commit"],
        "license_sha256": UPSTREAM_LICENSE_SHA256,
        "clips": clips,
        "fraunhofer_record": "https://zenodo.org/api/records/17525811",
        "dads_card": "https://huggingface.co/datasets/geronimobasso/drone-audio-detection-samples",
    }
    cells = [
        md("""# Atalaya · piloto acústico YAMNet

**Exploración técnica; no es un detector operativo.** El repositorio de
[DroneDetectionThesis v1.0.0](https://github.com/DroneDetectionThesis/Drone-detection-dataset/releases/tag/v1.0.0)
declara CC0, pero el [artículo de sus autores](https://www.mdpi.com/2504-446X/6/11/317)
indica que el vídeo visible incluye material externo; no está documentado si algún WAV procede
de esos vídeos. Se verificaron 24 clips por SHA-256 para una inspección inicial con YAMNet;
las nuevas descargas y el entrenamiento quedan **bloqueados** hasta aclarar derechos por
archivo, revisar voz y completar el intake. Los audios se pueden escuchar abajo para esa revisión.

El conjunto incluye 30 clips de dron, 30 de helicóptero y 30 de fondo. No hay IDs fiables de
vuelo, sesión o lugar por archivo. Cualquier reparto por clip sería solo una prueba de
funcionamiento, **no una medida de precisión en otro lugar ni de falsas alarmas de un
perímetro**. No se usa micrófono, audio de clientes, acceso al GitHub privado ni montaje de
Drive en el entorno de ejecución.

[Fraunhofer IDMT](https://zenodo.org/records/17525811) declara CC BY 4.0 y aporta una matriz
de ocho micrófonos para una prueba posterior de dirección de llegada. Una matriz única no
triangula posición por sí sola. [DADS](https://huggingface.co/datasets/geronimobasso/drone-audio-detection-samples)
queda excluido: pese a su etiqueta MIT, mezcla fuentes con restricciones de uso en seguridad,
defensa y uso comercial sin trazabilidad por muestra.
"""),
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
            """import hashlib, json, random, urllib.request, wave
from pathlib import Path
from urllib.parse import urlparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import librosa
import tensorflow as tf
import tensorflow_hub as hub
from IPython.display import Audio, display

PILOT = json.loads('''"""
            + json.dumps(config, ensure_ascii=False, separators=(",", ":"))
            + """''')
SEED = 20261111
N_PER_CLASS = 8  # 24 WAV / ~42 MB; sube hasta 30 tras revisar el coste y la privacidad.
BASE = Path("/content/atalaya_piloto")
BASE.mkdir(parents=True, exist_ok=True)
COMMIT = PILOT["source_commit"]
print("Fuente fijada:", COMMIT, "| clips inventariados:", len(PILOT["clips"]))
"""
        ),
        code("""# Verifica la licencia original antes de descargar datos. Las redirecciones son restringidas.
ALLOWED_HOSTS = {"raw.githubusercontent.com", "api.github.com"}
def read_source(url):
    parsed = urlparse(url)
    assert parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS, "Origen no permitido"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Atalaya-Colab-Pilot/1"}), timeout=90) as r:
        redirected = urlparse(r.geturl())
        assert redirected.scheme == "https" and redirected.hostname in ALLOWED_HOSTS, "Redirección no permitida"
        return r.read()

ROOT_URL = f"https://raw.githubusercontent.com/DroneDetectionThesis/Drone-detection-dataset/{COMMIT}"
license_bytes = read_source(ROOT_URL + "/LICENSE")
assert hashlib.sha256(license_bytes).hexdigest() == PILOT["license_sha256"]
assert b"CC0 1.0 Universal" in license_bytes
print("Licencia CC0 original verificada por SHA-256.")
"""),
        code("""# Selección reproducible y descarga con SHA-256 por archivo. Solo datos públicos.
# La atribución de cada WAV del artículo todavía no está probada. La descarga
# exploratoria inicial ya se verificó; las ejecuciones futuras quedan cerradas.
SOURCE_INTAKE_DOWNLOAD_APPROVED = False
assert SOURCE_INTAKE_DOWNLOAD_APPROVED, "Procedencia por WAV sin verificar: no repetir la ingesta."
assert 1 <= N_PER_CLASS <= 30
randomizer = random.Random(SEED)
selected = []
for prefix in ("BACKGROUND", "HELICOPTER", "DRONE"):
    candidates = sorted((c for c in PILOT["clips"] if c["name"].startswith(prefix + "_")),
                        key=lambda c: c["name"])
    assert len(candidates) == 30
    # La fuente contiene al menos un duplicado exacto: nunca meterlo dos veces.
    unique = {c["sha256"]: c for c in candidates}
    assert len(unique) >= N_PER_CLASS
    selected += randomizer.sample(sorted(unique.values(), key=lambda c: c["name"]), N_PER_CLASS)

for item in selected:
    name = item["name"]
    assert name.replace("_", "").replace(".", "").isalnum() and name.endswith(".wav")
    path = BASE / name
    if path.exists():
        raw = path.read_bytes()
    else:
        raw = read_source(f"{ROOT_URL}/Data/Audio/{name}")
    assert len(raw) == item["bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"], name
    if not path.exists():
        path.write_bytes(raw)
    with wave.open(str(path), "rb") as wav:
        assert wav.getframerate() == 44100 and wav.getsampwidth() == 2
        assert wav.getnchannels() in (1, 2) and 9.9 <= wav.getnframes()/44100 <= 10.1
print(f"Descargados y verificados {len(selected)} WAV ({sum(c['bytes'] for c in selected)/1e6:.1f} MB).")
"""),
        md("""## Revisión de privacidad

Escucha al menos una muestra aleatoria de cada clase y comprueba que no haya voz
identificable u otros datos personales. El resultado automático de YAMNet más abajo
sirve de ayuda, **no sustituye** esta escucha. Si aparece voz, no entrenes; documenta
el clip y resuelve su tratamiento antes de seguir. Los WAV permanecen solo en el
almacenamiento temporal de este entorno de Colab.
"""),
        code("""# Reproducción de tres clips públicos, uno por clase, para revisión humana.
review_names = []
for prefix in ("BACKGROUND", "HELICOPTER", "DRONE"):
    candidate = next(c for c in selected if c["name"].startswith(prefix + "_"))
    review_names.append(candidate["name"])
    audio, sr = librosa.load(BASE / candidate["name"], sr=None, mono=True)
    print(candidate["name"], f"{len(audio)/sr:.1f} s")
    display(Audio(audio, rate=sr))
"""),
        code("""# Intake pendiente: la ficha CC0 no identifica el origen de cada WAV.
# Esta celda documenta el bloqueo; no se desbloquea cambiando una casilla.
TRAINING_ALLOWED = False
assert TRAINING_ALLOWED, "Intake sin aprobar: derechos por fichero, revisión de voz, data card y agrupación."
"""),
        code("""# YAMNet oficial: señal mono float32 a 16 kHz; embeddings congelados por ventana.
MODEL_URL = "https://tfhub.dev/google/yamnet/1"
yamnet = hub.load(MODEL_URL)
class_map_path = yamnet.class_map_path().numpy().decode()
class_names = pd.read_csv(class_map_path)["display_name"].tolist()
assert len(class_names) == 521

rows, vectors, frame_vectors, waveforms = [], [], {}, {}
for item in selected:
    name = item["name"]
    signal, sr = librosa.load(BASE / name, sr=16000, mono=True)
    assert sr == 16000 and np.isfinite(signal).all()
    scores, embeddings, _ = yamnet(tf.convert_to_tensor(signal, dtype=tf.float32))
    score_array, embedding_array = scores.numpy(), embeddings.numpy()
    assert embedding_array.shape[1] == 1024
    vectors.append(embedding_array.mean(axis=0))
    frame_vectors[name] = embedding_array
    waveforms[name] = signal
    speech_columns = [i for i, label in enumerate(class_names)
                      if label in {"Speech", "Conversation", "Narration, monologue", "Child speech, kid speaking"}]
    speech_score = float(score_array[:, speech_columns].max()) if speech_columns else float("nan")
    rows.append({"clip": name, "clase": name.split("_")[0], "dron": int(name.startswith("DRONE_")),
                 "ventanas": len(score_array), "max_speech_score": round(speech_score, 3),
                 "evento_YAMNet": class_names[int(score_array.mean(axis=0).argmax())]})
df = pd.DataFrame(rows)
display(df.sort_values("max_speech_score", ascending=False).head(10))
print("Si YAMNet marca voz, revisa esos clips y no uses material con datos personales sin base resuelta.")
"""),
        code("""# Clasificador simple: regresión logística sobre embeddings congelados de YAMNet.
# Separación por clip: diagnóstica, NO evaluación independiente de vuelos o lugares.
assert TRAINING_ALLOWED, "Entrenamiento bloqueado: el intake de derechos, privacidad y grupos sigue pendiente."
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import ConfusionMatrixDisplay, classification_report

X = np.asarray(vectors)
y = df["dron"].to_numpy()
idx = np.arange(len(y))
train_idx, test_idx = train_test_split(idx, test_size=0.25, random_state=SEED, stratify=y)
head = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEED)
head.fit(X[train_idx], y[train_idx])
proba = head.predict_proba(X[test_idx])[:, 1]
pred = (proba >= 0.5).astype(int)
print("PRUEBA TÉCNICA POR CLIP · posible contaminación entre vuelos/sesiones · no sirve para campo")
print("train:", len(train_idx), "test:", len(test_idx), "umbral fijo: 0.5")
print(classification_report(y[test_idx], pred, labels=[0, 1], target_names=["no dron", "dron"], zero_division=0))
ConfusionMatrixDisplay.from_predictions(y[test_idx], pred, display_labels=["no dron", "dron"])
plt.title("Solo prueba técnica; generalización no verificada")
plt.show()
"""),
        code("""# Resultado visual sobre un clip retenido: espectrograma y puntuación por ventana.
chosen = next((i for i in test_idx if y[i] == 1), test_idx[0])
name = df.iloc[chosen]["clip"]
signal = waveforms[name]
mel = librosa.feature.melspectrogram(y=signal, sr=16000, n_mels=64)
db = librosa.power_to_db(mel, ref=np.max)
window_scores = head.predict_proba(frame_vectors[name])[:, 1]
fig, (a, b) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
librosa.display.specshow(db, sr=16000, x_axis="time", y_axis="mel", ax=a)
a.set_title(f"{name} · espectrograma")
b.plot(np.arange(len(window_scores)) * 0.48, window_scores)
b.axhline(0.5, color="red", linestyle="--", label="umbral exploratorio")
b.set(ylim=(0, 1), ylabel="Puntuación", xlabel="Tiempo (s)")
b.legend()
fig.suptitle("Puntuación sin calibración; no usar para alertas reales")
plt.tight_layout(); plt.show()
"""),
        md("""## Fuentes para las siguientes pruebas

- **Fraunhofer IDMT:** [registro original de Zenodo](https://zenodo.org/records/17525811),
  licencia CC BY 4.0; 1,515,112,211 bytes de audio multicanal. Su estructura y
  coordenadas deben validarse antes de estimar dirección de llegada (azimut). Esta
  descarga grande queda fuera del ensayo rápido de clasificación.
- **DroneDetectionThesis:** el ensayo anterior incluye helicópteros reales como
  confusor. Su conjunto es pequeño y carece de grupos fiables de vuelo/sitio por WAV.
- **DADS:** la [ficha del autor](https://huggingface.co/datasets/geronimobasso/drone-audio-detection-samples)
  declara MIT pero cita [Al-Emadi](https://github.com/saraalemadi/DroneAudioDataset/blob/master/LICENSE.md),
  que prohíbe usos de seguridad y defensa, y [UrbanSound8K](https://urbansounddataset.weebly.com/),
  que limita a usos no comerciales. Hasta tener procedencia por archivo y derechos compatibles, `DADS_ENABLED=False`;
  ningún clip suyo se descarga ni se usa para entrenar este cuaderno.
"""),
        code("""# Auditoría de metadatos de Fraunhofer; NO descarga su ZIP de 1.5 GB.
import urllib.request
FRAUNHOFER = PILOT["fraunhofer_record"]
with urllib.request.urlopen(FRAUNHOFER, timeout=30) as response:
    meta_record = json.load(response)
assert meta_record["metadata"]["license"]["id"] == "cc-by-4.0"
files = meta_record["files"]
assert len(files) == 1 and files[0]["key"] == "MicArrayData30s.zip"
assert files[0]["size"] == 1515112211
print("Fraunhofer:", meta_record["metadata"]["title"])
print("Licencia:", meta_record["metadata"]["license"]["id"], "| archivo:", files[0]["key"])
print("DOA/azimut: fase posterior, con control de geometría y referencia GPS.")
DADS_ENABLED = False
assert not DADS_ENABLED
print("DADS bloqueado hasta resolver licencias y procedencia por archivo.")
"""),
        md("""**Lectura de resultados:** cualquier acierto o error anterior describe solo
estos clips y este reparto. No se ha medido tasa de falsas alarmas por hora,
distancia de detección, precisión en cárceles, nuevos drones o emplazamientos.
Para eso se necesitan grabaciones de campo independientes, negativos continuos,
revisión de privacidad y una evaluación congelada por vuelo/sitio.
"""),
    ]
    # Los scores preentrenados de YAMNet ayudan a dirigir la revisión, pero solo
    # la declaración humana desbloquea el entrenamiento posterior.
    cells[7], cells[8] = cells[8], cells[7]
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
    OUTPUT.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()

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
# Código probado en pilots/acoustic/tests; se incrusta literalmente (Colab no accede al repo).
GROUPED_EVAL = ROOT / "pilots/acoustic/acoustic_pilot/grouped_eval.py"
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
        {
            "name": c["path"],
            "sha256": c["sha256"],
            "bytes": c["bytes"],
            "group_id": c["group_id"],
            "training_excluded": c["training_excluded"],
        }
        for c in manifest["clips"]
    ]
    assert len(clips) == 90
    assert manifest["group_status"] in {"provisional", "verified"}
    grouped_eval_source = GROUPED_EVAL.read_text(encoding="utf-8")
    assert "__future__" not in grouped_eval_source  # se incrusta a mitad de cuaderno
    config = {
        "source_commit": manifest["commit"],
        "license_sha256": UPSTREAM_LICENSE_SHA256,
        "group_status": manifest["group_status"],
        "clips": clips,
        "fraunhofer_record": "https://zenodo.org/api/records/17525811",
        "dads_card": "https://huggingface.co/datasets/geronimobasso/drone-audio-detection-samples",
    }
    cells = [
        md("""# Atalaya · piloto acústico YAMNet

**Exploración técnica; no es un detector operativo.** El repositorio de
[DroneDetectionThesis v1.0.0](https://github.com/DroneDetectionThesis/Drone-detection-dataset/releases/tag/v1.0.0)
declara CC0, pero el artículo de sus autores (Svanström, Alonso-Fernandez y Englund,
[*A dataset for multi-sensor drone detection*](https://arxiv.org/pdf/2111.01888),
*Data in Brief* 39 (2021), 107521) indica que una parte pequeña del conjunto procede de YouTube
y que el audio se extrajo de los vídeos o se grabó aparte; la
[tesis del primer autor](https://hh.diva-portal.org/smash/get/diva2%3A1434532/FULLTEXT02.pdf)
sitúa 49 clips externos en el vídeo visible. No está documentado si algún WAV procede de ellos.

**Recuento de clips:** el inventario fijado contiene **90 WAV** (30 por clase), verificados por
SHA-256 en el preflight local de la data card. Este cuaderno usa una **muestra de 24**
(`N_PER_CLASS = 8` por clase, sin duplicados exactos) y verifica cada WAV contra ese inventario.
Las nuevas descargas y el entrenamiento quedan **bloqueados** hasta aclarar derechos por
archivo, revisar voz y completar el intake. Los audios se pueden escuchar abajo para esa revisión.

Pesos de [YAMNet](https://www.kaggle.com/models/google/yamnet) (Google, vía TF Hub/Kaggle):
licencia Apache 2.0 según la ficha oficial de Kaggle (véase la model card del piloto).

No hay IDs fiables de vuelo, sesión o lugar por archivo: los grupos son provisionales (un
clip, o un par de duplicados exactos). La partición train/validación/test por grupos es solo una
prueba de funcionamiento, con contaminación entre particiones no descartada, **no una medida de precisión en otro lugar ni de falsas alarmas de un
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
import librosa.display
import tensorflow as tf
import tensorflow_hub as hub
from IPython.display import Audio, display
# Las funciones split_indices_by_group, choose_threshold, binary_metrics, group_bootstrap,
# false_alarms_per_hour y metric_caption se definen en la celda siguiente (código probado).

PILOT = json.loads('''"""
            + json.dumps(config, ensure_ascii=False, separators=(",", ":"))
            + """''')
SEED = 20261111
N_PER_CLASS = 8  # muestra de 24 de los 90 WAV inventariados (~42 MB); máx. 30 tras revisar coste y privacidad.
BASE = Path("/content/atalaya_piloto")
BASE.mkdir(parents=True, exist_ok=True)
COMMIT = PILOT["source_commit"]
print("Fuente fijada:", COMMIT, "| clips inventariados:", len(PILOT["clips"]),
      "| muestra prevista:", 3 * N_PER_CLASS, "| grupos:", PILOT["group_status"])
"""
        ),
        code(grouped_eval_source),
        code("""# Verifica la licencia original antes de descargar datos. Las redirecciones son restringidas.
ALLOWED_HOSTS = {"raw.githubusercontent.com", "api.github.com"}
def read_https(url, allowed_hosts, timeout=90):
    parsed = urlparse(url)
    assert parsed.scheme == "https" and parsed.hostname in allowed_hosts, "Origen no permitido"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Atalaya-Colab-Pilot/1"}), timeout=timeout) as r:
        redirected = urlparse(r.geturl())
        assert redirected.scheme == "https" and redirected.hostname in allowed_hosts, "Redirección no permitida"
        return r.read()

def read_source(url):
    return read_https(url, ALLOWED_HOSTS)

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
    candidates = [c for c in candidates if not c["training_excluded"]]
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
        code("""# Clasificador simple: regresión logística sobre la MEDIA de embeddings YAMNet por clip.
# Partición train/validación/test por group_id (ningún grupo en dos particiones).
# El umbral se fija en validación y se guarda; test solo se usa para medir.
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import ConfusionMatrixDisplay

assert TRAINING_ALLOWED, "Entrenamiento bloqueado: intake de derechos, privacidad y grupos pendiente."

PROVISIONAL = PILOT["group_status"] != "verified"
CAPTION = metric_caption(provisional=PROVISIONAL)
GROUP_OF = {c["name"]: c["group_id"] for c in PILOT["clips"]}
X = np.asarray(vectors)  # una fila por clip: media temporal de los embeddings de 1024 dimensiones
y = df["dron"].to_numpy().astype(int)
groups = [GROUP_OF[n] for n in df["clip"]]
train_idx, validation_idx, test_idx = (np.asarray(part) for part in
                                       split_indices_by_group(y.tolist(), groups, seed=SEED))
part_groups = [{groups[i] for i in part} for part in (train_idx, validation_idx, test_idx)]
assert not (part_groups[0] & part_groups[1] or part_groups[0] & part_groups[2]
            or part_groups[1] & part_groups[2]), "un grupo aparece en dos particiones"

head = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEED)
head.fit(X[train_idx], y[train_idx])
threshold = choose_threshold(y[validation_idx], head.predict_proba(X[validation_idx])[:, 1])
MODEL_RECORD = {
    "modelo": "LogisticRegression sobre media de embeddings YAMNet por clip",
    "yamnet": MODEL_URL, "seed": SEED, "group_status": PILOT["group_status"],
    "umbral": threshold, "umbral_elegido_en": "validación (máximo F1; empate -> umbral mayor)",
    "particiones": {k: sorted(df["clip"].iloc[v]) for k, v in
                    (("train", train_idx), ("validacion", validation_idx), ("test", test_idx))},
    "coef_sha256": hashlib.sha256(head.coef_.tobytes() + head.intercept_.tobytes()).hexdigest(),
}
(BASE / "modelo_piloto.json").write_text(json.dumps(MODEL_RECORD, ensure_ascii=False, indent=1))
print("Umbral fijado en validación y guardado en modelo_piloto.json:", round(threshold, 4))
print("clips train/val/test:", len(train_idx), len(validation_idx), len(test_idx),
      "| grupos:", [len(g) for g in part_groups], CAPTION)

proba = head.predict_proba(X[test_idx])[:, 1]
m = binary_metrics(y[test_idx], proba, threshold)
boot = group_bootstrap(y[test_idx], proba, [groups[i] for i in test_idx], threshold, seed=SEED)
def interval(name):
    if boot["status"] != "OK":
        return (f"IC 95 % por grupo: NO DISPONIBLE "
                f"({boot['n_groups']} grupos de test < {boot['min_groups']})")
    lo, hi = boot["intervals"][name]
    return f"IC 95 % por grupo [{lo:.3f}, {hi:.3f}]"
print("Matriz de confusión (test):", {k: m[k] for k in ("tn", "fp", "fn", "tp")}, CAPTION)
for name in ("precision", "recall", "pr_auc"):
    print(f"{name}: {m[name]:.3f} · {interval(name)} {CAPTION}")
# Los clips son de ~10 s y no contiguos: no hay duración negativa continua conocida.
# Mínimo exploratorio de este cuaderno, no requisito (REQ-NFR-004 se evalúa en evals/frozen).
FA_MIN_CONTINUOUS_HOURS = 24.0
LONGEST_CONTINUOUS_NEGATIVE_S = 10.0
fa = false_alarms_per_hour(m["fp"], continuous_negative_seconds=LONGEST_CONTINUOUS_NEGATIVE_S,
                           min_hours=FA_MIN_CONTINUOUS_HOURS)
print("Falsas alarmas por hora:", fa["status"] if fa["value"] is None else f"{fa['value']:.3f}",
      f"(negativo continuo conocido {fa['hours']*3600:.0f} s < {FA_MIN_CONTINUOUS_HOURS:.0f} h)"
      if fa["value"] is None else "", CAPTION)
ConfusionMatrixDisplay.from_predictions(y[test_idx], (proba >= threshold).astype(int),
                                        labels=[0, 1], display_labels=["no dron", "dron"])
plt.title(f"Test · umbral de validación {threshold:.3f}\\n{CAPTION}", fontsize=9)
plt.show()
"""),
        code("""# Ilustración sobre un clip de test: espectrograma y puntuación por ventana.
# AVISO: el clasificador se entrenó con la MEDIA de embeddings por clip. Aplicarlo a ventanas
# sueltas de 0,96 s (salto 0,48 s) queda fuera de su distribución de entrenamiento: la curva
# NO está calibrada y el umbral (fijado por clip en validación) no es un umbral por ventana.
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
b.axhline(threshold, color="red", linestyle="--",
          label="umbral por clip (validación); no válido por ventana")
b.set(ylim=(0, 1), ylabel="Puntuación sin calibrar", xlabel="Tiempo (s)")
b.legend()
fig.suptitle("Modelo por clip (media de embeddings) aplicado a ventanas: "
             "curva NO calibrada, solo ilustrativa\\n" + CAPTION, fontsize=9)
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
# Misma restricción de hosts y redirecciones que la celda de licencia de Svanström.
FRAUNHOFER_HOSTS = {"zenodo.org"}
FRAUNHOFER = PILOT["fraunhofer_record"]
meta_record = json.loads(read_https(FRAUNHOFER, FRAUNHOFER_HOSTS, timeout=30))
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
    cells[8], cells[9] = cells[9], cells[8]
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

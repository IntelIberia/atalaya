"""Celdas del cuaderno de la iteración 6 (hito 2, H2.5). Las genera ``build_colab.py --iter6``;
el cuaderno nunca se edita a mano. Reutiliza literalmente las celdas de descarga verificada de la
iteración 5 y añade: fuentes de dron extra (desactivadas sin autorización), rasgos por ventana con
normalización de canal y rasgo armónico, aumento de canal y mezclas cruzadas, evaluación LOSO
principal con criterio C-LOSO (ADR 0018) y D-6 de referencia, modelo final, ONNX con paridad,
artefacto modelo_hito2.json con vectores dorados y la sección «Prueba tu audio»."""

# ruff: noqa: E501 - el código de las celdas se mantiene legible dentro de cadenas.

from __future__ import annotations

ITER6_MODULES = (
    "channel_norm",
    "channel_augment",
    "harmonic",
    "alert_logic",
    "domain_robust",
    "model_export",
    "user_audio",
    "extra_sources",
)
MAIN_VARIANT = "iter6 · completo (canal + cruzadas + armónico + INLP + DRO)"
BASELINE_VARIANT = "iter5 · YAMNet media (línea base)"
# Pins de Colab (NO VERIFICADOS hasta ejecutar): tf2onnx sin dependencias para no degradar
# protobuf; onnx y onnxruntime sin tocar numpy/protobuf/tensorflow de Colab.
COLAB_PINS = {
    "tensorflow-hub": "0.16.1",
    "onnx": "1.17.0",
    "onnxruntime": "1.20.1",
    "tf2onnx": "1.16.1",
}
ONNX_OPSET = 17

INTRO6 = (
    """# Atalaya · piloto acústico YAMNet · iteración 6 (hito 2: contra el atajo de dominio)

**Exploración técnica; no es un detector operativo.** Prueba técnica aislada en Colab (ADR 0016
y ADR 0017): nada de este cuaderno entra en el producto. Las cifras no son métricas de campo.

**Por qué esta iteración.** La iteración 5 separaba bien dentro de las fuentes vistas, pero ante
una fuente nunca vista fallaba (leave-one-source-out: ROC-AUC 0,29–0,39 en ITU ARIS, recall ≈ 0
con el umbral, hasta 40–52 % de falsas alarmas en FSD50K): aprendía el canal de cada dataset.
El micrófono del Mac frente a un altavoz es otra fuente nueva.

**Qué cambia (todo el código probado en `pilots/acoustic/tests` e incrustado tal cual):**
1. **Normalización de canal** compartida con el Mac (`channel_norm`): 16 kHz, paso banda
   100–7 500 Hz, sonoridad por ventana y PCEN; YAMNet ve ventanas de 0,96 s normalizadas.
2. **Aumento de canal** solo en entrenamiento (`channel_augment`): EQ, micrófono, altavoz
   pequeño, sala sintética, códec mu-law y ruido; `synthetic=true`.
3. **Mezclas cruzadas** (`augment.plan_cross_mixes`): dron de una fuente sobre fondo de OTRA.
4. **Rasgo armónico de hélices** (`harmonic`): 8 rasgos que se concatenan al embedding.
5. **Contra el atajo de dominio** (`domain_robust`): INLP (se proyecta fuera lo que distingue una
   fuente de otra dentro de cada clase), group-DRO por fuente × clase y **umbral por peor fuente**
   (FPR de validación ≤ 5 % en cada fuente); calibración de sitio como variante aparte (D-7).
6. **Evaluación:** **LOSO es la métrica principal**; criterio **C-LOSO** (ADR 0018, propuesto) y
   D-6 como referencia. Modelo principal **preinscrito** (no se elige mirando LOSO):
   `"""
    + MAIN_VARIANT
    + """`.
7. **Exportación:** YAMNet a ONNX con `tf2onnx` y paridad ≤ 1e-4 frente a TensorFlow;
   `modelo_hito2.json` (pesos, Platt, alerta, hashes y vectores dorados), `predicciones.csv`,
   `registro_iter6.json` y `SHA256SUMS`. Recálculo independiente:
   `uv run python recompute_metrics.py predicciones.csv --sha256 <hash> --record registro_iter6.json --artifact modelo_hito2.json --criterio c-loso`.
8. **Prueba tu audio:** al final, sube un fichero propio y el cuaderno lo analiza por la misma
   ruta que el modelo exportado (ventanas, puerta de voz, alerta 3 de 5 con histéresis).

**Fuentes:** las mismas que la iteración 5 (Svanström CC0, ESC-10 CC BY 3.0, FSD50K solo CC0/CC BY
por clip, ITU ARIS CC BY 4.0). Las fuentes de dron extra (Salford DroneNoise CC BY 4.0,
DroneAudioSet solo-dron MIT, Yi-KAIST CC BY 4.0) están **desactivadas** salvo autorización expresa
registrada en `docs/requirements/DECISIONES-USUARIO.md`: sin ellas, el criterio C-LOSO queda
**NO EVALUABLE** en los pliegues con una sola fuente de dron entrenando. **Prohibidas** (nunca se
descargan): DADS, Al-Emadi, UrbanSound8K, ESC-50 fuera de ESC-10, Sonniss y AeroSonicDB.

**Cómo ejecutarlo:** Colab gratuito (CPU), «Entorno de ejecución → Ejecutar todas». No hace falta
reiniciar tras instalar dependencias (solo se instala lo que falta, sin tocar numpy ni protobuf).
Puntos de control en `/content/atalaya_piloto` (sin Drive): si el kernel se reinicia, «Ejecutar
todas» salta lo ya descargado y calculado; si Colab recicla la máquina, se empieza de cero.
Tiempo orientativo **NO VERIFICADO**: 1,5–3 h.
"""
)

DEPS6 = (
    r"""# Dependencias: SOLO lo que falta, fijando numpy/protobuf/tensorflow a lo que ya trae Colab para no
# obligar a reiniciar el kernel. tf2onnx va sin dependencias (las suyas exigen protobuf 3.20).
import importlib, importlib.metadata as meta, importlib.util, subprocess, sys
PINS = """
    + repr(COLAB_PINS)
    + r"""
def _missing(module):
    return importlib.util.find_spec(module) is None
keep = [f"{name}=={meta.version(name)}" for name in ("numpy", "protobuf", "tensorflow")]
tf_minor = ".".join(meta.version("tensorflow").split(".")[:2])
wanted = [(f"tensorflow-hub=={PINS['tensorflow-hub']}", "tensorflow_hub"), (f"tf-keras=={tf_minor}.*", "tf_keras"),
          (f"onnx=={PINS['onnx']}", "onnx"), (f"onnxruntime=={PINS['onnxruntime']}", "onnxruntime")]
todo = [spec for spec, module in wanted if _missing(module)]
if todo:
    print("Instalando:", ", ".join(todo))
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *todo, *keep])
if _missing("tf2onnx"):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--no-deps", f"tf2onnx=={PINS['tf2onnx']}"])
importlib.invalidate_caches()
for name in ("tensorflow", "tensorflow-hub", "onnx", "onnxruntime", "tf2onnx", "numpy", "protobuf", "librosa", "soundfile"):
    try:
        print(f"  {name} {meta.version(name)}")
    except meta.PackageNotFoundError:
        print(f"  {name}: NO INSTALADO")
print("Dependencias listas; no hace falta reiniciar el entorno.")
"""
)


def setup6(config_json: str, extra_authorization: dict) -> str:
    return (
        r"""import csv, hashlib, io, json, math, os, random, tarfile, time, wave, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import librosa
import tensorflow as tf
import tensorflow_hub as hub
from IPython.display import Audio, display
# Las celdas siguientes definen el código probado en pilots/acoustic/tests (incrustado tal cual).

"""
        + "PILOT = json.loads('''"
        + config_json
        + r"""''')
SEED = 20261111
N_PER_CLASS = 30
TARGET_RECALL = 0.90  # SOLO para la línea base de la iteración 5 (su regla de umbral)
N_FOLDS = 5
# Iteración 6 (valores fijados ANTES de ejecutar; no se ajustan mirando LOSO ni test):
MAIN_VARIANT = """
        + repr(MAIN_VARIANT)
        + r"""
BASELINE_VARIANT = """
        + repr(BASELINE_VARIANT)
        + r"""
MAX_WINDOWS_CLIP = 24     # ventanas de 0,96 s por clip (equiespaciadas, deterministas)
MAX_WINDOWS_AUG = 4       # ventanas por copia aumentada o mezcla cruzada
MAX_FRAMES_TRAIN = 4      # ventanas por clip en el entrenamiento
N_CROSS_MIXES = 1500      # mezclas cruzadas dron/fondo (fuentes distintas), solo entrenamiento
N_CHANNEL_AUG = 2000      # copias con canal aleatorio (ambas clases), solo entrenamiento
MAX_FPR_ON = 0.05         # umbral por peor fuente: FPR de validación <= 5 % en CADA fuente
MAX_FPR_OFF = 0.15        # fin de alerta (histéresis)
INLP_ROUNDS = 2
DRO_ROUNDS = 3
DRO_ETA = 1.0
LR_C = 0.5
CAL_GROUPS = 5            # variante de sitio (D-7): grupos negativos de la fuente retenida
ONNX_OPSET = """
        + str(ONNX_OPSET)
        + r"""
PARITY_TOL = 1e-4
PARITY_WINDOWS = 60
CODE_VERSION = "iteracion-6"
NOTEBOOK_CODE_SHA256 = "__CODIGO_SHA256__"  # SHA-256 de las celdas (con este marcador), fijado al generar
EXTRA_AUTHORIZATION = """
        + repr(extra_authorization)
        + r"""  # fuente -> cita de DECISIONES-USUARIO.md (None = desactivada)
BASE = Path("/content/atalaya_piloto")
BASE.mkdir(parents=True, exist_ok=True)
CHECKPOINTS = BASE / "checkpoints"
CHECKPOINTS.mkdir(exist_ok=True)
COMMIT = PILOT["source_commit"]
PROHIBITED = PILOT["prohibited"]
T0 = time.time()
def step(msg):
    print(f"[{(time.time() - T0) / 60:6.1f} min] {msg}", flush=True)
def load_audio(path):
    return librosa.load(str(path), sr=None, mono=False)
step(f"Iteración 6 · modelo principal preinscrito: {MAIN_VARIANT}")
print("Fuentes prohibidas (no se descargan):", ", ".join(PROHIBITED))
"""
    )


EXTRA6 = r"""# Fuentes de DRON adicionales (iteración 6). Sus manifiestos siguen con intake_approved=false: solo
# se descargan si EXTRA_AUTHORIZATION tiene la cita de la decisión del usuario para cada una.
# Cada fichero se verifica por tamaño y MD5/SHA-256 publicados por la fuente original.
EXTRA_ENABLED = enabled_extra_sources(EXTRA_AUTHORIZATION)
EXTRA_INVENTORY = []
if not EXTRA_ENABLED:
    print("Fuentes de dron extra: NINGUNA (sin autorización registrada). C-LOSO quedará NO EVALUABLE en",
          "los pliegues con una sola fuente de dron entrenando.")
else:
    step("Fuentes de dron extra autorizadas: " + ", ".join(EXTRA_ENABLED))
import soundfile as sf
if "salford" in EXTRA_ENABLED:
    SAL = PILOT["extra"]["salford"]
    FIGSHARE_HOSTS = {"api.figshare.com", "ndownloader.figshare.com", "s3-eu-west-1.amazonaws.com"}
    record = json.loads(read_https(SAL["api"], FIGSHARE_HOSTS, limit=1 << 22))
    assert record["license"]["name"] == "CC BY 4.0", record["license"]
    remote_files = {f["id"]: (f["computed_md5"], f["size"]) for f in record["files"]}
    (BASE / "salford").mkdir(exist_ok=True)
    def fetch_salford(f):
        assert remote_files[f["figshare_file_id"]] == (f["md5"], f["bytes"]), f["path"]
        path = BASE / "salford" / f["path"]
        return path, stream_download(f["url"], FIGSHARE_HOSTS, path, size=f["bytes"], md5=f["md5"])
    got = run_concurrent(SAL["files"], fetch_salford, workers=4, on_done=Progress("Salford", len(SAL["files"]), every=20))
    for f, (path, digest) in zip(SAL["files"], got):
        CATALOG.append({"clip": f"salford/{f['path']}", "fuente": "salford", "path": path, "clase": "SALFORD_" + f["suas_code"],
                        "dron": 1, "grupo": f["group_id"], "split": None, "recorte": "energia"})
        EXTRA_INVENTORY.append((f"salford/{f['path']}", digest))
    step(f"Salford: {len(SAL['files'])} sobrevuelos verificados (MD5 de Figshare; SHA-256 calculado)")
if "droneaudioset" in EXTRA_ENABLED:
    DAS = PILOT["extra"]["droneaudioset"]
    HF_HOSTS = {"huggingface.co", "cdn-lfs.hf.co", "cdn-lfs-us-1.hf.co", "cas-bridge.xethub.hf.co", "cdn-lfs.huggingface.co"}
    das_info = json.loads(read_https(DAS["info_url"], HF_HOSTS, limit=1 << 22))
    assert das_info.get("sha") == DAS["revision"] and das_info.get("cardData", {}).get("license") == "mit"
    import pyarrow.parquet as pq
    (BASE / "droneaudioset").mkdir(exist_ok=True)
    for f in DAS["files"]:
        path = BASE / "droneaudioset" / f["path"].split("/")[-1]
        digest = stream_download(f["url"], HF_HOSTS, path, size=f["bytes"], sha256=f["sha256"])
        table = pq.read_table(path).to_pylist()
        wanted = {r["upstream_file_path"]: r for r in f["rows"]}
        for row in table:
            meta_row = wanted.get(row.get("file_path"))
            if meta_row is None:
                continue  # silence u otra toma no admitida
            audio = next(v for v in row.values() if isinstance(v, dict) and ("bytes" in v or "array" in v))
            if audio.get("bytes"):
                data, sr = sf.read(io.BytesIO(audio["bytes"]), always_2d=True)
            else:
                data, sr = np.asarray(audio["array"], dtype=np.float32).reshape(-1, 1), int(audio["sampling_rate"])
            mono = data[:, 0].astype(np.float32)  # un canal (micrófono de referencia de cada toma)
            stem = meta_row["upstream_file_path"].replace("/", "__").removesuffix(".wav")
            for k, start in enumerate(chunk_starts(len(mono), sr)):
                out = BASE / "droneaudioset" / f"{stem}__{k}.wav"
                chunk = mono[start:start + int(EXTRA_CHUNK_SECONDS * sr)]
                if not out.is_file():
                    sf.write(str(out), chunk, sr, subtype="FLOAT")
                CATALOG.append({"clip": f"droneaudioset/{out.name}", "fuente": "droneaudioset", "path": out,
                                "clase": "DAS_" + meta_row["drone"], "dron": 1, "grupo": meta_row["group_id"], "split": None})
        EXTRA_INVENTORY.append((f"droneaudioset/{f['path']}", digest))
        del table
    step(f"DroneAudioSet: {len(DAS['files'])} parquet verificados por SHA-256 (una toma por sesión)")
if "yi_kaist" in EXTRA_ENABLED:
    YI = PILOT["extra"]["yi_kaist"]
    yi_record = json.loads(read_https(YI["api"], ZENODO_HOSTS, limit=1 << 22))
    assert yi_record["metadata"]["license"]["id"] == "cc-by-4.0"
    tar_path = BASE / "yi_kaist" / YI["file"]["path"]
    digest = stream_download(YI["file"]["url"], ZENODO_HOSTS, tar_path, size=YI["file"]["bytes"], md5=YI["file"]["md5"])
    EXTRA_INVENTORY.append((f"yi_kaist/{YI['file']['path']}", digest))
    normal = {}
    with tarfile.open(tar_path, mode="r|") as archive:
        for member in archive:
            name = member.name
            meta_name = parse_yi_name(name)
            if not member.isfile() or meta_name is None or meta_name["fault"] != "N" or not name.lower().endswith(".wav"):
                continue
            assert not name.startswith("/") and ".." not in name.split("/"), name
            normal[name] = archive.extractfile(member).read()
    pairs = yi_selection(sorted(normal), n_pairs=YI["n_pairs"], seed=SEED)
    (BASE / "yi_kaist" / "pares").mkdir(parents=True, exist_ok=True)
    for p in pairs:
        parts = [sf.read(io.BytesIO(normal[s]), always_2d=True) for s in p["segments"]]
        sr = parts[0][1]
        joined = concat_with_crossfade([d[:, 0] for d, _ in parts], sr)
        out = BASE / "yi_kaist" / "pares" / f"{p['id']}.wav"
        sf.write(str(out), joined, sr, subtype="FLOAT")
        CATALOG.append({"clip": f"yi_kaist/{p['id']}.wav", "fuente": "yi_kaist", "path": out, "clase": "YI_A_NORMAL",
                        "dron": 1, "grupo": p["group_id"], "split": None})
    del normal
    step(f"Yi-KAIST: {len(pairs)} pares de segmentos normales concatenados (1 s; synthetic_concat=true)")
catalog = pd.DataFrame(CATALOG)
assert catalog["clip"].is_unique
assert not set(catalog["fuente"]) - {"svanstrom", "esc10", "fsd50k", "aris", *EXTRA_ENABLED}
display(catalog.groupby(["fuente", "dron"]).agg(clips=("clip", "size"), grupos=("grupo", "nunique")))
"""

FEATURES6 = r"""# YAMNet + rasgos por lotes con puntos de control (código probado: data_quality, channel_norm,
# harmonic, model_export.window_features). Por clip: calidad (corrupto/silencioso/saturado), mono
# 16 kHz y DOS vistas: (a) línea base de la iteración 5, YAMNet sobre el clip entero SIN
# normalización (embedding medio y puntuación de voz por clip); (b) iteración 6, ventanas de 0,96 s
# con salto de 0,48 s (máx. MAX_WINDOWS_CLIP) -> normalización de canal -> YAMNet -> rasgo
# armónico: EXACTAMENTE la ruta del Mac y de «Prueba tu audio».
MODEL_URL = "https://tfhub.dev/google/yamnet/1"
if "yamnet" not in globals():
    yamnet = hub.load(MODEL_URL)
class_names = pd.read_csv(yamnet.class_map_path().numpy().decode())["display_name"].tolist()
assert len(class_names) == 521
speech_columns = [i for i, label in enumerate(class_names)
                  if label in {"Speech", "Conversation", "Narration, monologue", "Child speech, kid speaking"}]
assert len(speech_columns) == 4
SPEECH_NAMES = [class_names[i] for i in speech_columns]

def yamnet_tf(window):
    scores, embeddings, _ = yamnet(tf.convert_to_tensor(np.asarray(window, dtype=np.float32)))
    return scores.numpy(), embeddings.numpy()

def pick_windows(n_samples, limit):
    starts = frame_starts(n_samples)
    if len(starts) > limit:
        starts = [starts[i] for i in np.unique(np.linspace(0, len(starts) - 1, limit).round().astype(int))]
    return starts

def windows_of_signal(signal16k, limit):
    feats = [window_features(extract_window(signal16k, s), yamnet_tf, speech_columns) for s in pick_windows(len(signal16k), limit)]
    x = np.stack([np.concatenate([f["embedding"], f["armonico"]]) for f in feats]).astype(np.float32)
    return x, np.array([f["voz"] for f in feats], dtype=np.float32)

PATHS = {c["clip"]: c["path"] for c in CATALOG}
CLIP_SOURCE = {c["clip"]: c["fuente"] for c in CATALOG}
CROP = {c["clip"]: c.get("recorte") for c in CATALOG}
FILE_SHA256 = {c["clip"]: hashlib.sha256(Path(c["path"]).read_bytes()).hexdigest() for c in CATALOG}
DATA_INVENTORY_SHA256 = inventory_sha256(FILE_SHA256.items())
FEAT_CONTEXT = f"{MODEL_URL}|{TARGET_SR}|{CODE_VERSION}|{norm_config_sha256()}|{json.dumps(HARMONIC_CONFIG, sort_keys=True)}|{MAX_WINDOWS_CLIP}"
FEAT_SHARD = 128
step(f"Inventario de datos SHA-256: {DATA_INVENTORY_SHA256} ({len(CATALOG)} clips)")

def load_signal(clip):
    raw, sr = load_audio(PATHS[clip])
    signal = normalize_format(raw, sr)
    return energy_crop(signal, TARGET_SR) if CROP.get(clip) == "energia" else signal

def feature_shard(items):
    rows, quality_dropped, means5, blocks6, speech6 = [], [], [], [], []
    for item in items:
        try:
            raw, sr = load_audio(item["path"])
            quality = clip_quality(raw, sr)
        except Exception as exc:  # ilegible => corrupto (se informa; nunca se corrige)
            quality = {"status": "corrupto", "error": type(exc).__name__}
        if quality["status"] != "ok":
            quality_dropped.append({"clip": item["clip"], "fuente": item["fuente"], "motivo": "calidad: " + quality["status"],
                                    "detalle": json.dumps(quality, default=str, sort_keys=True)})
            continue
        signal = normalize_format(raw, sr)
        if item.get("recorte") == "energia":
            signal = energy_crop(signal, TARGET_SR)
        padded = signal if len(signal) >= 15600 else np.pad(signal, (0, 15600 - len(signal)))
        scores5, emb5 = yamnet_tf(padded)
        x6, voz6 = windows_of_signal(signal, MAX_WINDOWS_CLIP)
        means5.append(emb5.mean(axis=0))
        blocks6.append(x6)
        speech6.append(voz6)
        rows.append({"clip": item["clip"], "fuente": item["fuente"], "clase": item["clase"], "dron": int(item["dron"]),
                     "grupo": item["grupo"], "tipo": "dron" if item["dron"] else negative_type(item["fuente"], item["clase"]),
                     "segundos": round(len(signal) / TARGET_SR, 3), "ventanas": int(len(x6)),
                     "max_speech_score": round(float(scores5[:, speech_columns].max()), 3),
                     "pcm_sha256": pcm_sha256(signal), "file_sha256": FILE_SHA256[item["clip"]]})
    x6, off6 = pack_frames(blocks6) if blocks6 else (np.zeros((0, 1032), np.float32), np.zeros(1, np.int64))
    sp6, _ = pack_frames([v[:, None] for v in speech6]) if speech6 else (np.zeros((0, 1), np.float32), None)
    arrays = {"means5": np.asarray(means5, np.float32).reshape(-1, 1024), "x6": x6, "off6": off6, "voz6": sp6[:, 0]}
    return arrays, {"rows": rows, "quality": quality_dropped}

rows, QUALITY_DROPPED, parts = [], [], []
ranges = shard_ranges(len(CATALOG), FEAT_SHARD)
reused = 0
for n, (a, b) in enumerate(ranges, 1):
    items = CATALOG[a:b]
    key = shard_key([(c["clip"], FILE_SHA256[c["clip"]]) for c in items], FEAT_CONTEXT)
    path = CHECKPOINTS / f"rasgos6_{a:06d}_{key[:16]}.npz"
    loaded = load_shard(path, key)
    if loaded is None:
        loaded = feature_shard(items)
        save_shard(path, key, *loaded)  # guardado incremental: un corte solo pierde el lote en curso
    else:
        reused += 1
    arrays, meta = loaded
    rows += meta["rows"]
    QUALITY_DROPPED += meta["quality"]
    parts.append(arrays)
    step(f"Rasgos: lote {n}/{len(ranges)} ({b}/{len(CATALOG)} clips; {reused} lotes reutilizados)")
MEANS5 = np.vstack([p["means5"] for p in parts])
X6, OFF6 = pack_frames([unpack_frames(p["x6"], p["off6"], i) for p in parts for i in range(len(p["off6"]) - 1)])
VOZ6 = np.concatenate([p["voz6"] for p in parts])
del parts
assert len(MEANS5) == len(rows) == len(OFF6) - 1 and len(VOZ6) == len(X6)
info = pd.DataFrame(rows)
step(f"Rasgos listos: {len(info)} clips, {len(X6)} ventanas normalizadas; descartados por calidad: {len(QUALITY_DROPPED)}")
display(info.groupby("fuente")[["segundos", "ventanas"]].sum())
"""

GATE6 = r"""# Puerta automática de privacidad (código probado: apply_speech_gate) en TODAS las fuentes, igual
# que en la iteración 5 (puntuación de voz de YAMNet sobre el clip completo). Además, en la
# iteración 6 las VENTANAS con voz >= umbral se descartan como en el Mac (puerta por ventana).
HUMAN_CLEARED = {
    "svanstrom/BACKGROUND_006.wav": "usuario, 2026-11-11: escuchado; crujido de madera, no es voz",
}
SPEECH_GATE = apply_speech_gate(info["clip"].tolist(), info["max_speech_score"].tolist(),
                                threshold=SPEECH_EXCLUSION_THRESHOLD, human_cleared=HUMAN_CLEARED)
SPEECH_DROPPED = [{"clip": e["clip"], "fuente": CLIP_SOURCE[e["clip"]], "motivo": "posible voz",
                   "detalle": f"{e['motivo']}; max_speech_score={e['max_speech_score']}"}
                  for e in SPEECH_GATE["excluded"]]
print(f"Excluidos por posible voz (umbral {SPEECH_EXCLUSION_THRESHOLD:.2f}): {len(SPEECH_DROPPED)}; "
      f"reincorporados por revisión humana: {SPEECH_GATE['human_cleared']}")
print(SPEECH_GATE["note"])
keep = list(SPEECH_GATE["kept_indices"])
info = info.iloc[keep].reset_index(drop=True)
MEANS5 = MEANS5[keep]
blocks = [unpack_frames(X6, OFF6, i) for i in keep]
voz_blocks = [VOZ6[OFF6[i]:OFF6[i + 1]] for i in keep]
X6, OFF6 = pack_frames(blocks)
VOZ6 = np.concatenate(voz_blocks)
WINDOW_SPEECH = VOZ6 >= SPEECH_EXCLUSION_THRESHOLD
print(f"Ventanas con voz descartadas (puerta por ventana): {int(WINDOW_SPEECH.sum())} de {len(VOZ6)}")
assert len(MEANS5) == len(info) == len(OFF6) - 1
"""

TRAINING_GATE6 = r"""# Intake pendiente: los manifiestos del repo siguen con intake_approved=false.
# Decisión del usuario 2026-11-11 (prueba técnica) y plan del hito 2 aprobado el 2026-11-16 (H2.5):
# entrenamiento SOLO en esta prueba técnica aislada; nada entra en el producto.
TRAINING_ALLOWED = True
assert TRAINING_ALLOWED, "Intake sin aprobar: derechos por fichero, revisión de voz, data card y agrupación."
"""

DEDUP6 = r"""# Duplicados exactos (hash del PCM) y casi duplicados (coseno de la media de embeddings YAMNet de la
# línea base >= NEAR_DUPLICATE_COSINE entre grupos distintos), como en la iteración 5.
assert TRAINING_ALLOWED, "Entrenamiento bloqueado"
exact = exact_duplicates(info["pcm_sha256"].tolist(), info["clip"].tolist())
pairs = [(i, j, s) for i, j, s in near_duplicate_pairs(MEANS5, threshold=NEAR_DUPLICATE_COSINE, groups=info["grupo"].tolist())
         if i not in exact and j not in exact]
near = resolve_near_duplicates(pairs, info["grupo"].tolist(), info["clip"].tolist())
DUP_DROPPED = [{"clip": info["clip"][i], "fuente": info["fuente"][i], "motivo": "duplicado exacto",
                "detalle": "se conserva " + info["clip"][d["kept"]]} for i, d in exact.items()]
DUP_DROPPED += [{"clip": info["clip"][i], "fuente": info["fuente"][i], "motivo": "casi duplicado entre grupos",
                 "detalle": f"coseno >= {NEAR_DUPLICATE_COSINE}; grupo conservado {g}"} for i, g in near["dropped"].items()]
drop = set(exact) | set(near["dropped"])
keep = [i for i in range(len(info)) if i not in drop]
info = info.iloc[keep].reset_index(drop=True)
MEANS5 = MEANS5[keep]
voz_blocks = [VOZ6[OFF6[i]:OFF6[i + 1]] for i in keep]
X6, OFF6 = pack_frames([unpack_frames(X6, OFF6, i) for i in keep])
VOZ6 = np.concatenate(voz_blocks)
WINDOW_SPEECH = VOZ6 >= SPEECH_EXCLUSION_THRESHOLD
residual = near_duplicate_pairs(MEANS5, threshold=NEAR_DUPLICATE_COSINE, groups=info["grupo"].tolist())
assert not residual, "quedan casi duplicados entre grupos distintos"
DISCARDS = sorted(QUALITY_DROPPED + SPEECH_DROPPED + DUP_DROPPED, key=lambda r: (r["motivo"], r["clip"]))
buffer = io.StringIO()
writer = csv.DictWriter(buffer, fieldnames=["clip", "fuente", "motivo", "detalle"], lineterminator="\n")
writer.writeheader()
writer.writerows(DISCARDS)
DISCARDS_CSV = buffer.getvalue().encode("utf-8")
DISCARDS_SHA256 = hashlib.sha256(DISCARDS_CSV).hexdigest()
(BASE / "descartes.csv").write_bytes(DISCARDS_CSV)
y = info["dron"].to_numpy().astype(int)
groups = info["grupo"].tolist()
src = info["fuente"].tolist()
DRONE_SOURCES = sorted({s for s, label in zip(src, y) if label == 1})
step(f"Clips finales: {len(info)}; fuentes con dron: {DRONE_SOURCES}; descartes.csv SHA-256 {DISCARDS_SHA256}")
display(info.groupby(["fuente", "dron"]).agg(clips=("clip", "size"), grupos=("grupo", "nunique"),
                                             horas=("segundos", lambda s: round(s.sum() / 3600, 2))))
"""

AUGMENT6 = r"""# Aumento SOLO para entrenamiento (código probado: augment.plan_cross_mixes, channel_augment):
# - N_CROSS_MIXES mezclas CRUZADAS: dron de una fuente sobre fondo de OTRA, cada una con un canal
#   aleatorio encima (random_channel por semilla);
# - N_CHANNEL_AUG copias de clips de AMBAS clases con canal aleatorio (el canal deja de delatar
#   la clase). En cada pliegue solo entran las que vienen de clips de entrenamiento (fallo cerrado).
print(SYNTHETIC_NOTE)
print(CHANNEL_SYNTHETIC_NOTE)
positives = [i for i in range(len(y)) if y[i] == 1]
negatives = [i for i in range(len(y)) if y[i] == 0]
CROSS_PLAN = plan_cross_mixes(positives, negatives, src, info["segundos"].tolist(), n=N_CROSS_MIXES, seed=SEED)
CHAN_PLAN = plan_channel_augment(list(range(len(y))), src, n=N_CHANNEL_AUG, seed=SEED + 1, labels=y.tolist())
def _named(plan, keys):
    return [{**m, **{k: info["clip"][m[k]] for k in keys}} for m in plan]
_, CROSS_PLAN_SHA256 = canonical_json(_named(CROSS_PLAN, ("drone", "background")))
_, CHAN_PLAN_SHA256 = canonical_json(_named(CHAN_PLAN, ("clip",)))
AUG_SHARD = 100

def render_cross(m):
    mix = render_mix(m, load_signal(info["clip"][m["drone"]]), load_signal(info["clip"][m["background"]]), TARGET_SR)
    return apply_channel(mix, random_channel(SEED + int(m["id"][-5:])))

def render_channel(p):
    signal = load_signal(info["clip"][p["clip"]])
    length = min(len(signal), int(5.0 * TARGET_SR))
    start = int((len(signal) - length) * p["offset"])
    return apply_channel(signal[start:start + length], random_channel(p["seed"]))

def augmented_features(plan, render, tag):
    blocks, valid = [], []
    for a, b in shard_ranges(len(plan), AUG_SHARD):
        items = [(m["id"], canonical_json(_named([m], ("drone", "background") if "drone" in m else ("clip",)))[1]) for m in plan[a:b]]
        key = shard_key(items, FEAT_CONTEXT + "|" + tag)
        path = CHECKPOINTS / f"{tag}_{a:06d}_{key[:16]}.npz"
        loaded = load_shard(path, key)
        if loaded is None:
            part, ok = [], []
            for m in plan[a:b]:
                try:
                    x, _ = windows_of_signal(render(m), MAX_WINDOWS_AUG)
                    part.append(x)
                    ok.append(1)
                except (SilentMixError, ValueError):
                    part.append(np.zeros((0, 1032), np.float32))
                    ok.append(0)
            frames, offsets = pack_frames(part)
            loaded = ({"x": frames, "off": offsets, "ok": np.asarray(ok, np.int8)}, {})
            save_shard(path, key, *loaded)
        arrays, _ = loaded
        blocks += [unpack_frames(arrays["x"], arrays["off"], i) for i in range(len(arrays["off"]) - 1)]
        valid += arrays["ok"].astype(bool).tolist()
        step(f"  {tag}: {b}/{len(plan)}")
    frames, offsets = pack_frames(blocks)
    return frames, offsets, np.asarray(valid, dtype=bool)

CROSS_X, CROSS_OFF, CROSS_OK = augmented_features(CROSS_PLAN, render_cross, "cruzadas6")
CHAN_X, CHAN_OFF, CHAN_OK = augmented_features(CHAN_PLAN, render_channel, "canal6")
step(f"Aumento: {int(CROSS_OK.sum())}/{len(CROSS_PLAN)} mezclas cruzadas y {int(CHAN_OK.sum())}/{len(CHAN_PLAN)} copias de canal válidas")
"""

EVAL6 = r"""# Evaluación de la iteración 6. LOSO es la métrica PRINCIPAL (cada fuente entera es test nunca
# vista); StratifiedGroupKFold (5 folds) es secundaria y solo para la línea base y el principal.
# Por variante: regresión logística por VENTANA sobre rasgos (embedding normalizado [+ armónico]),
# puntuación de clip = persistencia 3 de 5 (equivale a la alerta del Mac), Platt en validación,
# umbral por PEOR FUENTE de validación (FPR <= MAX_FPR_ON en cada fuente). La línea base de la
# iteración 5 se reentrena con su receta exacta (media de embeddings sin normalizar, pesos por
# clase y fuente, umbral con recall >= 0,90). En cada partición: grupos disjuntos y ningún casi
# duplicado cruza particiones; aumento y mezclas solo desde clips de entrenamiento.
from sklearn.linear_model import LogisticRegression
assert TRAINING_ALLOWED, "Entrenamiento bloqueado"
CAPTION = metric_caption(provisional=PILOT["group_status"] != "verified")
EMB = slice(0, 1024)
VARIANTS6 = {
    "iter6 · normalización": {"harm": False, "aug": False, "inlp": 0, "dro": False},
    "iter6 · + canal + cruzadas": {"harm": False, "aug": True, "inlp": 0, "dro": False},
    "iter6 · + armónico": {"harm": True, "aug": True, "inlp": 0, "dro": False},
    "iter6 · + INLP": {"harm": True, "aug": True, "inlp": INLP_ROUNDS, "dro": False},
    MAIN_VARIANT: {"harm": True, "aug": True, "inlp": INLP_ROUNDS, "dro": True},
}
VARIANTS = (BASELINE_VARIANT, *VARIANTS6)
SGKF_VARIANTS = (BASELINE_VARIANT, MAIN_VARIANT)

def cols(x, spec):
    return x if spec["harm"] else x[:, EMB]

def clip_windows(i, use_speech_gate=True):
    w = unpack_frames(X6, OFF6, i)
    if use_speech_gate:
        mask = ~WINDOW_SPEECH[OFF6[i]:OFF6[i + 1]]
        if mask.any():
            return w[mask]
    return w

def training_windows(train, held_out, spec, centers=None):
    xs, ys, doms = [], [], []
    for i in train:
        w = clip_windows(i)
        if len(w) > MAX_FRAMES_TRAIN:
            w = w[np.unique(np.linspace(0, len(w) - 1, MAX_FRAMES_TRAIN).round().astype(int))]
        xs.append(w); ys += [int(y[i])] * len(w); doms += [src[i]] * len(w)
    n_aug = 0
    if spec["aug"]:
        cross = [k for k in cross_mixes_for_fold(CROSS_PLAN, train, held_out=held_out) if CROSS_OK[k]]
        chan = [k for k in channel_augs_for_training(CHAN_PLAN, train) if CHAN_OK[k]]
        assert_channel_augs_training_only(CHAN_PLAN, chan, train)
        for k in cross:
            w = unpack_frames(CROSS_X, CROSS_OFF, k)
            xs.append(w); ys += [1] * len(w); doms += ["cruzada:" + CROSS_PLAN[k]["background_source"]] * len(w)
        for k in chan:
            w = unpack_frames(CHAN_X, CHAN_OFF, k)
            xs.append(w); ys += [int(y[CHAN_PLAN[k]["clip"]])] * len(w); doms += ["canal:" + src[CHAN_PLAN[k]["clip"]]] * len(w)
        n_aug = len(cross) + len(chan)
    x = np.vstack(xs).astype(np.float64)
    if centers is not None:
        x = x - np.vstack([centers[d.split(":")[-1]] for d in doms])
    return cols(x, spec), np.asarray(ys), doms, n_aug

def fit_variant(train, held_out, spec, centers=None):
    x, labels, doms, n_aug = training_windows(train, held_out, spec, centers)
    if spec["dro"]:
        model, _ = group_dro_fit(x, labels, [f"{d}|{v}" for d, v in zip(doms, labels)], seed=SEED, rounds=DRO_ROUNDS,
                                 eta=DRO_ETA, c=LR_C, domains=doms, inlp_rounds=spec["inlp"])
    else:
        model = fit_linear(x, labels, class_source_weights(labels, doms), seed=SEED, c=LR_C, domains=doms,
                           inlp_rounds=spec["inlp"])
    return model, n_aug

def clip_scores(model, indices, spec, centers=None):
    out = []
    for i in indices:
        w = clip_windows(i).astype(np.float64)
        if centers is not None:
            w = w - centers[src[i]]
        out.append(persistence_score(linear_proba(model, cols(w, spec)), 3, 5))
    return np.asarray(out)

def baseline_scores(train, parts):
    train = list(train)
    w = class_source_weights(y[train], [src[i] for i in train])
    model = LogisticRegression(max_iter=3000, random_state=SEED).fit(MEANS5[train], y[train], sample_weight=w)
    return [model.predict_proba(MEANS5[list(p)])[:, 1] for p in parts]

PRED_ROWS, RULES, AUG_COUNT = [], {}, {}

def record(variant, scheme, partition, validation, test, pv, pt):
    yv = y[list(validation)]
    platt, iso = fit_calibrator(yv, pv, "platt"), fit_calibrator(yv, pv, "isotonica")
    if platt["a"] <= 0:  # validación degenerada: Platt decreciente no se usa (se informa)
        platt = {"method": "platt", "a": 1.0, "b": 0.0, "nota": "Platt no creciente en validación; identidad"}
    cv_ = apply_calibration(platt, pv)
    if variant == BASELINE_VARIANT:
        rule = choose_threshold_for_recall(yv, cv_, target_recall=TARGET_RECALL)
        thr, detail = rule["threshold"], {"regla": "recall >= 0,90 (iteración 5)"}
    else:
        h = hysteresis_thresholds(yv, cv_, [src[i] for i in validation], max_fpr_on=MAX_FPR_ON, max_fpr_off=MAX_FPR_OFF)
        thr, detail = h["theta_on"], {"regla": "peor fuente", "theta_off": h["theta_off"],
                                      "fuente_limitante": h["detalle_on"]["fuente_limitante"]}
    RULES[(variant, scheme, partition)] = {"platt": platt, "umbral": float(thr), **detail}
    for i, a, b, c in zip(test, apply_calibration(platt, pt), pt, apply_calibration(iso, pt)):
        PRED_ROWS.append({"modelo": variant, "esquema": scheme, "particion": partition, "fuente": src[i],
                          "clip": info["clip"][i], "grupo": groups[i], "tipo": info["tipo"][i], "dron": int(y[i]),
                          "puntuacion": float(a), "puntuacion_cruda": float(b), "puntuacion_isotonica": float(c),
                          "umbral": float(thr)})

def check_partition(train, validation, test):
    assign = np.full(len(y), "fuera", dtype=object)
    for name, part in (("train", train), ("val", validation), ("test", test)):
        assign[list(part)] = name
    seen = [{groups[i] for i in part} for part in (train, validation, test)]
    assert not (seen[0] & seen[1] or seen[0] & seen[2] or seen[1] & seen[2]), "un grupo cruza particiones"
    used = np.flatnonzero(assign != "fuera")
    crossing = near_duplicate_pairs(MEANS5[used], threshold=NEAR_DUPLICATE_COSINE, groups=assign[used].tolist())
    assert_no_cross_partition_pairs(crossing, assign[used].tolist())

def evaluate(scheme, partition, train, validation, test, held_out, variants):
    check_partition(train, validation, test)
    for variant in variants:
        if variant == BASELINE_VARIANT:
            pv, pt = baseline_scores(train, [validation, test])
        else:
            spec = VARIANTS6[variant]
            model, AUG_COUNT[(variant, scheme, partition)] = fit_variant(train, held_out, spec)
            pv, pt = clip_scores(model, validation, spec), clip_scores(model, test, spec)
        record(variant, scheme, partition, validation, test, pv, pt)
    step(f"  {scheme} {partition}: train/val/test = {len(train)}/{len(validation)}/{len(test)} clips")

LOSO = leave_one_source_out(y.tolist(), groups, src, seed=SEED)
for split in LOSO:
    evaluate("loso", "sin_" + split["fuente"], split["train"], split["validation"], split["test"], split["fuente"], VARIANTS)
folds = stratified_group_folds(y.tolist(), groups, k=N_FOLDS, seed=SEED)
for f, (tr, va, te) in enumerate(rotating_folds(folds, N_FOLDS)):
    evaluate("sgkf5", f"fold{f}", tr, va, te, None, SGKF_VARIANTS)
"""

SITE6 = r"""# Variante de SITIO (D-7), SIEMPRE aparte y fuera de C-LOSO: para cada fuente retenida con
# negativos se apartan CAL_GROUPS grupos negativos como «calibración del sitio» (fuera del test);
# los rasgos se centran por fuente con la media de sus negativos (entrenamiento: negativos de
# entrenamiento de cada fuente; fuente retenida: solo los de calibración). Esquema «loso_cal».
spec = VARIANTS6[MAIN_VARIANT]
for split in LOSO:
    held = split["fuente"]
    held_neg_groups = sorted({groups[i] for i in split["test"] if y[i] == 0})
    if len(held_neg_groups) <= CAL_GROUPS:
        print(f"  loso_cal sin_{held}: {len(held_neg_groups)} grupos negativos; no hay bastantes para calibrar")
        continue
    rng = np.random.default_rng(SEED)
    cal_groups = set(rng.choice(held_neg_groups, size=CAL_GROUPS, replace=False).tolist())
    cal = [i for i in split["test"] if groups[i] in cal_groups]
    test = [i for i in split["test"] if groups[i] not in cal_groups]
    rows_neg = [(src[i], clip_windows(i)) for i in list(split["train"]) + cal if y[i] == 0]
    centers = {}
    for s in sorted({s for s, _ in rows_neg}):
        centers[s] = np.vstack([w for t, w in rows_neg if t == s]).astype(np.float64).mean(axis=0)
    for s in set(src) - set(centers):  # fuente sin negativos de entrenamiento (solo dron): sin centrar
        centers[s] = np.zeros(X6.shape[1])
    model, _ = fit_variant(split["train"], held, spec, centers)
    pv = clip_scores(model, split["validation"], spec, centers)
    pt = clip_scores(model, test, spec, centers)
    record(MAIN_VARIANT, "loso_cal", "sin_" + held, split["validation"], test, pv, pt)
    step(f"  loso_cal sin_{held}: {len(cal)} clips de calibración apartados del test")
pred = pd.DataFrame(PRED_ROWS)
assert pred.groupby(["modelo", "esquema"])["clip"].apply(lambda c: c.is_unique).all()
step(f"Predicciones fuera de fold: {len(pred)} filas {CAPTION}")
"""

SUMMARY6 = r"""# Resumen LOSO (principal) con IC 95 % por grupos, criterio C-LOSO (ADR 0018) y D-6 de referencia.
# ROC-AUC (independiente de la prevalencia) con IC por remuestreo de grupos completos.
from sklearn.metrics import average_precision_score

def interval(boot, name):
    if boot["status"] != "OK":
        return f"NO DISPONIBLE ({boot['n_groups']} grupos)"
    iv = boot["intervals"][name]
    return "—" if iv is None else f"[{iv[0]:.3f}, {iv[1]:.3f}]"

def auc_interval(sub, n_boot=300):
    yy, pp, gg = sub["dron"].to_numpy(), sub["puntuacion"].to_numpy(), sub["grupo"].to_numpy()
    unique = np.unique(gg)
    if len(unique) < 10 or len(set(yy.tolist())) < 2:
        return "NO DISPONIBLE"
    members = {g: np.flatnonzero(gg == g) for g in unique}
    rng = np.random.default_rng(SEED)
    vals = []
    for _ in range(n_boot):
        idx = np.concatenate([members[unique[k]] for k in rng.choice(len(unique), len(unique))])
        v = safe_roc_auc(yy[idx], pp[idx])
        if v is not None:
            vals.append(v)
    return f"[{np.percentile(vals, 2.5):.3f}, {np.percentile(vals, 97.5):.3f}]" if len(vals) >= n_boot // 2 else "NO DISPONIBLE"

def summarize(sub):
    yy = sub["dron"].to_numpy()
    alarm = (sub["puntuacion"] >= sub["umbral"]).to_numpy().astype(float)
    m = binary_metrics(yy, alarm, 0.5)
    boot = group_bootstrap(yy, alarm, sub["grupo"].tolist(), 0.5, n_boot=500, seed=SEED)
    both = len(set(yy.tolist())) == 2
    r = lambda v: None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), 3)
    return {"n": len(sub), "positivos": int(yy.sum()), "recall": r(m["recall"]), "IC95_recall": interval(boot, "recall"),
            "fpr": r(m["fpr"]), "IC95_fpr": interval(boot, "fpr"),
            "roc_auc": r(safe_roc_auc(yy, sub["puntuacion"])) if both else None, "IC95_roc_auc": auc_interval(sub) if both else "—",
            "pr_auc": r(average_precision_score(yy, sub["puntuacion"])) if both else None,
            "ece_platt": r(expected_calibration_error(yy, sub["puntuacion"]))}

loso_pred = pred[pred["esquema"] == "loso"]
LOSO_SUMMARY = pd.DataFrame([{"modelo": v, "fuente_no_vista": p.replace("sin_", ""), **summarize(g)}
                             for (v, p), g in loso_pred.groupby(["modelo", "particion"])])
print("Leave-one-source-out (MÉTRICA PRINCIPAL; fuente nunca vista)", CAPTION)
display(LOSO_SUMMARY)

def c_loso(model):
    out = []
    for s, g in loso_pred[loso_pred["modelo"] == model].groupby("fuente"):
        yy = g["dron"].to_numpy()
        alarm = (g["puntuacion"] >= g["umbral"]).to_numpy()
        training_drone = [d for d in DRONE_SOURCES if d != s]
        e = {"fuente_retenida": s, "fuentes_dron_entrenando": training_drone, "positivos": int(yy.sum()),
             "roc_auc": safe_roc_auc(yy, g["puntuacion"]), "recall": float(alarm[yy == 1].mean()) if yy.any() else None,
             "fpr": float(alarm[yy == 0].mean()) if (yy == 0).any() else None}
        checks = []
        if e["positivos"]:
            if len(training_drone) < 2:
                e["estado"] = "NO EVALUABLE"
            else:
                checks.append(e["recall"] >= 0.50)
                if e["fpr"] is not None:  # ROC-AUC solo si la fuente tiene también negativos
                    checks.append(e["roc_auc"] is not None and e["roc_auc"] >= 0.85)
        if e["fpr"] is not None:
            checks.append(e["fpr"] <= 0.10)
        e.setdefault("estado", "CUMPLE" if all(checks) else "NO CUMPLE")
        out.append(e)
    states = {e["estado"] for e in out}
    overall = "CUMPLE" if states == {"CUMPLE"} else ("NO EVALUABLE" if "NO EVALUABLE" in states and "NO CUMPLE" not in states else "NO CUMPLE")
    return overall, out

CRITERIA = {}
for v in (MAIN_VARIANT, BASELINE_VARIANT):
    overall, table = c_loso(v)
    by = {e["fuente_retenida"]: e for e in table}
    sub = loso_pred[loso_pred["modelo"] == v]
    aris, fsd = sub[sub["fuente"] == "aris"], sub[sub["fuente"] == "fsd50k"]
    d6 = {"pr_auc_aris": float(average_precision_score(aris["dron"], aris["puntuacion"])),
          "recall_aris": float((aris.loc[aris["dron"] == 1, "puntuacion"] >= aris.loc[aris["dron"] == 1, "umbral"]).mean()),
          "fpr_fsd50k": float((fsd["puntuacion"] >= fsd["umbral"]).mean())}
    d6["cumple"] = d6["pr_auc_aris"] >= 0.85 and d6["recall_aris"] >= 0.50 and d6["fpr_fsd50k"] <= 0.10
    CRITERIA[v] = {"c_loso": overall, "por_fuente": table, "d6_referencia": d6}
    print(f"\n{v}\n  C-LOSO (ADR 0018, propuesto): {overall}")
    display(pd.DataFrame(table))
    print(f"  D-6 (referencia; depende de la prevalencia de ARIS): PR-AUC ARIS {d6['pr_auc_aris']:.3f}, "
          f"recall ARIS {d6['recall_aris']:.3f}, FPR FSD50K {d6['fpr_fsd50k']:.3f} -> {'cumple' if d6['cumple'] else 'NO cumple'}")
GENERALIZES = CRITERIA[MAIN_VARIANT]["c_loso"] == "CUMPLE"
if not GENERALIZES:
    print("\nAVISO: el modelo principal NO cumple C-LOSO: la demo debe rotularse «modelo que no generaliza» y se itera.")
cal_pred = pred[pred["esquema"] == "loso_cal"]
if len(cal_pred):
    print("\nVariante de sitio (D-7; aparte, NO cuenta para C-LOSO):")
    display(pd.DataFrame([{"fuente_no_vista": p.replace("sin_", ""), **summarize(g)} for p, g in cal_pred.groupby("particion")]))
cv_pred = pred[pred["esquema"] == "sgkf5"]
print("\nStratifiedGroupKFold (secundaria, fuentes vistas):")
display(pd.DataFrame([{"modelo": v, **summarize(cv_pred[cv_pred["modelo"] == v])} for v in SGKF_VARIANTS]))
print("Línea base exacta de la iteración 5 (otra ejecución): predicciones.csv SHA-256 "
      "8ec5d2281682dd02cb11c3a0d9a74feb59df508325afdaa99a715d39a7c67407; aquí se reentrena con su receta.")
"""

FINAL6 = r"""# Modelo FINAL (el que se exporta): receta del principal con TODAS las fuentes. Partición por grupos:
# fold 0 = TEST final (nunca visto: autocomprobación de «Prueba tu audio»), fold 1 = validación
# (Platt y umbrales por peor fuente con histéresis), resto = entrenamiento.
spec = VARIANTS6[MAIN_VARIANT]
FINAL_FOLDS = stratified_group_folds(y.tolist(), groups, k=N_FOLDS, seed=SEED + 7)
FINAL_TEST = [i for i in range(len(y)) if FINAL_FOLDS[i] == 0]
FINAL_VAL = [i for i in range(len(y)) if FINAL_FOLDS[i] == 1]
FINAL_TRAIN = [i for i in range(len(y)) if FINAL_FOLDS[i] >= 2]
check_partition(FINAL_TRAIN, FINAL_VAL, FINAL_TEST)
FINAL_MODEL, _ = fit_variant(FINAL_TRAIN, None, spec)
FINAL_MODEL = {**FINAL_MODEL, "nombre": MAIN_VARIANT}
pv = clip_scores(FINAL_MODEL, FINAL_VAL, spec)
FINAL_PLATT = fit_calibrator(y[FINAL_VAL], pv, "platt")
assert FINAL_PLATT["a"] > 0, "Platt no creciente: no se exporta un modelo con calibración invertida"
FINAL_TH = hysteresis_thresholds(y[FINAL_VAL], apply_calibration(FINAL_PLATT, pv), [src[i] for i in FINAL_VAL],
                                 max_fpr_on=MAX_FPR_ON, max_fpr_off=MAX_FPR_OFF)
FINAL_ALERT = {"theta_on": FINAL_TH["theta_on"], "theta_off": FINAL_TH["theta_off"], **ALERT_DEFAULTS}
pt = apply_calibration(FINAL_PLATT, clip_scores(FINAL_MODEL, FINAL_TEST, spec))
yt = y[FINAL_TEST]
FINAL_TEST_METRICS = {"roc_auc": safe_roc_auc(yt, pt), "recall": float((pt[yt == 1] >= FINAL_ALERT["theta_on"]).mean()),
                      "fpr": float((pt[yt == 0] >= FINAL_ALERT["theta_on"]).mean()), "n": len(yt)}
step(f"Modelo final: {FINAL_MODEL['inlp_direcciones']} direcciones INLP; theta_on {FINAL_ALERT['theta_on']:.4f}, "
     f"theta_off {FINAL_ALERT['theta_off']:.4f}; test final (fuentes vistas) {FINAL_TEST_METRICS}")
"""

ONNX6 = r"""# YAMNet -> ONNX con tf2onnx (opset fijo) y PARIDAD frente a TensorFlow en >= 50 ventanas reales
# normalizadas (y las entradas doradas). Si la conversión falla o la diferencia supera PARITY_TOL,
# NO se exporta yamnet.onnx ni modelo_hito2.json (fallo cerrado) y «Prueba tu audio» usa TensorFlow.
YAMNET_ONNX = BASE / "yamnet.onnx"
ONNX_INFO = {"origen": MODEL_URL, "opset": ONNX_OPSET, "entrada": "waveform float32 [n] a 16 kHz (ventana de 15 600 muestras)",
             "salidas": ["scores (n, 521)", "embeddings (n, 1024)"], "paridad_tol": PARITY_TOL}
PARITY_OK, yamnet_onnx = False, None
try:
    import onnxruntime as ort
    import tf2onnx
    sig = (tf.TensorSpec([None], tf.float32, name="waveform"),)
    @tf.function(input_signature=sig)
    def yamnet_serving(waveform):
        scores, embeddings, _ = yamnet(waveform)
        return {"scores": scores, "embeddings": embeddings}
    tf2onnx.convert.from_function(yamnet_serving, input_signature=sig, opset=ONNX_OPSET, output_path=str(YAMNET_ONNX))
    session = ort.InferenceSession(str(YAMNET_ONNX), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    def yamnet_onnx(window):
        outs = session.run(None, {input_name: np.asarray(window, dtype=np.float32)})
        by_dim = {o.shape[-1]: o for o in outs if o.ndim == 2}
        return by_dim[521], by_dim[1024]
    rng = np.random.default_rng(SEED)
    probe = rng.choice(len(info), size=min(PARITY_WINDOWS, len(info)), replace=False)
    windows = [normalize_window(extract_window(load_signal(info["clip"][i]), 0)) for i in probe]
    windows += [normalize_window(to_mono_16k(golden_input(s, k), GOLDEN_SR)) for s, k in zip((101, 202, 303), GOLDEN_KINDS)]
    diffs_e, diffs_s = [], []
    for w in windows:
        s_tf, e_tf = yamnet_tf(w)
        s_ox, e_ox = yamnet_onnx(w)
        diffs_e.append(float(np.max(np.abs(e_tf - e_ox))))
        diffs_s.append(float(np.max(np.abs(s_tf - s_ox))))
    ONNX_INFO.update({"onnx_sha256": hashlib.sha256(YAMNET_ONNX.read_bytes()).hexdigest(), "bytes": YAMNET_ONNX.stat().st_size,
                      "paridad_ventanas": len(windows), "paridad_max_embedding": max(diffs_e), "paridad_max_scores": max(diffs_s),
                      "versiones": dependency_versions(["tensorflow", "tf2onnx", "onnx", "onnxruntime"])})
    PARITY_OK = max(diffs_e) <= PARITY_TOL and max(diffs_s) <= PARITY_TOL
    step(f"ONNX: {ONNX_INFO['bytes'] / 1e6:.1f} MB; paridad máx. embedding {max(diffs_e):.2e}, voz/clases {max(diffs_s):.2e} "
         f"en {len(windows)} ventanas -> {'OK' if PARITY_OK else 'FALLA'}")
except Exception as exc:  # conversión no disponible: se informa y no se exporta
    ONNX_INFO["error"] = f"{type(exc).__name__}: {exc}"[:300]
    print("ONNX NO disponible:", ONNX_INFO["error"])
ONNX_INFO["paridad_ok"] = bool(PARITY_OK)
if not PARITY_OK:
    print("FALLO CERRADO: sin paridad ONNX <= 1e-4 no se exporta el artefacto para el Mac.")
    YAMNET_ONNX.unlink(missing_ok=True)
"""

EXPORT6 = r"""# Exportación: predicciones.csv (código probado: predictions), registro_iter6.json (experiment) y,
# SOLO con paridad ONNX, modelo_hito2.json (model_export: pesos, Platt, alerta, normalización,
# índices de voz, vectores dorados calculados con la sesión ONNX que usará el Mac) y SHA256SUMS.
csv_bytes, csv_sha256 = predictions_csv(PRED_ROWS, columns=EXTENDED_COLUMNS)
(BASE / "predicciones.csv").write_bytes(csv_bytes)
DEPENDENCIES = dependency_versions(["tensorflow", "tensorflow-hub", "tf-keras", "tf2onnx", "onnx", "onnxruntime", "librosa",
                                    "soundfile", "scikit-learn", "scipy", "numpy", "pandas", "matplotlib"])
EXPERIMENT = experiment_record(
    config={"iteracion": 6, "semilla": SEED, "n_folds": N_FOLDS, "modelo_principal": MAIN_VARIANT, "variantes": list(VARIANTS),
            "max_ventanas_clip": MAX_WINDOWS_CLIP, "max_ventanas_aumento": MAX_WINDOWS_AUG, "max_ventanas_entreno": MAX_FRAMES_TRAIN,
            "n_cruzadas": N_CROSS_MIXES, "n_canal": N_CHANNEL_AUG, "max_fpr_on": MAX_FPR_ON, "max_fpr_off": MAX_FPR_OFF,
            "inlp_rondas": INLP_ROUNDS, "dro_rondas": DRO_ROUNDS, "dro_eta": DRO_ETA, "lr_c": LR_C, "cal_grupos": CAL_GROUPS,
            "normalizacion_sha256": norm_config_sha256(), "armonico": HARMONIC_CONFIG, "voz_umbral": SPEECH_EXCLUSION_THRESHOLD,
            "fuentes_extra": EXTRA_ENABLED, "autorizaciones_extra": EXTRA_AUTHORIZATION},
    data={"inventario_sha256": DATA_INVENTORY_SHA256, "inventario_extra": sorted(EXTRA_INVENTORY), "descartes_csv_sha256": DISCARDS_SHA256,
          "plan_cruzadas_sha256": CROSS_PLAN_SHA256, "plan_canal_sha256": CHAN_PLAN_SHA256, "clips_evaluados": len(info),
          "fuentes_dron": DRONE_SOURCES, "group_status_svanstrom": PILOT["group_status"]},
    dependencies=DEPENDENCIES, predictions_sha256=csv_sha256, notebook_code_sha256=NOTEBOOK_CODE_SHA256,
    extra={"modelo_principal": MAIN_VARIANT, "criterios": CRITERIA, "generaliza": GENERALIZES,
           "reglas": {"|".join(k): v for k, v in RULES.items()}, "onnx": ONNX_INFO, "test_final": FINAL_TEST_METRICS,
           "puerta_voz": {"umbral": SPEECH_GATE["threshold"], "nota": SPEECH_GATE["note"]},
           "excluidos_por_voz": SPEECH_GATE["excluded"], "revisiones_humanas": SPEECH_GATE["human_cleared"],
           "nota_sintetico": [SYNTHETIC_NOTE, CHANNEL_SYNTHETIC_NOTE], "filas_predicciones": len(PRED_ROWS),
           "linea_base_iter5_csv_sha256": "8ec5d2281682dd02cb11c3a0d9a74feb59df508325afdaa99a715d39a7c67407"})
assert verify_record(EXPERIMENT)
(BASE / "registro_iter6.json").write_text(json.dumps(EXPERIMENT, ensure_ascii=False, indent=1))
summary_criteria = {"c_loso": CRITERIA[MAIN_VARIANT]["c_loso"], "d6_referencia": CRITERIA[MAIN_VARIANT]["d6_referencia"],
                    "generaliza": GENERALIZES, "rotulo_demo": "" if GENERALIZES else "modelo que no generaliza"}
ARTIFACT = build_artifact(model=FINAL_MODEL, platt=FINAL_PLATT, alert=FINAL_ALERT, yamnet_info=ONNX_INFO,
                          speech_indices=speech_columns, speech_names=SPEECH_NAMES, speech_threshold=SPEECH_EXCLUSION_THRESHOLD,
                          criteria=summary_criteria, predictions_sha256=csv_sha256, record_sha256=EXPERIMENT["registro_sha256"],
                          yamnet_fn=yamnet_onnx if PARITY_OK else yamnet_tf)
EXPORTS = ["predicciones.csv", "registro_iter6.json", "descartes.csv"]
if PARITY_OK:
    data = json.dumps(ARTIFACT, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8")
    assert len(data) <= 200_000, f"modelo_hito2.json demasiado grande: {len(data)} bytes"
    (BASE / "modelo_hito2.json").write_bytes(data)
    assert check_golden(json.loads(data), yamnet_onnx) <= GOLDEN_TOLERANCE
    EXPORTS = ["modelo_hito2.json", "yamnet.onnx", *EXPORTS]
sums = "".join(f"{hashlib.sha256((BASE / n).read_bytes()).hexdigest()}  {n}\n" for n in EXPORTS)
(BASE / "SHA256SUMS").write_text(sums)
print(sums)
print("Recalcular en el repo: uv run python recompute_metrics.py predicciones.csv --sha256", csv_sha256,
      "--record registro_iter6.json" + (" --artifact modelo_hito2.json" if PARITY_OK else ""), "--criterio c-loso")
try:
    from google.colab import files  # descarga al navegador del usuario; no monta Drive
    for name in [*EXPORTS, "SHA256SUMS"]:
        files.download(str(BASE / name))
except ImportError:
    pass
"""

USER_MD6 = """## Prueba tu audio

Sube un fichero de audio (wav, mp3, m4a, ogg o flac) y el cuaderno te dice si detecta un dron,
usando **exactamente** la ruta del modelo exportado: remuestreo a 16 kHz → ventanas de 0,96 s con
salto de 0,48 s → normalización de canal → YAMNet (ONNX si la paridad pasó) → **puerta de voz**
(ventanas con voz ≥ 0,30 se descartan y se cuentan) → rasgo armónico → clasificador calibrado →
**alerta 3 de 5 con histéresis**.

**Usa solo audio propio o con una licencia que lo permita. No descargues audio de YouTube ni de
otras plataformas.** El fichero se analiza en esta sesión y se **borra** al terminar; no se guarda
en Drive ni en el repositorio. Resultado de una prueba técnica: **no** es un vuelo real verificado.
"""

SELFCHECK6 = r"""# Autocomprobación de punta a punta: un clip de DRON y uno de FONDO del TEST final (nunca vistos al
# entrenar ni al calibrar) pasan por analyze_audio (la función de «Prueba tu audio») y su veredicto
# debe coincidir con la decisión de la ruta por lotes del modelo final. Se eligen clips con >= 5
# ventanas y <= MAX_WINDOWS_CLIP (misma regla 3 de 5 en ambas rutas).
USER_YAMNET = yamnet_onnx if PARITY_OK else yamnet_tf
def batch_decision(i):
    p = apply_calibration(FINAL_PLATT, np.array([persistence_score(linear_proba(FINAL_MODEL, clip_windows(i, use_speech_gate=False).astype(np.float64)), 3, 5)]))[0]
    return p >= FINAL_ALERT["theta_on"], p
eligible = [i for i in FINAL_TEST if 5 <= info["ventanas"][i] <= MAX_WINDOWS_CLIP
            and not WINDOW_SPEECH[OFF6[i]:OFF6[i + 1]].any()]
chosen = {}
for want in (1, 0):
    cands = [i for i in eligible if y[i] == want and batch_decision(i)[0] == bool(want)]
    if cands:
        chosen[want] = cands[0]
SELF_CHECK = []
for want, i in sorted(chosen.items(), reverse=True):
    signal = load_signal(info["clip"][i])
    report = analyze_audio(signal, TARGET_SR, artifact=ARTIFACT, yamnet_fn=USER_YAMNET)
    expected = VERDICT_YES if want else VERDICT_NO
    SELF_CHECK.append({"clip": info["clip"][i], "esperado": expected, "obtenido": report["veredicto"],
                       "prob_lotes": round(float(batch_decision(i)[1]), 4), "persistencia_ruta_usuario": report["persistencia"]})
    assert report["veredicto"] == expected, SELF_CHECK[-1]
display(pd.DataFrame(SELF_CHECK))
if len(chosen) < 2:
    print("AVISO: no hubo en el test final un clip de dron detectado y uno de fondo rechazado con >= 5 ventanas;",
          "la autocomprobación es parcial:", sorted(chosen))
else:
    step("Autocomprobación OK: la ruta de «Prueba tu audio» reproduce la decisión del modelo final")
"""

UPLOAD6 = r"""# Prueba tu audio: sube uno o varios ficheros. Se analizan en memoria (los no WAV se escriben un
# instante en /content/prueba_audio para que ffmpeg/soundfile los decodifiquen) y se BORRAN después.
print(USER_AUDIO_NOTE)
def show_report(name, signal, sr, report):
    print(f"\n=== {name}: {report['veredicto']} ===  ({report['rotulo']})")
    if report["prob_max"] is not None:
        print(f"Probabilidad máx. {report['prob_max']:.3f} · media {report['prob_media']:.3f} · "
              f"{100 * report['fraccion_sobre_umbral']:.0f} % de ventanas sobre el umbral ({report['theta_on']:.3f}) · "
              f"{report['alertas']} alerta(s)")
    print(f"{report['ventanas']} ventanas; {report['ventanas_voz_descartadas']} descartadas por voz")
    for w in report["avisos"]:
        print("AVISO:", w)
    mono = to_16k_any(signal, sr)
    fig, (a, b) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    a.specgram(mono, NFFT=512, Fs=16000, noverlap=352, cmap="magma")
    a.set(ylabel="Hz", title=f"{name} · espectrograma (16 kHz)")
    t = np.array(report["tiempos_s"]) + 0.48
    probs = [np.nan if p is None else p for p in report["prob_por_ventana"]]
    b.plot(t, probs, "o-", label="probabilidad calibrada por ventana")
    b.axhline(report["theta_on"], color="red", ls="--", label="umbral de alerta")
    b.axhline(report["theta_off"], color="orange", ls=":", label="fin de alerta (histéresis)")
    b.set(ylim=(0, 1), xlabel="Tiempo (s)", ylabel="Probabilidad")
    b.legend(fontsize=8)
    plt.tight_layout(); plt.show()

try:
    from google.colab import files
    uploaded = files.upload()
except ImportError:
    uploaded = {}
    print("Fuera de Colab: no hay subida de ficheros.")
work = Path("/content/prueba_audio")
for name, data in uploaded.items():
    path = work / Path(name).name
    try:
        if path.suffix.lower() == ".wav":
            try:
                signal, sr = decode_wav_bytes(data)
            except AudioDecodeError:
                signal = None
        else:
            signal = None
        if signal is None:
            work.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            signal, sr = load_user_audio(path, fallback_loader=load_audio)
        report = analyze_audio(signal, sr, artifact=ARTIFACT, yamnet_fn=USER_YAMNET)
        show_report(name, signal, sr, report)
    except (AudioDecodeError, ValueError) as exc:
        print(f"\n=== {name}: no se pudo analizar ({exc}) ===")
    finally:
        path.unlink(missing_ok=True)  # borrado explícito: nada queda en /content
        signal = data = None
uploaded = None
print("Ficheros subidos borrados de la sesión.")
"""

CLOSING6 = r"""# Ninguna fuente prohibida aparece en las descargadas.
DADS_ENABLED = False
assert not DADS_ENABLED
assert set(catalog["fuente"]) <= {"svanstrom", "esc10", "fsd50k", "aris", *EXTRA_ENABLED}
assert not set(EXTRA_ENABLED) - {"salford", "droneaudioset", "yi_kaist"}
print("DADS y demás fuentes prohibidas bloqueadas:", ", ".join(PROHIBITED))
step("Fin del cuaderno de la iteración 6")
"""

READING6 = """**Lectura de resultados:** describen solo estos clips, fuentes y repartos. ITU ARIS es una sola
sesión; FSD50K y ESC-10 son clips cortos de Freesound. Las mezclas y copias con canal aleatorio son
sintéticas (`synthetic=true`) y nunca se puntúan. No se ha medido vuelo real, distancia, falsas
alarmas por hora en un emplazamiento ni el micrófono del Mac (eso es el protocolo en sala del
hito 2, H2.14). Si C-LOSO no se cumple, la demo se rotula «modelo que no generaliza».
"""


def iter6_cells(
    config_json: str,
    extra_authorization: dict,
    embedded: dict[str, str],
    iter5_cell: callable,
    md: callable,
    code: callable,
) -> list[dict]:
    """Lista de celdas; ``iter5_cell(prefijo)`` devuelve una celda de la iteración 5 tal cual."""
    return [
        md(INTRO6),
        code(DEPS6),
        code(setup6(config_json, extra_authorization)),
        *[code(text) for text in embedded.values()],
        iter5_cell("# Svanström: licencia original"),
        iter5_cell("# Svanström: selección reproducible"),
        iter5_cell("# ESC-10 (CC BY 3.0)"),
        iter5_cell("# FSD50K (Zenodo 4060432)"),
        iter5_cell("# ITU ARIS Lab"),
        code(EXTRA6),
        iter5_cell("## Revisión de privacidad"),
        iter5_cell("# Reproducción de un clip por fuente"),
        code(FEATURES6),
        code(GATE6),
        code(TRAINING_GATE6),
        code(DEDUP6),
        code(AUGMENT6),
        code(EVAL6),
        code(SITE6),
        code(SUMMARY6),
        code(FINAL6),
        code(ONNX6),
        code(EXPORT6),
        md(USER_MD6),
        code(SELFCHECK6),
        code(UPLOAD6),
        code(CLOSING6),
        md(READING6),
    ]

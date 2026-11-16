# Filtros de licencia por clip, selección reproducible y agrupación por fuente/sesión.
# Autocontenido (solo stdlib): build_colab.py lo incrusta tal cual en el cuaderno de Colab, y
# build_sources.py lo usa para fijar los manifiestos; el código probado es el que se ejecuta.
import csv
import hashlib
import io
import re
from collections.abc import Iterable, Mapping, Sequence

# Licencias por clip admitidas (URL exacta de Freesound/FSD50K). Todo lo demás se rechaza:
# CC BY-NC (no comercial), CC Sampling+ (dudosa) y cualquier valor desconocido.
ALLOWED_CLIP_LICENSES = {
    "http://creativecommons.org/publicdomain/zero/1.0/": "CC0-1.0",
    "http://creativecommons.org/licenses/by/3.0/": "CC-BY-3.0",
    "http://creativecommons.org/licenses/by/4.0/": "CC-BY-4.0",
}

# Etiquetas FSD50K de sonidos humanos (voz, cuerpo, grupos) y música: siempre se excluyen.
HUMAN_OR_MUSIC_LABELS = frozenset(
    {
        "Applause",
        "Breathing",
        "Burping_and_eructation",
        "Chatter",
        "Cheering",
        "Chewing_and_mastication",
        "Child_speech_and_kid_speaking",
        "Chuckle_and_chortle",
        "Clapping",
        "Conversation",
        "Cough",
        "Crowd",
        "Crying_and_sobbing",
        "Fart",
        "Female_singing",
        "Female_speech_and_woman_speaking",
        "Finger_snapping",
        "Gasp",
        "Giggle",
        "Hands",
        "Human_group_actions",
        "Human_voice",
        "Laughter",
        "Male_singing",
        "Male_speech_and_man_speaking",
        "Respiratory_sounds",
        "Run",
        "Screaming",
        "Shout",
        "Sigh",
        "Singing",
        "Sneeze",
        "Speech",
        "Speech_synthesizer",
        "Walk_and_footsteps",
        "Whispering",
        "Yell",
        "Music",
    }
)

# Confusores pedidos: motores, motos, barcos, aviones, insectos, viento, lluvia y aves.
FSD50K_TARGET_LABELS = (
    "Engine",
    "Motorcycle",
    "Boat_and_Water_vehicle",
    "Fixed-wing_aircraft_and_airplane",
    "Aircraft",
    "Insect",
    "Wind",
    "Rain",
    "Gull_and_seagull",
    "Bird",
)

# Un dron no puede entrar como negativo: se descarta cualquier mención (con límite de palabra;
# «dji» no coincide con «zildjian»). Conservador: también excluye «drone» musical.
DRONE_PATTERN = re.compile(
    r"\b(drones?|quadcopters?|quadrocopters?|multicopters?|multirotors?|hexacopters?|"
    r"octocopters?|uavs?|uas|dji|mavic)\b",
    re.IGNORECASE,
)


def clip_license_allowed(url: str) -> bool:
    return str(url).strip() in ALLOWED_CLIP_LICENSES


def mentions_drone(info: Mapping) -> bool:
    text = " ".join(
        [str(info.get("title", "")), str(info.get("description", ""))]
        + [str(t) for t in info.get("tags", []) or []]
    )
    return bool(DRONE_PATTERN.search(text.replace("_", " ").replace("-", " ")))


def uploader_group(source: str, uploader: str) -> str:
    """Grupo = fuente + autor (seudonimizado). Mismo autor => mismo grupo (fuga de equipo)."""
    if not str(uploader).strip():
        raise ValueError("uploader vacío: no se puede agrupar")
    digest = hashlib.sha256(str(uploader).strip().encode("utf-8")).hexdigest()[:12]
    return f"{source}:u-{digest}"


def read_fsd50k_ground_truth(text: str, split: str) -> dict[str, list[str]]:
    rows = {}
    for row in csv.DictReader(io.StringIO(text)):
        fname = row["fname"].strip()
        if not fname.isdigit() or fname in rows:
            raise ValueError(f"fname no válido o repetido en {split}: {fname!r}")
        rows[fname] = [label for label in row["labels"].split(",") if label]
    return rows


def fsd50k_rejection(fname: str, labels: Sequence[str], info: Mapping | None) -> str | None:
    """Motivo de rechazo de un clip, o None si es admisible como negativo."""
    if info is None:
        return "sin_metadatos"
    if not clip_license_allowed(info.get("license", "")):
        return "licencia_no_admitida"
    if set(labels) & HUMAN_OR_MUSIC_LABELS:
        return "etiqueta_humana_o_musica"
    if mentions_drone(info):
        return "menciona_dron"
    if not str(info.get("uploader", "")).strip():
        return "sin_autor"
    return None


def _rank(seed: int, key: str) -> str:
    return hashlib.sha256(f"{seed}:{key}".encode()).hexdigest()


def select_fsd50k(
    ground_truth: Mapping[str, Mapping[str, Sequence[str]]],
    clips_info: Mapping[str, Mapping[str, Mapping]],
    compressed_sizes: Mapping[str, Mapping[str, int]],
    *,
    target_labels: Sequence[str] = FSD50K_TARGET_LABELS,
    per_label: int,
    per_uploader_per_label: int,
    max_compressed_bytes: int,
    excluded_ids: Iterable[str] = (),
    seed: int,
) -> list[dict]:
    """Selección determinista: por etiqueta objetivo (en orden), clips admisibles ordenados
    por hash con semilla, con tope por autor y presupuesto de bytes repartido por etiqueta.
    Cada clip se asigna a la primera etiqueta objetivo que lo reclama (sin repeticiones)."""
    if per_label < 1 or per_uploader_per_label < 1 or max_compressed_bytes < 1:
        raise ValueError("topes de selección no válidos")
    excluded = {str(x) for x in excluded_ids}
    budget = max_compressed_bytes // len(target_labels)
    chosen: dict[str, dict] = {}
    for label in target_labels:
        candidates = []
        for split in sorted(ground_truth):
            for fname, labels in ground_truth[split].items():
                if label not in labels or fname in excluded or fname in chosen:
                    continue
                info = clips_info.get(split, {}).get(fname)
                if fsd50k_rejection(fname, labels, info) is not None:
                    continue
                size = compressed_sizes.get(split, {}).get(fname)
                if size is None:
                    continue
                candidates.append((_rank(seed, f"{label}:{fname}"), split, fname, size))
        used, per_uploader, n = 0, {}, 0
        for _, split, fname, size in sorted(candidates):
            if n >= per_label:
                break
            info = clips_info[split][fname]
            uploader = str(info["uploader"]).strip()
            if per_uploader.get(uploader, 0) >= per_uploader_per_label or used + size > budget:
                continue
            per_uploader[uploader] = per_uploader.get(uploader, 0) + 1
            used += size
            n += 1
            chosen[fname] = {
                "fname": fname,
                "split": split,
                "target_label": label,
                "labels": list(ground_truth[split][fname]),
                "license": ALLOWED_CLIP_LICENSES[str(info["license"]).strip()],
                "license_url": str(info["license"]).strip(),
                "uploader": uploader,
                "title": str(info.get("title", "")),
                "group_id": uploader_group("fsd50k", uploader),
                "compressed_bytes": size,
            }
    return sorted(chosen.values(), key=lambda c: (c["target_label"], c["split"], int(c["fname"])))


def verify_fsd50k_pins(
    pinned: Sequence[Mapping],
    ground_truth: Mapping[str, Mapping[str, Sequence[str]]],
    clips_info: Mapping[str, Mapping[str, Mapping]],
) -> list[str]:
    """Revalida en los metadatos de la fuente cada clip fijado: licencia por clip admitida e
    igual a la fijada, sin etiquetas humanas, sin mención a drones y mismo autor. Devuelve
    la lista de errores (vacía si todo cuadra)."""
    errors = []
    seen = set()
    for pin in pinned:
        split, fname = pin["split"], str(pin["fname"])
        if (split, fname) in seen:
            errors.append(f"{fname}: repetido")
        seen.add((split, fname))
        labels = ground_truth.get(split, {}).get(fname)
        info = clips_info.get(split, {}).get(fname)
        if labels is None:
            errors.append(f"{fname}: no está en ground truth de {split}")
            continue
        reason = fsd50k_rejection(fname, labels, info)
        if reason is not None:
            errors.append(f"{fname}: {reason}")
            continue
        if str(info["license"]).strip() != pin["license_url"]:
            errors.append(f"{fname}: licencia distinta de la fijada")
        if str(info["uploader"]).strip() != pin["uploader"]:
            errors.append(f"{fname}: autor distinto del fijado")
        if pin["target_label"] not in labels:
            errors.append(f"{fname}: ya no tiene la etiqueta {pin['target_label']}")
    return errors


def aris_segments(groups_doc: Mapping, split_doc: Mapping) -> list[dict]:
    """Segmentos de ITU ARIS con su grupo (intervalo de dron o bloque de fondo) y la
    partición de los autores. Falla si un grupo cruza particiones, si la etiqueta no
    coincide con la ruta o si falta algún segmento: nunca se parte al azar."""
    assignment = split_doc["assignment"]
    segments = groups_doc["segments"]
    files = [s["file"] for s in segments]
    if len(set(files)) != len(files):
        raise ValueError("segmento repetido en groups.json")
    if set(files) != set(assignment):
        raise ValueError("groups.json y el split no cubren los mismos segmentos")
    if any(v not in {"train", "val", "test"} for v in assignment.values()):
        raise ValueError("partición desconocida en el split")
    out, part_of_group = [], {}
    for seg in segments:
        path, label, group = seg["file"], seg["label"], str(seg["group"])
        folder = path.split("/")[1] if path.count("/") >= 2 else ""
        if label not in {"drone", "background"} or folder != label:
            raise ValueError(f"etiqueta y ruta no coinciden: {path}")
        if not re.fullmatch(r"audio/(drone|background)/\1_\d{4}\.wav", path):
            raise ValueError(f"ruta no permitida: {path}")
        part = assignment[path]
        if part_of_group.setdefault(group, part) != part:
            raise ValueError(f"el grupo {group} cruza particiones")
        out.append(
            {
                "path": path,
                "label": int(label == "drone"),
                "group_id": f"aris:{group}",
                "split": part,
            }
        )
    return out


def parse_sha256sums(text: str) -> dict[str, str]:
    """Fichero SHA256SUMS de la fuente: «<hex>  <ruta>» por línea."""
    sums = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        digest, _, path = line.partition("  ")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest) or not path:
            raise ValueError(f"línea SHA256SUMS no válida: {line[:80]!r}")
        if path in sums:
            raise ValueError(f"ruta repetida en SHA256SUMS: {path}")
        sums[path] = digest
    return sums

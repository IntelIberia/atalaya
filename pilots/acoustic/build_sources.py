"""Fija los manifiestos de FSD50K (subconjunto CC0/CC BY de confusores) e ITU ARIS Lab.

Lee la fuente original en Zenodo (API del registro, metadatos y directorio central de los ZIP
por rangos HTTP), aplica el filtro de licencias por clip y la selección probados en
``acoustic_pilot.sources`` y calcula el SHA-256 de cada clip **en memoria** (no escribe audio
en disco). El cuaderno de Colab repite todas las verificaciones contra estos valores.

Uso (red necesaria, ~0,8 GB de tráfico):  uv run python build_sources.py
"""

# ruff: noqa: E501 - textos de procedencia legibles en el manifiesto

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from acoustic_pilot import remote_zip, sources
from acoustic_pilot.remote import read_https

ROOT = Path(__file__).resolve().parents[2]
HOSTS = frozenset({"zenodo.org"})
FSD_RECORD = "4060432"
ARIS_RECORD = "22682339"
SEED = 20261112
PER_LABEL = 120
PER_UPLOADER_PER_LABEL = 3
MAX_COMPRESSED_BYTES = 800_000_000
FSD_DIR = ROOT / "ml/datasets/fsd50k-subset"
ARIS_DIR = ROOT / "ml/datasets/itu-aris"
ARIS_PREFIX = "itu-aris-lab-acoustic-drone-dataset/"
ARIS_SMALL = (
    "LICENSE",
    "README.md",
    "metadata.json",
    "groups.json",
    "SHA256SUMS",
    "splits/split_interval_disjoint.json",
    "splits/split_temporal.json",
)


def _get(url: str, **kw: Any) -> bytes:
    return read_https(url, HOSTS, **kw)


def _file_url(record: str, key: str) -> str:
    return f"https://zenodo.org/api/records/{record}/files/{key}/content"


def _record(record: str) -> dict[str, Any]:
    data = json.loads(_get(f"https://zenodo.org/api/records/{record}", limit=1 << 22))
    assert isinstance(data, dict)
    return data


def _zenodo_file(rec: dict[str, Any], key: str) -> dict[str, Any]:
    (entry,) = [f for f in rec["files"] if f["key"] == key]
    return {"key": key, "bytes": entry["size"], "md5": entry["checksum"].removeprefix("md5:")}


def _download_checked(record: str, info: dict[str, Any]) -> bytes:
    data = _get(_file_url(record, info["key"]), limit=info["bytes"])
    if (
        len(data) != info["bytes"]
        # MD5 = suma publicada por Zenodo, solo para cotejar; la integridad la fija el SHA-256.
        or hashlib.md5(data, usedforsecurity=False).hexdigest() != info["md5"]  # nosemgrep
    ):
        raise ValueError(f"{info['key']}: tamaño o MD5 de Zenodo no coinciden")
    info["sha256"] = hashlib.sha256(data).hexdigest()
    return data


def _central_directory(
    rec: dict[str, Any], part: str, n_split: int
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    keys = [f"FSD50K.{part}_audio.z{i:02d}" for i in range(1, n_split + 1)] + [
        f"FSD50K.{part}_audio.zip"
    ]
    volumes = [_zenodo_file(rec, k) for k in keys]
    sizes = [v["bytes"] for v in volumes]
    last = volumes[-1]
    tail = _get(_file_url(FSD_RECORD, last["key"]), byte_range=(sizes[-1] - 65536, sizes[-1]))
    eocd = remote_zip.parse_eocd(tail)
    if eocd["zip64_locator"]:
        loc = eocd["zip64_locator"]
        record64 = _get(
            _file_url(FSD_RECORD, keys[loc["disk"]]), byte_range=(loc["offset"], loc["offset"] + 56)
        )
        eocd.update(remote_zip.parse_zip64_eocd(record64))
    start = eocd["cd_offset"]
    cd = _get(
        _file_url(FSD_RECORD, keys[eocd["cd_disk"]]), byte_range=(start, start + eocd["cd_size"])
    )
    entries = remote_zip.parse_central_directory(cd, eocd["n_entries"])
    info = {
        "volumes": volumes,
        "central_directory": {
            "disk": eocd["cd_disk"],
            "offset": start,
            "bytes": eocd["cd_size"],
            "n_entries": eocd["n_entries"],
            "sha256": hashlib.sha256(cd).hexdigest(),
        },
    }
    return info, entries


def _entry_fields(entry: dict[str, Any], digest: str) -> dict[str, Any]:
    return {
        "member": entry["name"],
        "disk": entry["disk"],
        "offset": entry["offset"],
        "method": entry["method"],
        "size": entry["size"],
        "crc32": entry["crc32"],
        "sha256": digest,
    }


def build_fsd50k() -> dict[str, Any]:
    rec = _record(FSD_RECORD)
    meta = {
        k: _zenodo_file(rec, k)
        for k in ("FSD50K.doc.zip", "FSD50K.ground_truth.zip", "FSD50K.metadata.zip")
    }
    blobs = {
        k: zipfile.ZipFile(io.BytesIO(_download_checked(FSD_RECORD, v))) for k, v in meta.items()
    }
    license_text = blobs["FSD50K.doc.zip"].read("FSD50K.doc/LICENSE-DATASET")
    readme = blobs["FSD50K.doc.zip"].read("FSD50K.doc/README.md").decode("utf-8")
    assert b"Attribution 4.0 International (CC BY 4.0)" in license_text
    assert "Each clip has its own license" in readme
    gt = {
        p: sources.read_fsd50k_ground_truth(
            blobs["FSD50K.ground_truth.zip"].read(f"FSD50K.ground_truth/{p}.csv").decode("utf-8"), p
        )
        for p in ("dev", "eval")
    }
    infos = {
        p: json.loads(
            blobs["FSD50K.metadata.zip"].read(f"FSD50K.metadata/{p}_clips_info_FSD50K.json")
        )
        for p in ("dev", "eval")
    }
    archives, members = {}, {}
    for part, n_split in (("dev", 5), ("eval", 1)):
        archives[part], entries = _central_directory(rec, part, n_split)
        members[part] = {
            e["name"].removeprefix(f"FSD50K.{part}_audio/").removesuffix(".wav"): e
            for e in entries
            if e["name"].endswith(".wav") and not e["encrypted"]
        }
    esc10 = json.loads((ROOT / "ml/datasets/esc10/manifest.json").read_text(encoding="utf-8"))
    esc_ids = {f["freesound_src_file"] for f in esc10["files"]}
    chosen = sources.select_fsd50k(
        gt,
        infos,
        {p: {k: e["compressed_size"] for k, e in m.items()} for p, m in members.items()},
        per_label=PER_LABEL,
        per_uploader_per_label=PER_UPLOADER_PER_LABEL,
        max_compressed_bytes=MAX_COMPRESSED_BYTES,
        excluded_ids=esc_ids,
        seed=SEED,
    )
    assert sources.verify_fsd50k_pins(chosen, gt, infos) == []
    # Caché opcional de hashes FUERA del repo (FSD_HASH_CACHE): permite reanudar tras un corte.
    cache_path = Path(os.environ["FSD_HASH_CACHE"]) if os.environ.get("FSD_HASH_CACHE") else None
    cache = json.loads(cache_path.read_text()) if cache_path and cache_path.exists() else {}
    clips = []
    for n, clip in enumerate(chosen, 1):
        part = clip["split"]
        entry = members[part][clip["fname"]]
        cache_key = f"{part}/{entry['name']}/{entry['crc32']}/{entry['size']}"
        if cache_key in cache:
            clips.append(clip | _entry_fields(entry, cache[cache_key]))
            continue
        sizes = [v["bytes"] for v in archives[part]["volumes"]]
        keys = [v["key"] for v in archives[part]["volumes"]]
        span = (
            remote_zip.LOCAL_HEADER_LEN
            + len(entry["name"].encode())
            + 512
            + entry["compressed_size"]
        )
        span = min(span, sum(sizes[entry["disk"] :]) - entry["offset"])
        raw = b"".join(
            _get(_file_url(FSD_RECORD, keys[d]), byte_range=(a, b))
            for d, a, b in remote_zip.volume_ranges(entry["disk"], entry["offset"], span, sizes)
        )
        head = remote_zip.local_header_length(raw, entry["name"])
        if head + entry["compressed_size"] > len(raw):
            raise ValueError(f"cabecera local inesperadamente larga: {entry['name']}")
        wav = remote_zip.decode_member(
            raw[head : head + entry["compressed_size"]],
            method=entry["method"],
            size=entry["size"],
            crc32=entry["crc32"],
        )
        assert wav[:4] == b"RIFF" and wav[8:12] == b"WAVE", entry["name"]
        digest = hashlib.sha256(wav).hexdigest()
        clips.append(clip | _entry_fields(entry, digest))
        if cache_path:
            cache[cache_key] = digest
            cache_path.write_text(json.dumps(cache))
        if n % 50 == 0:
            print(f"  FSD50K {n}/{len(chosen)}", flush=True)
        time.sleep(0.5)  # límite de Zenodo (~133 peticiones/minuto)
    (FSD_DIR / "LICENSE-DATASET-fuente.txt").write_bytes(license_text)
    return {
        "source_id": "fsd50k-subset",
        "source": f"https://zenodo.org/records/{FSD_RECORD}",
        "doi": rec["doi"],
        "version": rec["metadata"].get("version"),
        "zenodo_license_id": rec["metadata"]["license"]["id"],
        "dataset_license": "CC-BY-4.0",
        "clip_license_policy": "solo CC0-1.0, CC-BY-3.0 y CC-BY-4.0 por clip (clips_info de FSD50K); "
        "CC BY-NC y CC Sampling+ excluidas",
        "license_evidence": {
            "path": "LICENSE-DATASET-fuente.txt",
            "sha256": hashlib.sha256(license_text).hexdigest(),
            "archive": "FSD50K.doc.zip",
        },
        "metadata_archives": list(meta.values()),
        "audio_archives": archives,
        "retrieved_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "selection": {
            "target_labels": list(sources.FSD50K_TARGET_LABELS),
            "excluded_labels": sorted(sources.HUMAN_OR_MUSIC_LABELS),
            "drone_pattern": sources.DRONE_PATTERN.pattern,
            "per_label": PER_LABEL,
            "per_uploader_per_label": PER_UPLOADER_PER_LABEL,
            "max_compressed_bytes": MAX_COMPRESSED_BYTES,
            "seed": SEED,
            "excluded_ids": "freesound_src_file de ml/datasets/esc10/manifest.json (mismo audio de Freesound)",
        },
        "group_policy": "group_id = fsd50k + autor de Freesound seudonimizado (SHA-256): un autor nunca cruza particiones",
        "intake_approved": False,
        "training_allowed": False,
        "production_allowed": False,
        "alcance": "prueba técnica aislada en Colab (ADR 0016); nada entra en el producto",
        "clip_count": len(clips),
        "total_compressed_bytes": sum(c["compressed_bytes"] for c in clips),
        "total_wav_bytes": sum(c["size"] for c in clips),
        "clips": clips,
    }


def build_aris() -> dict[str, Any]:
    rec = _record(ARIS_RECORD)
    assert rec["metadata"]["license"]["id"] == "cc-by-4.0"
    key = "itu-aris-lab-acoustic-drone-dataset-v1.0.0.zip"
    archive = _zenodo_file(rec, key)
    data = _download_checked(ARIS_RECORD, archive)
    zf = zipfile.ZipFile(io.BytesIO(data))
    small = {name: zf.read(ARIS_PREFIX + name) for name in ARIS_SMALL}
    assert b"Creative Commons Attribution 4.0 International (CC BY 4.0)" in small["LICENSE"]
    assert b"commercially" in small["LICENSE"]
    sums = sources.parse_sha256sums(small["SHA256SUMS"].decode("utf-8"))
    groups = json.loads(small["groups.json"])
    split = json.loads(small["splits/split_interval_disjoint.json"])
    segments = sources.aris_segments(groups, split)
    for seg in segments:
        wav = zf.read(ARIS_PREFIX + seg["path"])
        if hashlib.sha256(wav).hexdigest() != sums[seg["path"]]:
            raise ValueError(f"SHA256SUMS no cuadra: {seg['path']}")
    (ARIS_DIR / "LICENSE-fuente.txt").write_bytes(small["LICENSE"])
    counts: dict[str, int] = {}
    for seg in segments:
        k = f"{'drone' if seg['label'] else 'background'}:{seg['split']}"
        counts[k] = counts.get(k, 0) + 1
    return {
        "source_id": "itu-aris",
        "source": f"https://zenodo.org/records/{ARIS_RECORD}",
        "doi": rec["doi"],
        "version": rec["metadata"].get("version"),
        "license": "CC-BY-4.0",
        "zenodo_license_id": rec["metadata"]["license"]["id"],
        "license_evidence": {
            "path": "LICENSE-fuente.txt",
            "sha256": hashlib.sha256(small["LICENSE"]).hexdigest(),
        },
        "attribution": json.loads(small["metadata.json"])["citation"],
        "archive": archive,
        "inner_files_sha256": {n: hashlib.sha256(b).hexdigest() for n, b in small.items()},
        "inner_prefix": ARIS_PREFIX,
        "split_used": "splits/split_interval_disjoint.json",
        "group_policy": "group_id = intervalo de dron o bloque de fondo de groups.json; segmentos "
        "solapados al 50 %: nunca se parte por segmento",
        "segment_count": len(segments),
        "counts": counts,
        "retrieved_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "personal_data": "README: voz de los operadores audible en algunos segmentos (miembros del "
        "grupo, con consentimiento para publicar); la puerta automática de voz se aplica igualmente",
        "intake_approved": False,
        "training_allowed": False,
        "production_allowed": False,
        "alcance": "prueba técnica aislada en Colab (ADR 0016); nada entra en el producto",
    }


def main() -> int:
    FSD_DIR.mkdir(parents=True, exist_ok=True)
    ARIS_DIR.mkdir(parents=True, exist_ok=True)
    if "--only-fsd50k" not in sys.argv:
        aris = build_aris()
        (ARIS_DIR / "manifest.json").write_text(
            json.dumps(aris, ensure_ascii=False, indent=1) + "\n"
        )
        print("ITU ARIS:", aris["segment_count"], "segmentos", flush=True)
    fsd = build_fsd50k()
    (FSD_DIR / "manifest.json").write_text(json.dumps(fsd, ensure_ascii=False, indent=1) + "\n")
    print(
        "FSD50K:", fsd["clip_count"], "clips,", fsd["total_compressed_bytes"], "bytes comprimidos"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

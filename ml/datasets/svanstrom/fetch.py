"""Descarga solo el audio de Svanström v1.0.0 y verifica los blobs originales.

Los WAV quedan en data/raw/ (ignorado por Git). El inventario SHA-256 no contiene audio.
La ejecución no concede permiso para entrenar: privacidad y agrupación siguen en intake.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
import wave
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "raw" / "svanstrom"
META = ROOT / "ml" / "datasets" / "svanstrom"
COMMIT = "e7a6eaf9760fa3f9ecc37d09cd11a8cd20be90dd"
REPO = "DroneDetectionThesis/Drone-detection-dataset"
TREE_URL = f"https://api.github.com/repos/{REPO}/git/trees/{COMMIT}?recursive=1"
RAW_URL = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}"
LICENSE_BLOB = "0e259d42c996742e9e3cba14c677129b2c1b6311"
WAV_RE = re.compile(r"Data/Audio/(DRONE|HELICOPTER|BACKGROUND)_[0-9]{3}\.wav")
EXPECTED_COUNT = 90
EXPECTED_BYTES = 158_764_512


def _get(url: str) -> bytes:
    allowed_hosts = {"api.github.com", "raw.githubusercontent.com"}
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        raise ValueError(f"URL de origen no permitida: {url}")
    request = urllib.request.Request(  # noqa: S310 - HTTPS y host comprobados arriba
        url, headers={"User-Agent": "atalaya-dataset-intake/1"}
    )
    with urllib.request.urlopen(request, timeout=90) as response:  # noqa: S310
        redirected = urlparse(response.geturl())
        if redirected.scheme != "https" or redirected.hostname not in allowed_hosts:
            raise ValueError(f"redirección inesperada: {response.geturl()}")
        return cast(bytes, response.read())


def _blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


def _download(path: str, expected_sha1: str, expected_size: int, dest: Path) -> bytes:
    if dest.exists():
        existing = dest.read_bytes()
        if len(existing) == expected_size and _blob_sha1(existing) == expected_sha1:
            return existing
    data = _get(f"{RAW_URL}/{path}")
    if len(data) != expected_size or _blob_sha1(data) != expected_sha1:
        raise ValueError(f"origen distinto del árbol fijado: {path}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    temporary = dest.with_suffix(dest.suffix + ".part")
    temporary.write_bytes(data)
    temporary.replace(dest)
    return data


def _tree() -> list[dict[str, Any]]:
    result = json.loads(_get(TREE_URL))
    if result.get("truncated"):
        raise ValueError("árbol GitHub truncado")
    blobs = [
        entry
        for entry in result["tree"]
        if entry.get("type") == "blob" and WAV_RE.fullmatch(entry["path"])
    ]
    counts = Counter(entry["path"].split("/")[-1].split("_", 1)[0] for entry in blobs)
    if (
        len(blobs) != EXPECTED_COUNT
        or sum(entry["size"] for entry in blobs) != EXPECTED_BYTES
        or counts != {"DRONE": 30, "HELICOPTER": 30, "BACKGROUND": 30}
    ):
        raise ValueError(f"inventario original inesperado: {len(blobs)} clips, {counts}")
    return sorted(blobs, key=lambda entry: entry["path"])


def main() -> int:
    META.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(UTC).isoformat()
    license_bytes = _get(f"{RAW_URL}/LICENSE")
    if _blob_sha1(license_bytes) != LICENSE_BLOB or b"CC0 1.0 Universal" not in license_bytes:
        raise ValueError("licencia original no coincide con el tag fijado")
    license_archive = (
        f"Fuente original: https://github.com/{REPO}/blob/{COMMIT}/LICENSE\n"
        f"Consultada (UTC): {retrieved_at}\n"
        "Clasificación declarada por el repositorio: CC0-1.0. "
        "La procedencia por clip se evalúa aparte.\n\n"
    ).encode() + license_bytes
    (META / "LICENSE-fuente.txt").write_bytes(license_archive)

    clips = []
    for entry in _tree():
        path = entry["path"]
        name = Path(path).name
        data = _download(path, entry["sha"], entry["size"], OUT / name)
        with wave.open(str(OUT / name), "rb") as wav:
            channels = wav.getnchannels()
            sample_width_bytes = wav.getsampwidth()
            sample_rate = wav.getframerate()
            if (
                channels not in {1, 2}
                or sample_width_bytes != 2
                or sample_rate != 44_100
                or wav.getcomptype() != "NONE"
            ):
                raise ValueError(f"formato WAV inesperado: {name}")
            seconds = wav.getnframes() / sample_rate
            if not 9.9 <= seconds <= 10.1:
                raise ValueError(f"duración WAV inesperada: {name}: {seconds:.3f} s")
        category = name.split("_", 1)[0]
        recording_id = name.removesuffix(".wav")
        sha256 = hashlib.sha256(data).hexdigest()
        clips.append(
            {
                "path": name,
                "sha256": sha256,
                "bytes": len(data),
                "channels": channels,
                "sample_width_bytes": sample_width_bytes,
                "sample_rate_hz": sample_rate,
                "duration_seconds": round(seconds, 6),
                "label": int(category == "DRONE"),
                "source_class": category,
                "recording_id": recording_id,
                "group_id": recording_id,
                "grouping_status": "provisional_clip_or_exact_duplicate",
                "site_id": None,
                "upstream_git_blob_sha1": entry["sha"],
            }
        )
        print(f"OK {name} {clips[-1]['sha256']}")

    # El nombre de archivo no identifica vuelo ni sitio. Los duplicados exactos
    # comparten al menos el grupo provisional para evitar fugas triviales.
    first_recording_by_hash: dict[str, str] = {}
    for clip in clips:
        first_recording = first_recording_by_hash.setdefault(clip["sha256"], clip["recording_id"])
        clip["group_id"] = first_recording
        clip["training_excluded"] = first_recording != clip["recording_id"]
        clip["exclusion_reason"] = (
            f"exact_duplicate_of:{first_recording}.wav" if clip["training_excluded"] else None
        )

    manifest = {
        "source_id": "svanstrom-v1.0.0-audio",
        "source": f"https://github.com/{REPO}/tree/{COMMIT}/Data/Audio",
        "commit": COMMIT,
        "license": "CC0-1.0",
        "license_url": f"https://github.com/{REPO}/blob/{COMMIT}/LICENSE",
        "license_evidence": {
            "path": "LICENSE-fuente.txt",
            "sha256": hashlib.sha256(license_archive).hexdigest(),
            "upstream_sha256": hashlib.sha256(license_bytes).hexdigest(),
            "upstream_git_blob_sha1": LICENSE_BLOB,
        },
        "retrieved_at_utc": retrieved_at,
        "group_status": "provisional",
        "intake_approved": False,
        "training_allowed": False,
        "production_allowed": False,
        "generalization_eval_allowed": False,
        "reason": "per-clip provenance, privacy and source-session grouping review pending",
        "clips": clips,
    }
    destination = META / "manifest.json"
    temporary = destination.with_suffix(".json.part")
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(destination)
    print(f"Intake descargado y verificado: {len(clips)} WAV; entrenamiento bloqueado")
    return 0


if __name__ == "__main__":
    sys.exit(main())

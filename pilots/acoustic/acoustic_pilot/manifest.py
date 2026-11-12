"""Carga de audios con procedencia e integridad verificadas antes de entrenar."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Clip:
    relative_path: str
    sha256: str
    label: int
    recording_id: str
    group_id: str
    site_id: str | None


@dataclass(frozen=True)
class Manifest:
    source_id: str
    group_status: str
    clips: tuple[Clip, ...]
    license_file: Path
    license_sha256: str
    intake_approved: bool

    @property
    def training_allowed(self) -> bool:
        """El intake técnico/legal permite entrenar; no acredita generalización."""
        return self.intake_approved

    @property
    def generalization_eval_allowed(self) -> bool:
        """Solo IDs de grupo verificados permiten una evaluación por grupos."""
        return self.intake_approved and self.group_status == "verified"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} debe ser texto no vacío")
    return value.strip()


def _sha256(value: Any, name: str) -> str:
    digest = _text(value, name)
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError(f"{name} debe ser SHA-256 hexadecimal")
    return digest


def _safe_relative(value: Any, name: str) -> str:
    raw = _text(value, name)
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts or path.suffix.lower() != ".wav":
        raise ValueError(f"{name}: ruta WAV relativa no permitida")
    return path.as_posix()


def _evidence_file(base: Path, info: Any, name: str) -> Path:
    if not isinstance(info, dict):
        raise ValueError(f"falta {name}")
    relative = Path(_text(info.get("path"), f"{name}.path"))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{name}.path debe ser relativa")
    root = base.resolve()
    real_path = (root / relative).resolve()
    if root not in real_path.parents:
        raise ValueError(f"{name}.path sale del directorio permitido")
    expected = _sha256(info.get("sha256"), f"{name}.sha256")
    if not real_path.is_file() or file_sha256(real_path) != expected:
        raise ValueError(f"{name}: archivo ausente o con SHA-256 distinto")
    return real_path


def _check_intake_review(
    raw: dict[str, Any],
    manifest_path: Path,
    evidence_root: Path | None,
    clips: tuple[Clip, ...],
    verified_hashes: tuple[str, ...],
) -> None:
    if raw.get("training_allowed") is not True:
        raise ValueError("training_allowed debe ser true tras aprobar el intake")
    if evidence_root is None:
        raise ValueError("evidence_root requerido para comprobar revisión, data card y DVC")
    review_path = _evidence_file(
        manifest_path.parent, raw.get("intake_review_evidence"), "intake_review_evidence"
    )
    review: Any = json.loads(review_path.read_text(encoding="utf-8"))
    if not isinstance(review, dict):
        raise ValueError("intake_review_evidence debe ser objeto JSON")
    if (
        review.get("source_id") != raw["source_id"]
        or review.get("clip_count") != len(verified_hashes)
        or review.get("training_clip_count") != len(clips)
    ):
        raise ValueError("revisión de intake no corresponde al origen y recuento de clips")
    clip_digest = hashlib.sha256("\n".join(sorted(verified_hashes)).encode("ascii")).hexdigest()
    if review.get("clip_hashes_sha256") != clip_digest:
        raise ValueError("revisión de intake no corresponde a estos SHA-256 de audio")
    if not all(review.get(key) is True for key in ("source_rights_reviewed", "privacy_reviewed")):
        raise ValueError("faltan revisiones de derechos o privacidad")
    _text(review.get("reviewed_by"), "reviewed_by")
    _text(review.get("reviewed_at_utc"), "reviewed_at_utc")
    _evidence_file(evidence_root, review.get("data_card_evidence"), "data_card_evidence")
    _evidence_file(evidence_root, review.get("dvc_pointer_evidence"), "dvc_pointer_evidence")
    if raw["group_status"] == "verified":
        if review.get("grouping_reviewed") is not True:
            raise ValueError("grouping_reviewed debe ser true para grupos verificados")
        mapping_path = _evidence_file(
            evidence_root, review.get("group_mapping_evidence"), "group_mapping_evidence"
        )
        mapping: Any = json.loads(mapping_path.read_text(encoding="utf-8"))
        expected_mapping = {
            clip.relative_path: {
                "recording_id": clip.recording_id,
                "group_id": clip.group_id,
                "site_id": clip.site_id,
            }
            for clip in clips
        }
        if not isinstance(mapping, dict) or mapping.get("clips") != expected_mapping:
            raise ValueError("group_mapping_evidence no corresponde a los clips entrenables")


def load_manifest(path: Path, data_root: Path, *, evidence_root: Path | None = None) -> Manifest:
    """Valida licencia, hashes, rutas y grupos sin decodificar el audio."""
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("manifest debe ser un objeto JSON")
    source_id = _text(raw.get("source_id"), "source_id")
    group_status = raw.get("group_status")
    if group_status not in {"verified", "provisional"}:
        raise ValueError("group_status debe ser verified o provisional")
    if raw.get("intake_approved") is not True:
        raise ValueError(
            "intake_approved debe constar como true tras revisión de fuente y privacidad"
        )

    license_info = raw.get("license_evidence")
    license_path = _evidence_file(path.parent, license_info, "license_evidence")
    license_sha = _sha256(license_info["sha256"], "license_evidence.sha256")

    items = raw.get("clips")
    if not isinstance(items, list) or len(items) < 6:
        raise ValueError("se requieren al menos seis clips con metadatos completos")
    clips: list[Clip] = []
    seen_paths: set[str] = set()
    included_by_path: dict[str, Clip] = {}
    included_by_hash: dict[str, Clip] = {}
    verified_hashes: list[str] = []
    recording_group: dict[str, str] = {}
    root = data_root.resolve()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"clip {index}: objeto JSON requerido")
        relative_path = _safe_relative(item.get("path"), f"clip {index}.path")
        if relative_path in seen_paths:
            raise ValueError(f"clip {index}: ruta duplicada")
        seen_paths.add(relative_path)
        real_path = (root / relative_path).resolve()
        if root not in real_path.parents or not real_path.is_file():
            raise ValueError(f"clip {index}: archivo fuera de data-root o ausente")
        expected_hash = _sha256(item.get("sha256"), f"clip {index}.sha256")
        if file_sha256(real_path) != expected_hash:
            raise ValueError(f"clip {index}: SHA-256 distinto")
        verified_hashes.append(expected_hash)
        label = item.get("label")
        if type(label) is not int or label not in {0, 1}:
            raise ValueError(f"clip {index}: label debe ser 0 o 1")
        recording = _text(item.get("recording_id"), f"clip {index}.recording_id")
        group = _text(item.get("group_id"), f"clip {index}.group_id")
        site = item.get("site_id")
        if site is not None:
            site = _text(site, f"clip {index}.site_id")
        if recording in recording_group and recording_group[recording] != group:
            raise ValueError(f"clip {index}: una grabación figura en dos grupos")
        recording_group[recording] = group
        clip = Clip(relative_path, expected_hash, label, recording, group, site)
        excluded = item.get("training_excluded", False)
        if type(excluded) is not bool:
            raise ValueError(f"clip {index}: training_excluded debe ser booleano")
        if excluded:
            reason = _text(item.get("exclusion_reason"), f"clip {index}.exclusion_reason")
            prefix = "exact_duplicate_of:"
            if not reason.startswith(prefix):
                raise ValueError(f"clip {index}: exclusión no reconocida")
            original = included_by_path.get(reason[len(prefix) :])
            if original is None or (
                clip.sha256,
                clip.label,
                clip.group_id,
                clip.site_id,
            ) != (
                original.sha256,
                original.label,
                original.group_id,
                original.site_id,
            ):
                raise ValueError(f"clip {index}: referencia de duplicado no coincide")
            continue
        if expected_hash in included_by_hash:
            raise ValueError(f"clip {index}: audio idéntico duplicado")
        if item.get("exclusion_reason") is not None:
            raise ValueError(f"clip {index}: exclusion_reason sin exclusión")
        included_by_hash[expected_hash] = clip
        included_by_path[relative_path] = clip
        clips.append(clip)
    if {clip.label for clip in clips} != {0, 1}:
        raise ValueError("el manifest necesita positivos y negativos")
    verified_clips = tuple(clips)
    _check_intake_review(raw, path, evidence_root, verified_clips, tuple(verified_hashes))
    return Manifest(source_id, group_status, verified_clips, license_path, license_sha, True)

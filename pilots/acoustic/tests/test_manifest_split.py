"""Puertas del manifiesto y partición: fallan antes de entrenar datos no válidos."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from acoustic_pilot.manifest import load_manifest
from acoustic_pilot.split import split_manifest


def _fixture(
    tmp_path: Path, *, approved: bool = True, status: str = "verified"
) -> tuple[Path, Path, dict[str, Any]]:
    source = tmp_path / "source"
    source.mkdir()
    license_file = source / "LICENSE-fuente.txt"
    license_bytes = b"synthetic fixture license; no third-party audio\n"
    license_file.write_bytes(license_bytes)
    audio = tmp_path / "audio"
    audio.mkdir()
    clips = []
    for index in range(12):
        name = f"clip-{index:02}.wav"
        payload = b"RIFF-test-only-" + index.to_bytes(2, "little")
        (audio / name).write_bytes(payload)
        clips.append(
            {
                "path": name,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "label": index % 2,
                "recording_id": f"recording-{index}",
                "group_id": f"group-{index}",
                "site_id": None,
            }
        )
    data = {
        "source_id": "synthetic-test-only",
        "group_status": status,
        "intake_approved": approved,
        "training_allowed": approved,
        "license_evidence": {
            "path": license_file.name,
            "sha256": hashlib.sha256(license_bytes).hexdigest(),
        },
        "clips": clips,
    }
    card = tmp_path / "data-card.md"
    card.write_text("Synthetic data-card fixture only\n", encoding="utf-8")
    dvc = tmp_path / "audio.dvc"
    dvc.write_text("Synthetic DVC pointer fixture only\n", encoding="utf-8")
    mapping = tmp_path / "group-mapping.json"
    mapping.write_text(
        json.dumps(
            {
                "clips": {
                    clip["path"]: {
                        "recording_id": clip["recording_id"],
                        "group_id": clip["group_id"],
                        "site_id": clip["site_id"],
                    }
                    for clip in clips
                }
            }
        ),
        encoding="utf-8",
    )
    review = {
        "source_id": data["source_id"],
        "clip_count": len(clips),
        "training_clip_count": len(clips),
        "clip_hashes_sha256": hashlib.sha256(
            "\n".join(sorted(clip["sha256"] for clip in clips)).encode("ascii")
        ).hexdigest(),
        "source_rights_reviewed": True,
        "privacy_reviewed": True,
        "grouping_reviewed": status == "verified",
        "reviewed_by": "synthetic-fixture-reviewer",
        "reviewed_at_utc": "2026-11-11T00:00:00Z",
        "data_card_evidence": {
            "path": card.name,
            "sha256": hashlib.sha256(card.read_bytes()).hexdigest(),
        },
        "dvc_pointer_evidence": {
            "path": dvc.name,
            "sha256": hashlib.sha256(dvc.read_bytes()).hexdigest(),
        },
        "group_mapping_evidence": {
            "path": mapping.name,
            "sha256": hashlib.sha256(mapping.read_bytes()).hexdigest(),
        },
    }
    review_file = source / "INTAKE-REVIEW.json"
    review_file.write_text(json.dumps(review), encoding="utf-8")
    data["intake_review_evidence"] = {
        "path": review_file.name,
        "sha256": hashlib.sha256(review_file.read_bytes()).hexdigest(),
    }
    path = source / "manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, audio, data


def _write(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _update_review(path: Path, data: dict[str, Any], *, training_clip_count: int) -> None:
    review_path = path.parent / "INTAKE-REVIEW.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review["training_clip_count"] = training_clip_count
    review["clip_hashes_sha256"] = hashlib.sha256(
        "\n".join(sorted(clip["sha256"] for clip in data["clips"])).encode("ascii")
    ).hexdigest()
    _write(review_path, review)
    data["intake_review_evidence"]["sha256"] = hashlib.sha256(review_path.read_bytes()).hexdigest()
    _write(path, data)


def test_manifest_intake_gate_fails_before_audio_use(tmp_path: Path) -> None:
    path, audio, _data = _fixture(tmp_path, approved=False)
    with pytest.raises(ValueError, match="intake_approved"):
        load_manifest(path, audio)


def test_group_split_is_deterministic_and_disjoint(tmp_path: Path) -> None:
    path, audio, _data = _fixture(tmp_path)
    manifest = load_manifest(path, audio, evidence_root=tmp_path)
    split = split_manifest(manifest, seed=17)
    assert split == split_manifest(manifest, seed=17)
    assert manifest.training_allowed and manifest.generalization_eval_allowed
    assert not split.provisional
    assert set(split.train).isdisjoint(split.validation)
    assert set(split.train).isdisjoint(split.test)
    assert set(split.validation).isdisjoint(split.test)
    assert set(split.train + split.validation + split.test) == set(range(12))
    for partition in (split.train, split.validation, split.test):
        assert {manifest.clips[index].label for index in partition} == {0, 1}


def test_provisional_groups_require_explicit_mode(tmp_path: Path) -> None:
    path, audio, _data = _fixture(tmp_path, status="provisional")
    manifest = load_manifest(path, audio, evidence_root=tmp_path)
    assert manifest.training_allowed
    assert not manifest.generalization_eval_allowed
    with pytest.raises(ValueError, match="modo exploratorio explícito"):
        split_manifest(manifest)
    assert split_manifest(manifest, allow_provisional=True).provisional


def test_split_rejects_unapproved_manifest_instance(tmp_path: Path) -> None:
    path, audio, _data = _fixture(tmp_path)
    manifest = replace(load_manifest(path, audio, evidence_root=tmp_path), intake_approved=False)
    with pytest.raises(ValueError, match="intake no aprobado"):
        split_manifest(manifest)


def test_audio_tampering_fails_hash_gate(tmp_path: Path) -> None:
    path, audio, data = _fixture(tmp_path)
    (audio / data["clips"][0]["path"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="SHA-256 distinto"):
        load_manifest(path, audio, evidence_root=tmp_path)


def test_approved_manifest_requires_data_card_and_dvc_evidence(tmp_path: Path) -> None:
    path, audio, _data = _fixture(tmp_path)
    (tmp_path / "data-card.md").write_text("changed after review", encoding="utf-8")
    with pytest.raises(ValueError, match="data_card_evidence"):
        load_manifest(path, audio, evidence_root=tmp_path)


def test_training_allowed_cannot_be_false_with_intake_approved(tmp_path: Path) -> None:
    path, audio, data = _fixture(tmp_path)
    data["training_allowed"] = False
    _write(path, data)
    with pytest.raises(ValueError, match="training_allowed"):
        load_manifest(path, audio, evidence_root=tmp_path)


def test_license_symlink_cannot_escape_manifest_directory(tmp_path: Path) -> None:
    path, audio, data = _fixture(tmp_path)
    outside = tmp_path / "outside-license.txt"
    outside.write_bytes(b"other bytes")
    (path.parent / "alias.txt").symlink_to(outside)
    data["license_evidence"]["path"] = "alias.txt"
    data["license_evidence"]["sha256"] = hashlib.sha256(outside.read_bytes()).hexdigest()
    _write(path, data)
    with pytest.raises(ValueError, match="sale del directorio"):
        load_manifest(path, audio, evidence_root=tmp_path)


def test_duplicate_audio_is_rejected_even_same_class(tmp_path: Path) -> None:
    path, audio, data = _fixture(tmp_path)
    first = data["clips"][0]
    duplicate = data["clips"][2]
    (audio / duplicate["path"]).write_bytes((audio / first["path"]).read_bytes())
    duplicate["sha256"] = first["sha256"]
    duplicate["group_id"] = first["group_id"]
    _write(path, data)
    with pytest.raises(ValueError, match="audio idéntico duplicado"):
        load_manifest(path, audio, evidence_root=tmp_path)


def test_documented_exact_duplicate_is_verified_then_excluded(tmp_path: Path) -> None:
    path, audio, data = _fixture(tmp_path, status="provisional")
    first = data["clips"][0]
    duplicate = data["clips"][2]
    (audio / duplicate["path"]).write_bytes((audio / first["path"]).read_bytes())
    duplicate["sha256"] = first["sha256"]
    duplicate["group_id"] = first["group_id"]
    duplicate["training_excluded"] = True
    duplicate["exclusion_reason"] = f"exact_duplicate_of:{first['path']}"
    _update_review(path, data, training_clip_count=11)
    manifest = load_manifest(path, audio, evidence_root=tmp_path)
    assert len(manifest.clips) == 11
    assert duplicate["path"] not in {clip.relative_path for clip in manifest.clips}
    split = split_manifest(manifest, allow_provisional=True)
    assert len(split.train + split.validation + split.test) == 11


def test_duplicate_exclusion_must_reference_matching_audio(tmp_path: Path) -> None:
    path, audio, data = _fixture(tmp_path)
    data["clips"][2]["training_excluded"] = True
    data["clips"][2]["exclusion_reason"] = "exact_duplicate_of:clip-00.wav"
    _write(path, data)
    with pytest.raises(ValueError, match="referencia de duplicado no coincide"):
        load_manifest(path, audio, evidence_root=tmp_path)


def test_one_recording_cannot_cross_groups(tmp_path: Path) -> None:
    path, audio, data = _fixture(tmp_path)
    data["clips"][1]["recording_id"] = data["clips"][0]["recording_id"]
    _write(path, data)
    with pytest.raises(ValueError, match="una grabación figura en dos grupos"):
        load_manifest(path, audio, evidence_root=tmp_path)


def test_manifest_rejects_path_traversal(tmp_path: Path) -> None:
    path, audio, data = _fixture(tmp_path)
    data["clips"][0]["path"] = "../outside.wav"
    _write(path, data)
    with pytest.raises(ValueError, match="ruta WAV relativa no permitida"):
        load_manifest(path, audio, evidence_root=tmp_path)


def test_site_split_requires_sites(tmp_path: Path) -> None:
    path, audio, _data = _fixture(tmp_path)
    manifest = load_manifest(path, audio, evidence_root=tmp_path)
    with pytest.raises(ValueError, match="site_id verificado"):
        split_manifest(manifest, key="site")

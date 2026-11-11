"""Particiones deterministas por grupos; nunca por ventanas del mismo audio."""

from __future__ import annotations

from dataclasses import dataclass

from acoustic_pilot.grouped_eval import split_indices_by_group
from acoustic_pilot.manifest import Manifest


@dataclass(frozen=True)
class Split:
    train: tuple[int, ...]
    validation: tuple[int, ...]
    test: tuple[int, ...]
    key: str
    provisional: bool


def split_manifest(
    manifest: Manifest,
    *,
    seed: int = 20261111,
    key: str = "group",
    allow_provisional: bool = False,
) -> Split:
    if not manifest.training_allowed:
        raise ValueError("intake no aprobado: no se permite separar datos para entrenamiento")
    if key not in {"group", "site"}:
        raise ValueError("split key debe ser group o site")
    provisional = manifest.group_status == "provisional"
    if provisional and not allow_provisional:
        raise ValueError("grupos provisionales: exige modo exploratorio explícito")
    if key == "site" and any(clip.site_id is None for clip in manifest.clips):
        raise ValueError("split por sitio exige site_id verificado en todos los clips")

    groups = [str(clip.group_id if key == "group" else clip.site_id) for clip in manifest.clips]
    labels = [clip.label for clip in manifest.clips]
    train, validation, test = split_indices_by_group(labels, groups, seed=seed)
    if len(set(train + validation + test)) != len(manifest.clips):
        raise ValueError("una grabación aparece en varias particiones")
    return Split(train, validation, test, key, provisional)

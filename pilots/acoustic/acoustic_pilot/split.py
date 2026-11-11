"""Particiones deterministas por grupos; nunca por ventanas del mismo audio."""

from __future__ import annotations

import random
from dataclasses import dataclass

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

    group_for_index = {
        index: (clip.group_id if key == "group" else clip.site_id)
        for index, clip in enumerate(manifest.clips)
    }
    groups = sorted({group for group in group_for_index.values() if group is not None})
    if len(groups) < 6:
        raise ValueError("se necesitan al menos seis grupos independientes")
    n_test = max(2, round(len(groups) * 0.2))
    n_validation = max(2, round(len(groups) * 0.2))
    if len(groups) - n_test - n_validation < 2:
        raise ValueError("grupos insuficientes para train/validation/test")

    for attempt in range(1000):
        shuffled = groups.copy()
        random.Random(seed + attempt).shuffle(shuffled)
        test_groups = set(shuffled[:n_test])
        validation_groups = set(shuffled[n_test : n_test + n_validation])
        train_groups = set(shuffled[n_test + n_validation :])
        partitions = [
            tuple(i for i, group in group_for_index.items() if group in selected)
            for selected in (train_groups, validation_groups, test_groups)
        ]
        if all({manifest.clips[i].label for i in part} == {0, 1} for part in partitions):
            train, validation, test = partitions
            if len(set(train + validation + test)) != len(manifest.clips):
                raise ValueError("una grabación aparece en varias particiones")
            return Split(train, validation, test, key, provisional)
    raise ValueError("no hay partición por grupos con ambas clases en los tres conjuntos")

"""Filtro de licencias por clip (FSD50K), selección, agrupación y carga de ITU ARIS."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acoustic_pilot import sources
from acoustic_pilot.sources import (
    aris_segments,
    clip_license_allowed,
    fsd50k_rejection,
    mentions_drone,
    parse_sha256sums,
    read_fsd50k_ground_truth,
    select_fsd50k,
    uploader_group,
    verify_fsd50k_pins,
)

CC0 = "http://creativecommons.org/publicdomain/zero/1.0/"
BY3 = "http://creativecommons.org/licenses/by/3.0/"
NC = "http://creativecommons.org/licenses/by-nc/3.0/"
SAMPLING = "http://creativecommons.org/licenses/sampling+/1.0/"


def _info(license_url: str = CC0, uploader: str = "ana", **extra: object) -> dict:
    return {
        "title": "engine idle",
        "description": "",
        "tags": ["car"],
        "license": license_url,
        "uploader": uploader,
    } | extra


# --- Licencia por clip ------------------------------------------------------------------


@pytest.mark.parametrize("url", [CC0, BY3, "http://creativecommons.org/licenses/by/4.0/"])
def test_cc0_and_cc_by_are_admitted(url: str) -> None:
    assert clip_license_allowed(url)


@pytest.mark.parametrize(
    "url", [NC, SAMPLING, "", "https://creativecommons.org/licenses/by-sa/4.0/", "CC0"]
)
def test_nc_sampling_and_unknown_licenses_are_rejected(url: str) -> None:
    assert not clip_license_allowed(url)


def test_rejection_reasons_cover_license_humans_music_drones_and_metadata() -> None:
    assert fsd50k_rejection("1", ["Engine"], _info()) is None
    assert fsd50k_rejection("1", ["Engine"], None) == "sin_metadatos"
    assert fsd50k_rejection("1", ["Engine"], _info(NC)) == "licencia_no_admitida"
    assert fsd50k_rejection("1", ["Engine", "Speech"], _info()) == "etiqueta_humana_o_musica"
    assert fsd50k_rejection("1", ["Wind", "Music"], _info()) == "etiqueta_humana_o_musica"
    assert fsd50k_rejection("1", ["Engine", "Walk_and_footsteps"], _info()) is not None
    drone = _info(tags=["DJI", "phantom"])
    assert fsd50k_rejection("1", ["Engine"], drone) == "menciona_dron"
    assert fsd50k_rejection("1", ["Engine"], _info(uploader=" ")) == "sin_autor"


def test_drone_pattern_uses_word_boundaries() -> None:
    assert mentions_drone({"title": "Quadcopter flyby"})
    assert mentions_drone({"tags": ["uav"]})
    assert mentions_drone({"description": "my_drone recording"})
    assert not mentions_drone({"tags": ["zildjian", "cymbal"]})
    assert not mentions_drone({"title": "Squadron of geese"})


def test_uploader_group_is_pseudonymous_stable_and_source_scoped() -> None:
    a = uploader_group("fsd50k", "Ana")
    assert a == uploader_group("fsd50k", " Ana ") and a.startswith("fsd50k:u-")
    assert "Ana" not in a and a != uploader_group("esc10", "Ana")
    with pytest.raises(ValueError):
        uploader_group("fsd50k", "")


def test_ground_truth_reader_rejects_bad_or_repeated_ids() -> None:
    text = 'fname,labels,mids,split\n1,"Engine,Vehicle",/m/x,train\n2,Wind,/m/y,val\n'
    assert read_fsd50k_ground_truth(text, "dev") == {"1": ["Engine", "Vehicle"], "2": ["Wind"]}
    with pytest.raises(ValueError):
        read_fsd50k_ground_truth(text + "1,Rain,/m/z,train\n", "dev")
    with pytest.raises(ValueError):
        read_fsd50k_ground_truth("fname,labels,mids\nx.wav,Rain,/m/z\n", "eval")


# --- Selección ----------------------------------------------------------------------------


def _corpus() -> tuple[dict, dict, dict]:
    gt = {"dev": {}, "eval": {}}
    info = {"dev": {}, "eval": {}}
    sizes = {"dev": {}, "eval": {}}
    for i in range(1, 41):
        split = "dev" if i <= 30 else "eval"
        fname = str(i)
        label = "Engine" if i % 2 else "Wind"
        gt[split][fname] = [label] + (["Speech"] if i == 3 else [])
        lic = NC if i == 5 else CC0
        info[split][fname] = _info(lic, uploader=f"u{i % 4}")
        sizes[split][fname] = 100
    return gt, info, sizes


def test_selection_is_deterministic_filtered_capped_and_grouped_by_uploader() -> None:
    gt, info, sizes = _corpus()
    kwargs = {
        "target_labels": ("Engine", "Wind"),
        "per_label": 6,
        "per_uploader_per_label": 2,
        "max_compressed_bytes": 10_000,
        "excluded_ids": {"7"},
        "seed": 1,
    }
    chosen = select_fsd50k(gt, info, sizes, **kwargs)
    assert chosen == select_fsd50k(gt, info, sizes, **kwargs)
    ids = {c["fname"] for c in chosen}
    assert not ids & {"3", "5", "7"}  # voz, licencia NC, excluido (p. ej. ya en ESC-10)
    for label in ("Engine", "Wind"):
        mine = [c for c in chosen if c["target_label"] == label]
        assert len(mine) <= 6
        per_uploader: dict[str, int] = {}
        for c in mine:
            per_uploader[c["uploader"]] = per_uploader.get(c["uploader"], 0) + 1
        assert max(per_uploader.values()) <= 2
    assert all(c["group_id"] == uploader_group("fsd50k", c["uploader"]) for c in chosen)
    assert all(c["license"] == "CC0-1.0" for c in chosen)
    assert chosen != select_fsd50k(gt, info, sizes, **(kwargs | {"seed": 2}))


def test_selection_respects_byte_budget_per_label_and_skips_unsized() -> None:
    gt, info, sizes = _corpus()
    del sizes["dev"]["1"]
    chosen = select_fsd50k(
        gt,
        info,
        sizes,
        target_labels=("Engine", "Wind"),
        per_label=50,
        per_uploader_per_label=50,
        max_compressed_bytes=1_000,
        seed=1,
    )
    for label in ("Engine", "Wind"):
        assert sum(c["compressed_bytes"] for c in chosen if c["target_label"] == label) <= 500
    assert "1" not in {c["fname"] for c in chosen}
    with pytest.raises(ValueError):
        select_fsd50k(
            gt, info, sizes, per_label=0, per_uploader_per_label=1, max_compressed_bytes=1, seed=1
        )


def test_clip_is_assigned_to_first_target_label_only_once() -> None:
    gt = {"dev": {"1": ["Engine", "Wind"]}}
    info = {"dev": {"1": _info()}}
    sizes = {"dev": {"1": 10}}
    chosen = select_fsd50k(
        gt,
        info,
        sizes,
        target_labels=("Engine", "Wind"),
        per_label=5,
        per_uploader_per_label=5,
        max_compressed_bytes=1000,
        seed=0,
    )
    assert [(c["fname"], c["target_label"]) for c in chosen] == [("1", "Engine")]


def test_pins_are_revalidated_against_source_metadata() -> None:
    gt, info, sizes = _corpus()
    chosen = select_fsd50k(
        gt,
        info,
        sizes,
        target_labels=("Engine",),
        per_label=3,
        per_uploader_per_label=3,
        max_compressed_bytes=10_000,
        seed=1,
    )
    assert verify_fsd50k_pins(chosen, gt, info) == []
    first = chosen[0]
    changed_license = {s: {k: dict(v) for k, v in d.items()} for s, d in info.items()}
    changed_license[first["split"]][first["fname"]]["license"] = NC
    assert any("licencia_no_admitida" in e for e in verify_fsd50k_pins(chosen, gt, changed_license))
    swapped = {s: {k: dict(v) for k, v in d.items()} for s, d in info.items()}
    swapped[first["split"]][first["fname"]]["license"] = BY3
    assert any("distinta" in e for e in verify_fsd50k_pins(chosen, gt, swapped))
    relabeled = {s: dict(d) for s, d in gt.items()}
    relabeled[first["split"]][first["fname"]] = ["Engine", "Conversation"]
    assert any("humana" in e for e in verify_fsd50k_pins(chosen, relabeled, info))
    assert any("repetido" in e for e in verify_fsd50k_pins([first, first], gt, info))
    ghost = dict(first, fname="999")
    assert any("no está" in e for e in verify_fsd50k_pins([ghost], gt, info))


# --- ITU ARIS -----------------------------------------------------------------------------


def _aris() -> tuple[dict, dict]:
    segments, assignment = [], {}
    for i in range(1, 7):
        path = f"audio/drone/drone_{i:04d}.wav"
        group = f"drone_interval_{(i - 1) // 3:02d}"
        segments.append({"file": path, "label": "drone", "group": group})
        assignment[path] = "train" if i <= 3 else "test"
    for i in range(1, 5):
        path = f"audio/background/background_{i:04d}.wav"
        segments.append({"file": path, "label": "background", "group": "background_block_00"})
        assignment[path] = "val"
    return {"segments": segments}, {"assignment": assignment}


def test_aris_segments_keep_author_groups_and_split() -> None:
    groups, split = _aris()
    rows = aris_segments(groups, split)
    assert len(rows) == 10
    assert {r["group_id"] for r in rows if r["label"]} == {
        "aris:drone_interval_00",
        "aris:drone_interval_01",
    }
    assert {r["split"] for r in rows if not r["label"]} == {"val"}


def test_aris_group_crossing_splits_fails_closed() -> None:
    groups, split = _aris()
    split["assignment"]["audio/drone/drone_0002.wav"] = "test"
    with pytest.raises(ValueError, match="cruza particiones"):
        aris_segments(groups, split)


def test_aris_label_path_coverage_and_paths_are_checked() -> None:
    groups, split = _aris()
    groups["segments"][0]["label"] = "background"
    with pytest.raises(ValueError, match="no coinciden"):
        aris_segments(groups, split)
    groups, split = _aris()
    del split["assignment"]["audio/drone/drone_0001.wav"]
    with pytest.raises(ValueError, match="mismos segmentos"):
        aris_segments(groups, split)
    groups, split = _aris()
    bad = "audio/drone/../drone_0001.wav"
    groups["segments"][0]["file"] = bad
    split["assignment"][bad] = split["assignment"].pop("audio/drone/drone_0001.wav")
    with pytest.raises(ValueError):
        aris_segments(groups, split)
    groups, split = _aris()
    split["assignment"]["audio/drone/drone_0001.wav"] = "holdout"
    with pytest.raises(ValueError, match="desconocida"):
        aris_segments(groups, split)


def test_sha256sums_parser() -> None:
    a, b = "a" * 64, "b" * 64
    assert parse_sha256sums(f"{a}  audio/x.wav\n{b}  README.md\n") == {
        "audio/x.wav": a,
        "README.md": b,
    }
    with pytest.raises(ValueError):
        parse_sha256sums(f"{a}  x\n{a}  x\n")
    with pytest.raises(ValueError):
        parse_sha256sums("zz  x\n")


def test_module_is_self_contained_for_colab_embedding() -> None:
    tree = ast.parse(Path(sources.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported <= {"collections", "csv", "hashlib", "io", "re"}
    assert "__future__" not in Path(sources.__file__).read_text(encoding="utf-8")

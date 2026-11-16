"""Fuentes de dron adicionales: autorización explícita, selección y grupos (REQ-LEG-009)."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pytest

from acoustic_pilot.extra_sources import (
    EXTRA_SOURCES,
    chunk_starts,
    concat_with_crossfade,
    droneaudioset_selection,
    enabled_extra_sources,
    energy_crop,
    parse_yi_name,
    salford_selection,
    stream_download,
    yi_selection,
)

pytestmark = pytest.mark.req("REQ-LEG-009")
ROOT = Path(__file__).resolve().parents[3]


class _FakeResponse(io.BytesIO):
    def __init__(self, data: bytes, url: str) -> None:
        super().__init__(data)
        self._url = url

    def geturl(self) -> str:
        return self._url


class _FakeOpener:
    def __init__(self, data: bytes, final_url: str) -> None:
        self.data, self.final_url, self.calls = data, final_url, 0

    def open(self, request, timeout=None):
        self.calls += 1
        return _FakeResponse(self.data, self.final_url)


def test_stream_download_verifies_hashes_hosts_and_reuses(tmp_path: Path) -> None:
    data = b"x" * 3000
    md5 = hashlib.md5(data, usedforsecurity=False).hexdigest()
    sha = hashlib.sha256(data).hexdigest()
    hosts = {"zenodo.org"}
    url = "https://zenodo.org/f"
    opener = _FakeOpener(data, url)
    dest = tmp_path / "a.tar"
    assert stream_download(url, hosts, dest, size=3000, md5=md5, opener=opener, chunk=512) == sha
    assert stream_download(url, hosts, dest, size=3000, md5=md5, opener=opener) == sha
    assert opener.calls == 1  # reutilizado sin volver a descargar
    with pytest.raises(ValueError):  # hash distinto: se borra el parcial
        stream_download(url, hosts, tmp_path / "b", size=3000, sha256="0" * 64, opener=opener)
    assert not (tmp_path / "b.part").exists() and not (tmp_path / "b").exists()
    other = _FakeOpener(data, "https://otro.example/f")
    with pytest.raises(ValueError):  # redirección a otro host
        stream_download(url, hosts, tmp_path / "c", size=3000, md5=md5, opener=other)
    with pytest.raises(ValueError):  # host no permitido de entrada
        stream_download("https://otro.example/f", hosts, tmp_path / "d", size=3000, md5=md5)
    with pytest.raises(ValueError):  # tamaño excedido
        stream_download(url, hosts, tmp_path / "e", size=100, md5=md5, opener=opener)
    with pytest.raises(ValueError):  # sin hash de referencia
        stream_download(url, hosts, tmp_path / "f", size=3000, opener=opener)


def test_sources_are_disabled_without_explicit_authorization() -> None:
    assert enabled_extra_sources({}) == []
    assert enabled_extra_sources({s: None for s in EXTRA_SOURCES}) == []
    assert enabled_extra_sources({"salford": "  "}) == []
    assert enabled_extra_sources({"salford": "usuario, 2026-11-17: «sí»"}) == ["salford"]
    with pytest.raises(ValueError):
        enabled_extra_sources({"dads": "sí"})


def test_salford_selection_uses_flight_files_grouped_by_event() -> None:
    manifest = json.loads((ROOT / "ml/datasets/salford-dronenoise/manifest.json").read_text())
    sel = salford_selection(manifest["files"])
    assert len(sel) == 164
    assert all(f["kind"] == "flight" and not f["training_excluded"] for f in sel)
    events = {f["group_id"] for f in sel}
    assert len(events) < len(sel) and all(g.startswith("salford:Ed_") for g in events)


def test_droneaudioset_selection_one_parquet_per_session_without_silence() -> None:
    manifest = json.loads((ROOT / "ml/datasets/droneaudioset-drone-only/manifest.json").read_text())
    sel = droneaudioset_selection(manifest["files"], seed=1)
    assert sel == droneaudioset_selection(manifest["files"], seed=1)
    sessions = {r["group_id"] for f in sel for r in f["rows"]}
    assert len(sessions) == 8
    assert all(r["take"] != "silence" for f in sel for r in f["rows"])
    assert sum(f["bytes"] for f in sel) < 1.5e9  # cabe de sobra en Colab gratuito


def test_yi_names_pairs_and_groups() -> None:
    names = [
        f"drone_A/mic1/A_{d}_{f}_{i}_construction_{j}_10.wav"
        for d in ("F", "CC")
        for f in ("N", "MF1")
        for i in ("3", "4")
        for j in ("1", "2")
    ]
    assert parse_yi_name(names[0])["fault"] == "N"
    assert parse_yi_name("otra_cosa.wav") is None
    pairs = yi_selection(names, n_pairs=10, seed=0)
    assert pairs == yi_selection(names, n_pairs=10, seed=0)
    for p in pairs:
        assert all(parse_yi_name(s)["fault"] == "N" for s in p["segments"])
        assert p["segments"][0] != p["segments"][1]
        assert p["group_id"] in {"yi_kaist:A_3", "yi_kaist:A_4"}
    with pytest.raises(ValueError):
        yi_selection([n for n in names if "_MF1_" in n], n_pairs=1, seed=0)


def test_energy_crop_chunks_and_crossfade() -> None:
    sr = 1000
    x = np.zeros(20 * sr, np.float32)
    x[12 * sr : 13 * sr] = 1.0
    crop = energy_crop(x, sr, seconds=4.0)
    assert len(crop) == 4 * sr and crop.max() == 1.0
    assert chunk_starts(3 * sr, sr, seconds=5.0) == [0]
    starts = chunk_starts(60 * sr, sr, seconds=5.0, max_chunks=6)
    assert len(starts) == 6 and starts[0] == 0 and starts[-1] == 55 * sr
    joined = concat_with_crossfade([np.ones(500), np.ones(500)], sr, fade_s=0.01)
    assert len(joined) == 990 and np.allclose(joined, 1.0)

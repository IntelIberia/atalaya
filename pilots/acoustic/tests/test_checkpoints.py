"""Iteración 5 · puntos de control, descargas concurrentes limitadas y progreso visible."""

from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path

import numpy as np
import pytest

from acoustic_pilot.checkpoints import (
    Progress,
    RateLimiter,
    load_shard,
    run_concurrent,
    save_shard,
    shard_key,
    shard_ranges,
    verified_cached_bytes,
    write_atomic,
)

# --- Caché de ficheros verificados --------------------------------------------------------


def test_verified_cache_returns_bytes_only_when_hash_matches(tmp_path: Path) -> None:
    path = tmp_path / "a.wav"
    assert verified_cached_bytes(path, "0" * 64) is None  # no existe
    write_atomic(path, b"audio")
    good = hashlib.sha256(b"audio").hexdigest()
    assert verified_cached_bytes(path, good) == b"audio"
    path.write_bytes(b"audiX")  # fichero alterado o a medias: se vuelve a descargar
    assert verified_cached_bytes(path, good) is None
    assert not list(tmp_path.glob("*.tmp*"))


# --- Fragmentos de embeddings con hash de entrada ------------------------------------------


def test_shard_ranges_cover_everything_once() -> None:
    assert shard_ranges(10, 4) == [(0, 4), (4, 8), (8, 10)]
    assert shard_ranges(0, 4) == []
    with pytest.raises(ValueError):
        shard_ranges(5, 0)


def test_shard_key_depends_on_content_and_context() -> None:
    items = [("a.wav", "1" * 64), ("b.wav", "2" * 64)]
    k = shard_key(items, "ctx")
    assert k == shard_key(list(items), "ctx")
    assert k != shard_key(items[::-1], "ctx")  # el orden importa: define las filas
    assert k != shard_key([items[0], ("b.wav", "3" * 64)], "ctx")
    assert k != shard_key(items, "otro-modelo")


def test_save_and_load_shard_round_trip_and_reject_stale(tmp_path: Path) -> None:
    path = tmp_path / "s.npz"
    arrays = {"means": np.ones((2, 3), np.float32), "offsets": np.array([0, 1, 2])}
    meta = {"rows": [{"clip": "a"}, {"clip": "b"}]}
    save_shard(path, "k1", arrays, meta)
    loaded = load_shard(path, "k1")
    assert loaded is not None
    got, got_meta = loaded
    np.testing.assert_array_equal(got["means"], arrays["means"])
    assert got_meta == meta
    assert load_shard(path, "k2") is None  # otra entrada => se recalcula
    assert load_shard(tmp_path / "no.npz", "k1") is None
    path.write_bytes(b"truncado")  # desconexión a mitad de escritura
    assert load_shard(path, "k1") is None


# --- Concurrencia con límite de peticiones ------------------------------------------------


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.lock = threading.Lock()

    def time(self) -> float:
        with self.lock:
            return self.now

    def sleep(self, seconds: float) -> None:
        with self.lock:
            self.now += seconds


def test_rate_limiter_spaces_requests() -> None:
    clock = FakeClock()
    limiter = RateLimiter(120, clock=clock.time, sleep=clock.sleep)
    stamps = []
    for _ in range(5):
        limiter.acquire()
        stamps.append(clock.time())
    assert np.diff(stamps) == pytest.approx([0.5] * 4)
    with pytest.raises(ValueError):
        RateLimiter(0)


def test_rate_limiter_is_shared_across_threads() -> None:
    limiter = RateLimiter(6000)  # 10 ms entre peticiones, para TODOS los hilos juntos
    start = time.monotonic()
    run_concurrent(list(range(12)), lambda _: limiter.acquire(), workers=8)
    # 12 peticiones con 8 hilos no pueden ir más rápido que 11 intervalos
    assert time.monotonic() - start >= 0.11 - 1e-3


def test_run_concurrent_keeps_order_reports_progress_and_fails_closed() -> None:
    seen: list[tuple[int, int]] = []
    out = run_concurrent(
        list(range(20)),
        lambda x: x * x,
        workers=8,
        on_done=lambda done, total: seen.append((done, total)),
    )
    assert out == [x * x for x in range(20)]
    assert seen[-1] == (20, 20) and len(seen) == 20

    def boom(x: int) -> int:
        if x == 3:
            raise ValueError("hash distinto")
        return x

    with pytest.raises(ValueError, match="hash distinto"):
        run_concurrent(list(range(6)), boom, workers=3)


def test_progress_prints_by_source(capsys: pytest.CaptureFixture[str]) -> None:
    clock = FakeClock()
    progress = Progress("FSD50K", 10, every=5, clock=clock.time)
    for k in range(1, 11):
        clock.sleep(1.0)
        progress(k, 10)
    lines = capsys.readouterr().out.rstrip().splitlines()
    assert lines == [
        "  FSD50K: 5/10 (50 %) · 1.0 por s",
        "  FSD50K: 10/10 (100 %) · 1.0 por s",
    ]

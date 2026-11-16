"""H2.7: búfer circular en memoria y ventanas de 0,96 s con salto de 0,48 s a 16 kHz."""

from __future__ import annotations

import threading

import numpy as np
import pytest

from live.ring import DEFAULT_CAPACITY, HOP_SAMPLES, WINDOW_SAMPLES, RingBuffer

pytestmark = pytest.mark.req("REQ-LEG-005", "REQ-PRIV-002", "REQ-FUN-027")


def _ramp(start: int, n: int) -> np.ndarray:
    return (np.arange(start, start + n) % 1_000_003).astype(np.float32)


def test_defaults_are_four_seconds_and_yamnet_windows() -> None:
    assert DEFAULT_CAPACITY == 64_000
    assert WINDOW_SAMPLES == 15_360 and HOP_SAMPLES == 7_680
    ring = RingBuffer()
    assert ring.nbytes == 64_000 * 4  # 256 kB preasignados, float32


def test_after_ten_full_turns_only_last_capacity_samples_remain() -> None:
    ring = RingBuffer(capacity=64_000)
    total = 10 * 64_000 + 123
    for start in range(0, total, 1000):
        ring.write(_ramp(start, min(1000, total - start)))
    np.testing.assert_array_equal(ring.latest(64_000), _ramp(total - 64_000, 64_000))
    assert ring.total_written == total


def test_block_longer_than_capacity_keeps_tail() -> None:
    ring = RingBuffer(capacity=100)
    ring.write(_ramp(0, 250))
    np.testing.assert_array_equal(ring.latest(100), _ramp(150, 100))


def test_windows_overlap_fifty_percent_and_are_aligned() -> None:
    ring = RingBuffer(capacity=64_000)
    ring.write(_ramp(0, 15_360 + 3 * 7_680))
    windows = []
    while (w := ring.next_window(15_360, 7_680)) is not None:
        windows.append(w)
    assert [w.start for w in windows] == [0, 7_680, 15_360, 23_040]
    for w in windows:
        assert w.samples.shape == (15_360,) and w.samples.dtype == np.float32
        np.testing.assert_array_equal(w.samples, _ramp(w.start, 15_360))
    np.testing.assert_array_equal(windows[0].samples[7_680:], windows[1].samples[:7_680])
    assert ring.overruns == 0


def test_window_is_a_copy_not_a_view() -> None:
    ring = RingBuffer(capacity=32)
    ring.write(np.ones(16, dtype=np.float32))
    w = ring.next_window(16, 8)
    assert w is not None
    ring.wipe()
    assert w.samples.sum() == 16  # la ventana entregada no depende del búfer


def test_no_window_until_enough_samples() -> None:
    ring = RingBuffer(capacity=64_000)
    ring.write(np.zeros(15_359, dtype=np.float32))
    assert ring.next_window(15_360, 7_680) is None
    ring.write(np.zeros(1, dtype=np.float32))
    assert ring.next_window(15_360, 7_680) is not None


def test_wipe_zeroes_every_sample_and_resets_positions() -> None:
    ring = RingBuffer(capacity=1000)
    ring.write(np.full(1500, 0.7, dtype=np.float32))
    ring.wipe()
    assert not ring.raw_view_for_tests().any()
    assert ring.total_written == 0 and ring.next_window(10, 5) is None


def test_zero_range_clears_only_that_region() -> None:
    ring = RingBuffer(capacity=100)
    ring.write(np.ones(100, dtype=np.float32))
    ring.zero_range(start=40, length=20)
    data = ring.latest(100)
    assert data[40:60].sum() == 0 and data[:40].sum() == 40 and data[60:].sum() == 40


def test_zero_range_ignores_already_overwritten_samples() -> None:
    ring = RingBuffer(capacity=100)
    ring.write(np.ones(300, dtype=np.float32))
    ring.zero_range(start=0, length=210)  # 0–199 ya no están: solo se borra 200–209
    data = ring.latest(100)
    assert data[:10].sum() == 0 and data[10:].sum() == 90


def test_window_larger_than_capacity_is_rejected() -> None:
    ring = RingBuffer(capacity=1000)
    with pytest.raises(ValueError, match="capacidad"):
        ring.next_window(1001, 500)
    with pytest.raises(ValueError):
        ring.next_window(100, 0)
    with pytest.raises(ValueError):
        ring.latest(1001)


def test_invalid_capacity_and_blocks_are_rejected() -> None:
    with pytest.raises(ValueError):
        RingBuffer(capacity=0)
    ring = RingBuffer(capacity=10)
    with pytest.raises(ValueError, match="mono"):
        ring.write(np.zeros((4, 2), dtype=np.float32))


def test_slow_consumer_counts_overruns_and_skips_forward() -> None:
    # Prueba negativa: si el consumidor se retrasa no se encola nada; se cuentan desbordes y la
    # siguiente ventana es la más reciente alineada que sigue en el búfer.
    ring = RingBuffer(capacity=64_000)
    ring.write(_ramp(0, 200_000))
    w = ring.next_window(15_360, 7_680)
    assert w is not None
    assert ring.overruns == 1
    assert w.start % 7_680 == 0
    assert w.start >= 200_000 - 64_000
    np.testing.assert_array_equal(w.samples, _ramp(w.start, 15_360))
    assert ring.nbytes == 64_000 * 4  # la memoria no crece


def test_memory_constant_over_ten_simulated_minutes() -> None:
    ring = RingBuffer()
    block = np.zeros(1600, dtype=np.float32)
    address = ring.raw_view_for_tests().ctypes.data
    windows = 0
    for _ in range(10 * 60 * 10):  # 10 min a 16 kHz en bloques de 0,1 s
        ring.write(block)
        while ring.next_window(15_360, 7_680) is not None:
            windows += 1
    assert ring.nbytes == 64_000 * 4
    assert ring.raw_view_for_tests().ctypes.data == address  # mismo almacenamiento
    assert windows == (10 * 60 * 16_000 - 15_360) // 7_680 + 1
    assert ring.overruns == 0


def test_concurrent_writer_and_reader_are_consistent() -> None:
    ring = RingBuffer(capacity=64_000)
    total = 16_000 * 20
    errors: list[str] = []
    done = threading.Event()
    seen: list[int] = []

    def writer() -> None:
        for start in range(0, total, 800):
            ring.write(_ramp(start, 800))
        done.set()

    def reader() -> None:
        while True:
            finished = done.is_set()
            w = ring.next_window(15_360, 7_680)
            if w is None:
                if finished:
                    return
                continue
            seen.append(w.start)
            if not np.array_equal(w.samples, _ramp(w.start, 15_360)):
                errors.append(f"ventana incoherente en {w.start}")

    t_w, t_r = threading.Thread(target=writer), threading.Thread(target=reader)
    t_r.start()
    t_w.start()
    t_w.join()
    t_r.join(timeout=10)
    assert errors == [] and seen
    assert seen == sorted(seen) and all(s % 7_680 == 0 for s in seen)

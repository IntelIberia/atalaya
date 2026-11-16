"""H2.7: captura solo de entrada, remuestreo por bloques y vigilancia de salud.

Nunca se abre el micrófono real: ``sounddevice`` se sustituye por un módulo falso que registra
qué flujos se crean.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from scipy.signal import resample_poly

from live import capture
from live.capture import CaptureEngine, SoundDeviceSource, StreamResampler
from live.interfaces import Source
from live.synthetic import SyntheticSource, noise, tone

pytestmark = pytest.mark.req("REQ-LEG-005", "REQ-PRIV-002", "REQ-FUN-027")

LIVE_DIR = Path(capture.__file__).resolve().parent


class FakeStream:
    def __init__(self, registry: list[tuple[str, dict[str, Any]]], kind: str, **kwargs: Any):
        registry.append((kind, kwargs))
        self.kwargs = kwargs
        self.started = self.stopped = self.closed = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


class FakeSoundDevice:
    """Imita la API de ``sounddevice`` sin tocar hardware y registra todo lo que se crea."""

    def __init__(self, rate: float = 48_000.0, channels: int = 1) -> None:
        self.created: list[tuple[str, dict[str, Any]]] = []
        self.rate, self.channels = rate, channels
        self.streams: list[FakeStream] = []

    def query_devices(self, device: Any, kind: str) -> dict[str, Any]:
        assert kind == "input"
        return {"default_samplerate": self.rate, "max_input_channels": self.channels}

    def InputStream(self, **kwargs: Any) -> FakeStream:  # noqa: N802 (API de sounddevice)
        stream = FakeStream(self.created, "InputStream", **kwargs)
        self.streams.append(stream)
        return stream

    def _forbidden(self, name: str) -> Any:
        def _raise(*a: Any, **k: Any) -> None:
            self.created.append((name, k))
            raise AssertionError(f"{name} no debe usarse nunca")

        return _raise

    def __getattr__(self, name: str) -> Any:
        if name in {"OutputStream", "Stream", "RawStream", "RawOutputStream", "play", "playrec"}:
            return self._forbidden(name)
        raise AttributeError(name)


@pytest.mark.parametrize("rate", [48_000, 44_100, 32_000])
def test_block_resampling_equals_whole_signal_resample_poly(rate: int) -> None:
    rng = np.random.default_rng(rate)
    x = rng.standard_normal(rate * 2)
    resampler = StreamResampler(rate)
    out, i = [], 0
    while i < x.shape[0]:
        size = int(rng.integers(1, 4000))
        out.append(resampler.process(x[i : i + size]))
        i += size
    y = np.concatenate(out)
    ref = resample_poly(x, 16_000, rate)
    assert ref.shape[0] - y.shape[0] < 40  # solo falta la cola que aún no tiene futuro
    np.testing.assert_allclose(y, ref[: y.shape[0]], atol=1e-5)


def test_resampling_keeps_tone_frequency() -> None:
    rate = 48_000
    t = np.arange(rate * 2) / rate
    y = StreamResampler(rate).process(np.sin(2 * np.pi * 1000.0 * t))
    spectrum = np.abs(np.fft.rfft(y[1000 : 1000 + 16_000]))
    assert abs(np.argmax(spectrum) * 16_000 / 16_000 - 1000.0) <= 1.0


def test_sixteen_khz_is_passthrough() -> None:
    x = np.linspace(-1, 1, 1000)
    np.testing.assert_allclose(StreamResampler(16_000).process(x), x.astype(np.float32))


@pytest.mark.parametrize("rate", [8_000, 0, -1, 44_100.5])
def test_unsupported_rates_are_rejected(rate: Any) -> None:
    with pytest.raises(ValueError):
        StreamResampler(rate)


def test_reset_zeroes_history() -> None:
    r = StreamResampler(48_000)
    r.process(np.ones(1000))
    r.reset()
    assert r.process(np.zeros(3000)).sum() == 0


def test_sounddevice_source_opens_only_a_mono_input_stream() -> None:
    sd = FakeSoundDevice(rate=48_000.0)
    src = SoundDeviceSource(sd_module=sd)
    assert isinstance(src, Source) and src.sample_rate == 48_000
    received: list[np.ndarray] = []
    src.start(received.append)
    assert [kind for kind, _ in sd.created] == ["InputStream"]
    kwargs = sd.created[0][1]
    assert kwargs["channels"] == 1 and kwargs["dtype"] == "float32"
    assert kwargs["samplerate"] == 48_000
    # El callback de PortAudio entrega una copia mono.
    indata = np.full((480, 1), 0.25, dtype=np.float32)
    kwargs["callback"](indata, 480, None, SimpleNamespace(input_overflow=True))
    indata[:] = 0
    assert received[0].shape == (480,) and received[0].sum() == pytest.approx(120.0)
    assert src.input_overflows == 1
    src.stop()
    src.stop()  # idempotente
    assert sd.streams[0].stopped and sd.streams[0].closed


def test_sounddevice_source_rejects_device_without_input() -> None:
    with pytest.raises(ValueError, match="entrada"):
        SoundDeviceSource(sd_module=FakeSoundDevice(channels=0))


def _attribute_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.ImportFrom):
            names |= {a.name for a in node.names}
    return names


def test_live_code_never_references_output_or_duplex_streams() -> None:
    # Prueba negativa estática: ningún módulo de live/ nombra un flujo de salida o dúplex.
    forbidden = {"OutputStream", "Stream", "RawStream", "RawOutputStream", "play", "playrec"}
    for path in sorted(LIVE_DIR.rglob("*.py")):
        hits = _attribute_names(path) & forbidden
        assert not hits, f"{path.name} usa {sorted(hits)}"


def test_engine_at_48k_produces_exact_16k_windows() -> None:
    src = SyntheticSource(48_000, tone(440.0), seed=1)
    engine = CaptureEngine(src)
    engine.start()
    src.pump(3.0)
    windows = []
    while (w := engine.next_window()) is not None:
        windows.append(w)
    assert len(windows) >= 4
    assert all(w.samples.shape == (15_360,) for w in windows)
    assert [w.start for w in windows] == [i * 7_680 for i in range(len(windows))]


def test_engine_stop_wipes_buffer_and_stops_source() -> None:
    src = SyntheticSource(16_000, noise(0.2), seed=2)
    engine = CaptureEngine(src)
    engine.start()
    src.pump(2.0)
    assert engine.ring.raw_view_for_tests().any()
    engine.stop()
    assert src.stopped
    assert not engine.ring.raw_view_for_tests().any()
    assert engine.ring.total_written == 0


def test_engine_zero_window_clears_that_region() -> None:
    src = SyntheticSource(16_000, noise(0.2), seed=3)
    engine = CaptureEngine(src)
    engine.start()
    src.pump(1.0)
    w = engine.next_window()
    assert w is not None
    engine.zero_window(w)
    assert not engine.ring.latest(16_000)[: w.samples.shape[0]].any()


class Clock:
    def __init__(self) -> None:
        self.t = 100.0

    def __call__(self) -> float:
        return self.t


def test_health_degrades_after_two_seconds_without_input() -> None:
    clock = Clock()
    src = SyntheticSource(16_000, noise(0.05), seed=4)
    engine = CaptureEngine(src, clock=clock)
    engine.start()
    src.pump(0.5)
    assert not engine.health().degraded
    clock.t += 2.5
    health = engine.health()
    assert health.degraded and "sin_entrada" in health.reasons


def test_health_degrades_if_nothing_ever_arrives() -> None:
    clock = Clock()
    engine = CaptureEngine(SyntheticSource(16_000), clock=clock)
    engine.start()
    clock.t += 2.1
    assert engine.health().reasons == ("sin_entrada",)


def test_health_degrades_on_saturation_above_one_percent() -> None:
    clock = Clock()
    src = SyntheticSource(16_000, tone(100.0, level=5.0), seed=5)  # recortada a ±1
    engine = CaptureEngine(src, clock=clock)
    engine.start()
    src.pump(0.5)
    assert "saturacion" in engine.health().reasons


def test_health_degrades_on_overruns() -> None:
    clock = Clock()
    src = SyntheticSource(16_000, noise(0.05), seed=6)
    engine = CaptureEngine(src, clock=clock)
    engine.start()
    src.pump(10.0)  # nadie consume: el búfer de 4 s se sobrescribe
    assert engine.next_window() is not None
    assert "desbordes" in engine.health().reasons
    clock.t += 3.0
    src.pump(0.1)
    assert "desbordes" not in engine.health().reasons


def test_static_stream_check_catches_an_injected_output_stream(tmp_path: Path) -> None:
    # Control de la prueba: el análisis detecta un flujo de salida inyectado.
    bad = tmp_path / "bad.py"
    bad.write_text("import sounddevice as sd\ns = sd.OutputStream(samplerate=16000)\n")
    assert "OutputStream" in _attribute_names(bad)

"""H2.7: captura en memoria (solo entrada) → remuestreo a 16 kHz → búfer circular.

- ``SoundDeviceSource`` abre **únicamente** ``sounddevice.InputStream`` (mono, ``float32``, a la
  frecuencia nativa del dispositivo). No existe ningún camino de salida de sonido: ni
  ``OutputStream`` ni flujos dúplex (lo comprueba ``tests/live/test_capture.py``). El módulo
  ``sounddevice`` se inyecta para que los tests nunca abran el micrófono real.
- ``StreamResampler`` remuestrea por bloques con el mismo filtro que ``scipy.signal.resample_poly``
  (Kaiser β = 5, semiancho 10·max(up, down)) y da exactamente las mismas muestras que el remuestreo
  de la señal completa, sin cortes entre bloques.
- ``CaptureEngine`` une origen, remuestreo y búfer, y vigila la salud: sin entrada > 2 s,
  desbordes o saturación > 1 % de muestras → ``degraded``. ``stop()`` borra el búfer.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.signal import firwin, upfirdn

from live.interfaces import BlockCallback, Source
from live.ring import SAMPLE_RATE, WINDOW_SAMPLES, RingBuffer, Window

NO_INPUT_DEGRADED_S = 2.0
SATURATION_LEVEL = 0.999
SATURATION_MAX_FRACTION = 0.01
SATURATION_WINDOW_S = 2.0


class StreamResampler:
    """Remuestreo racional por bloques equivalente a ``resample_poly`` sobre la señal entera."""

    def __init__(self, in_rate: int, out_rate: int = SAMPLE_RATE) -> None:
        if not isinstance(in_rate, int) or isinstance(in_rate, bool) or in_rate < out_rate:
            raise ValueError(f"frecuencia de entrada no admitida: {in_rate!r} (mín. {out_rate})")
        g = math.gcd(in_rate, out_rate)
        self.in_rate, self.out_rate = in_rate, out_rate
        self._up, self._down = out_rate // g, in_rate // g
        self._passthrough = self._up == self._down == 1
        max_rate = max(self._up, self._down)
        self._half = 10 * max_rate
        self._h = (
            np.ones(1)
            if self._passthrough
            else firwin(2 * self._half + 1, 1.0 / max_rate, window=("kaiser", 5.0)) * self._up
        )
        self.reset()

    def reset(self) -> None:
        """Olvida (y pone a cero) la historia de entrada."""
        if hasattr(self, "_x"):
            self._x.fill(0.0)
        self._x = np.zeros(0, dtype=np.float64)
        self._x0 = 0  # índice absoluto de self._x[0]
        self._n_in = 0
        self._j = 0  # siguiente índice de salida

    def _first_input(self, j: int) -> int:
        a = j * self._down - self._half
        return max(0, -(-a // self._up))

    def process(self, block: NDArray[np.floating]) -> NDArray[np.float32]:
        arr = np.asarray(block, dtype=np.float64).reshape(-1)
        if self._passthrough:
            return arr.astype(np.float32)
        self._x = np.concatenate([self._x, arr])
        self._n_in += arr.shape[0]
        up, down, d = self._up, self._down, self._half
        num = self._n_in * up - d
        j_end = -(-num // down) if num > 0 else 0
        if j_end <= self._j:
            return np.zeros(0, dtype=np.float32)
        s = self._first_input(self._j)
        segment = self._x[s - self._x0 :]
        pad = (s * up - d) % down
        h = np.concatenate([np.zeros(pad), self._h])
        z = upfirdn(h, segment, up, down)
        m0 = self._j + (pad + d - s * up) // down
        count = j_end - self._j
        out = z[m0 : m0 + count]
        if out.shape[0] != count:  # defensa: nunca debería ocurrir
            raise RuntimeError("remuestreo por bloques inconsistente")
        self._j = j_end
        keep_from = self._first_input(self._j)
        if keep_from > self._x0:
            self._x[: keep_from - self._x0] = 0.0
            self._x = self._x[keep_from - self._x0 :].copy()
            self._x0 = keep_from
        return out.astype(np.float32)


class SoundDeviceSource:
    """``Source`` sobre ``sounddevice.InputStream``. Solo entrada; nunca escribe en disco."""

    def __init__(
        self,
        *,
        device: int | str | None = None,
        blocksize: int = 0,
        sd_module: Any = None,
    ) -> None:
        if sd_module is None:
            import sounddevice as sd_module  # importación diferida: extra live

        self._sd = sd_module
        self._device = device
        self._blocksize = blocksize
        info = sd_module.query_devices(device, "input")
        if int(info["max_input_channels"]) < 1:
            raise ValueError("el dispositivo no tiene entrada")
        rate = float(info["default_samplerate"])
        if not rate.is_integer():
            raise ValueError(f"frecuencia nativa no entera: {rate}")
        self.sample_rate = int(rate)
        self._stream: Any = None
        self.input_overflows = 0

    def start(self, on_block: BlockCallback) -> None:
        if self._stream is not None:
            raise RuntimeError("la captura ya está en marcha")

        def _callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
            if status and getattr(status, "input_overflow", False):
                self.input_overflows += 1
            on_block(np.array(indata[:, 0], dtype=np.float32, copy=True))

        self._stream = self._sd.InputStream(
            samplerate=self.sample_rate,
            device=self._device,
            channels=1,
            dtype="float32",
            blocksize=self._blocksize,
            callback=_callback,
        )
        self._stream.start()

    def stop(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
            finally:
                stream.close()


@dataclass(frozen=True)
class Health:
    seconds_since_input: float | None
    overruns: int
    input_overflows: int
    saturation_fraction: float
    degraded: bool
    reasons: tuple[str, ...]


class CaptureEngine:
    """Origen → remuestreo a 16 kHz → búfer circular, con vigilancia de salud."""

    def __init__(
        self,
        source: Source,
        *,
        ring: RingBuffer | None = None,
        window_samples: int = WINDOW_SAMPLES,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._source = source
        self._ring = ring or RingBuffer()
        self._window = window_samples
        self._hop = window_samples // 2
        self._resampler = StreamResampler(int(source.sample_rate))
        self._clock = clock
        self._lock = threading.Lock()
        self._last_input: float | None = None
        self._started_at: float | None = None
        self._sat: deque[tuple[float, int, int]] = deque()
        self._overruns_seen = 0
        self._overflows_seen = 0
        self._last_overrun: float | None = None

    @property
    def ring(self) -> RingBuffer:
        return self._ring

    def _on_block(self, block: NDArray[np.float32]) -> None:
        resampled = self._resampler.process(block)
        now = self._clock()
        n_sat = int(np.count_nonzero(np.abs(block) >= SATURATION_LEVEL))
        with self._lock:
            self._last_input = now
            self._sat.append((now, int(block.shape[0]), n_sat))
            while self._sat and now - self._sat[0][0] > SATURATION_WINDOW_S:
                self._sat.popleft()
        self._ring.write(resampled)

    def start(self) -> None:
        self._started_at = self._clock()
        self._source.start(self._on_block)

    def stop(self) -> None:
        """Cierra el origen y borra el búfer y la historia del remuestreo (también ante señales)."""
        try:
            self._source.stop()
        finally:
            self._ring.wipe()
            self._resampler.reset()
            with self._lock:
                self._sat.clear()

    def next_window(self) -> Window | None:
        return self._ring.next_window(self._window, self._hop)

    def zero_window(self, window: Window) -> None:
        self._ring.zero_range(window.start, window.samples.shape[0])

    def health(self) -> Health:
        now = self._clock()
        with self._lock:
            last = self._last_input
            total = sum(n for _, n, _ in self._sat)
            sat = sum(s for _, _, s in self._sat)
        reasons: list[str] = []
        ref = last if last is not None else self._started_at
        since = None if last is None else now - last
        if ref is None or now - ref > NO_INPUT_DEGRADED_S:
            reasons.append("sin_entrada")
        overruns = self._ring.overruns
        overflows = int(getattr(self._source, "input_overflows", 0))
        if overruns > self._overruns_seen or overflows > self._overflows_seen:
            self._overruns_seen, self._overflows_seen = overruns, overflows
            self._last_overrun = now
        if self._last_overrun is not None and now - self._last_overrun <= NO_INPUT_DEGRADED_S:
            reasons.append("desbordes")
        fraction = sat / total if total else 0.0
        if fraction > SATURATION_MAX_FRACTION:
            reasons.append("saturacion")
        return Health(
            seconds_since_input=since,
            overruns=overruns,
            input_overflows=overflows,
            saturation_fraction=fraction,
            degraded=bool(reasons),
            reasons=tuple(reasons),
        )

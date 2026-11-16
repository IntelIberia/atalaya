"""Origen sintético (``Source``) para tests y para ver la página sin micrófono.

Genera señales deterministas con semilla (silencio, ruido, tono, peine armónico) y las entrega
por bloques cuando se llama a ``pump``: sin hilos, sin dispositivo y sin ficheros.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

from live.interfaces import BlockCallback

Generator = Callable[[NDArray[np.float64], np.random.Generator], NDArray[np.float64]]


def silence(t: NDArray[np.float64], rng: np.random.Generator) -> NDArray[np.float64]:
    return np.zeros_like(t)


def noise(level: float = 0.05) -> Generator:
    def _gen(t: NDArray[np.float64], rng: np.random.Generator) -> NDArray[np.float64]:
        return level * rng.standard_normal(t.shape[0])

    return _gen


def tone(freq_hz: float, level: float = 0.3) -> Generator:
    def _gen(t: NDArray[np.float64], rng: np.random.Generator) -> NDArray[np.float64]:
        return level * np.sin(2 * np.pi * freq_hz * t)

    return _gen


def harmonic_comb(f0_hz: float = 180.0, harmonics: int = 8, level: float = 0.3) -> Generator:
    """Peine armónico (tipo paso de palas) más un poco de ruido."""

    def _gen(t: NDArray[np.float64], rng: np.random.Generator) -> NDArray[np.float64]:
        sig = sum(np.sin(2 * np.pi * f0_hz * k * t) / k for k in range(1, harmonics + 1))
        return level * sig / 2 + 0.01 * rng.standard_normal(t.shape[0])

    return _gen


class SyntheticSource:
    def __init__(
        self,
        sample_rate: int = 16_000,
        generator: Generator = silence,
        *,
        seed: int = 0,
        block_seconds: float = 0.1,
    ) -> None:
        self.sample_rate = sample_rate
        self.generator = generator
        self.input_overflows = 0
        self._rng = np.random.default_rng(seed)
        self._block = max(1, round(block_seconds * sample_rate))
        self._callback: BlockCallback | None = None
        self._n = 0
        self.started = False
        self.stopped = False

    def start(self, on_block: BlockCallback) -> None:
        self._callback = on_block
        self.started = True
        self.stopped = False

    def stop(self) -> None:
        self._callback = None
        self.stopped = True

    def pump(self, seconds: float) -> int:
        """Entrega ``seconds`` de señal en bloques; devuelve las muestras entregadas."""
        if self._callback is None:
            return 0
        total = round(seconds * self.sample_rate)
        sent = 0
        while sent < total and self._callback is not None:
            n = min(self._block, total - sent)
            t = (self._n + np.arange(n)) / self.sample_rate
            block = np.clip(self.generator(t, self._rng), -1.0, 1.0).astype(np.float32)
            self._callback(block)
            self._n += n
            sent += n
        return sent

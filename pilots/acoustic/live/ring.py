"""H2.7: búfer circular ``float32`` preasignado, solo en memoria.

- Capacidad fija (por defecto 4 s a 16 kHz = 64 000 muestras, 256 kB): la escritura sobrescribe
  lo más antiguo y la memoria no crece nunca.
- Ventanas de 0,96 s con salto de 0,48 s alineadas al inicio de la sesión; cada ventana es una
  **copia** que el consumidor descarta tras inferir.
- Si el consumidor se retrasa y lo pendiente ya se ha sobrescrito, se cuenta un desborde y se salta
  a la ventana alineada más reciente (nunca se encolan muestras sin límite).
- ``wipe()`` pone a cero todo el búfer; ``zero_range()`` borra una región (puerta de voz, H2.9).

Seguro entre el hilo de captura (escribe) y el de inferencia (lee).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

SAMPLE_RATE = 16_000
DEFAULT_CAPACITY = 4 * SAMPLE_RATE
# 0,96 s y 0,48 s a 16 kHz. Si el ONNX real de YAMNet exige 15 600 muestras, el artefacto lo fija
# (``window_samples``) y el cargador comprueba que da exactamente un parche (H2.6).
WINDOW_SAMPLES = 15_360
HOP_SAMPLES = WINDOW_SAMPLES // 2


@dataclass(frozen=True)
class Window:
    start: int  # índice absoluto de la primera muestra desde el inicio de la sesión
    samples: NDArray[np.float32]


class RingBuffer:
    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        if capacity <= 0:
            raise ValueError("la capacidad debe ser positiva")
        self._capacity = int(capacity)
        self._buf = np.zeros(self._capacity, dtype=np.float32)
        self._lock = threading.Lock()
        self._total = 0
        self._next_start = 0
        self._overruns = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def nbytes(self) -> int:
        return int(self._buf.nbytes)

    @property
    def total_written(self) -> int:
        return self._total

    @property
    def overruns(self) -> int:
        return self._overruns

    def write(self, block: NDArray[np.floating]) -> None:
        arr = np.asarray(block, dtype=np.float32)
        if arr.ndim != 1:
            raise ValueError(f"el bloque debe ser mono (1 dimensión), no {arr.shape}")
        n = arr.shape[0]
        if n == 0:
            return
        with self._lock:
            cap = self._capacity
            start = self._total
            if n > cap:
                arr = arr[n - cap :]
                start += n - cap
            self._put(start, arr)
            self._total += n

    def _put(self, abs_start: int, arr: NDArray[np.float32]) -> None:
        cap = self._capacity
        idx = abs_start % cap
        first = min(arr.shape[0], cap - idx)
        self._buf[idx : idx + first] = arr[:first]
        if first < arr.shape[0]:
            self._buf[: arr.shape[0] - first] = arr[first:]

    def _get(self, abs_start: int, length: int) -> NDArray[np.float32]:
        cap = self._capacity
        idx = abs_start % cap
        first = min(length, cap - idx)
        out = np.empty(length, dtype=np.float32)
        out[:first] = self._buf[idx : idx + first]
        if first < length:
            out[first:] = self._buf[: length - first]
        return out

    def latest(self, length: int) -> NDArray[np.float32]:
        """Copia de las últimas ``length`` muestras."""
        with self._lock:
            if length <= 0 or length > min(self._capacity, self._total):
                raise ValueError("longitud fuera de lo disponible en el búfer")
            return self._get(self._total - length, length)

    def next_window(self, window: int, hop: int) -> Window | None:
        """Siguiente ventana alineada a ``hop`` o ``None`` si aún no hay muestras suficientes."""
        if window <= 0 or hop <= 0 or hop > window:
            raise ValueError("ventana y salto deben ser positivos y salto ≤ ventana")
        if window > self._capacity:
            raise ValueError(f"ventana de {window} muestras mayor que la capacidad")
        with self._lock:
            oldest = max(0, self._total - self._capacity)
            if self._next_start < oldest:
                self._overruns += 1
                newest = ((self._total - window) // hop) * hop
                self._next_start = max(newest, -(-oldest // hop) * hop)
            if self._next_start + window > self._total:
                return None
            start = self._next_start
            samples = self._get(start, window)
            self._next_start += hop
            return Window(start=start, samples=samples)

    def zero_range(self, start: int, length: int) -> None:
        """Pone a cero ``[start, start + length)`` (índices absolutos) si sigue en el búfer."""
        with self._lock:
            lo = max(start, self._total - self._capacity, 0)
            hi = min(start + length, self._total)
            if hi > lo:
                self._put(lo, np.zeros(hi - lo, dtype=np.float32))

    def wipe(self) -> None:
        """Borra todas las muestras (a cero) y reinicia las posiciones."""
        with self._lock:
            self._buf.fill(0.0)
            self._total = 0
            self._next_start = 0
            self._overruns = 0

    def raw_view_for_tests(self) -> NDArray[np.float32]:
        """Vista de solo lectura del almacenamiento interno (para comprobar el borrado)."""
        view = self._buf.view()
        view.flags.writeable = False
        return view

"""Subsemillas por componente (T1.10, REQ-FUN-003).

Cada componente del simulador tiene su propio `random.Random`, sembrado con
`sha256("atalaya-sim-v1" ‖ 0 ‖ semilla_global ‖ 0 ‖ nombre)` (8 primeros bytes, big-endian).
Así el orden en que los componentes consumen números no afecta a los demás, y nada depende de
`hash()` (aleatorizado por `PYTHONHASHSEED`) ni del `random` global (sembrado por el sistema).
"""

from __future__ import annotations

import hashlib
from random import Random

_DOMAIN = b"atalaya-sim-v1"
MAX_SEED = 2**64 - 1


def check_seed(seed: object) -> int:
    """Devuelve la semilla si es un entero en [0, 2⁶⁴); si no, `ValueError`."""
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= MAX_SEED:
        raise ValueError(f"semilla inválida: {seed!r} (entero en [0, 2^64))")
    return seed


def derive_seed(seed: int, component: str) -> int:
    """Subsemilla determinista de `component` a partir de la semilla global."""
    check_seed(seed)
    if not isinstance(component, str) or not component:
        raise ValueError("el componente necesita un nombre no vacío")
    material = _DOMAIN + b"\x00" + str(seed).encode() + b"\x00" + component.encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


class RngRegistry:
    """Un `random.Random` por componente, creado bajo demanda y reutilizado."""

    def __init__(self, seed: int) -> None:
        self.seed = check_seed(seed)
        self._streams: dict[str, Random] = {}

    def get(self, component: str) -> Random:
        stream = self._streams.get(component)
        if stream is None:
            stream = Random(derive_seed(self.seed, component))  # noqa: S311 (simulación, no cripto)
            self._streams[component] = stream
        return stream

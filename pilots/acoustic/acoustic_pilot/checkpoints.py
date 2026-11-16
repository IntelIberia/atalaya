# Puntos de control y descargas concurrentes (iteración 5). En Colab sin Drive todo vive en
# /content: sobrevive a un reinicio del kernel o a una reconexión a la MISMA máquina, no a que
# Colab recicle la máquina virtual. Ficheros verificados por SHA-256 antes de reutilizarse,
# fragmentos .npz con hash de entrada y escritura atómica, peticiones concurrentes con un límite
# global por minuto (Zenodo admite ~133) y progreso visible por fuente.
# Autocontenido (stdlib y numpy): build_colab.py lo incrusta tal cual en el cuaderno.
import hashlib
import io
import json
import os
import threading
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np


def write_atomic(path: Path, data: bytes) -> None:
    """Escribe en un temporal y renombra: una desconexión nunca deja un fichero a medias."""
    path = Path(path)
    tmp = path.with_name(f"{path.name}.tmp{os.getpid()}-{threading.get_ident()}")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def verified_cached_bytes(path: Path, sha256: str) -> bytes | None:
    """Contenido del fichero en caché solo si su SHA-256 coincide; si no, None (se descarga)."""
    path = Path(path)
    if not path.is_file():
        return None
    data = path.read_bytes()
    return data if hashlib.sha256(data).hexdigest() == sha256 else None


def shard_ranges(n: int, size: int) -> list[tuple[int, int]]:
    if size <= 0:
        raise ValueError("tamaño de fragmento no válido")
    return [(a, min(a + size, n)) for a in range(0, n, size)]


def shard_key(items: Sequence[tuple[str, str]], context: str) -> str:
    """Hash de entrada de un fragmento: (clip, sha256) en orden + contexto (modelo, código)."""
    h = hashlib.sha256(context.encode())
    for clip, digest in items:
        h.update(f"\n{clip}\t{digest}".encode())
    return h.hexdigest()


def save_shard(path: Path, key: str, arrays: dict, meta: dict) -> None:
    buffer = io.BytesIO()
    np.savez_compressed(
        buffer, **arrays, _key=np.array(key), _meta=np.array(json.dumps(meta, ensure_ascii=False))
    )
    write_atomic(Path(path), buffer.getvalue())


def load_shard(path: Path, key: str) -> tuple[dict, dict] | None:
    """(arrays, meta) si el fragmento existe, se lee entero y su hash de entrada coincide."""
    path = Path(path)
    if not path.is_file():
        return None
    try:
        with np.load(path, allow_pickle=False) as z:
            if str(z["_key"]) != key:
                return None
            arrays = {k: z[k] for k in z.files if k not in ("_key", "_meta")}
            return arrays, json.loads(str(z["_meta"]))
    except Exception:  # fichero truncado o corrupto: se recalcula, nunca se usa
        return None


class RateLimiter:
    """Límite global de peticiones por minuto compartido entre hilos (espaciado uniforme)."""

    def __init__(self, per_minute: float, *, clock=time.monotonic, sleep=time.sleep) -> None:  # type: ignore[no-untyped-def]
        if per_minute <= 0:
            raise ValueError("per_minute debe ser positivo")
        self.interval = 60.0 / per_minute
        self.clock, self.sleep = clock, sleep
        self.lock = threading.Lock()
        self.next_slot: float | None = None

    def acquire(self) -> None:
        with self.lock:
            now = self.clock()
            slot = now if self.next_slot is None else max(now, self.next_slot)
            self.next_slot = slot + self.interval
        if slot > now:
            self.sleep(slot - now)


class Progress:
    """Imprime «fuente: hechos/total (%) · velocidad» cada `every` elementos y al final."""

    def __init__(self, label: str, total: int, *, every: int = 50, clock=time.monotonic) -> None:  # type: ignore[no-untyped-def]
        self.label, self.total, self.every, self.clock = label, total, max(1, every), clock
        self.start = clock()

    def __call__(self, done: int, total: int) -> None:
        if done % self.every == 0 or done == total:
            rate = done / max(self.clock() - self.start, 1e-9)
            share = 100 * done // max(total, 1)
            print(f"  {self.label}: {done}/{total} ({share} %) · {rate:.1f} por s")


def run_concurrent(
    items: Sequence,
    fn: Callable,
    *,
    workers: int = 8,
    on_done: Callable[[int, int], None] | None = None,
) -> list:
    """Aplica fn a cada elemento con un pool de hilos; resultados en el orden de entrada. Si
    alguno falla (p. ej. hash distinto), se cancela lo pendiente y se relanza el error."""
    results: list = [None] * len(items)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fn, item): k for k, item in enumerate(items)}
        try:
            for done, future in enumerate(as_completed(futures), 1):
                results[futures[future]] = future.result()
                if on_done:
                    on_done(done, len(items))
        except BaseException:
            for f in futures:
                f.cancel()
            raise
    return results

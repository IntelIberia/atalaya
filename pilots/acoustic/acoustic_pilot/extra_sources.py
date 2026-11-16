# Fuentes de DRON adicionales para la iteración 6 (Salford DroneNoise CC BY 4.0, DroneAudioSet
# solo-dron MIT, Yi-KAIST CC BY 4.0): selección determinista, agrupación sin fugas y recortes.
# Sus manifiestos siguen con intake_approved=false: el cuaderno solo las usa si build_colab.py
# lleva una autorización explícita del usuario (texto de DECISIONES-USUARIO.md) para cada una.
# Autocontenido (numpy, stdlib) salvo la importación relativa de remote (en el cuaderno ya está
# definida y build_colab.py la quita).
import hashlib
import os
import re
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np

from .remote import check_url, make_opener

EXTRA_SOURCES = ("salford", "droneaudioset", "yi_kaist")
EXTRA_CROP_SECONDS = 8.0  # Salford: tramo de más energía (paso del dron) de cada sobrevuelo
EXTRA_CHUNK_SECONDS = 5.0  # DroneAudioSet: tomas largas en trozos de 5 s
EXTRA_MAX_CHUNKS = 6
YI_NAME = re.compile(
    r"(?P<model>[ABC])_(?P<direction>CC|[FBRLC])_(?P<fault>N|MF[1-4]|PC[1-4])_(?P<drone>[^_]+)_"
    r"(?P<background>[^_]+)_(?P<bg_index>[^_]+)_(?P<snr>[^_.]+)"
)


def enabled_extra_sources(authorizations: Mapping[str, str | None]) -> list[str]:
    """Fuentes extra con autorización explícita (texto no vacío); fallo cerrado ante nombres
    desconocidos."""
    unknown = set(authorizations) - set(EXTRA_SOURCES)
    if unknown:
        raise ValueError(f"fuentes extra desconocidas: {sorted(unknown)}")
    return [s for s in EXTRA_SOURCES if (authorizations.get(s) or "").strip()]


def stream_download(
    url: str,
    hosts: set[str] | frozenset[str],
    dest: Path,
    *,
    size: int,
    md5: str | None = None,
    sha256: str | None = None,
    opener=None,
    chunk: int = 1 << 20,
) -> str:
    """Descarga a disco por trozos (ficheros de GB sin llenar la RAM) con host comprobado también
    tras redirecciones, tamaño exacto y MD5 y/o SHA-256; reutiliza un fichero ya verificado.
    Escritura atómica (.part + rename). Devuelve el SHA-256."""
    if md5 is None and sha256 is None:
        raise ValueError("hace falta al menos un hash de referencia")
    dest = Path(dest)

    def digests(path: Path) -> tuple[str, str]:
        h_md5, h_sha = hashlib.md5(usedforsecurity=False), hashlib.sha256()
        with path.open("rb") as fh:
            for block in iter(lambda: fh.read(chunk), b""):
                h_md5.update(block)
                h_sha.update(block)
        return h_md5.hexdigest(), h_sha.hexdigest()

    def ok(path: Path) -> str | None:
        if not path.is_file() or path.stat().st_size != size:
            return None
        got_md5, got_sha = digests(path)
        if (md5 is None or got_md5 == md5) and (sha256 is None or got_sha == sha256):
            return got_sha
        return None

    cached = ok(dest)
    if cached:
        return cached
    check_url(url, hosts)
    client = opener or make_opener(hosts)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    total = 0
    request = urllib.request.Request(url, headers={"User-Agent": "Atalaya-Colab-Pilot/1"})
    with client.open(request, timeout=300) as response, tmp.open("wb") as out:
        check_url(response.geturl(), hosts)
        for block in iter(lambda: response.read(chunk), b""):
            total += len(block)
            if total > size:
                raise ValueError(f"tamaño excedido: {dest.name}")
            out.write(block)
    got = ok(tmp)
    if total != size or got is None:
        tmp.unlink(missing_ok=True)
        raise ValueError(f"verificación fallida: {dest.name} ({total} B)")
    os.replace(tmp, dest)
    return got


def salford_selection(files: Sequence[dict]) -> list[dict]:
    """Solo grabaciones de vuelo no excluidas; grupo = evento (los 9 micrófonos de un evento
    graban a la vez y nunca se separan)."""
    out = []
    for f in files:
        if f.get("kind") != "flight" or f.get("training_excluded") or f.get("label") != 1:
            continue
        out.append({**f, "group_id": "salford:" + f["event_id"]})
    return sorted(out, key=lambda f: f["path"])


def energy_crop(signal: np.ndarray, sr: int, seconds: float = EXTRA_CROP_SECONDS) -> np.ndarray:
    """Tramo de `seconds` centrado en el segundo de más energía (el paso del dron)."""
    x = np.asarray(signal, dtype=np.float32)
    n = int(seconds * sr)
    if len(x) <= n:
        return x
    hop = max(1, sr // 4)
    energy = np.array(
        [np.mean(x[i : i + sr].astype(np.float64) ** 2) for i in range(0, len(x) - sr + 1, hop)]
    )
    centre = int(np.argmax(energy)) * hop + sr // 2
    start = min(max(0, centre - n // 2), len(x) - n)
    return x[start : start + n]


def chunk_starts(
    n_samples: int,
    sr: int,
    *,
    seconds: float = EXTRA_CHUNK_SECONDS,
    max_chunks: int = EXTRA_MAX_CHUNKS,
) -> list[int]:
    """Inicios equiespaciados y deterministas de hasta max_chunks trozos sin solape."""
    size = int(seconds * sr)
    if n_samples < size:
        return [0] if n_samples > 0 else []
    fits = n_samples // size
    count = min(fits, max_chunks)
    return [int(v) for v in np.linspace(0, n_samples - size, count).round()]


def droneaudioset_selection(files: Sequence[dict], *, seed: int) -> list[dict]:
    """Un parquet por sesión (dron x distancia x acelerador), elegido con semilla; filas sin las
    tomas «silence» (etiqueta pendiente de escucha). Grupo = sesión."""
    rng = np.random.default_rng(seed)
    by_session: dict[str, list[dict]] = {}
    for f in files:
        sessions = sorted({r["group_id"] for r in f["rows"]})
        for s in sessions:
            by_session.setdefault(s, []).append(f)
    chosen: dict[str, dict] = {}
    for session in sorted(by_session):
        candidates = sorted(by_session[session], key=lambda f: f["path"])
        pick = candidates[int(rng.integers(len(candidates)))]
        chosen[pick["path"]] = pick
    out = []
    for path in sorted(chosen):
        f = chosen[path]
        rows = [
            {**r, "group_id": "droneaudioset:" + r["group_id"]}
            for r in f["rows"]
            if r["take"] != "silence" and r["label_status"] == "drone_only_upstream"
        ]
        if rows:
            out.append({**f, "rows": rows})
    return out


def parse_yi_name(name: str) -> dict | None:
    m = YI_NAME.match(name.rsplit("/", 1)[-1])
    return m.groupdict() if m else None


def yi_selection(names: Sequence[str], *, n_pairs: int, seed: int) -> list[dict]:
    """Pares de segmentos de 0,5 s en estado normal (fallo N) del mismo grupo (modelo, índice de
    grabación del dron, fondo), concatenados después en 1 s; grupo = modelo + índice del dron
    (el reparto de los autores es por segmento y tiene fugas)."""
    cells: dict[tuple, list[str]] = {}
    for name in sorted(names):
        meta = parse_yi_name(name)
        if meta is None or meta["fault"] != "N" or not name.lower().endswith(".wav"):
            continue
        cells.setdefault((meta["model"], meta["drone"], meta["background"]), []).append(name)
    usable = {k: v for k, v in cells.items() if len(v) >= 2}
    if not usable:
        raise ValueError("no hay segmentos normales emparejables")
    rng = np.random.default_rng(seed)
    keys = sorted(usable)
    out = []
    for k in range(n_pairs):
        key = keys[int(rng.integers(len(keys)))]
        a, b = rng.choice(len(usable[key]), size=2, replace=False)
        out.append(
            {
                "id": f"yi{k:05d}",
                "segments": [usable[key][int(a)], usable[key][int(b)]],
                "group_id": f"yi_kaist:{key[0]}_{key[1]}",
                "synthetic_concat": True,
            }
        )
    return out


def concat_with_crossfade(parts: Sequence[np.ndarray], sr: int, fade_s: float = 0.01) -> np.ndarray:
    """Concatena con fundido cruzado lineal (evita el clic de la unión)."""
    fade = int(fade_s * sr)
    out = np.asarray(parts[0], dtype=np.float64)
    for p in parts[1:]:
        q = np.asarray(p, dtype=np.float64)
        f = min(fade, len(out), len(q))
        ramp = np.linspace(0, 1, f) if f else np.zeros(0)
        mixed = out[len(out) - f :] * (1 - ramp) + q[:f] * ramp
        out = np.concatenate([out[: len(out) - f], mixed, q[f:]])
    return out.astype(np.float32)

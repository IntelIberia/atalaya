"""Descarga verificada de DroneAudioSet, SOLO el subconjunto drone-only (MIT), para Colab.

Preflight de intake: comprueba en la revisión fijada de Hugging Face que el metadato de licencia
sigue siendo MIT y que los 28 parquet de drone-only coinciden en tamaño y SHA-256 (oid LFS) con el
manifiesto. Nunca descarga drone-with-source, source-only ni ground-truth (audio de terceros y voz).
Hosts permitidos: huggingface.co y su CDN *.hf.co, comprobados también en cada redirección.
Si pyarrow está disponible (Colab), compara además las filas (file_path) con el manifiesto.
No concede permiso para entrenar (intake_approved=false).

Uso en Colab:  python fetch.py --out /content/data/droneaudioset-drone-only
Comprobación sin audio:  python fetch.py --metadata-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
REPO = "ahlab-drone-project/DroneAudioSet"
REVISION = "e794007062e2d2ad29262a5795b60d09f2b345c4"
SUBSET = "drone-only"
INFO_URL = f"https://huggingface.co/api/datasets/{REPO}/revision/{REVISION}"
TREE_URL = f"https://huggingface.co/api/datasets/{REPO}/tree/{REVISION}/{SUBSET}?recursive=true"
EXPECTED_LICENSE = "mit"
ALLOWED_HOSTS = {"huggingface.co"}
ALLOWED_SUFFIXES = (".hf.co",)  # CDN de Hugging Face para LFS/Xet
CHUNK = 1 << 20


def _check_url(url: str) -> None:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if parsed.scheme != "https" or not (host in ALLOWED_HOSTS or host.endswith(ALLOWED_SUFFIXES)):
        raise ValueError(f"host no permitido: {url}")


class _CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        _check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_CheckedRedirect)


def _open(url: str) -> Any:
    _check_url(url)
    request = urllib.request.Request(  # noqa: S310 - HTTPS y host comprobados arriba
        url, headers={"User-Agent": "dataset-intake/1"}
    )
    response = _OPENER.open(request, timeout=120)
    _check_url(response.geturl())
    return response


def _download(url: str, dest: Path, size: int, sha256: str) -> str:
    if dest.exists() and dest.stat().st_size == size:
        h = hashlib.sha256()
        with dest.open("rb") as fh:
            for chunk in iter(lambda: fh.read(CHUNK), b""):
                h.update(chunk)
        if h.hexdigest() == sha256:
            return sha256
    h, total = hashlib.sha256(), 0
    tmp = dest.with_name(dest.name + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with _open(url) as response, tmp.open("wb") as out:
        for chunk in iter(lambda: response.read(CHUNK), b""):
            total += len(chunk)
            if total > size:
                raise ValueError(f"tamaño excedido: {dest.name}")
            h.update(chunk)
            out.write(chunk)
    if total != size or h.hexdigest() != sha256:
        tmp.unlink(missing_ok=True)
        raise ValueError(f"verificación fallida: {dest.name} ({total} B)")
    tmp.replace(dest)
    return sha256


def _check_source(manifest: dict[str, Any]) -> None:
    with _open(INFO_URL) as response:
        info = json.loads(response.read())
    if info.get("sha") != REVISION or info.get("cardData", {}).get("license") != EXPECTED_LICENSE:
        raise ValueError("revisión o licencia de la fuente distinta de la fijada")
    with _open(TREE_URL) as response:
        tree = json.loads(response.read())
    upstream = {(e["path"], e["size"], e["lfs"]["oid"]) for e in tree if e["type"] == "file"}
    pinned = {(f["path"], f["bytes"], f["sha256"]) for f in manifest["files"]}
    if upstream != pinned or any(not p.startswith(f"{SUBSET}/") for p, _, _ in pinned):
        raise ValueError("el árbol drone-only no coincide con el manifiesto")


def _check_rows(path: Path, expected: list[str]) -> str:
    try:
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
    except ImportError:
        return "rows_not_checked_no_pyarrow"
    table = pq.read_table(path, columns=["file_path", "data_type"])
    if sorted(table.column("file_path").to_pylist()) != sorted(expected):
        raise ValueError(f"filas inesperadas en {path.name}")
    if set(table.column("data_type").to_pylist()) != {SUBSET}:
        raise ValueError(f"data_type inesperado en {path.name}")
    return "rows_match_manifest"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("/content/data/droneaudioset-drone-only"))
    parser.add_argument("--manifest", type=Path, default=HERE / "manifest.json")
    parser.add_argument("--metadata-only", action="store_true", help="solo licencia e inventario")
    parser.add_argument("--allow-outside-colab", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    _check_source(manifest)
    print(f"Licencia MIT y {len(manifest['files'])} parquet drone-only en {REVISION[:12]}: OK")
    if args.metadata_only:
        return 0
    if not Path("/content").is_dir() and not args.allow_outside_colab:
        print("Descarga pensada para Colab (~3,4 GB); usa --allow-outside-colab para forzarla.")
        return 2

    inventory = []
    for entry in manifest["files"]:
        dest = args.out / entry["path"]
        digest = _download(entry["url"], dest, entry["bytes"], entry["sha256"])
        rows = _check_rows(dest, [r["upstream_file_path"] for r in entry["rows"]])
        inventory.append(
            {"path": entry["path"], "bytes": entry["bytes"], "sha256": digest, "rows": rows}
        )
        print(f"OK {entry['path']} {digest} {rows}")
    report = {
        "source_id": manifest["source_id"],
        "revision": REVISION,
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "intake_approved": False,
        "files": inventory,
    }
    (args.out / "inventory-sha256.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"{len(inventory)} parquet verificados; entrenamiento sigue bloqueado")
    return 0


if __name__ == "__main__":
    sys.exit(main())

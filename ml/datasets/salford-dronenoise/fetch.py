"""Descarga verificada de DroneNoise Database (U. de Salford, CC BY 4.0) para Colab.

Preflight de intake: comprueba que la licencia del registro original sigue siendo CC BY 4.0,
descarga solo desde hosts permitidos (también en cada redirección) y verifica tamaño y MD5
publicados por Figshare antes de aceptar cada fichero. Escribe el SHA-256 calculado en
``<out>/inventory-sha256.json``. No concede permiso para entrenar (intake_approved=false).

Uso en Colab:  python fetch.py --out /content/data/salford-dronenoise
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
API_URL = "https://api.figshare.com/v2/articles/22133411"
EXPECTED_LICENSE = "CC BY 4.0"
ALLOWED_HOSTS = {"api.figshare.com", "ndownloader.figshare.com", "s3-eu-west-1.amazonaws.com"}
# El almacenamiento S3 solo se admite dentro del bucket institucional de Salford.
S3_PREFIX = "/pstorage-salford-7894554354135/"
CHUNK = 1 << 20


def _check_url(url: str) -> None:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if parsed.scheme != "https" or host not in ALLOWED_HOSTS:
        raise ValueError(f"host no permitido: {url}")
    if host == "s3-eu-west-1.amazonaws.com" and not parsed.path.startswith(S3_PREFIX):
        raise ValueError(f"bucket no permitido: {url}")


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


def _download(url: str, dest: Path, size: int, md5: str) -> str:
    """Descarga en streaming; devuelve el SHA-256 si tamaño y MD5 coinciden."""
    if dest.exists() and dest.stat().st_size == size:
        h_md5, h_sha = hashlib.md5(usedforsecurity=False), hashlib.sha256()
        with dest.open("rb") as fh:
            for chunk in iter(lambda: fh.read(CHUNK), b""):
                h_md5.update(chunk)
                h_sha.update(chunk)
        if h_md5.hexdigest() == md5:
            return h_sha.hexdigest()
    h_md5, h_sha, total = hashlib.md5(usedforsecurity=False), hashlib.sha256(), 0
    tmp = dest.with_name(dest.name + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with _open(url) as response, tmp.open("wb") as out:
        for chunk in iter(lambda: response.read(CHUNK), b""):
            total += len(chunk)
            if total > size:
                raise ValueError(f"tamaño excedido: {dest.name}")
            h_md5.update(chunk)
            h_sha.update(chunk)
            out.write(chunk)
    if total != size or h_md5.hexdigest() != md5:
        tmp.unlink(missing_ok=True)
        raise ValueError(f"verificación fallida: {dest.name} ({total} B, md5 {h_md5.hexdigest()})")
    tmp.replace(dest)
    return h_sha.hexdigest()


def _check_source(manifest: dict[str, Any]) -> None:
    with _open(API_URL) as response:
        record = json.loads(response.read())
    if record["license"]["name"] != EXPECTED_LICENSE:
        raise ValueError(f"la licencia de la fuente cambió: {record['license']}")
    upstream = {(f["id"], f["computed_md5"], f["size"]) for f in record["files"]}
    pinned = {(f["figshare_file_id"], f["md5"], f["bytes"]) for f in manifest["files"]}
    if upstream != pinned:
        raise ValueError("la lista de ficheros de Figshare no coincide con el manifiesto")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("/content/data/salford-dronenoise"))
    parser.add_argument("--manifest", type=Path, default=HERE / "manifest.json")
    parser.add_argument("--metadata-only", action="store_true", help="solo licencia e inventario")
    parser.add_argument("--allow-outside-colab", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    _check_source(manifest)
    print(f"Licencia {EXPECTED_LICENSE} e inventario de {len(manifest['files'])} ficheros: OK")
    if args.metadata_only:
        return 0
    if not Path("/content").is_dir() and not args.allow_outside_colab:
        print("Descarga pensada para Colab; usa --allow-outside-colab para forzarla.")
        return 2

    inventory = []
    for entry in manifest["files"]:
        if (entry.get("exclusion_reason") or "").startswith("exact_duplicate"):
            continue
        digest = _download(entry["url"], args.out / entry["path"], entry["bytes"], entry["md5"])
        inventory.append({"path": entry["path"], "bytes": entry["bytes"], "sha256": digest})
        print(f"OK {entry['path']} {digest}")
    report = {
        "source_id": manifest["source_id"],
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "intake_approved": False,
        "files": inventory,
    }
    (args.out / "inventory-sha256.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"{len(inventory)} ficheros verificados; entrenamiento sigue bloqueado")
    return 0


if __name__ == "__main__":
    sys.exit(main())

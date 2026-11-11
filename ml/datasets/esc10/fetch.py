"""Descarga verificada de ESC-10 (CC BY 3.0), nunca de ESC-50 completo (CC BY-NC), para Colab.

Preflight de intake: en el commit fijado del repositorio original comprueba el Git blob del
LICENSE, el SHA-256 de ``meta/esc50.csv`` y que cada fichero del manifiesto está marcado
``esc10=True``. Descarga clip a clip desde raw.githubusercontent.com (solo ese host y
api.github.com, también en redirecciones), verificando tamaño y Git blob SHA-1, y calcula el
SHA-256. Por defecto omite los clips excluidos (sonidos de personas y licencia por clip no
admitida). No concede permiso para entrenar (intake_approved=false).

Uso en Colab:  python fetch.py --out /content/data/esc10
Comprobación sin audio:  python fetch.py --metadata-only
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
REPO = "karolpiczak/ESC-50"
COMMIT = "33c8ce9eb2cf0b1c2f8bcf322eb349b6be34dbb6"
RAW_URL = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}"
ALLOWED_HOSTS = {"api.github.com", "raw.githubusercontent.com"}
MAX_CLIP_BYTES = 1 << 20


def _check_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"host no permitido: {url}")


class _CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        _check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_CheckedRedirect)


def _get(url: str, limit: int) -> bytes:
    _check_url(url)
    request = urllib.request.Request(  # noqa: S310 - HTTPS y host comprobados arriba
        url, headers={"User-Agent": "dataset-intake/1"}
    )
    with _OPENER.open(request, timeout=90) as response:
        _check_url(response.geturl())
        data: bytes = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"respuesta demasiado grande: {url}")
    return data


def _blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


def _check_source(manifest: dict[str, Any]) -> None:
    evidence = manifest["license_evidence"]
    license_bytes = _get(f"{RAW_URL}/LICENSE", 1 << 21)
    if _blob_sha1(license_bytes) != evidence["upstream_git_blob_sha1"]:
        raise ValueError("el LICENSE del commit fijado no coincide")
    if b"The ESC-10 subset is licensed as a Creative Commons Attribution 3.0" not in license_bytes:
        raise ValueError("el LICENSE ya no declara CC BY 3.0 para ESC-10")
    meta = _get(f"{RAW_URL}/meta/esc50.csv", 1 << 21)
    if hashlib.sha256(meta).hexdigest() != manifest["metadata_csv_sha256"]:
        raise ValueError("meta/esc50.csv distinto del fijado")
    esc10 = {
        f"audio/{row['filename']}"
        for row in csv.DictReader(io.StringIO(meta.decode("utf-8")))
        if row["esc10"] == "True"
    }
    pinned = {entry["path"] for entry in manifest["files"]}
    if pinned != esc10 or len(pinned) != 400:
        raise ValueError("el manifiesto contiene ficheros fuera de ESC-10")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("/content/data/esc10"))
    parser.add_argument("--manifest", type=Path, default=HERE / "manifest.json")
    parser.add_argument("--include-excluded", action="store_true", help="solo para auditoría")
    parser.add_argument("--metadata-only", action="store_true", help="solo licencia e inventario")
    parser.add_argument("--allow-outside-colab", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    _check_source(manifest)
    print(f"Licencia ESC-10 CC BY 3.0 y {len(manifest['files'])} clips ESC-10 en {COMMIT[:12]}: OK")
    if args.metadata_only:
        return 0
    if not Path("/content").is_dir() and not args.allow_outside_colab:
        print("Descarga pensada para Colab; usa --allow-outside-colab para forzarla.")
        return 2

    inventory = []
    for entry in manifest["files"]:
        if entry["training_excluded"] and not args.include_excluded:
            continue
        dest = args.out / entry["path"]
        data = dest.read_bytes() if dest.exists() else b""
        if _blob_sha1(data) != entry["upstream_git_blob_sha1"]:
            data = _get(f"{RAW_URL}/{entry['path']}", MAX_CLIP_BYTES)
            if len(data) != entry["bytes"] or _blob_sha1(data) != entry["upstream_git_blob_sha1"]:
                raise ValueError(f"verificación fallida: {entry['path']}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + ".part")
            tmp.write_bytes(data)
            tmp.replace(dest)
        digest = hashlib.sha256(data).hexdigest()
        inventory.append({"path": entry["path"], "bytes": len(data), "sha256": digest})
        print(f"OK {entry['path']} {digest}")
    report = {
        "source_id": manifest["source_id"],
        "commit": COMMIT,
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "intake_approved": False,
        "files": inventory,
    }
    (args.out / "inventory-sha256.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"{len(inventory)} clips verificados; entrenamiento sigue bloqueado")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Descarga verificada de Yi et al. (KAIST, Zenodo 7779574, CC BY 4.0) para Colab.

Preflight de intake: comprueba que el registro original de Zenodo sigue declarando CC BY 4.0 y que
los TAR coinciden en tamaño y MD5 con el manifiesto; solo descarga de zenodo.org (también en
redirecciones). Por defecto baja únicamente el TAR del dron A (~2,55 GB). Tras verificar el TAR
calcula el SHA-256 de cada miembro (inventario completo) y extrae solo los WAV con fallo ``N``
(estado normal), sin seguir rutas absolutas, ``..`` ni enlaces. No concede permiso para entrenar.

Uso en Colab:  python fetch.py --out /content/data/yi-kaist --drone A
Comprobación sin audio:  python fetch.py --metadata-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tarfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
API_URL = "https://zenodo.org/api/records/7779574"
EXPECTED_LICENSE = "cc-by-4.0"
ALLOWED_HOSTS = {"zenodo.org"}
CHUNK = 1 << 20
# {model}_{direction}_{fault}_{drone_file_index}_{background}_{background_file_index}_{SNR}
NAME_RE = re.compile(r"(?P<model>[ABC])_(?P<direction>CC|[FBRLC])_(?P<fault>N|MF[1-4]|PC[1-4])_.+")


def _check_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
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
    response = _OPENER.open(request, timeout=300)
    _check_url(response.geturl())
    return response


def _hashes(path: Path) -> tuple[str, str]:
    h_md5, h_sha = hashlib.md5(usedforsecurity=False), hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            h_md5.update(chunk)
            h_sha.update(chunk)
    return h_md5.hexdigest(), h_sha.hexdigest()


def _download(url: str, dest: Path, size: int, md5: str) -> str:
    if dest.exists() and dest.stat().st_size == size:
        got_md5, got_sha = _hashes(dest)
        if got_md5 == md5:
            return got_sha
    tmp = dest.with_name(dest.name + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with _open(url) as response, tmp.open("wb") as out:
        for chunk in iter(lambda: response.read(CHUNK), b""):
            total += len(chunk)
            if total > size:
                raise ValueError(f"tamaño excedido: {dest.name}")
            out.write(chunk)
    got_md5, got_sha = _hashes(tmp)
    if total != size or got_md5 != md5:
        tmp.unlink(missing_ok=True)
        raise ValueError(f"verificación fallida: {dest.name} ({total} B, md5 {got_md5})")
    tmp.replace(dest)
    return got_sha


def _safe_relative(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"ruta insegura en el TAR: {name}")
    return path


def _inventory_and_extract(tar_path: Path, dest: Path) -> list[dict[str, Any]]:
    members = []
    with tarfile.open(tar_path, mode="r|") as archive:
        for member in archive:
            rel = _safe_relative(member.name)
            if not member.isfile():
                if not member.isdir():
                    raise ValueError(f"miembro no regular en el TAR: {member.name}")
                continue
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"miembro ilegible: {member.name}")
            match = NAME_RE.match(rel.name)
            fault = match.group("fault") if match else None
            keep = rel.suffix.lower() == ".wav" and fault == "N"
            h = hashlib.sha256()
            out = None
            if keep:
                target = dest.joinpath(*rel.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                out = target.open("wb")
            try:
                for chunk in iter(lambda: source.read(CHUNK), b""):  # noqa: B023
                    h.update(chunk)
                    if out is not None:
                        out.write(chunk)
            finally:
                if out is not None:
                    out.close()
            members.append(
                {
                    "path": str(rel),
                    "bytes": member.size,
                    "sha256": h.hexdigest(),
                    "fault": fault,
                    "direction": match.group("direction") if match else None,
                    "extracted": keep,
                }
            )
    return members


def _check_source(manifest: dict[str, Any]) -> None:
    with _open(API_URL) as response:
        record = json.loads(response.read())
    if record["metadata"]["license"]["id"] != EXPECTED_LICENSE:
        raise ValueError(f"la licencia de la fuente cambió: {record['metadata']['license']}")
    upstream = {(f["key"], f["size"], f["checksum"]) for f in record["files"]}
    pinned = {(f["path"], f["bytes"], f"md5:{f['md5']}") for f in manifest["files"]}
    if upstream != pinned:
        raise ValueError("los ficheros de Zenodo no coinciden con el manifiesto")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("/content/data/yi-kaist"))
    parser.add_argument("--manifest", type=Path, default=HERE / "manifest.json")
    parser.add_argument("--drone", choices=["A", "B", "C"], action="append")
    parser.add_argument("--metadata-only", action="store_true", help="solo licencia e inventario")
    parser.add_argument("--allow-outside-colab", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    _check_source(manifest)
    print(f"Licencia CC BY 4.0 y {len(manifest['files'])} TAR en Zenodo: OK")
    if args.metadata_only:
        return 0
    if not Path("/content").is_dir() and not args.allow_outside_colab:
        print("Descarga pensada para Colab (~2,5 GB por dron); usa --allow-outside-colab.")
        return 2

    drones = set(args.drone or ["A"])
    report_files = []
    for entry in manifest["files"]:
        if entry["drone_type"] not in drones:
            continue
        tar_path = args.out / "tar" / entry["path"]
        digest = _download(entry["url"], tar_path, entry["bytes"], entry["md5"])
        print(f"OK {entry['path']} {digest}")
        members = _inventory_and_extract(tar_path, args.out / "audio")
        kept = sum(m["extracted"] for m in members)
        print(f"{len(members)} miembros con SHA-256; {kept} WAV en estado normal extraídos")
        report_files.append(
            {"path": entry["path"], "bytes": entry["bytes"], "sha256": digest, "members": members}
        )
    report = {
        "source_id": manifest["source_id"],
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "intake_approved": False,
        "files": report_files,
    }
    (args.out / "inventory-sha256.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Inventario escrito; entrenamiento sigue bloqueado")
    return 0


if __name__ == "__main__":
    sys.exit(main())

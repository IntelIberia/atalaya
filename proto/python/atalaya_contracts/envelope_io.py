"""Formato de replay `.pb.zst` de Atalaya, versión 1 (T1.15, REQ-FUN-006, REQ-FUN-003).

Disposición del fichero (todos los enteros de la cabecera en big-endian):

    0   8 B  magia `ATLYRPLY`
    8   2 B  versión del formato (`FORMAT_VERSION`)
    10 32 B  SHA-256 del contenido sin comprimir
    42  …    una trama zstd (nivel fijo `ZSTD_LEVEL`, con tamaño y suma de comprobación)

Contenido sin comprimir: sucesión de registros `tipo (1 B) ‖ varint(longitud) ‖ mensaje`, con el
mensaje serializado de forma determinista. Tipos: 1 = `atalaya.v1.Envelope` (lo que viaja por
MQTT) y 2 = `atalaya.sim.v1.GroundTruth` (verdad del simulador; solo métricas). Se conserva el
orden de cada tipo.

La lectura es todo o nada: cabecera, trama, hash y registros se comprueban antes de devolver nada;
cualquier fallo lanza `ReplayFormatError` con el desplazamiento (en el fichero o en el contenido
descomprimido) y nunca una secuencia parcial.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import zstandard
from atalaya.sim.v1.ground_truth_pb2 import GroundTruth
from atalaya.v1.envelope_pb2 import Envelope
from google.protobuf.message import DecodeError, Message

MAGIC = b"ATLYRPLY"
FORMAT_VERSION = 1
ZSTD_LEVEL = 10
VERSION_OFFSET = len(MAGIC)
HASH_OFFSET = VERSION_OFFSET + 2
HEADER_LEN = HASH_OFFSET + 32
RECORD_ENVELOPE = 1
RECORD_GROUND_TRUTH = 2
_MAX_VARINT_BYTES = 10


class ReplayFormatError(ValueError):
    """Fichero de replay inválido; `offset` es el desplazamiento del fallo."""

    def __init__(self, where: str, offset: int, message: str) -> None:
        self.where = where
        self.offset = offset
        super().__init__(f"replay inválido ({where}, desplazamiento {offset}): {message}")


@dataclass(frozen=True)
class Replay:
    envelopes: list[Envelope] = field(default_factory=list)
    ground_truth: list[GroundTruth] = field(default_factory=list)
    content_sha256: str = ""


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _record(kind: int, message: Message) -> bytes:
    data = message.SerializeToString(deterministic=True)
    return bytes([kind]) + _varint(len(data)) + data


def encode_content(
    envelopes: Iterable[Envelope], ground_truth: Iterable[GroundTruth] = ()
) -> bytes:
    """Contenido sin comprimir (registros tipados y delimitados por longitud)."""
    parts: list[bytes] = []
    for env in envelopes:
        if not isinstance(env, Envelope):
            raise TypeError(f"se esperaba Envelope, no {type(env).__name__}")
        parts.append(_record(RECORD_ENVELOPE, env))
    for truth in ground_truth:
        if not isinstance(truth, GroundTruth):
            raise TypeError(f"se esperaba GroundTruth, no {type(truth).__name__}")
        parts.append(_record(RECORD_GROUND_TRUTH, truth))
    return b"".join(parts)


def encode(envelopes: Iterable[Envelope], ground_truth: Iterable[GroundTruth] = ()) -> bytes:
    """Fichero completo: cabecera con versión y hash más la trama zstd de nivel fijo."""
    content = encode_content(envelopes, ground_truth)
    frame = zstandard.ZstdCompressor(
        level=ZSTD_LEVEL, write_checksum=True, write_content_size=True
    ).compress(content)
    header = MAGIC + FORMAT_VERSION.to_bytes(2, "big") + hashlib.sha256(content).digest()
    return header + frame


def _decompress(data: bytes) -> bytes:
    frame = data[HEADER_LEN:]
    if not frame:
        raise ReplayFormatError("fichero", HEADER_LEN, "falta la trama zstd")
    dobj = zstandard.ZstdDecompressor().decompressobj()
    try:
        content = dobj.decompress(frame)
    except zstandard.ZstdError as exc:
        raise ReplayFormatError("fichero", HEADER_LEN, f"trama zstd corrupta: {exc}") from exc
    if not dobj.eof:
        raise ReplayFormatError("fichero", len(data), "trama zstd truncada")
    if dobj.unused_data:
        offset = len(data) - len(dobj.unused_data)
        raise ReplayFormatError("fichero", offset, "datos sobrantes tras la trama zstd")
    return content


def _read_varint(content: bytes, pos: int, record: int) -> tuple[int, int]:
    """Longitud en varint que empieza en `pos`; los errores señalan el inicio del registro."""
    value = 0
    for i in range(_MAX_VARINT_BYTES):
        if pos + i >= len(content):
            raise ReplayFormatError("contenido", record, "longitud truncada")
        byte = content[pos + i]
        value |= (byte & 0x7F) << (7 * i)
        if not byte & 0x80:
            return value, pos + i + 1
    raise ReplayFormatError("contenido", record, "longitud con más de 10 bytes")


def decode_content(content: bytes) -> tuple[list[Envelope], list[GroundTruth]]:
    envelopes: list[Envelope] = []
    truth: list[GroundTruth] = []
    pos = 0
    while pos < len(content):
        start = pos
        kind = content[pos]
        if kind not in (RECORD_ENVELOPE, RECORD_GROUND_TRUTH):
            raise ReplayFormatError("contenido", start, f"tipo de registro desconocido {kind}")
        length, pos = _read_varint(content, pos + 1, start)
        end = pos + length
        if end > len(content):
            raise ReplayFormatError("contenido", start, "registro truncado")
        message: Message = Envelope() if kind == RECORD_ENVELOPE else GroundTruth()
        try:
            message.ParseFromString(content[pos:end])
        except DecodeError as exc:
            raise ReplayFormatError("contenido", start, f"mensaje ilegible: {exc}") from exc
        if kind == RECORD_ENVELOPE:
            envelopes.append(message)  # type: ignore[arg-type]
        else:
            truth.append(message)  # type: ignore[arg-type]
        pos = end
    return envelopes, truth


def decode(data: bytes) -> Replay:
    """Lee un fichero de replay completo o lanza `ReplayFormatError`; nunca devuelve parciales."""
    if len(data) < HEADER_LEN:
        raise ReplayFormatError("fichero", len(data), "cabecera truncada")
    if data[:VERSION_OFFSET] != MAGIC:
        raise ReplayFormatError("fichero", 0, "magia desconocida: no es un replay de Atalaya")
    version = int.from_bytes(data[VERSION_OFFSET:HASH_OFFSET], "big")
    if version != FORMAT_VERSION:
        raise ReplayFormatError(
            "fichero", VERSION_OFFSET, f"versión de formato desconocida {version}"
        )
    content = _decompress(data)
    digest = hashlib.sha256(content).digest()
    if digest != data[HASH_OFFSET:HEADER_LEN]:
        raise ReplayFormatError("fichero", HASH_OFFSET, "el hash del contenido no coincide")
    envelopes, truth = decode_content(content)
    return Replay(envelopes, truth, digest.hex())


def write(
    path: Path, envelopes: Sequence[Envelope], ground_truth: Sequence[GroundTruth] = ()
) -> bytes:
    data = encode(envelopes, ground_truth)
    path.write_bytes(data)
    return data


def read(path: Path) -> Replay:
    return decode(path.read_bytes())

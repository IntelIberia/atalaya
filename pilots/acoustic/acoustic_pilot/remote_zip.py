# Lectura parcial de ZIP (también divididos en volúmenes .z01…/.zip) mediante rangos HTTP.
# Autocontenido (solo stdlib): build_colab.py lo incrusta tal cual en el cuaderno de Colab.
# Permite descargar solo los clips seleccionados de un archivo grande (FSD50K) sin bajarlo
# entero; cada clip se verifica después por tamaño, CRC-32 y SHA-256 fijado.
import struct
import zlib
from collections.abc import Sequence

EOCD_SIG = 0x06054B50
ZIP64_LOCATOR_SIG = 0x07064B50
ZIP64_EOCD_SIG = 0x06064B50
CENTRAL_SIG = 0x02014B50
LOCAL_SIG = 0x04034B50
LOCAL_HEADER_LEN = 30
_U32 = 0xFFFFFFFF
_U16 = 0xFFFF


def parse_eocd(tail: bytes) -> dict:
    """Busca el registro final (EOCD) en la cola del último volumen y, si existe, el
    localizador ZIP64 que lo precede. Las posiciones son relativas al inicio de ``tail``."""
    pos = tail.rfind(struct.pack("<I", EOCD_SIG))
    if pos < 0 or len(tail) - pos < 22:
        raise ValueError("no se encuentra el registro final del ZIP")
    (_, disk, cd_disk, _, n_entries, cd_size, cd_offset, comment_len) = struct.unpack(
        "<IHHHHIIH", tail[pos : pos + 22]
    )
    if pos + 22 + comment_len != len(tail):
        raise ValueError("registro final del ZIP truncado o con datos detrás")
    result = {
        "disk": disk,
        "cd_disk": cd_disk,
        "n_entries": n_entries,
        "cd_size": cd_size,
        "cd_offset": cd_offset,
        "zip64_locator": None,
    }
    loc = pos - 20
    if loc >= 0 and struct.unpack("<I", tail[loc : loc + 4])[0] == ZIP64_LOCATOR_SIG:
        _, z_disk, z_offset, total_disks = struct.unpack("<IIQI", tail[loc : loc + 20])
        result["zip64_locator"] = {"disk": z_disk, "offset": z_offset, "total_disks": total_disks}
    return result


def parse_zip64_eocd(record: bytes) -> dict:
    """Registro final ZIP64 (56 bytes fijos)."""
    if len(record) < 56 or struct.unpack("<I", record[:4])[0] != ZIP64_EOCD_SIG:
        raise ValueError("registro final ZIP64 no válido")
    (_, _, _, _, disk, cd_disk, _, n_entries, cd_size, cd_offset) = struct.unpack(
        "<IQHHIIQQQQ", record[:56]
    )
    return {
        "disk": disk,
        "cd_disk": cd_disk,
        "n_entries": n_entries,
        "cd_size": cd_size,
        "cd_offset": cd_offset,
    }


def _zip64_extra(extra: bytes, need: Sequence[str]) -> dict:
    values: dict = {}
    i = 0
    while i + 4 <= len(extra):
        tag, size = struct.unpack("<HH", extra[i : i + 4])
        body = extra[i + 4 : i + 4 + size]
        if tag == 0x0001:
            j = 0
            for name in need:
                width = 4 if name == "disk" else 8
                if j + width > len(body):
                    raise ValueError("campo ZIP64 truncado")
                values[name] = int.from_bytes(body[j : j + width], "little")
                j += width
            return values
        i += 4 + size
    if need:
        raise ValueError("faltan campos ZIP64")
    return values


def parse_central_directory(data: bytes, n_entries: int) -> list[dict]:
    """Entradas del directorio central: nombre, volumen, desplazamiento local, tamaños,
    método y CRC-32. Falla si el número de entradas no coincide."""
    entries, i = [], 0
    while i < len(data) and len(entries) < n_entries:
        if struct.unpack("<I", data[i : i + 4])[0] != CENTRAL_SIG:
            raise ValueError(f"firma de directorio central no válida en {i}")
        (
            _,
            _,
            _,
            flags,
            method,
            _,
            _,
            crc,
            csize,
            usize,
            nlen,
            xlen,
            clen,
            disk,
            _,
            _,
            offset,
        ) = struct.unpack("<IHHHHHHIIIHHHHHII", data[i : i + 46])
        name = data[i + 46 : i + 46 + nlen].decode("utf-8" if flags & 0x800 else "cp437")
        extra = data[i + 46 + nlen : i + 46 + nlen + xlen]
        need = [
            n
            for n, v, top in (
                ("usize", usize, _U32),
                ("csize", csize, _U32),
                ("offset", offset, _U32),
                ("disk", disk, _U16),
            )
            if v == top
        ]
        big = _zip64_extra(extra, need)
        entries.append(
            {
                "name": name,
                "disk": big.get("disk", disk),
                "offset": big.get("offset", offset),
                "compressed_size": big.get("csize", csize),
                "size": big.get("usize", usize),
                "method": method,
                "crc32": crc,
                "encrypted": bool(flags & 0x1),
            }
        )
        i += 46 + nlen + xlen + clen
    if len(entries) != n_entries:
        raise ValueError("el directorio central no tiene el número de entradas declarado")
    return entries


def local_header_length(header: bytes, expected_name: str) -> int:
    """Longitud de la cabecera local (30 + nombre + extra); comprueba firma y nombre."""
    if len(header) < LOCAL_HEADER_LEN or struct.unpack("<I", header[:4])[0] != LOCAL_SIG:
        raise ValueError("cabecera local no válida")
    nlen, xlen = struct.unpack("<HH", header[26:30])
    name = header[30 : 30 + nlen].decode("utf-8", errors="replace")
    if name != expected_name:
        raise ValueError(f"cabecera local de otro fichero: {name!r}")
    return LOCAL_HEADER_LEN + nlen + xlen


def volume_ranges(
    disk: int, offset: int, length: int, volume_sizes: Sequence[int]
) -> list[tuple[int, int, int]]:
    """Trocea un intervalo lógico que empieza en (disk, offset) en rangos por volumen:
    (volumen, inicio, fin_exclusivo). Un miembro puede cruzar al volumen siguiente."""
    if length < 0 or not 0 <= disk < len(volume_sizes):
        raise ValueError("volumen o longitud fuera de rango")
    if not 0 <= offset < volume_sizes[disk]:
        raise ValueError("desplazamiento fuera del volumen")
    ranges, remaining = [], length
    while remaining:
        if disk >= len(volume_sizes):
            raise ValueError("el intervalo sobrepasa el último volumen")
        take = min(remaining, volume_sizes[disk] - offset)
        ranges.append((disk, offset, offset + take))
        remaining -= take
        disk, offset = disk + 1, 0
    return ranges


def decode_member(payload: bytes, *, method: int, size: int, crc32: int) -> bytes:
    """Descomprime (almacenado o deflate) y verifica tamaño y CRC-32 del miembro."""
    if method == 0:
        data = payload
    elif method == 8:
        data = zlib.decompressobj(-15).decompress(payload)
    else:
        raise ValueError(f"método de compresión no admitido: {method}")
    if len(data) != size or (zlib.crc32(data) & _U32) != crc32:
        raise ValueError("tamaño o CRC-32 del miembro no coinciden")
    return data

"""Lectura parcial de ZIP por rangos (FSD50K): directorio central, ZIP64, volúmenes y CRC."""

from __future__ import annotations

import io
import struct
import zipfile
import zlib

import pytest

from acoustic_pilot.remote_zip import (
    CENTRAL_SIG,
    decode_member,
    local_header_length,
    parse_central_directory,
    parse_eocd,
    parse_zip64_eocd,
    volume_ranges,
)


def _zip(members: dict[str, bytes], *, comment: bytes = b"") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for i, (name, data) in enumerate(members.items()):
            method = zipfile.ZIP_STORED if i % 2 == 0 else zipfile.ZIP_DEFLATED
            archive.writestr(name, data, compress_type=method)
        archive.comment = comment
    return buffer.getvalue()


def _read_member(raw: bytes, entry: dict) -> bytes:
    """Lo que hace el cuaderno: cabecera local + datos comprimidos + verificación."""
    start = entry["offset"]
    head = local_header_length(raw[start : start + 1024], entry["name"])
    payload = raw[start + head : start + head + entry["compressed_size"]]
    return decode_member(payload, method=entry["method"], size=entry["size"], crc32=entry["crc32"])


def test_reads_selected_members_from_central_directory_without_whole_archive() -> None:
    members = {"FSD50K.dev_audio/1.wav": b"RIFF" + bytes(500), "x/2.wav": b"abc" * 300}
    raw = _zip(members, comment=b"comentario")
    eocd = parse_eocd(raw[-200:])
    assert eocd["n_entries"] == 2 and eocd["zip64_locator"] is None
    cd = raw[eocd["cd_offset"] : eocd["cd_offset"] + eocd["cd_size"]]
    entries = parse_central_directory(cd, eocd["n_entries"])
    assert [e["name"] for e in entries] == list(members)
    assert {e["method"] for e in entries} == {0, 8}
    for entry in entries:
        assert _read_member(raw, entry) == members[entry["name"]]


def test_corrupted_member_fails_crc_or_size() -> None:
    raw = bytearray(_zip({"a.wav": b"0123456789" * 50}))
    eocd = parse_eocd(bytes(raw[-100:]))
    cd = bytes(raw[eocd["cd_offset"] : eocd["cd_offset"] + eocd["cd_size"]])
    (entry,) = parse_central_directory(cd, 1)
    raw[entry["offset"] + 40] ^= 0xFF  # un byte dentro de los datos
    with pytest.raises(ValueError, match="CRC-32"):
        _read_member(bytes(raw), entry)
    with pytest.raises(ValueError, match="CRC-32"):
        decode_member(b"abc", method=0, size=4, crc32=zlib.crc32(b"abc"))


def test_unsupported_method_and_wrong_local_name_are_rejected() -> None:
    with pytest.raises(ValueError, match="método"):
        decode_member(b"", method=14, size=0, crc32=0)
    raw = _zip({"a.wav": b"x"})
    with pytest.raises(ValueError, match="otro fichero"):
        local_header_length(raw[:100], "b.wav")
    with pytest.raises(ValueError, match="cabecera local"):
        local_header_length(b"PK\x01\x02" + bytes(40), "a.wav")


def test_eocd_errors_and_entry_count_mismatch() -> None:
    with pytest.raises(ValueError, match="registro final"):
        parse_eocd(b"no hay zip aqui" * 3)
    raw = _zip({"a.wav": b"x", "b.wav": b"y"})
    with pytest.raises(ValueError, match="truncado"):
        parse_eocd(raw + b"basura")
    eocd = parse_eocd(raw[-100:])
    cd = raw[eocd["cd_offset"] : eocd["cd_offset"] + eocd["cd_size"]]
    with pytest.raises(ValueError, match="número de entradas"):
        parse_central_directory(cd, 3)
    with pytest.raises(ValueError, match="firma"):
        parse_central_directory(b"\x00" * 60, 1)


def _central_entry(name: bytes, extra: bytes, **fields: int) -> bytes:
    values = {"csize": 10, "usize": 10, "disk": 0, "offset": 0} | fields
    return (
        struct.pack(
            "<IHHHHHHIIIHHHHHII",
            CENTRAL_SIG,
            45,
            45,
            0,
            0,
            0,
            0,
            123,
            values["csize"],
            values["usize"],
            len(name),
            len(extra),
            0,
            values["disk"],
            0,
            0,
            values["offset"],
        )
        + name
        + extra
    )


def test_zip64_extra_fields_override_sentinels_in_order() -> None:
    # usize, csize, offset (8 bytes) y disk (4 bytes), solo los que llevan centinela.
    body = struct.pack("<QQQI", 5_000_000_000, 4_000_000_000, 3_500_000_000, 4)
    extra = struct.pack("<HH", 0x000A, 4) + b"skip" + struct.pack("<HH", 1, len(body)) + body
    data = _central_entry(
        b"big.wav", extra, csize=0xFFFFFFFF, usize=0xFFFFFFFF, offset=0xFFFFFFFF, disk=0xFFFF
    )
    (entry,) = parse_central_directory(data, 1)
    assert entry["size"] == 5_000_000_000
    assert entry["compressed_size"] == 4_000_000_000
    assert entry["offset"] == 3_500_000_000 and entry["disk"] == 4
    only_offset = struct.pack("<Q", 7_000_000_000)
    extra2 = struct.pack("<HH", 1, 8) + only_offset
    (entry2,) = parse_central_directory(_central_entry(b"o.wav", extra2, offset=0xFFFFFFFF), 1)
    assert entry2["offset"] == 7_000_000_000 and entry2["size"] == 10
    with pytest.raises(ValueError, match="ZIP64"):
        parse_central_directory(_central_entry(b"m.wav", b"", offset=0xFFFFFFFF), 1)


def test_zip64_locator_and_record() -> None:
    record = struct.pack("<IQHHIIQQQQ", 0x06064B50, 44, 45, 45, 6, 6, 40966, 40966, 7_000, 9_000)
    locator = struct.pack("<IIQI", 0x07064B50, 6, 2_300_000_000, 7)
    eocd = struct.pack("<IHHHHIIH", 0x06054B50, 6, 6, 0xFFFF, 0xFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0)
    parsed = parse_eocd(b"datos" + locator + eocd)
    assert parsed["zip64_locator"] == {"disk": 6, "offset": 2_300_000_000, "total_disks": 7}
    big = parse_zip64_eocd(record)
    assert (big["n_entries"], big["cd_size"], big["cd_offset"], big["cd_disk"]) == (
        40966,
        7_000,
        9_000,
        6,
    )
    with pytest.raises(ValueError, match="ZIP64"):
        parse_zip64_eocd(record[:40])


def test_volume_ranges_split_member_across_volumes() -> None:
    sizes = [100, 100, 50]
    assert volume_ranges(0, 10, 20, sizes) == [(0, 10, 30)]
    assert volume_ranges(0, 90, 30, sizes) == [(0, 90, 100), (1, 0, 20)]
    assert volume_ranges(0, 95, 150, sizes) == [(0, 95, 100), (1, 0, 100), (2, 0, 45)]
    assert volume_ranges(1, 99, 2, sizes) == [(1, 99, 100), (2, 0, 1)]
    with pytest.raises(ValueError, match="último volumen"):
        volume_ranges(2, 40, 20, sizes)
    with pytest.raises(ValueError, match="fuera del volumen"):
        volume_ranges(0, 100, 1, sizes)
    with pytest.raises(ValueError, match="fuera de rango"):
        volume_ranges(3, 0, 1, sizes)

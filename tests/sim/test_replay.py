"""T1.15: replay `.pb.zst` (REQ-FUN-006, REQ-FUN-003).

Propiedad: escribir y leer cualquier secuencia de `Envelope` devuelve la misma secuencia. El
replay de un escenario reproduce los mismos `Envelope` y la misma verdad terreno, en el mismo
orden. Negativas: fichero truncado, un byte alterado o versión desconocida → error explícito con
el desplazamiento del fallo, nunca una secuencia parcial en silencio.
"""

from __future__ import annotations

import hashlib
from functools import cache
from pathlib import Path

import pytest
from atalaya.sim.v1.ground_truth_pb2 import GroundTruth
from atalaya.v1.detection_pb2 import SENSOR_TYPE_ACOUSTIC, SENSOR_TYPE_ADSB, SENSOR_TYPE_REMOTE_ID
from atalaya.v1.envelope_pb2 import Envelope
from atalaya_contracts import envelope_io
from atalaya_contracts.envelope_io import ReplayFormatError
from hypothesis import given, settings
from hypothesis import strategies as st

from sim import replay
from sim.engine import encode_stream
from tests.contracts.test_roundtrip import GROUND_TRUTH, envelopes
from tests.sim.test_determinism import _cli, _parse_hashes

REPO = Path(__file__).resolve().parents[2]
SCENARIOS = REPO / "sim" / "scenarios"
NAMES = ("prision_ceuta", "puerto_ceuta", "aerodromo", "frontera_8km")


def _bytes(messages: list[Envelope] | list[GroundTruth]) -> list[bytes]:
    return [m.SerializeToString(deterministic=True) for m in messages]


# --- propiedad de ida y vuelta -------------------------------------------------------------


@pytest.mark.req("REQ-FUN-006")
@given(
    envs=st.lists(envelopes(), max_size=12),
    truth=st.lists(GROUND_TRUTH, max_size=5),
)
@settings(max_examples=150, derandomize=True, deadline=None)
def test_ida_y_vuelta_de_cualquier_secuencia(
    envs: list[Envelope], truth: list[GroundTruth]
) -> None:
    data = envelope_io.encode(envs, truth)
    back = envelope_io.decode(data)
    assert _bytes(back.envelopes) == _bytes(envs)
    assert _bytes(back.ground_truth) == _bytes(truth)
    assert (
        back.content_sha256 == hashlib.sha256(envelope_io.encode_content(envs, truth)).hexdigest()
    )


@pytest.mark.req("REQ-FUN-006")
def test_secuencia_vacia() -> None:
    back = envelope_io.decode(envelope_io.encode([]))
    assert back.envelopes == [] and back.ground_truth == []


@pytest.mark.req("REQ-FUN-003")
def test_codificacion_determinista_y_cabecera() -> None:
    env = Envelope(site_id="s", node_id="n", sequence=1)
    a = envelope_io.encode([env])
    assert a == envelope_io.encode([env])
    assert a[:8] == envelope_io.MAGIC
    assert int.from_bytes(a[8:10], "big") == envelope_io.FORMAT_VERSION == 1
    assert a[10:42] == hashlib.sha256(envelope_io.encode_content([env])).digest()


# --- replay de escenarios ------------------------------------------------------------------


@cache
def _recorded(name: str, seed: int = 21) -> replay.Recording:
    return replay.record(SCENARIOS / f"{name}.yaml", seed=seed, duration_s=420.0)


@pytest.mark.req("REQ-FUN-006")
@pytest.mark.parametrize("name", NAMES)
def test_replay_reproduce_envelopes_y_verdad_terreno_en_orden(name: str, tmp_path: Path) -> None:
    rec = _recorded(name)
    assert rec.envelopes and rec.ground_truth
    kinds = {e.WhichOneof("payload") for e in rec.envelopes}
    assert {"node_status", "detection"} <= kinds
    path = tmp_path / f"{name}.pb.zst"
    replay.write(path, rec)
    back = replay.read(path)
    assert _bytes(back.envelopes) == _bytes(rec.envelopes)
    assert _bytes(back.ground_truth) == _bytes(rec.ground_truth)
    assert [e.sequence for e in back.envelopes] == list(range(len(rec.envelopes)))


@pytest.mark.req("REQ-FUN-006")
def test_grabacion_incluye_todos_los_sensores_simulados() -> None:
    rec = _recorded("aerodromo")
    sensors = {
        e.detection.sensor_type for e in rec.envelopes if e.WhichOneof("payload") == "detection"
    }
    assert sensors == {SENSOR_TYPE_ACOUSTIC, SENSOR_TYPE_REMOTE_ID, SENSOR_TYPE_ADSB}
    assert {gt.is_forged for gt in rec.ground_truth} == {False, True}


@pytest.mark.req("REQ-FUN-006")
def test_negativa_sin_trama_zstd() -> None:
    with pytest.raises(ReplayFormatError, match="falta la trama") as err:
        envelope_io.decode(_sample()[: envelope_io.HEADER_LEN])
    assert err.value.offset == envelope_io.HEADER_LEN


@pytest.mark.req("REQ-FUN-003")
def test_replay_igual_a_nueva_ejecucion_con_la_misma_semilla(tmp_path: Path) -> None:
    rec = _recorded("aerodromo")
    again = replay.record(SCENARIOS / "aerodromo.yaml", seed=21, duration_s=420.0)
    assert replay.encode(rec) == replay.encode(again)
    assert replay.stream_sha256(rec) == hashlib.sha256(encode_stream(again.envelopes)).hexdigest()


# --- pruebas negativas ---------------------------------------------------------------------


@cache
def _sample() -> bytes:
    rec = _recorded("prision_ceuta")
    return replay.encode(rec)


@pytest.mark.req("REQ-FUN-006")
@pytest.mark.parametrize("cut", [0, 5, 9, 41, 42, 43, -1, -4, -50])
def test_negativa_fichero_truncado(cut: int) -> None:
    data = _sample()
    truncated = data[:cut] if cut >= 0 else data[: len(data) + cut]
    with pytest.raises(ReplayFormatError) as err:
        envelope_io.decode(truncated)
    assert "desplazamiento" in str(err.value)
    assert 0 <= err.value.offset <= len(truncated)


@pytest.mark.req("REQ-FUN-006")
@pytest.mark.parametrize("fraction", [0.0, 0.05, 0.12, 0.2, 0.5, 0.8, 0.99, 1.0])
def test_negativa_un_byte_alterado(fraction: float) -> None:
    data = bytearray(_sample())
    pos = min(len(data) - 1, int(fraction * (len(data) - 1)))
    data[pos] ^= 0x01
    with pytest.raises(ReplayFormatError) as err:
        envelope_io.decode(bytes(data))
    assert err.value.offset >= 0


@pytest.mark.req("REQ-FUN-006")
@pytest.mark.parametrize("pos", range(envelope_io.HEADER_LEN))
def test_negativa_cada_byte_de_la_cabecera(pos: int) -> None:
    data = bytearray(_sample())
    data[pos] ^= 0x80
    with pytest.raises(ReplayFormatError) as err:
        envelope_io.decode(bytes(data))
    expected = 0 if pos < 8 else 8 if pos < 10 else 10
    assert err.value.offset == expected


@pytest.mark.req("REQ-FUN-006")
@pytest.mark.parametrize("version", [0, 2, 255, 65535])
def test_negativa_version_de_formato_desconocida(version: int) -> None:
    data = bytearray(_sample())
    data[8:10] = version.to_bytes(2, "big")
    with pytest.raises(ReplayFormatError, match="versión de formato desconocida") as err:
        envelope_io.decode(bytes(data))
    assert err.value.offset == 8


@pytest.mark.req("REQ-FUN-006")
def test_negativa_datos_sobrantes_tras_la_trama() -> None:
    data = _sample() + b"\x00extra"
    with pytest.raises(ReplayFormatError, match="sobrantes") as err:
        envelope_io.decode(data)
    assert err.value.offset == len(_sample())


def _forge(content: bytes) -> bytes:
    """Fichero con contenido arbitrario pero cabecera y hash coherentes (fallos de registro)."""
    import zstandard

    frame = zstandard.ZstdCompressor(level=envelope_io.ZSTD_LEVEL).compress(content)
    return envelope_io.MAGIC + b"\x00\x01" + hashlib.sha256(content).digest() + frame


@pytest.mark.req("REQ-FUN-006")
@pytest.mark.parametrize(
    ("content", "offset", "message"),
    [
        (b"\x07\x00", 0, "tipo de registro desconocido"),
        (b"\x01", 0, "longitud truncada"),
        (b"\x01\x05abc", 0, "registro truncado"),
        (b"\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01", 0, "más de 10 bytes"),
        (b"\x01\x00\x01\x02\xff\xff", 2, "mensaje ilegible"),
    ],
)
def test_negativa_registros_invalidos_con_desplazamiento(
    content: bytes, offset: int, message: str
) -> None:
    with pytest.raises(ReplayFormatError, match=message) as err:
        envelope_io.decode(_forge(content))
    assert err.value.where == "contenido"
    assert err.value.offset == offset


@pytest.mark.req("REQ-FUN-006")
def test_negativa_nunca_devuelve_parciales() -> None:
    good = envelope_io.encode_content([Envelope(site_id="s", node_id="n", sequence=0)])
    with pytest.raises(ReplayFormatError) as err:
        envelope_io.decode(_forge(good + b"\x01\x09ab"))
    assert err.value.offset == len(good)


@pytest.mark.req("REQ-FUN-006")
def test_negativa_tipos_equivocados_al_escribir() -> None:
    with pytest.raises(TypeError):
        envelope_io.encode([GroundTruth()])  # type: ignore[list-item]
    with pytest.raises(TypeError):
        envelope_io.encode([], [Envelope()])  # type: ignore[list-item]


# --- CLI -----------------------------------------------------------------------------------


@pytest.mark.req("REQ-FUN-006")
@pytest.mark.subproceso
def test_cli_run_escribe_replay_y_replay_lo_lee(tmp_path: Path) -> None:
    out = tmp_path / "a.pb.zst"
    run = _cli(
        "run", "--scenario", str(SCENARIOS / "aerodromo.yaml"), "--seed", "21",
        "--duration", "420", "--out", str(out),
    )  # fmt: skip
    assert run.returncode == 0, run.stderr
    rec = _recorded("aerodromo")
    assert out.read_bytes() == replay.encode(rec)
    shown = _cli("replay", "--in", str(out), hashseed="7")
    assert shown.returncode == 0, shown.stderr
    fields = _parse_hashes(shown.stdout)
    assert fields["envelopes"] == str(len(rec.envelopes))
    assert fields["ground_truth"] == str(len(rec.ground_truth))
    assert fields["stream_sha256"] == _parse_hashes(run.stdout)["stream_sha256"]


@pytest.mark.req("REQ-FUN-006")
@pytest.mark.subproceso
def test_negativa_cli_replay_alterado_sale_con_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pb.zst"
    data = bytearray(_sample())
    data[8:10] = (9).to_bytes(2, "big")
    bad.write_bytes(bytes(data))
    shown = _cli("replay", "--in", str(bad))
    assert shown.returncode == 2
    assert "desplazamiento 8" in shown.stderr and "versión" in shown.stderr
    assert "envelopes=" not in shown.stdout
    truncated = tmp_path / "t.pb.zst"
    truncated.write_bytes(_sample()[:-10])
    hashed = _cli("hash", str(truncated))
    assert hashed.returncode == 2
    assert "desplazamiento" in hashed.stderr

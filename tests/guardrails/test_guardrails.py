"""Tests de scripts/guardrails.py: cada test intenta violar un guardarraíl.

Las muestras prohibidas se construyen por concatenación para que este fichero no
contenga los términos literales (y así no se bloquee a sí mismo ni dispare gitleaks).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts import guardrails as g

REPO = Path(__file__).resolve().parents[2]

# Muestras construidas por partes
TERMINOS = {
    "t01": "ja" + "mming",
    "t02": "ja" + "mmer",
    "t03": "spo" + "ofing",
    "t04": "de" + "auth",
    "t05": "take" + "over",
    "t06": "inhi" + "bir",
    "t07": "supla" + "ntar",
    "t08": "interfe" + "rir",
    "t09": "desaut" + "enticar",
    "t10": "neutra" + "lizar",
    "t11": "tomar el " + "control",
}
T01 = TERMINOS["t01"]


def reglas(path: str, contenido: str | bytes) -> set[str]:
    return {v.rule for v in g.check_file(path, contenido)}


# --- (a) transmisión SDR -----------------------------------------------------------
TX_MUESTRAS = [
    ("tools/x.sh", "hackrf" + "_transfer -t senal.iq -f 2440000000"),
    ("tools/x.sh", "hackrf" + "_transfer -c 127 -f 915000000"),
    ("edge/x.py", "sdr.setupStream(SOAPY_SDR_" + "TX, SOAPY_SDR_CF32)"),
    ("edge/x.py", "sdr.write" + "Stream(stream, [buf], len(buf))"),
    ("edge/x.py", "pluto = adi.Pluto(); pluto.t" + "x(muestras)"),
    ("edge/x.py", "pluto.tx_" + "hardwaregain_chan0 = -10"),
    ("edge/x.py", "pluto.tx_" + "lo = 2400000000"),
    ("edge/x.py", "snk = osmosdr." + "sink(args='hackrf')"),
    ("edge/x.c", "hackrf_start" + "_tx(device, callback, NULL);"),
    ("edge/x.c", "esp_wifi_80211" + "_tx(WIFI_IF_STA, frame, len, false);"),
    ("edge/x.c", "esp_ble_gap_start" + "_advertising(&adv_params);"),
    ("tools/x.sh", "sudo rpi" + "tx -m RF -i fichero.rf -f 434000"),
]


@pytest.mark.req("REQ-SEC-001", "REQ-LEG-002")
@pytest.mark.parametrize(("path", "linea"), TX_MUESTRAS)
def test_g02_transmision_sdr_bloqueada(path: str, linea: str) -> None:
    assert "sdr-tx" in reglas(path, linea + "\n")


@pytest.mark.req("REQ-SEC-001", "REQ-LEG-002")
def test_recepcion_sdr_permitida() -> None:
    codigo = (
        "sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)\n"
        "sdr.readStream(stream, [buf], len(buf))\n"
        "pluto.rx_lo = 2400000000\nmuestras = pluto.rx()\n"
        "hackrf_transfer -r captura.iq -f 2440000000\n"
    )
    assert reglas("edge/rx.py", codigo) == set()


# --- (b) términos ofensivos en código -----------------------------------------------
@pytest.mark.req("REQ-SEC-001", "REQ-LEG-001")
@pytest.mark.parametrize(
    "termino",
    list(TERMINOS.values()),
    ids=list(TERMINOS),
)
def test_g03_termino_ofensivo_en_codigo_bloqueado(termino: str) -> None:
    assert "offensive-term" in reglas("services/x.py", f"# modo {termino} del enlace\n")


@pytest.mark.req("REQ-SEC-001", "REQ-LEG-001")
def test_g03_termino_en_identificador_bloqueado() -> None:
    assert "offensive-term" in reglas("services/x.py", f"def start_{T01}() -> None: ...\n")


@pytest.mark.req("REQ-SEC-001")
def test_g04_identificador_defensivo_en_lista_blanca_permitido() -> None:
    ident = "spo" + "of_indicator"
    assert reglas("services/fusion/x.py", f"{ident} = score > 0.8\n") == set()


@pytest.mark.req("REQ-SEC-001")
def test_g04_vocabulario_defensivo_sin_terminos_permitido() -> None:
    assert reglas("services/x.py", "def detect_forged_remote_id(msg): ...\n") == set()


@pytest.mark.req("REQ-SEC-001")
def test_g04_identificador_parecido_no_listado_bloqueado() -> None:
    ident = "spo" + "of_remote_id"
    assert "offensive-term" in reglas("services/x.py", f"def {ident}(): ...\n")


@pytest.mark.req("REQ-SEC-001")
def test_terminos_en_documentacion_no_son_codigo() -> None:
    # La documentación se controla con check_spec.py (lista blanca de líneas revisadas).
    assert "offensive-term" not in reglas("docs/x.md", f"Prohibido el {T01}.\n")


@pytest.mark.req("REQ-SEC-001")
def test_interference_ingles_no_bloqueada() -> None:
    # «interference» (ruido RF) es vocabulario de medida legítimo.
    assert reglas("edge/rf.py", "snr_with_interference = 3.0\n") == set()


# --- (c) audio fuera de fixtures sintéticos --------------------------------------------
@pytest.mark.req("REQ-SEC-001", "REQ-LEG-005")
@pytest.mark.parametrize("ext", ["wav", "flac", "mp3", "ogg", "m4a", "opus", "aac", "aiff"])
def test_g01_audio_fuera_de_fixtures_bloqueado(ext: str) -> None:
    assert "audio-file" in reglas(f"ml/datasets/clip.{ext}", b"\x00\x01")


@pytest.mark.req("REQ-SEC-001", "REQ-LEG-005")
def test_g01_audio_renombrado_detectado_por_cabecera() -> None:
    wav = b"RIFF\x24\x00\x00\x00WAVEfmt "
    assert "audio-file" in reglas("ml/datasets/clip.bin", wav)


@pytest.mark.req("REQ-SEC-001", "REQ-LEG-005")
def test_g01_audio_en_fixtures_sinteticos_permitido() -> None:
    assert reglas("tests/fixtures/sinteticos/tono_1khz.wav", b"RIFF\x24\x00\x00\x00WAVE") == set()


# --- (d) datos de piloto/operador en esquemas públicos -------------------------------
@pytest.mark.req("REQ-SEC-001", "REQ-LEG-007")
def test_g05_pilot_en_proto_public_bloqueado() -> None:
    proto = "  double pilot_lat = 7 [(atalaya.v1.sensitivity) = PUBLIC];\n"
    assert "pilot-public" in reglas("proto/atalaya/v1/x.proto", proto)


@pytest.mark.req("REQ-SEC-001", "REQ-LEG-007")
def test_g05_operator_id_sin_sensibilidad_bloqueado() -> None:
    proto = "  string operator_id = 3;\n"
    assert "pilot-public" in reglas("proto/atalaya/v1/x.proto", proto)


@pytest.mark.req("REQ-SEC-001", "REQ-LEG-007")
def test_g05_pilot_fcse_only_permitido() -> None:
    proto = "  double pilot_lat = 7 [(atalaya.v1.sensitivity) = FCSE_ONLY];\n"
    assert reglas("proto/atalaya/v1/x.proto", proto) == set()


@pytest.mark.req("REQ-SEC-001", "REQ-LEG-007")
def test_g05_pilot_en_esquema_json_publico_bloqueado() -> None:
    js = '{"pilot_lon": {"type": "number", "sensitivity": "PUBLIC"}}\n'
    assert "pilot-public" in reglas("apps/incident-radar/schema.json", js)


# --- (e) secretos ------------------------------------------------------------------
SECRETOS = [
    "aws_key = 'AKIA" + "ABCDEFGHIJKLMNOP'",
    "-----BEGIN RSA " + "PRIVATE KEY-----",
    "token = 'ghp_" + "a" * 36 + "'",
    "password = '" + "S3cr3tPassw0rd!" + "'",
    "slack = 'xox" + "b-1234567890-abcdefghij'",
]


@pytest.mark.req("REQ-SEC-001", "REQ-SEC-012")
@pytest.mark.parametrize("linea", SECRETOS)
def test_g06_secreto_bloqueado(linea: str) -> None:
    assert "secret" in reglas("services/x.py", linea + "\n")


@pytest.mark.req("REQ-SEC-001", "REQ-SEC-012")
@pytest.mark.parametrize("nombre", [".env", ".env.local", "secrets/ca.key", "infra/secrets/x"])
def test_g06_fichero_de_secretos_bloqueado(nombre: str) -> None:
    assert "secret-file" in reglas(nombre, "X=1\n")


@pytest.mark.req("REQ-SEC-001")
def test_env_example_permitido() -> None:
    assert reglas(".env.example", "MQTT_PASSWORD=\n") == set()


@pytest.mark.req("REQ-SEC-001")
def test_variable_password_sin_valor_permitida() -> None:
    assert reglas("services/x.py", "password = os.environ['MQTT_PASSWORD']\n") == set()


# --- CLI ------------------------------------------------------------------------------
def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo_tmp(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "test")
    return tmp_path


def _cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(REPO / "scripts" / "guardrails.py"), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


@pytest.mark.req("REQ-SEC-001")
@pytest.mark.subproceso
def test_cli_staged_bloquea_con_exit_2(repo_tmp: Path) -> None:
    (repo_tmp / "x.py").write_text(f"MODE = '{T01}'\n")
    _git(repo_tmp, "add", "x.py")
    r = _cli(repo_tmp, "--staged")
    assert r.returncode == 2
    assert "offensive-term" in r.stderr
    assert "x.py" in r.stderr


@pytest.mark.req("REQ-SEC-001")
@pytest.mark.subproceso
def test_cli_staged_limpio_exit_0(repo_tmp: Path) -> None:
    (repo_tmp / "x.py").write_text("MODE = 'listen'\n")
    _git(repo_tmp, "add", "x.py")
    assert _cli(repo_tmp, "--staged").returncode == 0


@pytest.mark.req("REQ-SEC-001")
@pytest.mark.subproceso
def test_cli_staged_usa_contenido_del_indice_no_del_disco(repo_tmp: Path) -> None:
    f = repo_tmp / "x.py"
    f.write_text(f"MODE = '{T01}'\n")
    _git(repo_tmp, "add", "x.py")
    f.write_text("MODE = 'listen'\n")  # el disco está limpio, el índice no
    assert _cli(repo_tmp, "--staged").returncode == 2


@pytest.mark.req("REQ-SEC-003")
@pytest.mark.subproceso
def test_cli_range_analiza_commits(repo_tmp: Path) -> None:
    (repo_tmp / "a.py").write_text("x = 1\n")
    _git(repo_tmp, "add", ".")
    _git(repo_tmp, "commit", "-qm", "base")
    (repo_tmp / "clip.wav").write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
    _git(repo_tmp, "add", "-f", ".")
    _git(repo_tmp, "commit", "-qm", "audio")
    r = _cli(repo_tmp, "--range", "HEAD~1..HEAD")
    assert r.returncode == 2
    assert "audio-file" in r.stderr


@pytest.mark.req("REQ-SEC-001")
@pytest.mark.subproceso
def test_cli_paths(tmp_path: Path) -> None:
    f = tmp_path / "x.c"
    f.write_text("hackrf_start" + "_tx(d, cb, NULL);\n")
    assert _cli(tmp_path, "--paths", str(f)).returncode == 2


@pytest.mark.req("REQ-SEC-001")
@pytest.mark.subproceso
def test_cli_sin_argumentos_es_error_de_uso(tmp_path: Path) -> None:
    r = _cli(tmp_path)
    assert r.returncode not in (0, 2)


@pytest.mark.req("REQ-SEC-001")
@pytest.mark.subproceso
def test_cli_borrado_de_fichero_no_falla(repo_tmp: Path) -> None:
    (repo_tmp / "a.py").write_text("x = 1\n")
    _git(repo_tmp, "add", ".")
    _git(repo_tmp, "commit", "-qm", "base")
    _git(repo_tmp, "rm", "-q", "a.py")
    assert _cli(repo_tmp, "--staged").returncode == 0


@pytest.mark.req("REQ-SEC-002")
@pytest.mark.parametrize(
    ("comando", "bloqueado"),
    [
        ("cat .env", True),
        ("grep KEY .env.local", True),
        ("less secrets/ca.key", True),
        ("hackrf" + "_transfer -t x.iq -f 2.4e9", True),
        ("git push --force origin main", True),
        ("git push -f", True),
        ("cat README.md", False),
        ("hackrf_transfer -r captura.iq -f 2.4e9", False),
        ("git push origin main", False),
        ("ls .envrc-docs", False),
    ],
)
def test_comando_bash_peligroso(comando: str, bloqueado: bool) -> None:
    assert (g.check_command(comando) != []) is bloqueado


# --- en proceso (cobertura de main y casos límite) ---------------------------------
@pytest.mark.req("REQ-SEC-001")
def test_main_staged_en_proceso(repo_tmp: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo_tmp)
    (repo_tmp / "x.py").write_text(f"MODE = '{T01}'\n")
    _git(repo_tmp, "add", "x.py")
    assert g.main(["--staged"]) == g.EXIT_BLOCKED


@pytest.mark.req("REQ-SEC-003")
def test_main_range_en_proceso(repo_tmp: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo_tmp)
    (repo_tmp / "a.py").write_text("x = 1\n")
    _git(repo_tmp, "add", ".")
    _git(repo_tmp, "commit", "-qm", "base")
    (repo_tmp / "b.py").write_text("y = 2\n")
    _git(repo_tmp, "add", ".")
    _git(repo_tmp, "commit", "-qm", "limpio")
    assert g.main(["--range", "HEAD~1..HEAD"]) == 0


@pytest.mark.req("REQ-SEC-001")
def test_main_paths_en_proceso(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ok.py").write_text("x = 1\n")
    assert g.main(["--paths", "ok.py", "no_existe.py"]) == 0
    (tmp_path / "clip.wav").write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
    assert g.main(["--paths", "clip.wav"]) == g.EXIT_BLOCKED


@pytest.mark.req("REQ-SEC-002")
def test_main_command_en_proceso(capsys: pytest.CaptureFixture[str]) -> None:
    assert g.main(["--command", "cat .env"]) == g.EXIT_BLOCKED
    assert "secret-file" in capsys.readouterr().err
    assert g.main(["--command", "ls -la"]) == 0


@pytest.mark.req("REQ-SEC-001")
def test_main_error_de_uso_no_es_bloqueo() -> None:
    with pytest.raises(SystemExit) as exc:
        g.main([])
    assert exc.value.code == g.EXIT_USAGE
    assert g.EXIT_USAGE != g.EXIT_BLOCKED


@pytest.mark.req("REQ-SEC-001")
def test_lista_blanca_ausente_no_permite_nada(tmp_path: Path) -> None:
    allow = g.load_allowlist(tmp_path / "no_existe.txt")
    assert allow == frozenset()
    ident = "spo" + "of_indicator"
    assert "offensive-term" in {v.rule for v in g.check_file("x.py", f"{ident} = 1\n", allow)}


@pytest.mark.req("REQ-SEC-001")
def test_lista_blanca_ignora_comentarios(tmp_path: Path) -> None:
    f = tmp_path / "allow.txt"
    f.write_text("# comentario\n\nalfa   # nota\n")
    assert g.load_allowlist(f) == frozenset({"alfa"})


@pytest.mark.req("REQ-SEC-001")
def test_binario_no_se_analiza_como_texto() -> None:
    data = b"\x00\x01\x02" + T01.encode()
    assert reglas("ml/models/m.bin", data) == set()


@pytest.mark.req("REQ-SEC-001")
def test_latin1_se_analiza() -> None:
    data = f"# ñ modo {T01}\n".encode("latin-1")
    assert "offensive-term" in reglas("services/x.py", data)


@pytest.mark.req("REQ-SEC-001")
def test_violation_str_incluye_linea() -> None:
    v = g.Violation("a.py", "sdr-tx", "detalle", 3)
    assert str(v) == "[sdr-tx] a.py:3: detalle"
    assert str(g.Violation("a.py", "secret-file", "d")) == "[secret-file] a.py: d"


@pytest.mark.req("REQ-SEC-001")
def test_ruta_con_punto_barra_se_normaliza() -> None:
    assert "audio-file" in reglas("./tests/fixtures/otro/clip.wav", b"")
    assert reglas("./tests/fixtures/sinteticos/clip.wav", b"") == set()


@pytest.mark.req("REQ-SEC-001")
def test_env_con_punto_barra_sigue_bloqueado() -> None:
    assert "secret-file" in reglas("./.env", "X=1\n")


# --- contrato exacto de los informes (dónde y qué; lo que lee quien corrige) ----------
@pytest.mark.req("REQ-SEC-001")
def test_informe_exacto_por_regla() -> None:
    contenido = (
        "x = 1\n"
        "y = 2\n"
        "hackrf" + "_start_tx(d, cb, NULL)\n"
        f"modo = '{T01}'\n"
        "password = '" + "S3cr3tPassw0rd!" + "'\n"
    )
    got = [str(v) for v in g.check_file("edge/n.py", contenido, frozenset())]
    assert got == [
        "[sdr-tx] edge/n.py:3: transmisión por radio (REQ-LEG-002)",
        f"[offensive-term] edge/n.py:4: «{T01}» (REQ-LEG-001)",
        "[secret] edge/n.py:5: posible secreto",
    ]


@pytest.mark.req("REQ-SEC-001", "REQ-LEG-007")
def test_informe_exacto_pilot() -> None:
    got = [str(v) for v in g.check_file("p.proto", "a\n  string pilot_id = 2;\n", frozenset())]
    assert got == ["[pilot-public] p.proto:2: «pilot_id» debe ser FCSE_ONLY (REQ-LEG-007)"]


@pytest.mark.req("REQ-SEC-001")
def test_informe_exacto_ficheros() -> None:
    assert [str(v) for v in g.check_file(".env", "", frozenset())] == [
        "[secret-file] .env: fichero de secretos versionado"
    ]
    assert [str(v) for v in g.check_file("a/b.wav", b"", frozenset())] == [
        "[audio-file] a/b.wav: audio fuera de tests/fixtures/sinteticos/ (REQ-LEG-005)"
    ]


@pytest.mark.req("REQ-SEC-001")
def test_makefile_se_analiza_como_codigo() -> None:
    assert "sdr-tx" in reglas("Makefile", "tx:\n\trpi" + "tx -f 434000\n")


@pytest.mark.req("REQ-SEC-002")
@pytest.mark.parametrize(
    ("comando", "esperado"),
    [
        ("cat .env", ["[secret-file] <bash>: acceso a .env o secrets/"]),
        ("rpi" + "tx -f 434000", ["[sdr-tx] <bash>: transmisión por radio (REQ-LEG-002)"]),
        ("git push --force", ["[force-push] <bash>: git push forzado"]),
        ("ls", []),
    ],
)
def test_check_command_exacto(comando: str, esperado: list[str]) -> None:
    assert [str(v) for v in g.check_command(comando)] == esperado


# --- identificadores y lista blanca ------------------------------------------------
@pytest.mark.req("REQ-SEC-001")
def test_lista_blanca_usa_el_identificador_completo() -> None:
    allow = frozenset({"remote_id_" + "spo" + "of_indicator"})
    ok = "x = remote_id_" + "spo" + "of_indicator\n"
    assert g.check_file("a.py", ok, allow) == []
    # el fragmento final solo no está en la lista: se bloquea
    solo = "x = spo" + "of_indicator\n"
    assert [v.rule for v in g.check_file("a.py", solo, allow)] == ["offensive-term"]


@pytest.mark.req("REQ-SEC-001")
def test_lista_blanca_con_varios_comentarios(tmp_path: Path) -> None:
    f = tmp_path / "allow.txt"
    f.write_text("alfa # nota # otra\n")
    assert g.load_allowlist(f) == frozenset({"alfa"})


@pytest.mark.req("REQ-SEC-001")
def test_binario_con_extension_de_codigo_se_analiza_igualmente() -> None:
    # Antes este test daba por buena la evasión con un NUL (hallazgo P5): ahora se analiza.
    assert "offensive-term" in reglas("x.py", b"\x00\x01\x02" + T01.encode())


# --- fallo cerrado: si no se puede verificar, se bloquea -----------------------------
@pytest.mark.req("REQ-SEC-001", "REQ-SEC-003")
def test_rango_invalido_bloquea(repo_tmp: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo_tmp)
    (repo_tmp / "a.py").write_text("x = 1\n")
    _git(repo_tmp, "add", ".")
    _git(repo_tmp, "commit", "-qm", "base")
    assert g.main(["--range", "no-existe..HEAD"]) == g.EXIT_BLOCKED


@pytest.mark.req("REQ-SEC-001")
def test_staged_fuera_de_repo_bloquea(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert g.main(["--staged"]) == g.EXIT_BLOCKED


@pytest.mark.req("REQ-SEC-003")
@pytest.mark.parametrize("sep", ["..", "..."])
def test_rango_dos_y_tres_puntos(repo_tmp: Path, monkeypatch: pytest.MonkeyPatch, sep: str) -> None:
    monkeypatch.chdir(repo_tmp)
    (repo_tmp / "a.py").write_text("x = 1\n")
    _git(repo_tmp, "add", ".")
    _git(repo_tmp, "commit", "-qm", "base")
    (repo_tmp / "b.py").write_text(f"m = '{T01}'\n")
    _git(repo_tmp, "add", ".")
    _git(repo_tmp, "commit", "-qm", "malo")
    assert g.main(["--range", f"HEAD~1{sep}HEAD"]) == g.EXIT_BLOCKED
    assert g.main(["--range", "HEAD~1.."]) == g.EXIT_BLOCKED  # cabeza implícita = HEAD


@pytest.mark.req("REQ-SEC-001")
def test_borrado_en_proceso_no_falla(repo_tmp: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo_tmp)
    (repo_tmp / "a.py").write_text("x = 1\n")
    _git(repo_tmp, "add", ".")
    _git(repo_tmp, "commit", "-qm", "base")
    _git(repo_tmp, "rm", "-q", "a.py")
    assert g.main(["--staged"]) == 0


@pytest.mark.req("REQ-SEC-001")
def test_error_de_uso_explica_el_motivo(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        g.main(["--staged", "--paths", "x"])
    err = capsys.readouterr().err
    assert "usage:" in err
    assert "error:" in err


@pytest.mark.req("REQ-SEC-001")
def test_cabecera_del_informe(capsys: pytest.CaptureFixture[str]) -> None:
    assert g.main(["--command", "cat .env"]) == g.EXIT_BLOCKED
    err = capsys.readouterr().err.splitlines()
    assert err[0].startswith("GUARDARRAÍL: cambio bloqueado")
    assert err[1] == "  [secret-file] <bash>: acceso a .env o secrets/"


@pytest.mark.req("REQ-SEC-001")
def test_staged_limpio_en_proceso(repo_tmp: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo_tmp)
    (repo_tmp / "x.py").write_text("MODE = 'listen'\n")
    _git(repo_tmp, "add", "x.py")
    assert g.main(["--staged"]) == 0


@pytest.mark.req("REQ-SEC-003")
def test_rango_que_no_termina_en_head(repo_tmp: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo_tmp)
    b = repo_tmp / "b.py"
    b.write_text("x = 1\n")
    _git(repo_tmp, "add", ".")
    _git(repo_tmp, "commit", "-qm", "base")
    b.write_text(f"m = '{T01}'\n")
    _git(repo_tmp, "commit", "-qam", "malo")
    b.write_text("m = 'ok'\n")
    _git(repo_tmp, "commit", "-qam", "arreglado")
    # se analiza el contenido de HEAD~1 (malo), no el de HEAD (limpio)
    assert g.main(["--range", "HEAD~2..HEAD~1"]) == g.EXIT_BLOCKED
    assert g.main(["--range", "HEAD~1.."]) == 0


@pytest.mark.req("REQ-SEC-001")
def test_fallo_cerrado_explica_el_motivo(
    repo_tmp: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(repo_tmp)
    assert g.main(["--range", "no-existe..HEAD"]) == g.EXIT_BLOCKED
    err = capsys.readouterr().err
    assert err.startswith("GUARDARRAÍL: no se pudo verificar (")
    assert err.rstrip().endswith("bloqueado por seguridad.")


# --- evasión de los hooks ------------------------------------------------------------
@pytest.mark.req("REQ-SEC-003")
@pytest.mark.parametrize(
    ("comando", "bloqueado"),
    [
        ("git commit --no-verify -m x", True),
        ("git commit -nm x", True),
        ("git commit -n -m x", True),
        ("git -c core.hooksPath=/dev/null commit -m x", True),
        ("git config core.hooksPath ''", True),
        ("git config --unset core.hooksPath", True),
        ("git commit -m 'no verify needed'", False),
        ("git commit -m x", False),
        ("git config --get core.hooksPath", False),
    ],
)
def test_evasion_de_hooks(comando: str, bloqueado: bool) -> None:
    reglas_cmd = {v.rule for v in g.check_command(comando)}
    assert ("hook-bypass" in reglas_cmd) is bloqueado


# --- .claude/settings.json: nombrar TX solo para DENEGARLO ----------------------------
def _settings(deny: list[str], allow: list[str]) -> str:
    import json

    return json.dumps({"permissions": {"deny": deny, "allow": allow}}, indent=2)


@pytest.mark.req("REQ-SEC-002", "REQ-LEG-002")
def test_settings_tx_en_deny_permitido() -> None:
    txt = _settings(["Bash(rpi" + "tx *)", "Bash(send" + "iq *)"], [])
    assert reglas(".claude/settings.json", txt) == set()


@pytest.mark.req("REQ-SEC-002", "REQ-LEG-002")
def test_settings_tx_en_allow_bloqueado() -> None:
    txt = _settings([], ["Bash(rpi" + "tx *)"])
    assert "sdr-tx" in reglas(".claude/settings.json", txt)


@pytest.mark.req("REQ-SEC-002", "REQ-LEG-002")
def test_settings_tx_en_hook_bloqueado() -> None:
    import json

    txt = json.dumps({"hooks": {"Stop": [{"hooks": [{"command": "rpi" + "tx -f 434"}]}]}})
    assert "sdr-tx" in reglas(".claude/settings.json", txt)


@pytest.mark.req("REQ-SEC-002")
def test_settings_ilegible_se_analiza_entero() -> None:
    assert "sdr-tx" in reglas(".claude/settings.json", '{"deny": ["rpi' + 'tx" ')


@pytest.mark.req("REQ-SEC-002")
def test_settings_con_permissions_sin_deny() -> None:
    txt = _settings([], []).replace('"deny": [],', "")
    assert '"deny"' not in txt
    assert reglas(".claude/settings.json", txt) == set()


@pytest.mark.req("REQ-SEC-003")
def test_hook_bypass_informe_exacto() -> None:
    got = [str(v) for v in g.check_command("git commit --no-verify -m x")]
    assert got == ["[hook-bypass] <bash>: evasión de los hooks de git"]


# === Correcciones de la revisión P5 de la FASE 0 ======================================
@pytest.mark.req("REQ-SEC-001")
def test_p5_nul_en_fichero_de_codigo_no_anula_el_analisis() -> None:
    contenido = b"/* \x00 */\nMODE = '" + T01.encode() + b"'\n"
    assert "offensive-term" in reglas("edge/x.c", contenido)


@pytest.mark.req("REQ-SEC-001")
@pytest.mark.parametrize("ruta", ["tools/script", "Dockerfile", "nb.ipynb", "flujo.grc", "a.cfg"])
def test_p5_mas_tipos_de_fichero_se_analizan(ruta: str) -> None:
    contenido = ("#!/bin/sh\n" if ruta == "tools/script" else "") + f"modo={T01}\n"
    assert "offensive-term" in reglas(ruta, contenido)


@pytest.mark.req("REQ-SEC-001")
def test_p5_homoglifo_cirilico() -> None:
    assert "offensive-term" in reglas("x.py", "MODE = 'jа" + "mming'\n")


@pytest.mark.req("REQ-SEC-001", "REQ-LEG-007")
@pytest.mark.parametrize(
    "linea",
    [
        "  string uas_operator_id = 1 [(atalaya.v1.sensitivity) = PUBLIC];",
        "  string operatorId = 1;",
        "  double piloto_lat = 2;",
        "  double pilot_lat = 7 [(atalaya.v1.sensitivity) = PUBLIC]; // pasar a FCSE_ONLY",
    ],
)
def test_p5_pilot_public_variantes(linea: str) -> None:
    assert "pilot-public" in reglas("x.proto", linea + "\n")


@pytest.mark.req("REQ-SEC-001", "REQ-LEG-007")
@pytest.mark.parametrize(
    ("ruta", "linea"),
    [
        ("x.proto", "  string uas_operator_id = 1 [(atalaya.v1.sensitivity) = FCSE_ONLY];"),
        ("x.json", '{"pilot_lat": {"type": "number", "sensitivity": "FCSE_ONLY"}}'),
        ("x.yaml", "pilot_lat: {type: number, sensitivity: FCSE_ONLY}"),
    ],
)
def test_p5_pilot_fcse_only_real(ruta: str, linea: str) -> None:
    assert reglas(ruta, linea + "\n") == set()


@pytest.mark.req("REQ-SEC-001", "REQ-SEC-012")
@pytest.mark.parametrize(
    ("ruta", "linea"),
    [
        ("cfg.json", '{"password": "' + "S3cr3tPassw0rd!" + '"}'),
        ("compose.yaml", "      POSTGRES_PASSWORD: " + "hunter2hunter2"),
    ],
)
def test_p5_secretos_json_y_entorno(ruta: str, linea: str) -> None:
    assert "secret" in reglas(ruta, linea + "\n")


@pytest.mark.req("REQ-SEC-001")
@pytest.mark.parametrize(
    "linea",
    [
        "      MQTT_PASSWORD: ${MQTT_PASSWORD:?falta}",
        "REDIS_PASSWORD=",
        "password = os.environ['X']",
    ],
)
def test_p5_referencias_a_secretos_no_son_secretos(linea: str) -> None:
    assert reglas("c.yaml", linea + "\n") == set()


@pytest.mark.req("REQ-SEC-001")
def test_p5_envrc_es_fichero_de_secretos() -> None:
    assert "secret-file" in reglas(".envrc", "export X=1\n")


@pytest.mark.req("REQ-SEC-001", "REQ-LEG-005")
@pytest.mark.parametrize(
    ("ruta", "contenido"),
    [
        ("d.dat", b"\xff\xfb\x90\x64" + b"\x00" * 12),
        ("a.pcm", b"\x01"),
        ("a.webm", b"\x1a"),
        ("a.amr", b"#"),
    ],
)
def test_p5_audio_adicional(ruta: str, contenido: bytes) -> None:
    assert "audio-file" in reglas(ruta, contenido)


@pytest.mark.req("REQ-SEC-003")
@pytest.mark.parametrize(
    "comando",
    [
        "git commit --no-veri -m x",
        "git commit-tree HEAD^{tree} -m x",
        "chmod -x .githooks/pre-commit",
        "rm -rf .githooks",
        "git push origin +main",
    ],
)
def test_p5_evasion_de_hooks_y_push(comando: str) -> None:
    assert g.check_command(comando) != []


@pytest.mark.req("REQ-SEC-002")
@pytest.mark.parametrize("comando", ["cat .e*", "cat secret?/ca.key", "cat '.env'", 'cat ".env"'])
def test_p5_acceso_a_secretos_con_comodines_o_comillas(comando: str) -> None:
    assert {v.rule for v in g.check_command(comando)} == {"secret-file"}


@pytest.mark.req("REQ-SEC-003")
@pytest.mark.parametrize(
    "comando", ["git push origin main", "ls *.py", "git commit -m 'no-verify'", "git commit -am x"]
)
def test_p5_comandos_legitimos(comando: str) -> None:
    assert g.check_command(comando) == []


@pytest.mark.req("REQ-SEC-002")
def test_p5_settings_no_ascii_se_analiza() -> None:
    import json

    txt = json.dumps({"hooks": {"Stop": [{"hooks": [{"command": "tomó el con" + "trol"}]}]}})
    assert "offensive-term" in reglas(".claude/settings.json", txt)


@pytest.mark.req("REQ-SEC-002", "REQ-LEG-007")
def test_p5_settings_pilot_y_fcse_en_otra_clave() -> None:
    import json

    txt = json.dumps({"a": {"pilot_lat": "PUBLIC"}, "b": "FCSE_ONLY"}, indent=2)
    assert "pilot-public" in reglas(".claude/settings.json", txt)


@pytest.mark.req("REQ-SEC-001")
def test_p5_identificador_de_lista_blanca_que_empieza_por_el_termino() -> None:
    ident = T01 + "_detector"
    assert g.check_file("a.py", f"{ident} = 1\n", frozenset({ident})) == []


@pytest.mark.req("REQ-SEC-003")
def test_p5_rango_sin_dos_puntos_es_error_de_uso() -> None:
    with pytest.raises(SystemExit) as exc:
        g.main(["--range", "HEAD"])
    assert exc.value.code == g.EXIT_USAGE


# --- mutantes supervivientes tras las correcciones P5 ---------------------------------
@pytest.mark.req("REQ-SEC-001", "REQ-SEC-012")
def test_p5_texto_no_codigo_se_analiza_por_secretos() -> None:
    assert "secret" in reglas("notas.txt", "aws_key = 'AKIA" + "ABCDEFGHIJKLMNOP'\n")


@pytest.mark.req("REQ-SEC-001")
def test_p5_binario_no_codigo_no_se_analiza_como_texto() -> None:
    assert reglas("modelo.bin", b"\x00\x01" + T01.encode()) == set()


@pytest.mark.req("REQ-SEC-001")
def test_p5_dockerfile_con_sufijo() -> None:
    assert "offensive-term" in reglas("infra/Dockerfile.prod", f"RUN echo {T01}\n")


@pytest.mark.req("REQ-SEC-001")
def test_p5_sin_extension_ni_shebang_no_es_codigo() -> None:
    assert reglas("NOTAS", f"texto {T01}\n") == set()


@pytest.mark.req("REQ-SEC-001", "REQ-LEG-007")
def test_p5_comentario_que_imita_la_sensibilidad_no_cuenta() -> None:
    linea = (
        "  double pilot_lat = 7 [(atalaya.v1.sensitivity) = PUBLIC]; // sensitivity = FCSE_ONLY\n"
    )
    assert "pilot-public" in reglas("x.proto", linea)


@pytest.mark.req("REQ-SEC-002")
def test_p5_comodin_en_ruta_anidada_hacia_secrets() -> None:
    assert {v.rule for v in g.check_command("cat infra/secret?/ca.key")} == {"secret-file"}


@pytest.mark.req("REQ-SEC-001", "REQ-LEG-005")
def test_p5_trama_mpeg_minima() -> None:
    assert "audio-file" in reglas("x.dat", b"\xff\xfb")


@pytest.mark.req("REQ-SEC-001", "REQ-SEC-012")
def test_relevo_secretos_en_texto_bytes() -> None:
    assert "secret" in reglas("notas.txt", b"aws_key = 'AKIA" + b"ABCDEFGHIJKLMNOP'\n")


@pytest.mark.req("REQ-LEG-007")
def test_relevo_json_sensibilidad_de_campo_vecino() -> None:
    import json

    data = {"pilot_lat": {"type": "number"}, "private_field": {"sensitivity": "FCSE_ONLY"}}
    assert "pilot-public" in reglas("schema.json", json.dumps(data))
    data["pilot_lat"]["sensitivity"] = "FCSE_ONLY"
    assert "pilot-public" not in reglas("schema.json", json.dumps(data))


@pytest.mark.req("REQ-LEG-007")
@pytest.mark.parametrize("sensitivity", ["PUBLIC", "OPERATOR", "FCSE_ONLY"])
def test_relevo_json_descriptor(sensitivity: str) -> None:
    import json

    descriptor = {"fields": [{"name": "pilot_lat", "sensitivity": sensitivity}]}
    assert ("pilot-public" in reglas("schema.json", json.dumps(descriptor))) == (
        sensitivity != "FCSE_ONLY"
    )

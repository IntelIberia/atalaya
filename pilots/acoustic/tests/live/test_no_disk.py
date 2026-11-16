"""H2.8: ninguna muestra llega a disco. Tres capas con pruebas negativas que se ejecutan siempre."""

from __future__ import annotations

import http.client
import importlib.util
import json
import os
import signal
import socket
import subprocess
import sys
import textwrap
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest
from live_helpers import write_artifact

from live import privacy
from live.alert import AlertMachine
from live.artifact import load_artifact
from live.capture import CaptureEngine
from live.privacy import AuditViolation, WriteAudit, scan_package, scan_source, snapshot
from live.server import AlertBoard, LocalAlertServer
from live.synthetic import SyntheticSource, harmonic_comb

pytestmark = pytest.mark.req("REQ-PRIV-002", "REQ-LEG-005", "REQ-LEG-006", "REQ-PRIV-003")

PILOT_DIR = Path(__file__).resolve().parents[2]

# Módulos de prueba inyectados SOLO aquí: deben ser atrapados por las capas (a) y (b).
WAV_WRITER = textwrap.dedent(
    """
    import wave

    import numpy as np


    def leak(window, path):
        with wave.open(str(path), "wb") as fh:
            fh.setnchannels(1)
            fh.setsampwidth(2)
            fh.setframerate(16000)
            fh.writeframes((np.asarray(window) * 32767).astype("<i2").tobytes())
    """
)
NP_SAVER = textwrap.dedent(
    """
    import numpy as np


    def leak(buffer, path):
        np.save(path, buffer)
    """
)


def _load_module(tmp_path: Path, name: str, source: str) -> ModuleType:
    path = tmp_path / f"{name}.py"
    path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- (a) estática -----------------------------------------------------------------------


def test_live_package_has_no_static_violations() -> None:
    violations = scan_package()
    assert violations == [], "\n".join(map(str, violations))
    assert len(list(privacy.LIVE_DIR.glob("*.py"))) >= 6  # analiza el subpaquete real


def test_static_layer_catches_injected_wav_writer() -> None:
    rules = {v.rule for v in scan_source(WAV_WRITER, "bad_wav.py")}
    assert "import-prohibido" in rules


def test_static_layer_catches_injected_np_save() -> None:
    hits = [v.detail for v in scan_source(NP_SAVER, "bad_np.py")]
    assert "np.save" in hits


@pytest.mark.parametrize(
    "snippet",
    [
        "open('x.wav', 'wb')",
        "open(path, mode)",
        "import pickle",
        "from scipy.io import wavfile",
        "import soundfile as sf",
        "from numpy import savez",
        "buf.tofile('x.raw')",
        "Path('x').write_bytes(b'')",
        "os.write(fd, data)",
        "np.memmap('x', dtype='float32', mode='w+', shape=(4,))",
        "logging.info('ventana %s', window)",
        "logger.debug(samples)",
        "print(block[:10])",
        "import tempfile",
    ],
)
def test_static_layer_catches_each_forbidden_pattern(snippet: str) -> None:
    assert scan_source(snippet, "bad.py"), snippet


def test_static_layer_allows_reading_and_scalar_logs() -> None:
    ok = "open('a.json', 'rb')\nlogger.info('estado %s p=%.2f', state, prob)\nprint(len(rows))\n"
    assert scan_source(ok, "ok.py") == []


def test_no_recording_mode_exists() -> None:
    # REQ-LEG-006: no hay ninguna opción de sesión de grabación en el subpaquete.
    for path in privacy.LIVE_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for flag in ("--record", "--grab", "--save-audio", "--dump"):
            assert flag not in text, f"{path.name}: {flag}"


# --- (b) dinámica -----------------------------------------------------------------------


def test_full_simulated_session_writes_nothing(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    json_path, hashes = write_artifact(tmp_path / "model")
    loaded = load_artifact(json_path, hashes_file=hashes)  # la carga lee; sucede antes
    watched = [tmp_path, home, PILOT_DIR / "live"]
    before = snapshot(watched)

    src = SyntheticSource(48_000, harmonic_comb(), seed=7)
    engine = CaptureEngine(src)
    machine = AlertMachine(loaded.config.alert)
    board = AlertBoard()
    inferred = statuses = 0
    with WriteAudit() as audit:
        page = LocalAlertServer(board, 0)  # la página va incluida en la sesión auditada
        page.start_in_thread()
        engine.start()
        for step in range(120 * 4):  # 120 s simulados en bloques de 0,25 s
            src.pump(0.25)
            while (window := engine.next_window()) is not None:
                emb, scores = loaded.model.infer(window.samples)
                # Probabilidad de juguete (el clasificador real es H2.10): solo un escalar sale.
                prob = 0.9 if (inferred // 20) % 2 else 0.1
                d = machine.update(window.start / 16_000, probability=prob)
                board.publish({"state": d.state.value, "probability": d.probability})
                inferred += 1
                del emb, scores, window
            if step % 40 == 0:
                statuses += _exercise_page(page, board)
        engine.stop()
        page.stop()

    assert audit.events == []
    assert inferred >= 240 and statuses == 12 * 4
    assert snapshot(watched) == before
    assert not engine.ring.raw_view_for_tests().any()


def _exercise_page(page: LocalAlertServer, board: AlertBoard) -> int:
    """GET de la página, del estado y de eventos, y un POST de etiqueta; devuelve los 200."""
    port = page.server_address[1]
    ok = 0
    for method, path, body in (
        ("GET", "/", None),
        ("GET", "/state", None),
        ("POST", "/label", json.dumps({"label": "dron"}).encode()),
    ):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        headers = {"X-Atalaya-Token": board.token, "Content-Type": "application/json"}
        conn.request(method, path, body=body, headers=headers)
        ok += conn.getresponse().status == 200
        conn.close()
    page.max_events = 1
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", f"/events?token={board.token}")
    resp = conn.getresponse()
    ok += resp.status == 200 and resp.read().startswith(b"data: ")
    conn.close()
    return ok


# wave.Wave_write.__del__ falla al limpiar un fichero que nunca llegó a abrirse: es lo esperado.
@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
def test_dynamic_layer_blocks_injected_wav_writer(tmp_path: Path) -> None:
    module = _load_module(tmp_path, "bad_wav", WAV_WRITER)
    target = tmp_path / "fuga.wav"
    with WriteAudit() as audit, pytest.raises(AuditViolation):
        module.leak(np.zeros(15_360, dtype=np.float32), target)
    assert any("fuga.wav" in e for e in audit.events)
    assert not target.exists()


def test_dynamic_layer_blocks_injected_np_save(tmp_path: Path) -> None:
    module = _load_module(tmp_path, "bad_np", NP_SAVER)
    target = tmp_path / "fuga.npy"
    with WriteAudit() as audit, pytest.raises(AuditViolation):
        module.leak(np.ones(64_000, dtype=np.float32), target)
    assert audit.events and not target.exists()


@pytest.mark.parametrize(
    "action",
    [
        lambda p: p.write_bytes(b"RIFF"),
        lambda p: np.ones(4, dtype=np.float32).tofile(p),
        lambda p: os.close(os.open(p, os.O_WRONLY | os.O_CREAT)),
        lambda p: os.rename(p.with_name("existe.txt"), p),
        lambda p: os.remove(p.with_name("existe.txt")),
    ],
)
def test_dynamic_layer_blocks_other_disk_writes(tmp_path: Path, action) -> None:
    (tmp_path / "existe.txt").write_text("x", encoding="utf-8")
    target = tmp_path / "fuga.raw"
    with WriteAudit() as audit, pytest.raises(OSError):
        action(target)
    assert audit.events and not target.exists()
    assert (tmp_path / "existe.txt").exists()


def test_dynamic_layer_blocks_non_local_connections() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with WriteAudit() as audit, pytest.raises(AuditViolation):
            sock.connect(("192.0.2.1", 9))  # TEST-NET-1: el gancho corta antes de salir
    finally:
        sock.close()
    assert "no local" in audit.events[0]


def test_dynamic_layer_allows_loopback_connections() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with WriteAudit() as audit:
            client.connect(server.getsockname())
    finally:
        client.close()
        server.close()
    assert audit.events == []


def test_audit_inactive_outside_the_session(tmp_path: Path) -> None:
    with WriteAudit():
        pass
    (tmp_path / "fuera.txt").write_text("ok", encoding="utf-8")  # sin sesión no bloquea


def test_record_only_mode_does_not_block(tmp_path: Path) -> None:
    with WriteAudit(block=False) as audit:
        (tmp_path / "x.txt").write_text("x", encoding="utf-8")
    assert len(audit.events) == 1


def test_snapshot_detects_new_files(tmp_path: Path) -> None:
    before = snapshot([tmp_path])
    (tmp_path / "nuevo.wav").write_bytes(b"\x00")
    assert snapshot([tmp_path]) != before


# --- (c) proceso -----------------------------------------------------------------------


def test_core_dumps_disabled_in_a_fresh_process() -> None:
    code = (
        "import resource; from live.privacy import disable_core_dumps; "
        "print(disable_core_dumps(), resource.getrlimit(resource.RLIMIT_CORE))"
    )
    out = subprocess.run(  # noqa: S603 (intérprete propio, sin shell)
        [sys.executable, "-c", code],
        cwd=PILOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert out == "(0, 0) (0, 0)"


def test_sigterm_wipes_the_buffer() -> None:
    src = SyntheticSource(16_000, harmonic_comb(), seed=8)
    engine = CaptureEngine(src)
    engine.start()
    src.pump(2.0)
    assert engine.ring.raw_view_for_tests().any()
    with privacy.install_wipe_on_signals(engine.stop), pytest.raises(SystemExit) as exc:
        os.kill(os.getpid(), signal.SIGTERM)
    assert exc.value.code == 128 + signal.SIGTERM
    assert not engine.ring.raw_view_for_tests().any() and src.stopped


def test_sigint_wipes_the_buffer() -> None:
    src = SyntheticSource(16_000, harmonic_comb(), seed=9)
    engine = CaptureEngine(src)
    engine.start()
    src.pump(1.0)
    with privacy.install_wipe_on_signals(engine.stop) as handler, pytest.raises(KeyboardInterrupt):
        handler(signal.SIGINT, None)
    assert not engine.ring.raw_view_for_tests().any()
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler

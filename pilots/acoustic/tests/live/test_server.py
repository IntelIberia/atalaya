"""H2.12: página local de alertas (solo 127.0.0.1, Host, token, CSP, sin recursos externos)."""

from __future__ import annotations

import http.client
import json
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest

from live import server as srv
from live.server import AlertBoard, LocalAlertServer, check_bind_host

pytestmark = pytest.mark.req("REQ-LEG-005", "REQ-PRIV-010", "REQ-PRIV-003")

PILOT_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture
def running() -> Iterator[LocalAlertServer]:
    server = LocalAlertServer(AlertBoard(), 0, max_events=2)
    server.start_in_thread()
    try:
        yield server
    finally:
        server.stop()


def _request(
    server: LocalAlertServer,
    method: str,
    path: str,
    *,
    host: str | None = None,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> tuple[int, dict[str, str], bytes]:
    port = server.server_address[1]
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.putrequest(method, path, skip_host=True)
        conn.putheader("Host", host if host is not None else f"127.0.0.1:{port}")
        for key, value in (headers or {}).items():
            conn.putheader(key, value)
        if body is not None:
            conn.putheader("Content-Length", str(len(body)))
        conn.endheaders(body)
        resp = conn.getresponse()
        return resp.status, {k.lower(): v for k, v in resp.getheaders()}, resp.read()
    finally:
        conn.close()


def _label(server: LocalAlertServer, label: str, token: str | None, **kw) -> int:
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["X-Atalaya-Token"] = token
    headers.update(kw.pop("headers", {}))
    body = kw.pop("body", json.dumps({"label": label}).encode())
    return _request(server, "POST", "/label", headers=headers, body=body, **kw)[0]


def test_bind_is_loopback_only(running: LocalAlertServer) -> None:
    assert running.server_address[0] == "127.0.0.1"
    assert running.url.startswith("http://127.0.0.1:")


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.1.10", "localhost", ""])  # noqa: S104
def test_non_loopback_bind_is_rejected(host: str) -> None:
    with pytest.raises(ValueError):
        check_bind_host(host)


def test_cli_with_public_host_exits_non_zero() -> None:
    proc = subprocess.run(  # noqa: S603 (intérprete propio, sin shell)
        [sys.executable, "-m", "live.server", "--host", "0.0.0.0"],  # noqa: S104
        cwd=PILOT_DIR,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode != 0 and "127.0.0.1" in proc.stderr


def test_page_has_strict_headers_and_no_external_resources(running: LocalAlertServer) -> None:
    status, headers, body = _request(running, "GET", "/")
    assert status == 200
    csp = headers["content-security-policy"]
    assert "default-src 'none'" in csp and "script-src 'self'" in csp
    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp
    assert "frame-ancestors 'none'" in csp
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["cache-control"] == "no-store"
    assert "access-control-allow-origin" not in headers
    html = body.decode()
    assert "Reproducción en sala, no vuelo real" in html
    for content in (html, srv.APP_JS.decode(), srv.APP_CSS.decode()):
        assert not re.search(r"(?i)(https?:)?//[a-z0-9.-]+\.[a-z]{2,}", content), "recurso externo"
    assert "<script>" not in html and " style=" not in html and "onclick" not in html
    assert "innerHTML" not in srv.APP_JS.decode()


def test_static_assets_served_same_origin(running: LocalAlertServer) -> None:
    for path, ctype in (("/app.js", "text/javascript"), ("/app.css", "text/css")):
        status, headers, _ = _request(running, "GET", path)
        assert status == 200 and headers["content-type"].startswith(ctype)


@pytest.mark.parametrize(
    "host", ["evil.example:80", "127.0.0.1", "localhost", "127.0.0.1:1", "attacker.test"]
)
def test_wrong_host_header_is_forbidden(running: LocalAlertServer, host: str) -> None:
    assert _request(running, "GET", "/", host=host)[0] == 403


def test_localhost_host_header_is_accepted(running: LocalAlertServer) -> None:
    port = running.server_address[1]
    assert _request(running, "GET", "/", host=f"localhost:{port}")[0] == 200


def test_foreign_origin_is_forbidden(running: LocalAlertServer) -> None:
    token = running.board.token
    status = _label(running, "dron", token, headers={"Origin": "http://evil.example"})
    assert status == 403 and running.board.labels() == []


def test_label_requires_token(running: LocalAlertServer) -> None:
    assert _label(running, "dron", None) == 403
    assert _label(running, "dron", "x" * 43) == 403
    assert running.board.labels() == []


def test_label_with_token_is_recorded(running: LocalAlertServer) -> None:
    token = running.board.token
    assert _label(running, "dron", token) == 200
    assert _label(running, "ruido_casa", token) == 200
    assert _label(running, "fin", token) == 200
    assert [label for _, label in running.board.labels()] == ["dron", "ruido_casa", "fin"]


@pytest.mark.parametrize(
    "body",
    [b'{"label": "otra"}', b'{"label": "dron", "x": 1}', b"[1]", b"no json", b"{" + b" " * 600],
)
def test_bad_label_bodies_are_rejected(running: LocalAlertServer, body: bytes) -> None:
    assert _label(running, "", running.board.token, body=body) in {400, 413}
    assert running.board.labels() == []


def test_label_needs_json_content_type(running: LocalAlertServer) -> None:
    status = _label(running, "dron", running.board.token, headers={"Content-Type": "text/plain"})
    assert status == 415


def test_cors_preflight_is_refused(running: LocalAlertServer) -> None:
    status, headers, _ = _request(
        running, "OPTIONS", "/label", headers={"Origin": f"http://{running.url[7:-1]}"}
    )
    assert status == 403 and "access-control-allow-origin" not in headers


def test_events_require_token(running: LocalAlertServer) -> None:
    assert _request(running, "GET", "/events")[0] == 403
    assert _request(running, "GET", "/events?token=nope")[0] == 403
    assert _request(running, "GET", "/state")[0] == 403


def test_events_stream_only_scalars(running: LocalAlertServer) -> None:
    running.board.publish(
        {
            "state": "ALERTA",
            "probability": 0.87654,
            "t": 12.3456,
            "latency_ms": 41.2,
            "windows": 25,
            "speech_windows": 2,
            "alerts": 1,
            "overruns": 0,
            "alert_active": True,
            "model_id": "tiny",
        }
    )
    status, headers, body = _request(running, "GET", f"/events?token={running.board.token}")
    assert status == 200 and headers["content-type"].startswith("text/event-stream")
    events = [
        json.loads(line[6:]) for line in body.decode().splitlines() if line.startswith("data:")
    ]
    assert events
    for event in events:
        assert set(event) <= srv.EVENT_KEYS | {"banner"}
        for value in event.values():
            assert value is None or isinstance(value, str | int | float | bool)
    assert events[0]["probability"] == 0.88 and events[0]["state"] == "ALERTA"


def test_state_endpoint_with_token(running: LocalAlertServer) -> None:
    status, _, body = _request(
        running, "GET", "/state", headers={"X-Atalaya-Token": running.board.token}
    )
    assert status == 200 and json.loads(body)["banner"] == srv.BANNER


@pytest.mark.parametrize(
    "event",
    [
        {"samples": [0.1, 0.2]},
        {"probability": [0.1, 0.2]},
        {"probability": np.zeros(3)},
        {"state": {"a": 1}},
        {"probability": float("nan")},
        {"embedding": 1.0},
        {"state": "x" * 65},
    ],
)
def test_board_rejects_non_scalar_or_unknown_fields(event: dict) -> None:
    with pytest.raises(ValueError):
        AlertBoard().publish(event)


def test_unknown_label_rejected_by_board() -> None:
    with pytest.raises(ValueError):
        AlertBoard().add_label("muestras")


def test_tokens_are_random_per_session() -> None:
    tokens = {AlertBoard().token for _ in range(20)}
    assert len(tokens) == 20 and all(len(t) >= 40 for t in tokens)


def test_requests_are_not_logged(running: LocalAlertServer, capsys) -> None:
    _request(running, "GET", f"/events?token={running.board.token}")
    _request(running, "GET", "/")
    captured = capsys.readouterr()
    assert running.board.token not in captured.err + captured.out
    assert "GET" not in captured.err


# --- Revisión P8: sensibilidad declarada junto al esquema -------------------------------


def test_every_event_field_declares_operator_sensitivity() -> None:
    allowed = {"PUBLIC", "OPERATOR", "FCSE_ONLY"}
    assert set(srv.EVENT_SCHEMA) == set(srv.EVENT_KEYS)
    assert set(srv.EVENT_SCHEMA.values()) <= allowed
    assert all(v == "OPERATOR" for v in srv.EVENT_SCHEMA.values())
    assert srv.LABEL_SENSITIVITY == "OPERATOR"
    assert srv.BANNER_SENSITIVITY == "PUBLIC"


def test_snapshot_only_emits_declared_fields() -> None:
    board = AlertBoard()
    board.publish({k: None for k in srv.EVENT_KEYS if k != "state"})
    board.add_label("dron")
    _, event = board.snapshot()
    declared = set(srv.EVENT_SCHEMA) | {"banner"}
    assert set(event) <= declared

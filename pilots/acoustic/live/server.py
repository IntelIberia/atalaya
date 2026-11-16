"""H2.12: página local de alertas (biblioteca estándar, solo ``127.0.0.1``).

- ``ThreadingHTTPServer`` enlazado **solo** a ``127.0.0.1``; cualquier otra dirección se rechaza
  al arrancar (salida ≠ 0 desde la línea de órdenes).
- Comprobación de la cabecera ``Host`` (``127.0.0.1:<puerto>`` o ``localhost:<puerto>``) contra
  el reenlace DNS, y de ``Origin`` cuando llega; sin CORS.
- Token aleatorio por sesión para leer eventos y para etiquetar tramos.
- CSP estricta sin recursos externos ni código en línea; ``nosniff``; sin caché; sin marcos.
- Los eventos solo llevan escalares (estado, probabilidad con 2 decimales, hora, latencia,
  contadores, etiqueta): nunca muestras ni embeddings. El servidor no escribe logs de peticiones.
- Las etiquetas del usuario (tramos «reproduzco dron», «ruido de casa», «silencio», «fin») viven
  en memoria; H2.13 decidirá si se exportan.
"""

from __future__ import annotations

import argparse
import hmac
import json
import math
import secrets
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

ALLOWED_BIND = "127.0.0.1"
BANNER = "Reproducción en sala, no vuelo real"
LABELS: Mapping[str, str] = {
    "dron": "Reproduzco dron",
    "ruido_casa": "Ruido de casa",
    "silencio": "Silencio",
    "fin": "Fin del tramo",
}
# Sensibilidad de cada campo (niveles del producto: PUBLIC / OPERATOR / FCSE_ONLY, REQ-FUN-002).
# Todo lo que ve la página es OPERATOR: estado de un sensor en una vivienda, no apto para
# publicarse. Ningún campo es FCSE_ONLY ni identifica a nadie (revisión P8).
EVENT_SCHEMA: Mapping[str, str] = {
    "state": "OPERATOR",
    "probability": "OPERATOR",
    "t": "OPERATOR",
    "latency_ms": "OPERATOR",
    "windows": "OPERATOR",
    "speech_windows": "OPERATOR",
    "alerts": "OPERATOR",
    "overruns": "OPERATOR",
    "alert_active": "OPERATOR",
    "label": "OPERATOR",
    "model_id": "OPERATOR",
}
EVENT_KEYS = frozenset(EVENT_SCHEMA)
# Etiquetas de tramo puestas por el usuario: OPERATOR (cuándo reproducía qué en su casa).
LABEL_SENSITIVITY = "OPERATOR"
# Rótulo fijo, igual para todos.
BANNER_SENSITIVITY = "PUBLIC"
MAX_BODY = 512
MAX_LABELS = 10_000
SSE_INTERVAL_S = 0.5
CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
    "img-src 'none'; font-src 'none'; object-src 'none'; base-uri 'none'; "
    "form-action 'none'; frame-ancestors 'none'"
)
SECURITY_HEADERS: Mapping[str, str] = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
}

Scalar = str | int | float | bool | None


def _scalar(key: str, value: Any) -> Scalar:
    if value is None or isinstance(value, str | bool | int):
        if isinstance(value, str) and len(value) > 64:
            raise ValueError(f"{key}: texto demasiado largo")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{key}: valor no finito")
        return round(value, 2) if key == "probability" else round(value, 3)
    raise ValueError(f"{key}: solo se admiten escalares, no {type(value).__name__}")


class AlertBoard:
    """Estado compartido entre la sesión (escribe) y la página (lee). Solo escalares."""

    def __init__(self, *, token: str | None = None, clock: Callable[[], float] = time.monotonic):
        self.token = token or secrets.token_urlsafe(32)
        self._clock = clock
        self._t0 = clock()
        self._lock = threading.Lock()
        self._event: dict[str, Scalar] = {"state": "ESCUCHANDO", "label": None}
        self._labels: list[tuple[float, str]] = []
        self._version = 0
        self.closed = threading.Event()

    def publish(self, event: Mapping[str, Any]) -> None:
        unknown = set(event) - EVENT_KEYS
        if unknown:
            raise ValueError(f"campos no permitidos en el evento: {sorted(unknown)}")
        clean = {key: _scalar(key, value) for key, value in event.items()}
        with self._lock:
            self._event.update(clean)
            self._version += 1

    def add_label(self, label: str) -> float:
        if label not in LABELS:
            raise ValueError("etiqueta desconocida")
        t = round(self._clock() - self._t0, 3)
        with self._lock:
            if len(self._labels) >= MAX_LABELS:
                raise ValueError("demasiadas etiquetas")
            self._labels.append((t, label))
            self._event["label"] = None if label == "fin" else label
            self._version += 1
        return t

    def labels(self) -> list[tuple[float, str]]:
        with self._lock:
            return list(self._labels)

    def snapshot(self) -> tuple[int, dict[str, Scalar]]:
        with self._lock:
            return self._version, {**self._event, "banner": BANNER}


def _page(token: str) -> bytes:
    buttons = "\n".join(
        f'      <button type="button" data-label="{key}">{text}</button>'
        for key, text in LABELS.items()
    )
    html = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="atalaya-token" content="{token}">
  <title>Atalaya · demo local</title>
  <link rel="stylesheet" href="/app.css">
</head>
<body>
  <header><p class="banner">{BANNER}</p></header>
  <main>
    <section class="state" id="state-box" data-state="ESCUCHANDO">
      <h1 id="state">ESCUCHANDO</h1>
      <p>Probabilidad de dron: <strong id="probability">—</strong></p>
    </section>
    <dl class="stats">
      <dt>Tiempo de sesión</dt><dd id="t">—</dd>
      <dt>Latencia por ventana</dt><dd id="latency_ms">—</dd>
      <dt>Ventanas</dt><dd id="windows">0</dd>
      <dt>Ventanas con voz descartadas</dt><dd id="speech_windows">0</dd>
      <dt>Alertas</dt><dd id="alerts">0</dd>
      <dt>Desbordes</dt><dd id="overruns">0</dd>
      <dt>Modelo</dt><dd id="model_id">—</dd>
    </dl>
    <section class="labels">
      <h2>Etiquetar el tramo</h2>
      <p>Tramo actual: <strong id="label">ninguno</strong></p>
      <div class="buttons">
{buttons}
      </div>
      <p id="feedback" role="status"></p>
    </section>
    <p class="note">Solo local: el sonido se procesa en memoria y se descarta.
      Esta página no recibe sonido, solo estado y puntuación.</p>
  </main>
  <script src="/app.js"></script>
</body>
</html>
"""
    return html.encode("utf-8")


APP_JS = b"""'use strict';
(function () {
  const token = document.querySelector('meta[name="atalaya-token"]').content;
  const fields = ['probability', 't', 'latency_ms', 'windows', 'speech_windows', 'alerts',
                  'overruns', 'model_id'];
  const labelNames = {dron: 'Reproduzco dron', ruido_casa: 'Ruido de casa',
                      silencio: 'Silencio'};
  function fmt(key, value) {
    if (value === null || value === undefined) return '\\u2014';
    if (key === 't') return Number(value).toFixed(1) + ' s';
    if (key === 'latency_ms') return Number(value).toFixed(0) + ' ms';
    if (key === 'probability') return Number(value).toFixed(2);
    return String(value);
  }
  function render(ev) {
    const state = String(ev.state || 'ESCUCHANDO');
    document.getElementById('state').textContent =
      state === 'VOZ' ? 'VOZ: ventana descartada' : state;
    document.getElementById('state-box').dataset.state = state;
    document.getElementById('state-box').dataset.alert = ev.alert_active ? 'si' : 'no';
    for (const key of fields) {
      const el = document.getElementById(key);
      if (el) el.textContent = fmt(key, ev[key]);
    }
    document.getElementById('label').textContent =
      ev.label ? (labelNames[ev.label] || ev.label) : 'ninguno';
  }
  const source = new EventSource('/events?token=' + encodeURIComponent(token));
  source.onmessage = function (msg) { render(JSON.parse(msg.data)); };
  source.onerror = function () {
    document.getElementById('state').textContent = 'SIN CONEXI\\u00d3N';
    document.getElementById('state-box').dataset.state = 'DEGRADADO';
  };
  for (const button of document.querySelectorAll('button[data-label]')) {
    button.addEventListener('click', function () {
      fetch('/label', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-Atalaya-Token': token},
        body: JSON.stringify({label: button.dataset.label}),
        credentials: 'same-origin', cache: 'no-store'
      }).then(function (r) {
        document.getElementById('feedback').textContent =
          r.ok ? 'Etiqueta registrada: ' + button.textContent : 'Error al etiquetar';
      });
    });
  }
})();
"""

APP_CSS = b""":root { --bg: #f6f5f1; --fg: #1d1d1b; --muted: #5b5b57; --line: #d8d6cf;
  --listen: #2f6f4f; --possible: #9a6a00; --alert: #b3261e; --speech: #4a4a8a; --bad: #6b6b6b; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #161615; --fg: #ecebe6; --muted: #a3a29c; --line: #3a3936;
    --listen: #6fbf93; --possible: #e0b44c; --alert: #ff6b5e; --speech: #a3a3e6; --bad: #9a9a9a; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
  font: 16px/1.5 -apple-system, system-ui, sans-serif; }
header { border-bottom: 1px solid var(--line); padding: 8px 16px; }
.banner { margin: 0; font-weight: 600; letter-spacing: .02em; }
main { max-width: 720px; margin: 0 auto; padding: 16px; }
.state { border: 2px solid var(--line); border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.state h1 { margin: 0 0 4px; font-size: 2.2rem; }
.state[data-state="ESCUCHANDO"] h1 { color: var(--listen); }
.state[data-state="POSIBLE"] h1 { color: var(--possible); }
.state[data-state="ALERTA"] { border-color: var(--alert); }
.state[data-state="ALERTA"] h1 { color: var(--alert); }
.state[data-state="VOZ"] h1 { color: var(--speech); }
.state[data-state="DEGRADADO"] h1 { color: var(--bad); }
.stats { display: grid; grid-template-columns: 1fr auto; gap: 4px 16px; margin: 0 0 16px; }
.stats dt { color: var(--muted); }
.stats dd { margin: 0; font-variant-numeric: tabular-nums; text-align: right; }
.buttons { display: flex; flex-wrap: wrap; gap: 8px; }
button { font: inherit; padding: 8px 14px; border-radius: 6px; border: 1px solid var(--line);
  background: transparent; color: var(--fg); cursor: pointer; }
button:focus-visible { outline: 2px solid var(--fg); outline-offset: 2px; }
.note { color: var(--muted); font-size: .9rem; }
"""


class _Handler(BaseHTTPRequestHandler):
    server: LocalAlertServer
    server_version = "atalaya-local"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        """Sin logs de peticiones (llevarían rutas con el token)."""

    def _headers(self, status: int, ctype: str, length: int | None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        for key, value in SECURITY_HEADERS.items():
            self.send_header(key, value)
        if length is not None:
            self.send_header("Content-Length", str(length))
        self.end_headers()

    def _send(self, status: int, body: bytes, ctype: str = "text/plain; charset=utf-8") -> None:
        self._headers(status, ctype, len(body))
        if self.command != "HEAD":
            self.wfile.write(body)

    def _host_ok(self) -> bool:
        port = self.server.server_address[1]
        host = self.headers.get("Host", "")
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if host not in allowed:
            return False
        origin = self.headers.get("Origin")
        return origin is None or origin in {f"http://{h}" for h in allowed}

    def _token_ok(self, supplied: str | None) -> bool:
        return supplied is not None and hmac.compare_digest(
            supplied.encode("utf-8"), self.server.board.token.encode("utf-8")
        )

    def _guard(self) -> bool:
        if not self._host_ok():
            self._send(HTTPStatus.FORBIDDEN, b"host no permitido")
            return False
        return True

    def do_GET(self) -> None:  # noqa: N802 (API de http.server)
        if not self._guard():
            return
        url = urlsplit(self.path)
        board = self.server.board
        if url.path == "/":
            self._send(HTTPStatus.OK, _page(board.token), "text/html; charset=utf-8")
        elif url.path == "/app.js":
            self._send(HTTPStatus.OK, APP_JS, "text/javascript; charset=utf-8")
        elif url.path == "/app.css":
            self._send(HTTPStatus.OK, APP_CSS, "text/css; charset=utf-8")
        elif url.path == "/state":
            if not self._token_ok(self.headers.get("X-Atalaya-Token")):
                self._send(HTTPStatus.FORBIDDEN, b"token")
                return
            _, event = board.snapshot()
            self._send(HTTPStatus.OK, json.dumps(event).encode(), "application/json")
        elif url.path == "/events":
            token = parse_qs(url.query).get("token", [None])[0]
            if not self._token_ok(token):
                self._send(HTTPStatus.FORBIDDEN, b"token")
                return
            self._stream_events()
        else:
            self._send(HTTPStatus.NOT_FOUND, b"no encontrado")

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def _stream_events(self) -> None:
        board = self.server.board
        self.close_connection = True
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        for key, value in SECURITY_HEADERS.items():
            self.send_header(key, value)
        self.send_header("Connection", "close")
        self.end_headers()
        sent = 0
        try:
            # Un evento por intervalo (también sirve de latido): el estado completo, solo escalares.
            while not board.closed.is_set() and not self.server.stopping.is_set():
                _, event = board.snapshot()
                self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
                self.wfile.flush()
                sent += 1
                if self.server.max_events and sent >= self.server.max_events:
                    return
                board.closed.wait(SSE_INTERVAL_S)
        except (BrokenPipeError, ConnectionResetError):
            return

    def do_POST(self) -> None:  # noqa: N802
        if not self._guard():
            return
        if urlsplit(self.path).path != "/label":
            self._send(HTTPStatus.NOT_FOUND, b"no encontrado")
            return
        if not self._token_ok(self.headers.get("X-Atalaya-Token")):
            self._send(HTTPStatus.FORBIDDEN, b"token")
            return
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            self._send(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, b"solo JSON")
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            length = -1
        if not 0 < length <= MAX_BODY:
            self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, b"cuerpo no valido")
            return
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(body, dict) or set(body) != {"label"}:
                raise ValueError("esquema")
            t = self.server.board.add_label(str(body["label"]))
        except (ValueError, UnicodeDecodeError):
            self._send(HTTPStatus.BAD_REQUEST, b"etiqueta no valida")
            return
        self._send(HTTPStatus.OK, json.dumps({"t": t}).encode(), "application/json")

    def do_OPTIONS(self) -> None:  # noqa: N802
        # Sin CORS: ninguna preflight se autoriza.
        self._send(HTTPStatus.FORBIDDEN, b"sin CORS")

    do_PUT = do_DELETE = do_PATCH = do_OPTIONS


class LocalAlertServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, board: AlertBoard, port: int = 0, *, max_events: int = 0) -> None:
        self.board = board
        self.max_events = max_events
        self.stopping = threading.Event()
        super().__init__((ALLOWED_BIND, port), _Handler)

    @property
    def url(self) -> str:
        return f"http://{ALLOWED_BIND}:{self.server_address[1]}/"

    def start_in_thread(self) -> threading.Thread:
        thread = threading.Thread(
            target=self.serve_forever,
            kwargs={"poll_interval": 0.05},
            name="pagina-local",
            daemon=True,
        )
        thread.start()
        return thread

    def stop(self) -> None:
        self.stopping.set()
        self.board.closed.set()
        self.shutdown()
        self.server_close()


def check_bind_host(host: str) -> str:
    if host != ALLOWED_BIND:
        raise ValueError(f"solo se admite {ALLOWED_BIND}; rechazado: {host!r}")
    return host


DEMO_SCRIPT: Sequence[tuple[str, float | None, bool]] = (
    ("ESCUCHANDO", 0.05, False),
    ("POSIBLE", 0.74, False),
    ("POSIBLE", 0.41, False),
    ("ALERTA", 0.86, True),
    ("ALERTA", 0.91, True),
    ("VOZ", None, True),
    ("ALERTA", 0.62, True),
    ("ESCUCHANDO", 0.12, False),
)


def _run_demo(board: AlertBoard, seconds: float, step_s: float = 1.0) -> None:
    """Demo visual sin micrófono ni modelo: recorre estados escritos a mano (no son medidas)."""
    t0 = time.monotonic()
    windows = alerts = speech = 0
    previous_active = False
    while time.monotonic() - t0 < seconds and not board.closed.is_set():
        state, prob, active = DEMO_SCRIPT[windows % len(DEMO_SCRIPT)]
        windows += 1
        alerts += int(active and not previous_active)
        speech += int(state == "VOZ")
        previous_active = active
        board.publish(
            {
                "state": state,
                "probability": prob,
                "t": time.monotonic() - t0,
                "latency_ms": None,
                "windows": windows,
                "speech_windows": speech,
                "alerts": alerts,
                "overruns": 0,
                "alert_active": active,
                "model_id": "demo-sin-modelo",
            }
        )
        board.closed.wait(step_s)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Página local de alertas (solo 127.0.0.1)")
    parser.add_argument("--host", default=ALLOWED_BIND)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--demo-seconds",
        type=float,
        default=0.0,
        help="recorre estados de ejemplo sin micrófono ni modelo (solo para ver la página)",
    )
    args = parser.parse_args(argv)
    try:
        check_bind_host(args.host)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    board = AlertBoard()
    server = LocalAlertServer(board, args.port)
    server.start_in_thread()
    print(f"Página local: {server.url} (Ctrl+C para salir)", file=sys.stderr)
    try:
        if args.demo_seconds > 0:
            _run_demo(board, args.demo_seconds)
        else:
            board.closed.wait()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

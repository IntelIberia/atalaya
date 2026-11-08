#!/usr/bin/env python3
"""Smoke test del stack de compose (T0.10, REQ-SEC-005): cada servicio funciona CON
credenciales y rechaza el acceso SIN ellas o con credenciales erróneas. No imprime secretos."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT_SQL = "select extname from pg_extension where extname in ('postgis','timescaledb')"
COMPOSE = [
    "docker",
    "compose",
    "--env-file",
    str(ROOT / ".env"),
    "-f",
    str(ROOT / "infra/compose/compose.yaml"),
]


def load_env() -> dict[str, str]:
    env = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def sh(service: str, script: str, extra_env: dict[str, str] | None = None) -> tuple[int, str]:
    cmd = [*COMPOSE, "exec", "-T"]
    for k, v in (extra_env or {}).items():
        cmd += ["-e", f"{k}={v}"]
    r = subprocess.run([*cmd, service, "sh", "-c", script], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def nats_session(user: str, password: str, *, pubsub: bool) -> str:
    with socket.create_connection(("127.0.0.1", 4222), timeout=5) as s:
        f = s.makefile("rwb")
        f.readline()  # INFO
        conn = {"user": user, "pass": password, "verbose": False, "pedantic": True}
        f.write(f"CONNECT {json.dumps(conn)}\r\nPING\r\n".encode())
        if pubsub:
            f.write(b"SUB smoke.t 1\r\nPUB smoke.t 5\r\nhello\r\nPING\r\n")
        f.flush()
        out = b""
        deadline = time.time() + 5
        while time.time() < deadline:
            line = f.readline()
            if not line:
                break
            out += line
            if line.startswith(b"-ERR") or (not pubsub and line.startswith(b"PONG")):
                break
            if pubsub and b"hello" in out and out.count(b"PONG") >= 2:
                break
        return out.decode(errors="replace")


def main() -> int:
    e = load_env()
    mq_auth = f'-h localhost -u "{e["MQTT_USER"]}" -P "{e["MQTT_PASSWORD"]}"'
    checks: list[tuple[str, Callable[[], bool]]] = [
        (
            "mqtt pub/sub con credenciales",
            lambda: (
                "hola"
                in sh(
                    "mosquitto",
                    f"mosquitto_sub {mq_auth} -t smoke/t -C 1 -W 5 & sleep 1; "
                    f"mosquitto_pub {mq_auth} -t smoke/t -m hola; wait",
                )[1]
            ),
        ),
        (
            "mqtt anónimo RECHAZADO",
            lambda: sh("mosquitto", "mosquitto_pub -h localhost -t smoke/t -m x")[0] != 0,
        ),
        (
            "mqtt contraseña errónea RECHAZADA",
            lambda: (
                sh("mosquitto", f'mosquitto_pub -h localhost -u "{e["MQTT_USER"]}" -P x -t s -m x')[
                    0
                ]
                != 0
            ),
        ),
        (
            "nats pub/sub con credenciales",
            lambda: (
                "MSG smoke.t 1 5" in nats_session(e["NATS_USER"], e["NATS_PASSWORD"], pubsub=True)
            ),
        ),
        (
            "nats contraseña errónea RECHAZADA",
            lambda: "Authorization Violation" in nats_session(e["NATS_USER"], "x", pubsub=False),
        ),
        (
            "nats JetStream activo",
            lambda: (
                json.loads(
                    urllib.request.urlopen("http://127.0.0.1:8222/jsz", timeout=5).read()
                ).get("config")
                is not None
            ),
        ),
        (
            "redis PING con contraseña",
            lambda: (
                "PONG" in sh("redis", "redis-cli ping", {"REDISCLI_AUTH": e["REDIS_PASSWORD"]})[1]
            ),
        ),
        ("redis sin contraseña RECHAZADO", lambda: "NOAUTH" in sh("redis", "redis-cli ping")[1]),
        (
            "postgres PostGIS + TimescaleDB",
            lambda: all(
                x
                in sh(
                    "postgres",
                    f'psql -h 127.0.0.1 -U "{e["POSTGRES_USER"]}" -d atalaya -tAc "{EXT_SQL}"',
                    {"PGPASSWORD": e["POSTGRES_PASSWORD"]},
                )[1]
                for x in ("postgis", "timescaledb")
            ),
        ),
        (
            "postgres contraseña errónea RECHAZADA (loopback)",
            lambda: (
                sh(
                    "postgres",
                    f'psql -h 127.0.0.1 -U "{e["POSTGRES_USER"]}" -d atalaya -c "select 1"',
                    {"PGPASSWORD": "x"},
                )[0]
                != 0
            ),
        ),
        (
            "postgres contraseña errónea RECHAZADA (red docker)",
            lambda: (
                sh(
                    "postgres",
                    f'psql -h postgres -U "{e["POSTGRES_USER"]}" -d atalaya -c "select 1"',
                    {"PGPASSWORD": "x"},
                )[0]
                != 0
            ),
        ),
        (
            "postgres contraseña errónea RECHAZADA (socket local)",
            lambda: (
                sh(
                    "postgres",
                    f'psql -U "{e["POSTGRES_USER"]}" -d atalaya -c "select 1"',
                    {"PGPASSWORD": "x"},
                )[0]
                != 0
            ),
        ),
    ]
    fails = 0
    for name, fn in checks:
        try:
            ok = fn()
        except Exception as exc:  # un error de la comprobación cuenta como fallo
            ok = False
            name += f" (error: {type(exc).__name__})"
        print(f"{'OK   ' if ok else 'FALLO'} {name}")
        fails += not ok
    print(f"smoke: {len(checks) - fails}/{len(checks)} OK")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

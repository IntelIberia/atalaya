"""Docker Compose local sin credenciales por defecto (REQ-SEC-005, REQ-NFR-015)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

COMPOSE = Path("infra/compose/compose.yaml")
SERVICIOS = {"mosquitto", "nats", "redis", "postgres"}
SECRETO = re.compile(r"(?i)(pass|secret|token|key)")
VAR_OBLIGATORIA = re.compile(r"^\$\{[A-Z0-9_]+:\?[^}]*\}$")


def cargar(repo: Path) -> dict[str, Any]:
    data = yaml.safe_load((repo / COMPOSE).read_text())
    assert isinstance(data, dict)
    return data


def problemas(data: dict[str, Any], mosquitto_conf: str) -> list[str]:
    p: list[str] = []
    servicios: dict[str, Any] = data.get("services", {})
    if set(servicios) != SERVICIOS:
        p.append(f"servicios: {sorted(servicios)}")
    for nombre, s in servicios.items():
        imagen = str(s.get("image", ""))
        if ":" not in imagen or imagen.endswith((":latest", ":2", ":alpine")):
            p.append(f"{nombre}: imagen sin versión fija ({imagen})")
        for puerto in s.get("ports", []):
            if not str(puerto).startswith("127.0.0.1:"):
                p.append(f"{nombre}: puerto expuesto fuera de localhost ({puerto})")
        if "healthcheck" not in s:
            p.append(f"{nombre}: sin healthcheck")
        env = s.get("environment", {})
        for k, v in env.items() if isinstance(env, dict) else []:
            if SECRETO.search(k) and not VAR_OBLIGATORIA.match(str(v)):
                p.append(f"{nombre}: {k} no es una variable obligatoria ${{VAR:?}}")
    if not re.search(r"^allow_anonymous\s+false\s*$", mosquitto_conf, re.MULTILINE):
        p.append("mosquitto: allow_anonymous no es false")
    return p


@pytest.mark.req("REQ-SEC-005", "REQ-NFR-015")
def test_compose_seguro(repo: Path) -> None:
    conf = (repo / "infra/compose/mosquitto/mosquitto.conf").read_text()
    assert problemas(cargar(repo), conf) == []


@pytest.mark.req("REQ-SEC-005")
def test_detecta_password_literal_y_puerto_abierto(repo: Path) -> None:
    data = cargar(repo)
    data["services"]["redis"]["environment"] = {"REDIS_PASSWORD": "admin"}
    data["services"]["redis"]["ports"] = ["6379:6379"]
    conf = "allow_anonymous true\n"
    p = problemas(data, conf)
    assert "redis: REDIS_PASSWORD no es una variable obligatoria ${VAR:?}" in p
    assert "redis: puerto expuesto fuera de localhost (6379:6379)" in p
    assert "mosquitto: allow_anonymous no es false" in p


@pytest.mark.req("REQ-SEC-005")
def test_generador_de_secretos_no_tiene_valores_fijos(repo: Path) -> None:
    texto = (repo / "scripts/gen_local_secrets.sh").read_text()
    assert "openssl rand" in texto
    assert not re.search(r"(?i)password=[A-Za-z0-9]{4,}", texto)


@pytest.mark.req("REQ-SEC-005")
def test_postgres_sin_trust(repo: Path) -> None:
    vols = cargar(repo)["services"]["postgres"]["volumes"]
    assert any("99-endurecer-pg_hba.sh" in v for v in vols)
    script = (repo / "infra/compose/postgres/99-endurecer-pg_hba.sh").read_text()
    assert "scram-sha-256" in script

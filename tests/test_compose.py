"""Docker Compose local sin credenciales por defecto (REQ-SEC-005, REQ-NFR-015)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

COMPOSE = Path("infra/compose/compose.yaml")
SERVICIOS = {"mosquitto", "nats", "redis", "postgres"}
SECRETO = re.compile(r"(?i)(pass|secret|token|key)")
VAR_OBLIGATORIA = re.compile(r"^\$\{[A-Z0-9_]+:\?[^}]*\}$")
# Imagen fijada por etiqueta Y digest: nombre:etiqueta@sha256:<64 hex> (revisión P5).
IMAGEN_DIGEST = re.compile(r"^[a-z0-9./_-]+:[A-Za-z0-9._-]+@sha256:[0-9a-f]{64}$")
# Contraseñas en la línea de órdenes (visibles en `ps` y `docker inspect`): opciones de contraseña o
# una variable que compose interpola ($VAR / ${VAR}); `$$VAR` lo expande el sh del contenedor y en
# argv solo queda el nombre literal de la variable.
SECRETO_EN_ARGV = re.compile(
    r"(?i:--pass\b|--password\b|--requirepass\b)|(?<!\$)\$\{?[A-Z0-9_]*PASS"
)


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
        if not IMAGEN_DIGEST.match(imagen):
            p.append(f"{nombre}: imagen sin digest @sha256 ({imagen})")
        cmd = s.get("command", "")
        argv = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        if nombre != "mosquitto" and SECRETO_EN_ARGV.search(argv):
            # mosquitto: mosquitto_passwd recibe la contraseña en un proceso efímero que termina
            # antes del exec del broker; su argv final no la lleva.
            p.append(f"{nombre}: contraseña en argv del comando")
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


@pytest.mark.req("REQ-SEC-005")
def test_detecta_imagen_sin_digest(repo: Path) -> None:
    data = cargar(repo)
    data["services"]["nats"]["image"] = "nats:2.15.1-alpine"
    data["services"]["redis"]["image"] = "redis:7.4.11-alpine@sha256:abc123"
    conf = (repo / "infra/compose/mosquitto/mosquitto.conf").read_text()
    p = problemas(data, conf)
    assert "nats: imagen sin digest @sha256 (nats:2.15.1-alpine)" in p
    assert "redis: imagen sin digest @sha256 (redis:7.4.11-alpine@sha256:abc123)" in p
    assert not any(x.startswith(("mosquitto:", "postgres:")) for x in p)


@pytest.mark.req("REQ-SEC-005")
def test_detecta_contrasena_en_argv(repo: Path) -> None:
    data = cargar(repo)
    data["services"]["nats"]["command"] = ["-js", "--user", "u", "--pass", "${NATS_PASSWORD}"]
    data["services"]["redis"]["command"] = [
        "sh",
        "-c",
        'exec redis-server --requirepass "$$REDIS_PASSWORD"',
    ]
    conf = (repo / "infra/compose/mosquitto/mosquitto.conf").read_text()
    p = problemas(data, conf)
    assert "nats: contraseña en argv del comando" in p
    assert "redis: contraseña en argv del comando" in p


@pytest.mark.req("REQ-SEC-005")
def test_nats_conf_toma_credenciales_del_entorno(repo: Path) -> None:
    conf = (repo / "infra/compose/nats/nats.conf").read_text()
    # Sin comillas: entre comillas NATS no sustituye la variable (docs.nats.io, «Variables»).
    assert re.search(r"^\s*user:\s*\$NATS_USER\s*$", conf, re.MULTILINE)
    assert re.search(r"^\s*password:\s*\$NATS_PASSWORD\s*$", conf, re.MULTILINE)
    assert re.search(r'store_dir:\s*"/data"', conf)
    assert re.search(r"^http_port:\s*8222\s*$", conf, re.MULTILINE)
    vols = cargar(repo)["services"]["nats"]["volumes"]
    assert "./nats/nats.conf:/etc/nats/nats-server.conf:ro" in vols


# --- T1.16: cuentas de servicio MQTT y ACL por topic/sitio ----------------------------------

ACL = Path("infra/compose/mosquitto/acl.tmpl")
CUENTAS = {"@MQTT_USER@", "@MQTT_SIM_USER@", "@MQTT_INGEST_USER@"}
VARIABLES_MQTT = (
    "MQTT_USER",
    "MQTT_PASSWORD",
    "MQTT_SIM_USER",
    "MQTT_SIM_PASSWORD",
    "MQTT_INGEST_USER",
    "MQTT_INGEST_PASSWORD",
)


def sitios_de_escenarios(repo: Path) -> set[str]:
    sitios: set[str] = set()
    for f in sorted((repo / "sim/scenarios").glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        sitios |= {s["id"] for s in data["sites"]}
    return sitios


def reglas_acl(texto: str) -> dict[str, set[tuple[str, str]]]:
    """Reglas por usuario; `*` agrupa las que no tienen usuario o no se reconocen."""
    reglas: dict[str, set[tuple[str, str]]] = {}
    usuario = "*"
    for raw in texto.splitlines():
        linea = raw.strip()
        if not linea or linea.startswith("#"):
            continue
        partes = linea.split()
        if partes[0] == "user" and len(partes) == 2:
            usuario = partes[1]
            reglas.setdefault(usuario, set())
        elif partes[0] == "topic" and len(partes) == 3 and usuario != "*":
            reglas[usuario].add((partes[1], partes[2]))
        else:
            reglas.setdefault("*", set()).add(("desconocida", linea))
    return reglas


def problemas_acl(texto: str, sitios: set[str]) -> list[str]:
    p: list[str] = []
    reglas = reglas_acl(texto)
    if "*" in reglas:
        p.append(f"reglas sin usuario o desconocidas: {sorted(reglas['*'])}")
    if set(reglas) - {"*"} != CUENTAS:
        p.append(f"cuentas: {sorted(set(reglas) - {'*'})}")
    sim_esperado = {
        ("write", f"atalaya/v1/{s}/+/{k}") for s in sitios for k in ("detection", "node_status")
    }
    if reglas.get("@MQTT_SIM_USER@") != sim_esperado:
        p.append("simulador: solo escritura en los topics de sus sitios")
    ingest_esperado = {("read", f"atalaya/v1/+/+/{k}") for k in ("detection", "node_status")}
    if reglas.get("@MQTT_INGEST_USER@") != ingest_esperado:
        p.append("ingesta: solo lectura de detecciones y estado de nodo")
    if reglas.get("@MQTT_USER@") != {("read", "$SYS/broker/uptime"), ("readwrite", "smoke/#")}:
        p.append("administración: solo smoke y uptime, nunca atalaya/")
    return p


@pytest.mark.req("REQ-SEC-005")
def test_acl_mqtt_por_cuenta_topic_y_sitio(repo: Path) -> None:
    sitios = sitios_de_escenarios(repo)
    assert sitios == {"recinto", "muelles", "pista", "tramo-oeste", "tramo-este"}
    assert problemas_acl((repo / ACL).read_text(), sitios) == []


@pytest.mark.req("REQ-SEC-005")
@pytest.mark.parametrize(
    ("extra", "esperado"),
    [
        ("topic readwrite #\n", "reglas sin usuario"),
        ("pattern write atalaya/v1/%u/#\n", "reglas sin usuario"),
        ("user @MQTT_SIM_USER@\ntopic readwrite atalaya/v1/#\n", "simulador"),
        ("user @MQTT_SIM_USER@\ntopic write atalaya/v1/ajeno/+/detection\n", "simulador"),
        ("user @MQTT_INGEST_USER@\ntopic write atalaya/v1/+/+/detection\n", "ingesta"),
        ("user @MQTT_USER@\ntopic read atalaya/v1/#\n", "administración"),
        ("user otro\ntopic read smoke/#\n", "cuentas"),
    ],
)
def test_acl_detecta_permisos_de_mas(repo: Path, extra: str, esperado: str) -> None:
    texto = (
        extra + "\n" + (repo / ACL).read_text()
        if extra.startswith(("topic", "pattern"))
        else ((repo / ACL).read_text() + "\n" + extra)
    )
    assert any(x.startswith(esperado) for x in problemas_acl(texto, sitios_de_escenarios(repo)))


@pytest.mark.req("REQ-SEC-005")
def test_mosquitto_usa_acl_y_cuentas_de_servicio(repo: Path) -> None:
    conf = (repo / "infra/compose/mosquitto/mosquitto.conf").read_text()
    assert re.search(r"^acl_file\s+/mosquitto/acl\s*$", conf, re.MULTILINE)
    mosq = cargar(repo)["services"]["mosquitto"]
    for var in VARIABLES_MQTT:
        assert VAR_OBLIGATORIA.match(str(mosq["environment"][var])), var
    cmd = str(mosq["command"])
    for var in ("MQTT_USER", "MQTT_SIM_USER", "MQTT_INGEST_USER"):
        assert f'"$${var}" "$${var.replace("USER", "PASSWORD")}"' in cmd, var
        assert f"@{var}@" in cmd, var
    assert "./mosquitto/acl.tmpl:/mosquitto/config/acl.tmpl:ro" in mosq["volumes"]


def _copia_generador(repo: Path, destino: Path) -> Path:
    (destino / "scripts").mkdir(parents=True)
    script = destino / "scripts" / "gen_local_secrets.sh"
    script.write_bytes((repo / "scripts/gen_local_secrets.sh").read_bytes())
    script.chmod(0o700)
    return script


def _claves(env: Path) -> list[str]:
    return [ln.split("=", 1)[0] for ln in env.read_text().splitlines() if "=" in ln]


@pytest.mark.req("REQ-SEC-005")
def test_generador_crea_todas_las_cuentas_mqtt(repo: Path, tmp_path: Path) -> None:
    script = _copia_generador(repo, tmp_path)
    subprocess.run([str(script)], check=True, capture_output=True)
    env = tmp_path / ".env"
    claves = _claves(env)
    for var in VARIABLES_MQTT:
        assert claves.count(var) == 1, var
    assert env.stat().st_mode & 0o777 == 0o600
    valores = dict(ln.split("=", 1) for ln in env.read_text().splitlines() if "=" in ln)
    assert len({valores[v] for v in VARIABLES_MQTT}) == len(VARIABLES_MQTT)
    assert all(len(valores[v]) >= 32 for v in VARIABLES_MQTT if v.endswith("PASSWORD"))


@pytest.mark.req("REQ-SEC-005")
def test_generador_completa_un_env_antiguo_sin_tocar_lo_existente(
    repo: Path, tmp_path: Path
) -> None:
    script = _copia_generador(repo, tmp_path)
    env = tmp_path / ".env"
    antiguo = "# antiguo\nMQTT_USER=u_sintetico\nMQTT_PASSWORD=p_sintetica\n"
    env.write_text(antiguo)
    env.chmod(0o600)
    subprocess.run([str(script)], check=True, capture_output=True)
    texto = env.read_text()
    assert texto.startswith(antiguo)
    claves = _claves(env)
    for var in VARIABLES_MQTT:
        assert claves.count(var) == 1, var
    subprocess.run([str(script)], check=True, capture_output=True)
    assert env.read_text() == texto

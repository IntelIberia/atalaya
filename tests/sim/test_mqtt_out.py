"""T1.16: construcción de la salida MQTT del simulador, sin publicación (REQ-FUN-001, REQ-SEC-005,
REQ-PRIV-003, REQ-LEG-007).

La salida se construye (topic, QoS 1, MQTT 5, carga `Envelope` redactada a `OPERATOR`) pero la
puerta de publicación permanece cerrada hasta T1.7b: ningún intento de publicar llega al transporte
ni deja el payload en los logs. Las credenciales salen solo del entorno (`.env` de
`make bootstrap`), sin valores por defecto. Todos los datos son sintéticos.
"""

from __future__ import annotations

import logging
import secrets
from collections.abc import Callable
from functools import cache
from pathlib import Path

import paho.mqtt.client as paho
import pytest
from atalaya.v1.envelope_pb2 import Envelope
from atalaya.v1.evidence_pb2 import Evidence
from atalaya.v1.sighting_pb2 import Sighting
from atalaya.v1.signature_class_pb2 import SignatureClass
from atalaya_contracts.validate import validate

from sim import mqtt_out, replay
from sim.mqtt_out import (
    CredentialError,
    MqttCredentials,
    MqttPublisher,
    PublicationDenied,
    build_message,
    make_client,
    topic_for,
)
from tests.sim.test_determinism import _cli

REPO = Path(__file__).resolve().parents[2]
SCENARIO = REPO / "sim" / "scenarios" / "aerodromo.yaml"
SITES = frozenset({"pista"})
FCSE_FIELDS = ("operator_id", "operator_location", "uas_id", "self_id_description")


@cache
def _recording() -> replay.Recording:
    return replay.record(SCENARIO, seed=21, duration_s=120)


def sample_envelopes() -> list[Envelope]:
    """Copias de los `Envelope` sintéticos (detecciones y estado de nodo) de `aerodromo`."""
    out = []
    for env in _recording().envelopes:
        copy = Envelope()
        copy.CopyFrom(env)
        out.append(copy)
    return out


def detection_envelopes() -> list[Envelope]:
    return [e for e in sample_envelopes() if e.WhichOneof("payload") == "detection"]


def remote_id_envelope() -> Envelope:
    return next(e for e in detection_envelopes() if e.detection.HasField("remote_id"))


def node_status_envelope() -> Envelope:
    return next(e for e in sample_envelopes() if e.WhichOneof("payload") == "node_status")


def synthetic_env(prefix: str = "MQTT_SIM") -> dict[str, str]:
    """Credenciales generadas en el test (nunca las de `.env`)."""
    return {
        f"{prefix}_USER": f"atalaya_sim_{secrets.token_hex(4)}",
        f"{prefix}_PASSWORD": secrets.token_hex(24),
    }


def sentinels(env: Envelope) -> list[str]:
    """Valores que no pueden aparecer en ningún log."""
    values = [env.detection.detection_id] if env.HasField("detection") else []
    if env.HasField("detection") and env.detection.HasField("remote_id"):
        rid = env.detection.remote_id
        values += [rid.operator_id, rid.uas_id]
    return [v for v in values if v]


class SpyTransport:
    def __init__(self) -> None:
        self.created = 0

    def __call__(self, *args: object, **kwargs: object) -> object:
        self.created += 1
        raise AssertionError("la puerta cerrada no debe crear el transporte")


# --- topic y construcción del mensaje -------------------------------------------------------


@pytest.mark.req("REQ-FUN-001")
def test_topic_de_deteccion_y_de_estado_de_nodo() -> None:
    det = detection_envelopes()[0]
    status = node_status_envelope()
    assert topic_for(det, SITES) == f"atalaya/v1/pista/{det.node_id}/detection"
    assert topic_for(status, SITES) == f"atalaya/v1/pista/{status.node_id}/node_status"


@pytest.mark.req("REQ-FUN-001")
def test_mensaje_qos_1_con_envelope_serializado_de_forma_determinista() -> None:
    env = detection_envelopes()[0]
    msg = build_message(env, allowed_sites=SITES)
    assert msg.qos == 1 == mqtt_out.QOS
    assert msg.topic == topic_for(env, SITES)
    back = Envelope.FromString(msg.payload)
    assert back.detection.detection_id == env.detection.detection_id
    assert validate(back) == []
    assert build_message(env, allowed_sites=SITES).payload == msg.payload
    assert msg.payload not in repr(msg).encode()


@pytest.mark.req("REQ-FUN-001", "REQ-LEG-007", "REQ-PRIV-003")
def test_carga_redactada_a_operator_sin_campos_fcse_only() -> None:
    env = remote_id_envelope()
    rid = env.detection.remote_id
    assert rid.operator_id and rid.uas_id and rid.HasField("operator_location")
    msg = build_message(env, allowed_sites=SITES)
    back = Envelope.FromString(msg.payload).detection.remote_id
    for name in FCSE_FIELDS:
        assert not back.HasField(name), name
    assert rid.operator_id.encode() not in msg.payload
    assert rid.uas_id.encode() not in msg.payload
    # El mensaje original no se modifica.
    assert env.detection.remote_id.operator_id == rid.operator_id


@pytest.mark.req("REQ-FUN-001")
def test_todas_las_detecciones_del_escenario_se_construyen() -> None:
    envs = sample_envelopes()
    msgs = [build_message(e, allowed_sites=SITES) for e in envs]
    assert len(msgs) == len(envs) > 100
    assert {m.topic.rsplit("/", 1)[1] for m in msgs} == {"detection", "node_status"}


@pytest.mark.req("REQ-FUN-001", "REQ-PRIV-003")
@pytest.mark.parametrize(
    ("payload", "builder"),
    [
        ("evidence", lambda e: e.evidence.CopyFrom(Evidence(evidence_id="ev-1"))),
        ("sighting", lambda e: e.sighting.CopyFrom(Sighting(description="texto libre"))),
        ("signature_class", lambda e: e.signature_class.CopyFrom(SignatureClass())),
    ],
)
def test_cargas_no_publicables_rechazadas(
    payload: str, builder: Callable[[Envelope], None]
) -> None:
    env = Envelope(site_id="pista", node_id="ad-rx-1", sequence=1)
    env.emitted_at.seconds = 1
    builder(env)
    assert env.WhichOneof("payload") == payload
    with pytest.raises(ValueError, match="no publicable"):
        build_message(env, allowed_sites=SITES)


@pytest.mark.req("REQ-FUN-001", "REQ-FUN-062")
def test_deteccion_sin_class_scores_rechazada() -> None:
    env = detection_envelopes()[0]
    del env.detection.class_scores[:]
    with pytest.raises(ValueError, match="inválido"):
        build_message(env, allowed_sites=SITES)


@pytest.mark.req("REQ-SEC-005")
def test_sitio_no_autorizado_rechazado() -> None:
    env = detection_envelopes()[0]
    with pytest.raises(ValueError, match="sitio no autorizado"):
        topic_for(env, frozenset({"recinto"}))


@pytest.mark.req("REQ-SEC-005")
@pytest.mark.parametrize("bad", ["", "+", "#", "a/b", "pista/#", "Pista", "x" * 64, "$SYS"])
def test_segmentos_de_topic_invalidos_rechazados(bad: str) -> None:
    env = detection_envelopes()[0]
    env.site_id = bad
    env.detection.site_id = bad
    with pytest.raises(ValueError):
        topic_for(env, frozenset({bad}))
    env = detection_envelopes()[0]
    env.node_id = bad
    env.detection.node_id = bad
    with pytest.raises(ValueError):
        topic_for(env, SITES)


@pytest.mark.req("REQ-SEC-005")
def test_sitio_o_nodo_de_la_carga_distinto_del_envelope_rechazado() -> None:
    env = detection_envelopes()[0]
    env.detection.site_id = "recinto"
    with pytest.raises(ValueError, match="no coincide"):
        topic_for(env, frozenset({"pista", "recinto"}))
    env = node_status_envelope()
    env.node_status.node_id = "otro-nodo"
    with pytest.raises(ValueError, match="no coincide"):
        topic_for(env, SITES)


# --- credenciales: solo del entorno, sin valores por defecto --------------------------------


@pytest.mark.req("REQ-SEC-005")
def test_credenciales_desde_el_entorno() -> None:
    env = synthetic_env()
    creds = MqttCredentials.from_env(env)
    assert creds.username == env["MQTT_SIM_USER"]
    assert creds.password == env["MQTT_SIM_PASSWORD"]
    assert env["MQTT_SIM_PASSWORD"] not in repr(creds)
    assert env["MQTT_SIM_PASSWORD"] not in str(creds)


@pytest.mark.req("REQ-SEC-005")
@pytest.mark.parametrize("missing", ["MQTT_SIM_USER", "MQTT_SIM_PASSWORD"])
def test_sin_credenciales_falla_cerrado(missing: str) -> None:
    env = synthetic_env()
    env.pop(missing)
    with pytest.raises(CredentialError, match=missing):
        MqttCredentials.from_env(env)
    env[missing] = ""
    with pytest.raises(CredentialError, match=missing):
        MqttCredentials.from_env(env)
    with pytest.raises(CredentialError):
        MqttCredentials.from_env({})


@pytest.mark.req("REQ-SEC-005")
@pytest.mark.parametrize(
    "password",
    ["admin", "password", "a" * 31, "x" * 23 + " " + "y" * 24, "z" * 40 + "\n"],
)
def test_contrasena_debil_o_malformada_rechazada_sin_mostrarla(password: str) -> None:
    env = synthetic_env()
    env["MQTT_SIM_PASSWORD"] = password
    with pytest.raises(CredentialError) as info:
        MqttCredentials.from_env(env)
    assert password.strip() not in str(info.value)


@pytest.mark.req("REQ-SEC-005")
def test_usuario_igual_a_contrasena_o_con_espacios_rechazado() -> None:
    env = synthetic_env()
    env["MQTT_SIM_USER"] = env["MQTT_SIM_PASSWORD"]
    with pytest.raises(CredentialError):
        MqttCredentials.from_env(env)
    env = synthetic_env()
    env["MQTT_SIM_USER"] = "atalaya sim"
    with pytest.raises(CredentialError):
        MqttCredentials.from_env(env)


@pytest.mark.req("REQ-SEC-005")
def test_constructor_directo_tambien_valida() -> None:
    with pytest.raises(CredentialError):
        MqttCredentials("atalaya_sim_x", "admin")


@pytest.mark.req("REQ-FUN-001", "REQ-SEC-005")
def test_cliente_paho_mqtt5_con_credenciales_sin_conectar() -> None:
    creds = MqttCredentials.from_env(synthetic_env())
    client = make_client(creds, client_id="sim-test")
    assert client.protocol == paho.MQTTv5
    assert client.username == creds.username
    assert not client.is_connected()


# --- puerta de publicación cerrada hasta T1.7b ---------------------------------------------


def _publisher(spy: SpyTransport) -> MqttPublisher:
    return MqttPublisher(
        MqttCredentials.from_env(synthetic_env()), allowed_sites=SITES, transport_factory=spy
    )


@pytest.mark.req("REQ-SEC-005", "REQ-PRIV-003", "REQ-LEG-007")
def test_publicacion_denegada_sin_transporte_ni_payload_en_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    spy = SpyTransport()
    publisher = _publisher(spy)
    envs = [remote_id_envelope(), detection_envelopes()[0], node_status_envelope()]
    for env in envs:
        with pytest.raises(PublicationDenied):
            publisher.publish(env)
    assert spy.created == 0
    assert publisher.denied_total == len(envs)
    assert publisher.published_total == 0
    assert mqtt_out.publication_gate_open() is False
    text = caplog.text
    assert "denegada" in text
    for env in envs:
        for value in sentinels(env):
            assert value not in text
        assert env.node_id not in text


@pytest.mark.req("REQ-SEC-005", "REQ-PRIV-003")
def test_la_puerta_no_se_abre_por_entorno_ni_con_cargas_de_custodia(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    for name in ("ATALAYA_MQTT_PUBLISH", "ATALAYA_MQTT_ENABLED", "MQTT_PUBLISH", "ATALAYA_T17B"):
        monkeypatch.setenv(name, "1")
    spy = SpyTransport()
    publisher = _publisher(spy)
    env = Envelope(site_id="pista", node_id="ad-rx-1", sequence=1)
    env.evidence.CopyFrom(
        Evidence(evidence_id="ev-centinela", custodian_pseudonym="cust-centinela")
    )
    with pytest.raises(PublicationDenied):
        publisher.publish(env)
    with pytest.raises(PublicationDenied):
        publisher.publish(detection_envelopes()[0])
    assert spy.created == 0
    assert "centinela" not in caplog.text
    assert mqtt_out.publication_gate_open() is False


@pytest.mark.req("REQ-SEC-005")
def test_el_publicador_no_ofrece_forma_de_abrir_la_puerta() -> None:
    public = {n for n in dir(MqttPublisher) if not n.startswith("_")}
    assert public == {"publish", "denied_total", "published_total"}
    with pytest.raises(TypeError):
        MqttPublisher(  # type: ignore[call-arg]
            MqttCredentials.from_env(synthetic_env()),
            allowed_sites=SITES,
            enabled=True,
        )


@pytest.mark.req("REQ-SEC-005")
def test_publicador_exige_credenciales_y_sitios() -> None:
    with pytest.raises(TypeError):
        MqttPublisher("usuario:clave", allowed_sites=SITES)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        MqttPublisher(MqttCredentials.from_env(synthetic_env()), allowed_sites=frozenset())


@pytest.mark.subproceso
@pytest.mark.req("REQ-SEC-005", "REQ-PRIV-003")
def test_cli_run_mqtt_denegado_sin_escribir_ni_pedir_credenciales(tmp_path: Path) -> None:
    out = tmp_path / "x.pb.zst"
    result = _cli(
        "run", "--scenario", str(SCENARIO), "--seed", "21", "--duration", "30",
        "--out", str(out), "--mqtt",
    )  # fmt: skip
    assert result.returncode == 3, result.stderr
    assert "deshabilitada" in result.stderr
    assert not out.exists()
    assert result.stdout == ""

"""Salida MQTT del simulador (T1.16): construcción sin publicación.

Construye los mensajes que el simulador publicará por MQTT 5 con QoS 1 en
`atalaya/v1/<site>/<node>/{detection,node_status}`, con carga `Envelope` validada
(`atalaya_contracts.validate`) y redactada a `OPERATOR` (los campos `FCSE_ONLY` nunca salen por
MQTT). Solo `Detection` y `NodeStatus` son publicables: custodia (`Evidence`), avistamientos, texto
libre y el resto de cargas se rechazan.

**La publicación está deshabilitada** (enmienda v3.2 del plan de FASE 1): `MqttPublisher.publish`
deniega todo intento sin crear el transporte ni registrar el payload. La puerta no tiene interruptor
(ni parámetro, ni variable de entorno, ni método): solo T1.7b la sustituirá por la autenticación de
la cuenta de servicio, la ACL del broker y la decisión de autorización por rol y recurso.

Las credenciales salen únicamente del entorno (`MQTT_SIM_USER` y `MQTT_SIM_PASSWORD`, que genera
`make bootstrap` en `.env`), sin valores por defecto; si faltan o son débiles, falla cerrado.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Final

import paho.mqtt.client as paho
from atalaya.v1 import options_pb2
from atalaya.v1.envelope_pb2 import Envelope
from atalaya_contracts.redact import redact
from atalaya_contracts.validate import validate
from paho.mqtt.enums import CallbackAPIVersion

__all__ = [
    "QOS",
    "TOPIC_ROOT",
    "CredentialError",
    "MqttCredentials",
    "MqttPublisher",
    "OutboundMessage",
    "PublicationDenied",
    "build_message",
    "make_client",
    "publication_gate_open",
    "topic_for",
]

_LOG = logging.getLogger("atalaya.sim.mqtt_out")

TOPIC_ROOT: Final = "atalaya/v1"
QOS: Final = 1
MIN_PASSWORD_LENGTH: Final = 32
USER_VAR: Final = "MQTT_SIM_USER"
PASSWORD_VAR: Final = "MQTT_SIM_PASSWORD"  # noqa: S105 (nombre de variable, no un secreto)
# Carga del `Envelope` → sufijo del topic. Nada más es publicable.
_PUBLISHABLE: Final = {"detection": "detection", "node_status": "node_status"}
# Un segmento de topic: minúsculas, dígitos y guiones; sin `/`, `+`, `#` ni `$`.
_SEGMENT: Final = re.compile(r"[a-z0-9][a-z0-9-]{0,62}")
_TOKEN: Final = re.compile(r"[\x21-\x7e]+")


class CredentialError(ValueError):
    """Credenciales ausentes, débiles o malformadas (el mensaje nunca incluye su valor)."""


class PublicationDenied(PermissionError):
    """Publicación MQTT denegada: la puerta permanece cerrada hasta T1.7b."""


@dataclass(frozen=True)
class MqttCredentials:
    """Cuenta de servicio del simulador en el broker; la contraseña no aparece en `repr`."""

    username: str
    password: str = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.username, str) or not _TOKEN.fullmatch(self.username):
            raise CredentialError(f"{USER_VAR}: vacío o con espacios/caracteres de control")
        if not isinstance(self.password, str) or not _TOKEN.fullmatch(self.password):
            raise CredentialError(f"{PASSWORD_VAR}: vacía o con espacios/caracteres de control")
        if len(self.password) < MIN_PASSWORD_LENGTH:
            raise CredentialError(
                f"{PASSWORD_VAR}: menos de {MIN_PASSWORD_LENGTH} caracteres; usa make bootstrap"
            )
        if self.password == self.username:
            raise CredentialError(f"{PASSWORD_VAR}: igual al usuario")

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> MqttCredentials:
        """Lee la cuenta del entorno; sin valores por defecto (fallo cerrado)."""
        for var in (USER_VAR, PASSWORD_VAR):
            if not env.get(var):
                raise CredentialError(f"falta {var} en el entorno (.env de make bootstrap)")
        return cls(env[USER_VAR], env[PASSWORD_VAR])


@dataclass(frozen=True)
class OutboundMessage:
    """Mensaje listo para MQTT; el payload no aparece en `repr` (no acaba en logs)."""

    topic: str
    payload: bytes = field(repr=False)
    qos: int = QOS


def _segment(value: str, what: str) -> str:
    if not _SEGMENT.fullmatch(value):
        raise ValueError(f"{what} inválido para un topic MQTT")
    return value


def topic_for(envelope: Envelope, allowed_sites: frozenset[str]) -> str:
    """Topic de un `Envelope` publicable, solo para los sitios autorizados a esta cuenta."""
    kind = envelope.WhichOneof("payload")
    if kind not in _PUBLISHABLE:
        raise ValueError(f"carga {kind!r} no publicable por MQTT")
    site = _segment(envelope.site_id, "site_id")
    node = _segment(envelope.node_id, "node_id")
    if site not in allowed_sites:
        raise ValueError("sitio no autorizado para esta cuenta")
    inner = getattr(envelope, kind)
    if inner.site_id != site or inner.node_id != node:
        raise ValueError("el sitio o nodo de la carga no coincide con el Envelope")
    return f"{TOPIC_ROOT}/{site}/{node}/{_PUBLISHABLE[kind]}"


def build_message(envelope: Envelope, *, allowed_sites: frozenset[str]) -> OutboundMessage:
    """Valida, redacta a `OPERATOR` y serializa de forma determinista (no publica)."""
    topic = topic_for(envelope, allowed_sites)
    errors = validate(envelope)
    if errors:
        raise ValueError(f"Envelope inválido: {', '.join(errors)}")
    filtered = redact(envelope, options_pb2.OPERATOR)
    return OutboundMessage(topic, filtered.SerializeToString(deterministic=True))


def make_client(credentials: MqttCredentials, *, client_id: str) -> paho.Client:
    """Cliente paho MQTT 5 con la cuenta de servicio; no conecta."""
    client = paho.Client(CallbackAPIVersion.VERSION2, client_id=client_id, protocol=paho.MQTTv5)
    client.username_pw_set(credentials.username, credentials.password)
    return client


def publication_gate_open() -> bool:
    """Puerta de publicación: cerrada hasta T1.7b, sin forma de abrirla en T1.16."""
    return False


class MqttPublisher:
    """Publicador del simulador. En T1.16 deniega todo: la puerta está cerrada."""

    __slots__ = ("_allowed_sites", "_credentials", "_denied", "_published", "_transport_factory")

    def __init__(
        self,
        credentials: MqttCredentials,
        *,
        allowed_sites: frozenset[str],
        transport_factory: Callable[..., Any] = make_client,
    ) -> None:
        if not isinstance(credentials, MqttCredentials):
            raise TypeError("MqttPublisher requiere MqttCredentials")
        sites = frozenset(allowed_sites)
        if not sites:
            raise ValueError("MqttPublisher requiere al menos un sitio autorizado")
        for site in sites:
            _segment(site, "sitio autorizado")
        self._credentials = credentials
        self._allowed_sites = sites
        self._transport_factory = transport_factory
        self._denied = 0
        self._published = 0

    @property
    def denied_total(self) -> int:
        return self._denied

    @property
    def published_total(self) -> int:
        return self._published

    def publish(self, envelope: Envelope) -> None:
        """Deniega antes de mirar la carga o crear el transporte; el log no lleva el payload."""
        if not publication_gate_open():
            self._denied += 1
            _LOG.warning("mqtt_out: publicación denegada (puerta cerrada hasta T1.7b)")
            raise PublicationDenied("publicación MQTT deshabilitada hasta T1.7b")
        # Inalcanzable en T1.16; T1.7b añadirá aquí autenticación, ACL y autorización.
        raise PublicationDenied("publicación MQTT sin decisión de autorización")

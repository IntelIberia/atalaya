"""T1.16: ingesta mínima sin red (REQ-FUN-001, REQ-PRIV-003, REQ-LEG-007).

Decodifica, valida, deduplica por `detection_id` y entrega a un `DetectionSink` en memoria. Una
carga inválida se cuenta en `rejected_total` sin tumbar la ingesta; los logs nunca llevan el
payload. La conexión MQTT real llega en T1.7b: aquí los mensajes son los que construye
`sim.mqtt_out` con datos sintéticos.
"""

from __future__ import annotations

import logging
import random

import pytest
from atalaya.v1.detection_pb2 import Detection
from atalaya.v1.envelope_pb2 import Envelope
from atalaya.v1.evidence_pb2 import Evidence
from atalaya_ingest import DetectionSink, Ingest, InMemoryDetectionSink, Outcome

from sim.mqtt_out import build_message
from tests.sim.test_mqtt_out import (
    FCSE_FIELDS,
    SITES,
    detection_envelopes,
    node_status_envelope,
    remote_id_envelope,
    sentinels,
)


def _messages(envs: list[Envelope]) -> list[tuple[str, bytes]]:
    out = []
    for env in envs:
        msg = build_message(env, allowed_sites=SITES)
        out.append((msg.topic, msg.payload))
    return out


def _raw(env: Envelope, kind: str = "detection") -> tuple[str, bytes]:
    """Mensaje sin pasar por `build_message` (p. ej., con campos FCSE_ONLY o inválido)."""
    topic = f"atalaya/v1/{env.site_id}/{env.node_id}/{kind}"
    return topic, env.SerializeToString(deterministic=True)


def _ingest() -> tuple[Ingest, InMemoryDetectionSink]:
    sink = InMemoryDetectionSink()
    return Ingest(sink), sink


# --- camino feliz ---------------------------------------------------------------------------


@pytest.mark.req("REQ-FUN-001")
def test_entrega_cada_deteccion_una_vez() -> None:
    ingest, sink = _ingest()
    envs = detection_envelopes()
    outcomes = [ingest.handle(t, p) for t, p in _messages(envs)]
    assert outcomes == [Outcome.ACCEPTED] * len(envs)
    assert [d.detection_id for d in sink.detections] == [e.detection.detection_id for e in envs]
    assert ingest.stats.accepted_total == len(envs)
    assert ingest.stats.rejected_total == 0
    assert all(isinstance(d, Detection) for d in sink.detections)


@pytest.mark.req("REQ-FUN-001")
def test_duplicados_y_desorden_sin_perdidas_ni_duplicados() -> None:
    ingest, sink = _ingest()
    messages = _messages(detection_envelopes())
    rng = random.Random(1616)  # noqa: S311 (orden sintético reproducible, no criptografía)
    dups = rng.sample(messages, k=max(1, len(messages) // 20))
    stream = messages + dups
    rng.shuffle(stream)
    for topic, payload in stream:
        ingest.handle(topic, payload)
    ids = [d.detection_id for d in sink.detections]
    assert len(ids) == len(set(ids)) == len(messages)
    assert ingest.stats.duplicate_total == len(dups)
    assert ingest.stats.received_total == len(stream)


@pytest.mark.req("REQ-FUN-001")
def test_estado_de_nodo_validado_y_no_entregado_como_deteccion() -> None:
    ingest, sink = _ingest()
    topic, payload = _messages([node_status_envelope()])[0]
    assert ingest.handle(topic, payload) is Outcome.NODE_STATUS
    assert sink.detections == []
    assert ingest.stats.node_status_total == 1


@pytest.mark.req("REQ-FUN-001")
def test_el_sink_en_memoria_cumple_el_puerto() -> None:
    assert isinstance(InMemoryDetectionSink(), DetectionSink)


@pytest.mark.req("REQ-FUN-001", "REQ-LEG-007")
def test_campos_fcse_only_no_entran_en_el_canal_operator() -> None:
    env = remote_id_envelope()
    assert env.detection.remote_id.operator_id
    ingest, sink = _ingest()
    assert ingest.handle(*_raw(env)) is Outcome.ACCEPTED
    rid = sink.detections[0].remote_id
    for name in FCSE_FIELDS:
        assert not rid.HasField(name), name


# --- pruebas negativas: rechazo sin tumbar la ingesta ---------------------------------------


def _without_scores() -> tuple[str, bytes]:
    env = detection_envelopes()[0]
    del env.detection.class_scores[:]
    return _raw(env)


def _evidence_on_detection_topic() -> tuple[str, bytes]:
    env = Envelope(site_id="pista", node_id="ad-rx-1", sequence=1)
    env.emitted_at.seconds = 1
    env.evidence.CopyFrom(Evidence(evidence_id="ev-centinela"))
    return _raw(env)


def _site_mismatch() -> tuple[str, bytes]:
    topic, payload = _messages(detection_envelopes()[:1])[0]
    return topic.replace("/pista/", "/recinto/"), payload


def _detection_on_status_topic() -> tuple[str, bytes]:
    topic, payload = _messages(detection_envelopes()[:1])[0]
    return topic.replace("/detection", "/node_status"), payload


def _inner_site_mismatch() -> tuple[str, bytes]:
    env = detection_envelopes()[0]
    env.detection.site_id = "recinto"
    return _raw(env)


CASES = {
    "decode": lambda: ("atalaya/v1/pista/ad-rx-1/detection", b"\xff\xff\xff\xff"),
    "topic": lambda: ("atalaya/v1/pista/#/detection", _messages(detection_envelopes()[:1])[0][1]),
    "oversize": lambda: ("atalaya/v1/pista/ad-rx-1/detection", b"\x00" * (64 * 1024 + 1)),
    "invalid": _without_scores,
    "payload_kind": _evidence_on_detection_topic,
    "topic_mismatch": _site_mismatch,
    "kind_mismatch": _detection_on_status_topic,
    "inner_mismatch": _inner_site_mismatch,
}


@pytest.mark.req("REQ-FUN-001", "REQ-FUN-062")
@pytest.mark.parametrize("reason", sorted(CASES))
def test_carga_invalida_contada_y_la_ingesta_sigue(reason: str) -> None:
    ingest, sink = _ingest()
    topic, payload = CASES[reason]()
    assert ingest.handle(topic, payload) is Outcome.REJECTED
    assert ingest.stats.rejected_total == 1
    assert ingest.stats.rejected_by_reason == {reason: 1}
    assert sink.detections == []
    # La ingesta sigue viva: el siguiente mensaje válido se entrega.
    good = _messages(detection_envelopes()[:1])[0]
    assert ingest.handle(*good) is Outcome.ACCEPTED
    assert len(sink.detections) == 1


@pytest.mark.req("REQ-FUN-001")
@pytest.mark.parametrize("payload", [None, "texto", 123, bytearray(b"\x00")])
def test_tipo_de_carga_no_bytes_rechazado(payload: object) -> None:
    ingest, _ = _ingest()
    assert ingest.handle("atalaya/v1/pista/ad-rx-1/detection", payload) is Outcome.REJECTED  # type: ignore[arg-type]
    assert ingest.stats.rejected_by_reason == {"decode": 1}


@pytest.mark.req("REQ-FUN-001")
def test_topic_no_texto_rechazado() -> None:
    ingest, _ = _ingest()
    payload = _messages(detection_envelopes()[:1])[0][1]
    assert ingest.handle(b"atalaya/v1/pista/x/detection", payload) is Outcome.REJECTED  # type: ignore[arg-type]
    assert ingest.stats.rejected_by_reason == {"topic": 1}


class _FailingSink:
    def __init__(self) -> None:
        self.calls = 0

    def deliver(self, detection: Detection) -> None:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("almacenamiento no disponible")


@pytest.mark.req("REQ-FUN-001")
def test_fallo_del_sink_no_marca_la_deteccion_como_vista() -> None:
    sink = _FailingSink()
    ingest = Ingest(sink)
    msg = _messages(detection_envelopes()[:1])[0]
    assert ingest.handle(*msg) is Outcome.REJECTED
    assert ingest.stats.rejected_by_reason == {"sink": 1}
    assert ingest.handle(*msg) is Outcome.ACCEPTED
    assert ingest.handle(*msg) is Outcome.DUPLICATE
    assert sink.calls == 2


@pytest.mark.req("REQ-FUN-001")
def test_ventana_de_deduplicacion_acotada() -> None:
    sink = InMemoryDetectionSink()
    ingest = Ingest(sink, max_tracked_ids=2)
    a, b, c = _messages(detection_envelopes()[:3])
    for msg in (a, b, a, c):
        ingest.handle(*msg)
    assert ingest.stats.duplicate_total == 1
    # `a` sale de la ventana al entrar `c`; `b` y `c` siguen deduplicándose.
    assert ingest.handle(*b) is Outcome.DUPLICATE
    assert ingest.handle(*c) is Outcome.DUPLICATE
    assert ingest.handle(*a) is Outcome.ACCEPTED
    for bad in (0, -1, True):
        with pytest.raises(ValueError):
            Ingest(sink, max_tracked_ids=bad)


@pytest.mark.req("REQ-FUN-001")
def test_ingest_exige_un_sink() -> None:
    with pytest.raises(TypeError):
        Ingest(object())  # type: ignore[arg-type]


@pytest.mark.req("REQ-PRIV-003", "REQ-LEG-007")
def test_logs_sin_payload_ni_identificadores(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    ingest, _ = _ingest()
    rid = remote_id_envelope()
    ingest.handle(*_raw(rid))
    ingest.handle(*_raw(rid))
    for make in CASES.values():
        ingest.handle(*make())
    text = caplog.text
    assert "rechazado" in text
    for value in [*sentinels(rid), "centinela", rid.node_id]:
        assert value not in text

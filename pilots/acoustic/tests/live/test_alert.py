"""H2.11: máquina de estados de alerta (pura, sin E/S).

``hypothesis`` no está en el entorno del piloto: las propiedades se comprueban con secuencias
aleatorias de semilla fija (cientos de casos por propiedad), sin añadir dependencias.
"""

from __future__ import annotations

import random

import pytest
from live_helpers import valid_config

from live.alert import AlertConfig, AlertMachine, State
from live.artifact import ArtifactError, load_artifact

pytestmark = pytest.mark.req("REQ-FUN-027")

CFG = AlertConfig(theta_on=0.7, theta_off=0.5, k=3, n=5, off_windows=4, refractory_s=5.0)
HOP = 0.48
HIGH, MID, LOW = 0.9, 0.6, 0.1


def _run(machine: AlertMachine, probs, t0: float = 0.0):
    out = []
    for i, p in enumerate(probs):
        out.append(machine.update(t0 + i * HOP, probability=p))
    return out


def test_states_have_spanish_labels() -> None:
    assert {s.value for s in State} == {"ESCUCHANDO", "POSIBLE", "ALERTA", "VOZ", "DEGRADADO"}


def test_three_of_five_alerts() -> None:
    m = AlertMachine(CFG)
    decisions = _run(m, [HIGH, LOW, HIGH, LOW, HIGH])
    assert [d.state for d in decisions] == [
        State.POSSIBLE,
        State.POSSIBLE,
        State.POSSIBLE,
        State.POSSIBLE,
        State.ALERT,
    ]
    assert decisions[-1].alert_started and m.alert_active


def test_alert_ends_after_off_windows_below_theta_off() -> None:
    m = AlertMachine(CFG)
    _run(m, [HIGH] * 3)
    assert m.alert_active
    decisions = _run(m, [LOW, LOW, MID, LOW, LOW, LOW, LOW], t0=3 * HOP)
    # MID (entre θ_off y θ_on) reinicia la cuenta: hacen falta 4 seguidas por debajo de θ_off.
    assert [d.alert_ended for d in decisions] == [False] * 6 + [True]
    assert decisions[-1].state == State.LISTENING


def test_hysteresis_keeps_alert_between_thresholds() -> None:
    m = AlertMachine(CFG)
    _run(m, [HIGH] * 3)
    decisions = _run(m, [MID] * 50, t0=3 * HOP)
    assert all(d.state == State.ALERT for d in decisions)


def test_refractory_blocks_immediate_realert() -> None:
    m = AlertMachine(CFG)
    _run(m, [HIGH] * 3 + [LOW] * 4)  # alerta y fin en t = 6·0,48 = 2,88 s
    decisions = _run(m, [HIGH] * 20, t0=7 * HOP)
    starts = [7 * HOP + i * HOP for i, d in enumerate(decisions) if d.alert_started]
    assert starts and starts[0] - 6 * HOP >= 5.0


def test_speech_windows_do_not_count_and_hide_score() -> None:
    m = AlertMachine(CFG)
    for i in range(30):
        d = m.update(i * HOP, probability=0.99, speech=True)
        assert d.state == State.SPEECH and not d.alert_started
        assert d.probability is None
    assert not m.alert_active


def test_speech_during_alert_keeps_it_active_without_score() -> None:
    m = AlertMachine(CFG)
    _run(m, [HIGH] * 3)
    for i in range(3, 20):
        d = m.update(i * HOP, probability=0.0, speech=True)
        assert d.state == State.SPEECH and d.alert_active and d.probability is None
    assert m.alert_active


def test_speech_between_hits_neither_helps_nor_hurts() -> None:
    m = AlertMachine(CFG)
    m.update(0.0, probability=HIGH)
    m.update(HOP, probability=HIGH)
    for i in range(2, 10):
        m.update(i * HOP, probability=None, speech=True)
    d = m.update(10 * HOP, probability=HIGH)
    assert d.alert_started


def test_degraded_after_two_seconds_without_input() -> None:
    m = AlertMachine(CFG)
    m.update(0.0, probability=LOW)
    assert m.state_at(1.9) == State.LISTENING
    assert m.state_at(2.01) == State.DEGRADED


def test_degraded_flag_ends_alert_and_clears_history() -> None:
    m = AlertMachine(CFG)
    _run(m, [HIGH] * 3)
    d = m.update(3 * HOP, probability=HIGH, degraded=True)
    assert d.state == State.DEGRADED and d.alert_ended and not m.alert_active
    d = m.update(4 * HOP, probability=HIGH)
    assert d.state == State.POSSIBLE  # la historia previa no cuenta


def test_degraded_before_any_input() -> None:
    m = AlertMachine(CFG, started_at=0.0)
    assert m.state_at(2.5) == State.DEGRADED


@pytest.mark.parametrize(
    "kwargs",
    [
        {"theta_off": 0.7},
        {"theta_off": 0.8},
        {"k": 6},
        {"k": 0},
        {"off_windows": 0},
        {"refractory_s": -1.0},
        {"theta_on": 1.5},
        {"theta_off": -0.1},
    ],
)
def test_invalid_config_is_rejected(kwargs) -> None:
    base = {"theta_on": 0.7, "theta_off": 0.5, "k": 3, "n": 5, "off_windows": 4}
    with pytest.raises(ValueError):
        AlertConfig(**{**base, "refractory_s": 5.0, **kwargs})


def test_artifact_with_inconsistent_alert_config_is_rejected(make_artifact) -> None:
    alert = dict(valid_config()["alert"], theta_off=0.9)
    json_path, hashes = make_artifact(valid_config(alert=alert))
    with pytest.raises(ArtifactError, match="alert"):
        load_artifact(json_path, hashes_file=hashes)
    alert = dict(valid_config()["alert"], k=6)
    json_path, hashes = make_artifact(valid_config(alert=alert))
    with pytest.raises(ArtifactError, match="alert"):
        load_artifact(json_path, hashes_file=hashes)


def test_artifact_exposes_alert_config(make_artifact) -> None:
    json_path, hashes = make_artifact()
    cfg = load_artifact(json_path, hashes_file=hashes).config.alert
    assert isinstance(cfg, AlertConfig) and (cfg.k, cfg.n) == (3, 5)


# --- propiedades con secuencias aleatorias (semilla fija) -------------------------------


def test_property_isolated_spike_never_alerts() -> None:
    rng = random.Random(1234)
    for _ in range(300):
        m = AlertMachine(CFG)
        probs = []
        while len(probs) < 200:
            probs.append(rng.uniform(0.7, 1.0))
            probs.extend(rng.uniform(0.0, 0.69) for _ in range(rng.randint(4, 8)))
        assert not any(d.alert_started for d in _run(m, probs))


def test_property_any_three_hits_in_five_alerts() -> None:
    rng = random.Random(99)
    for _ in range(300):
        positions = sorted(rng.sample(range(5), 3))
        probs = [
            rng.uniform(0.7, 1.0) if i in positions else rng.uniform(0, 0.69) for i in range(5)
        ]
        decisions = _run(AlertMachine(CFG), probs)
        first = next(i for i, d in enumerate(decisions) if d.alert_started)
        assert first == positions[-1]


def test_property_alert_starts_respect_refractory() -> None:
    rng = random.Random(7)
    for _ in range(200):
        m = AlertMachine(CFG)
        p, starts, ends = 0.7, [], []
        for i in range(600):
            p = min(1.0, max(0.0, p + rng.uniform(-0.25, 0.25)))  # oscila alrededor de θ_on
            d = m.update(i * HOP, probability=p)
            if d.alert_started:
                starts.append(i * HOP)
            if d.alert_ended:
                ends.append(i * HOP)
        for end, nxt in zip(ends, starts[1:], strict=False):
            assert nxt - end >= CFG.refractory_s - 1e-9
        assert all(b - a >= CFG.refractory_s for a, b in zip(starts, starts[1:], strict=False))


def test_property_alert_start_requires_k_hits_in_last_n_scored() -> None:
    rng = random.Random(2026)
    for _ in range(200):
        m = AlertMachine(CFG)
        scored: list[float] = []
        for i in range(300):
            kind = rng.random()
            if kind < 0.15:
                d = m.update(i * HOP, probability=rng.random(), speech=True)
                assert not d.alert_started and d.probability is None
                continue
            if kind < 0.18:
                d = m.update(i * HOP, probability=rng.random(), degraded=True)
                assert d.state == State.DEGRADED and not m.alert_active
                scored.clear()
                continue
            p = rng.random()
            d = m.update(i * HOP, probability=p)
            scored.append(p)
            if d.alert_started:
                hits = sum(x >= CFG.theta_on for x in scored[-CFG.n :])
                assert hits >= CFG.k
            assert (d.state == State.ALERT) == m.alert_active

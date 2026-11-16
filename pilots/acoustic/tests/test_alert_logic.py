"""Lógica de alerta 3 de 5 con histéresis compartida por Colab y el Mac (REQ-FUN-027)."""

from __future__ import annotations

import random

import pytest

from acoustic_pilot.alert_logic import (
    ALERT_STATES,
    AlertMachine,
    persistence_score,
    run_alert,
    validate_alert_config,
)

pytestmark = pytest.mark.req("REQ-FUN-027")
CFG = {"theta_on": 0.6, "theta_off": 0.4}


def test_isolated_peak_never_alerts() -> None:
    states, events = run_alert([0.1, 0.1, 0.99, 0.1, 0.1, 0.1, 0.99, 0.1], None, CFG)
    assert events == 0 and "ALERTA" not in states and "POSIBLE" in states


def test_three_of_five_alerts_and_hysteresis_ends_it() -> None:
    probs = [0.1, 0.7, 0.2, 0.8, 0.9] + [0.5] * 6 + [0.3] * 4 + [0.1] * 3
    states, events = run_alert(probs, None, CFG)
    assert events == 1
    assert states[4] == "ALERTA"
    # 0,5 está entre theta_off y theta_on: la alerta sigue (histéresis)
    assert all(s == "ALERTA" for s in states[5:11])
    assert states[14] == "ESCUCHANDO" and set(states) <= set(ALERT_STATES)


def test_random_sequences_respect_refractory_period() -> None:
    rng = random.Random(1234)
    cfg = {**CFG, "refractario_s": 5.0}
    for _ in range(200):
        probs = [0.6 + rng.uniform(-0.25, 0.25) for _ in range(120)]  # oscila alrededor de theta_on
        machine = AlertMachine(cfg)
        starts, ends, prev = [], [], "ESCUCHANDO"
        for i, p in enumerate(probs):
            s = machine.step(p)
            if s == "ALERTA" and prev != "ALERTA":
                starts.append(i * 0.48)
            if prev == "ALERTA" and s != "ALERTA":
                ends.append(i * 0.48)
            prev = s
        for end, start in zip(ends, starts[1:], strict=False):
            assert start - end >= 5.0 - 0.48


def test_speech_windows_count_neither_for_nor_against() -> None:
    probs = [0.99] * 10
    states, events = run_alert(probs, [True] * 10, CFG)
    assert events == 0 and set(states) == {"VOZ"}
    # 2 ventanas altas, 3 con voz, 1 alta: 3 de las últimas 5 válidas -> alerta
    states, events = run_alert([0.9, 0.9, 0.99, 0.99, 0.99, 0.9], [0, 0, 1, 1, 1, 0], CFG)
    assert events == 1 and states[-1] == "ALERTA" and states[2:5] == ["VOZ"] * 3


def test_missing_data_is_degraded_without_alert() -> None:
    states, events = run_alert([None, float("nan"), None], None, CFG)
    assert states == ["DEGRADADO"] * 3 and events == 0


@pytest.mark.parametrize(
    "bad",
    [
        {"theta_on": 0.5, "theta_off": 0.5},
        {"theta_on": 0.4, "theta_off": 0.6},
        {"theta_on": 0.6, "theta_off": 0.4, "k": 6, "n": 5},
        {"theta_on": 1.2, "theta_off": 0.4},
        {"theta_on": 0.6},
        {"theta_on": 0.6, "theta_off": 0.4, "otro": 1},
        {"theta_on": 0.6, "theta_off": 0.4, "k": 0},
    ],
)
def test_invalid_configuration_is_rejected(bad: dict) -> None:
    with pytest.raises(ValueError):
        validate_alert_config(bad)


def test_persistence_score_matches_the_machine_on_long_clips() -> None:
    rng = random.Random(7)
    for _ in range(300):
        probs = [rng.random() for _ in range(rng.randint(5, 30))]
        theta = rng.uniform(0.3, 0.9)
        cfg = {"theta_on": theta, "theta_off": theta / 2, "refractario_s": 0.0}
        _, events = run_alert(probs, None, cfg)
        assert (events > 0) == (persistence_score(probs) >= theta)


def test_persistence_score_short_clips_and_errors() -> None:
    assert persistence_score([0.9]) == 0.9
    assert persistence_score([0.9, 0.2]) == 0.2  # k_m = ceil(3·2/5) = 2
    assert persistence_score([0.9, 0.8, 0.1]) == 0.8
    with pytest.raises(ValueError):
        persistence_score([])
    with pytest.raises(ValueError):
        persistence_score([0.5, float("nan")])

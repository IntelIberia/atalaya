"""«Prueba tu audio» del cuaderno de la iteración 6: misma ruta que el modelo final
(REQ-FUN-027, REQ-LEG-005: el audio se analiza en memoria y no se guarda)."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pytest

from acoustic_pilot.harmonic import HARMONIC_NAMES
from acoustic_pilot.model_export import EMBEDDING_DIM, build_artifact
from acoustic_pilot.user_audio import (
    USER_AUDIO_NOTE,
    VERDICT_NO,
    VERDICT_NONE,
    VERDICT_YES,
    AudioDecodeError,
    analyze_audio,
    decode_wav_bytes,
    load_user_audio,
    to_16k_any,
)

pytestmark = pytest.mark.req("REQ-FUN-027", "REQ-LEG-005")


def _yamnet(speech: float = 0.0):
    def fn(window: np.ndarray):
        scores = np.zeros((1, 521))
        scores[0, :4] = speech
        emb = np.abs(np.fft.rfft(np.asarray(window, np.float64), 2046))[:EMBEDDING_DIM]
        return scores, emb[None, :]

    return fn


@pytest.fixture(scope="module")
def artifact() -> dict:
    coef = np.zeros(EMBEDDING_DIM + len(HARMONIC_NAMES))
    coef[EMBEDDING_DIM + HARMONIC_NAMES.index("armonicidad")] = 10.0
    coef[EMBEDDING_DIM + HARMONIC_NAMES.index("n_armonicos")] = 10.0
    return build_artifact(
        model={"nombre": "prueba armónica", "coef": coef, "intercept": -6.0},
        platt={"a": 1.0, "b": 0.0},
        alert={"theta_on": 0.7, "theta_off": 0.5},
        yamnet_info={"origen": "sustituto de prueba"},
        speech_indices=[0, 1, 2, 3],
        speech_names=["Speech", "Child speech, kid speaking", "Conversation", "Narration"],
        speech_threshold=0.30,
        criteria={},
        predictions_sha256="0" * 64,
        record_sha256="0" * 64,
        yamnet_fn=_yamnet(),
    )


def _propeller(sr: int, seconds: float = 6.0, f0: float = 150.0) -> np.ndarray:
    rng = np.random.default_rng(1)
    t = np.arange(int(sr * seconds)) / sr
    top = min(12, int((sr / 2 - 200) // f0))
    x = sum(np.sin(2 * np.pi * h * f0 * t + rng.uniform(0, 6.28)) / h**0.5 for h in range(1, top))
    return (0.2 * x / np.std(x) + 0.01 * rng.standard_normal(len(t))).astype(np.float32)


def _pink(sr: int, seconds: float = 6.0) -> np.ndarray:
    rng = np.random.default_rng(2)
    n = int(sr * seconds)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / sr)
    spec[1:] /= np.sqrt(f[1:])
    spec[0] = 0
    x = np.fft.irfft(spec, n)
    return (0.1 * x / np.std(x)).astype(np.float32)


def _write_wav(path: Path, x: np.ndarray, sr: int, width: int = 2) -> Path:
    arr = np.atleast_2d(np.asarray(x, np.float64).T).T if x.ndim == 1 else x
    with wave.open(str(path), "wb") as w:
        w.setnchannels(arr.shape[1])
        w.setsampwidth(width)
        w.setframerate(sr)
        if width == 2:
            w.writeframes((np.clip(arr, -1, 1) * 32767).astype("<i2").tobytes())
        else:
            v = (np.clip(arr, -1, 1) * (2**23 - 1)).astype(np.int32).reshape(-1)
            w.writeframes(
                np.stack([v & 255, (v >> 8) & 255, (v >> 16) & 255], 1).astype(np.uint8).tobytes()
            )
    return path


@pytest.mark.parametrize("sr", [8000, 44100, 48000])
def test_propeller_tone_is_detected_and_pink_noise_is_not(sr: int, artifact: dict) -> None:
    yes = analyze_audio(_propeller(sr), sr, artifact=artifact, yamnet_fn=_yamnet())
    no = analyze_audio(_pink(sr), sr, artifact=artifact, yamnet_fn=_yamnet())
    assert yes["veredicto"] == VERDICT_YES and yes["alertas"] >= 1
    assert no["veredicto"] == VERDICT_NO and no["alertas"] == 0
    assert yes["prob_max"] > artifact["alerta"]["theta_on"] > no["prob_max"]
    assert 0 <= no["fraccion_sobre_umbral"] <= 1 and yes["ventanas"] == len(yes["estados"])
    if sr == 8000:
        assert any("Banda estrecha" in w for w in yes["avisos"])


def test_mono_and_stereo_wav_files_decode_identically(tmp_path: Path, artifact: dict) -> None:
    x = _propeller(44100, seconds=4.0)
    mono = _write_wav(tmp_path / "mono.wav", x, 44100)
    stereo = _write_wav(tmp_path / "stereo.wav", np.stack([x, x], axis=1), 44100, width=3)
    a, sr_a = load_user_audio(mono)
    b, sr_b = load_user_audio(stereo)
    assert sr_a == sr_b == 44100 and a.shape[1] == 1 and b.shape[1] == 2
    np.testing.assert_allclose(to_16k_any(a, sr_a), to_16k_any(b, sr_b), atol=1e-4)
    report = analyze_audio(b, sr_b, artifact=artifact, yamnet_fn=_yamnet())
    assert report["veredicto"] == VERDICT_YES


def test_speech_windows_are_discarded_and_counted(artifact: dict) -> None:
    report = analyze_audio(_propeller(16000), 16000, artifact=artifact, yamnet_fn=_yamnet(0.9))
    assert report["veredicto"] == VERDICT_NONE
    assert report["ventanas_voz_descartadas"] == report["ventanas"] > 0
    assert all(p is None for p in report["prob_por_ventana"]) and report["alertas"] == 0


def test_silence_short_and_saturated_audio_are_flagged(artifact: dict) -> None:
    silent = analyze_audio(
        np.zeros(16000 * 4, np.float32), 16000, artifact=artifact, yamnet_fn=_yamnet()
    )
    assert silent["veredicto"] == VERDICT_NO
    assert any("silencioso" in w for w in silent["avisos"])
    short = analyze_audio(
        _propeller(48000, seconds=1.0), 48000, artifact=artifact, yamnet_fn=_yamnet()
    )
    assert any("muy corto" in w for w in short["avisos"])
    loud = np.clip(_propeller(16000) * 20, -1, 1)
    sat = analyze_audio(loud, 16000, artifact=artifact, yamnet_fn=_yamnet())
    assert any("saturado" in w for w in sat["avisos"])


def test_corrupt_unsupported_and_empty_files_are_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "roto.wav"
    bad.write_bytes(b"RIFF\x00\x00\x00\x00WAVEbasura")
    with pytest.raises(AudioDecodeError):
        load_user_audio(bad)
    with pytest.raises(AudioDecodeError):
        decode_wav_bytes(b"")
    txt = tmp_path / "nota.txt"
    txt.write_text("hola")
    with pytest.raises(AudioDecodeError):
        load_user_audio(txt)
    with pytest.raises(AudioDecodeError):  # mp3 sin decodificador disponible
        load_user_audio(tmp_path / "x.mp3")

    def failing(_path):
        raise RuntimeError("ffmpeg no puede")

    with pytest.raises(AudioDecodeError):
        load_user_audio(bad, fallback_loader=failing)
    with pytest.raises(ValueError):
        to_16k_any(np.zeros(100, np.float32), 4000)
    with pytest.raises(ValueError):
        to_16k_any(np.array([np.nan], np.float32), 16000)


def test_fallback_loader_is_used_for_compressed_formats(tmp_path: Path) -> None:
    path = tmp_path / "x.ogg"
    path.write_bytes(b"no importa")
    sig, sr = load_user_audio(path, fallback_loader=lambda p: (np.ones((2, 100)), 22050))
    assert sr == 22050 and sig.shape == (100, 2)


def test_note_forbids_platform_downloads() -> None:
    assert "YouTube" in USER_AUDIO_NOTE and "se borra" in USER_AUDIO_NOTE

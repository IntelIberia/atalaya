"""Puerta automática de privacidad (voz) del cuaderno Colab.

El cuaderno incrusta ``acoustic_pilot.speech_gate`` tal cual: estos tests cubren la lógica que
excluye clips con posible voz antes del entrenamiento y la evaluación.
"""

from __future__ import annotations

import ast
import json
import math
from pathlib import Path

import pytest

from acoustic_pilot import speech_gate
from acoustic_pilot.speech_gate import (
    SPEECH_EXCLUSION_THRESHOLD,
    SPEECH_GATE_NOTE,
    apply_speech_gate,
)

PILOT_DIR = Path(__file__).resolve().parents[1]


def test_threshold_constant_and_note_document_limits() -> None:
    assert SPEECH_EXCLUSION_THRESHOLD == 0.30
    assert "no sustituye" in SPEECH_GATE_NOTE and "escucha humana" in SPEECH_GATE_NOTE


def test_excludes_scores_at_or_above_threshold_and_keeps_the_rest() -> None:
    names = ["A.wav", "B.wav", "C.wav", "D.wav"]
    gate = apply_speech_gate(names, [0.748, 0.30, 0.299, 0.05])
    assert gate["kept_indices"] == (2, 3)
    assert [row["clip"] for row in gate["excluded"]] == ["A.wav", "B.wav"]
    assert gate["excluded"][0]["max_speech_score"] == pytest.approx(0.748)
    assert all(row["motivo"] == "voz_automatica" for row in gate["excluded"])
    assert gate["threshold"] == SPEECH_EXCLUSION_THRESHOLD
    assert gate["note"] == SPEECH_GATE_NOTE


def test_missing_or_non_finite_score_fails_closed() -> None:
    gate = apply_speech_gate(["A.wav", "B.wav", "C.wav"], [math.nan, math.inf, 0.1])
    assert gate["kept_indices"] == (2,)
    assert [row["motivo"] for row in gate["excluded"]] == ["puntuacion_no_valida"] * 2
    assert gate["excluded"][0]["max_speech_score"] is None


def test_custom_threshold_is_respected() -> None:
    gate = apply_speech_gate(["A.wav", "B.wav"], [0.2, 0.1], threshold=0.15)
    assert gate["kept_indices"] == (1,)


@pytest.mark.parametrize("bad", [0.0, -0.1, 1.01, math.nan])
def test_rejects_invalid_threshold(bad: float) -> None:
    with pytest.raises(ValueError):
        apply_speech_gate(["A.wav"], [0.1], threshold=bad)


def test_rejects_length_mismatch_and_duplicate_names() -> None:
    with pytest.raises(ValueError):
        apply_speech_gate(["A.wav", "B.wav"], [0.1])
    with pytest.raises(ValueError):
        apply_speech_gate(["A.wav", "A.wav"], [0.1, 0.2])


def test_gate_is_pure_and_json_serializable() -> None:
    names, scores = ["A.wav", "B.wav"], [0.5, 0.1]
    first = apply_speech_gate(names, scores)
    assert names == ["A.wav", "B.wav"] and scores == [0.5, 0.1]
    assert first == apply_speech_gate(names, scores)
    json.dumps(first)


# --- Integración con el cuaderno ------------------------------------------------------


def test_module_is_self_contained_for_colab_embedding() -> None:
    source = Path(speech_gate.__file__).read_text(encoding="utf-8")
    assert "__future__" not in source
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported <= {"collections", "math"}


def _notebook_code() -> str:
    notebook = json.loads((PILOT_DIR / "Atalaya_YAMNet_Colab.ipynb").read_text(encoding="utf-8"))
    return "\n".join(
        "".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"
    )


def test_notebook_embeds_gate_and_filters_before_training() -> None:
    code = _notebook_code()
    assert Path(speech_gate.__file__).read_text(encoding="utf-8") in code
    gate_call = code.index('apply_speech_gate(df["clip"]')
    assert gate_call < code.index("split_with_preassigned(y.tolist()")
    assert '"excluidos_por_voz"' in code


def test_notebook_uses_all_inventoried_clips_and_mfcc_baseline() -> None:
    code = _notebook_code()
    assert "N_PER_CLASS = 30" in code
    assert "n_mfcc=40" in code
    # La línea base usa la MISMA partición y su propio umbral elegido en validación: ambos
    # modelos pasan por fit_predict con los mismos índices (iteración 4).
    assert '"MFCC(40) + reg. logística": np.asarray(mfcc_vectors)' in code
    same_split = "model, rule, proba = fit_predict(name, train_idx, validation_idx, test_idx)"
    assert f"for name in X:\n    {same_split}" in code
    assert "DADS_ENABLED = False" in code


def test_revision_humana_sin_voz_reincorpora_el_clip() -> None:
    cleared = {"a.wav": "usuario 2026-11-11: crujido de madera, sin voz"}
    r = apply_speech_gate(["a.wav", "b.wav"], [0.75, 0.40], human_cleared=cleared)
    assert r["kept_indices"] == (0,)
    assert [e["clip"] for e in r["excluded"]] == ["b.wav"]
    assert r["human_cleared"] == [
        {"clip": "a.wav", "max_speech_score": 0.75, "revision": cleared["a.wav"]}
    ]


def test_revision_humana_no_rescata_puntuacion_invalida() -> None:
    r = apply_speech_gate(["a.wav"], [float("nan")], human_cleared={"a.wav": "x"})
    assert r["kept_indices"] == ()


def test_revision_humana_sin_motivo_es_error() -> None:
    import pytest

    with pytest.raises(ValueError):
        apply_speech_gate(["a.wav"], [0.9], human_cleared={"a.wav": "  "})

# Puerta automática de privacidad: excluye clips con posible voz según YAMNet.
# Autocontenido (solo stdlib): build_colab.py lo incrusta tal cual en el cuaderno de Colab,
# de modo que el código probado es el que se ejecuta allí.
import math
from collections.abc import Mapping, Sequence

# Máxima puntuación YAMNet de Speech/Conversation/Narration/Child speech en cualquier ventana.
# Revisión AUTOMÁTICA y conservadora para la prueba técnica; NO sustituye a la escucha humana.
SPEECH_EXCLUSION_THRESHOLD = 0.30
SPEECH_GATE_NOTE = (
    "Exclusión automática por puntuación de voz de YAMNet (max_speech_score >= umbral); "
    "revisión automática que no sustituye a la escucha humana"
)


def apply_speech_gate(
    names: Sequence[str],
    max_speech_scores: Sequence[float],
    *,
    threshold: float = SPEECH_EXCLUSION_THRESHOLD,
    human_cleared: Mapping[str, str] | None = None,
) -> dict:
    """Separa los clips aptos de los excluidos por posible voz (función pura, fallo cerrado).

    Se excluye todo clip con puntuación >= umbral y todo clip sin puntuación finita, salvo
    que una persona lo haya escuchado y declarado sin voz (human_cleared: clip -> revisión
    con revisor, fecha y nota). La revisión humana nunca rescata una puntuación no válida.
    """
    cleared = dict(human_cleared or {})
    if any(not str(v).strip() for v in cleared.values()):
        raise ValueError("toda revisión humana debe indicar revisor, fecha y nota")
    if not (isinstance(threshold, (int, float)) and 0.0 < threshold <= 1.0):
        raise ValueError("el umbral de voz debe estar en (0, 1]")
    if len(names) != len(max_speech_scores):
        raise ValueError("names y max_speech_scores deben tener la misma longitud")
    if len(set(names)) != len(names):
        raise ValueError("nombres de clip duplicados")
    kept, excluded, rescued = [], [], []
    for index, (name, score) in enumerate(zip(names, max_speech_scores, strict=True)):
        value = float(score)
        if not math.isfinite(value):
            excluded.append(
                {"clip": str(name), "max_speech_score": None, "motivo": "puntuacion_no_valida"}
            )
        elif value >= threshold and str(name) in cleared:
            rescued.append(
                {"clip": str(name), "max_speech_score": value, "revision": cleared[str(name)]}
            )
            kept.append(index)
        elif value >= threshold:
            excluded.append(
                {"clip": str(name), "max_speech_score": value, "motivo": "voz_automatica"}
            )
        else:
            kept.append(index)
    return {
        "threshold": float(threshold),
        "note": SPEECH_GATE_NOTE,
        "kept_indices": tuple(kept),
        "excluded": excluded,
        "human_cleared": rescued,
    }

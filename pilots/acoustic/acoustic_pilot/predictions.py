# Exportación de predicciones a CSV determinista con SHA-256 (ADR 0016, pendiente: métricas
# recalculadas por script desde un fichero de predicciones, no copiadas de la salida).
# Autocontenido (solo stdlib): build_colab.py lo incrusta tal cual en el cuaderno de Colab.
# El recálculo independiente está en pilots/acoustic/recompute_metrics.py.
import csv
import hashlib
import io
import math
from collections.abc import Iterable, Mapping

PREDICTION_COLUMNS = (
    "modelo",
    "esquema",
    "particion",
    "fuente",
    "clip",
    "grupo",
    "dron",
    "puntuacion",
    "umbral",
)


def predictions_csv(rows: Iterable[Mapping]) -> tuple[bytes, str]:
    """CSV UTF-8 con columnas fijas, filas ordenadas y números con 9 decimales; devuelve
    (bytes, sha256). Mismas predicciones => mismos bytes => mismo hash."""
    clean = []
    for row in rows:
        if set(row) != set(PREDICTION_COLUMNS):
            raise ValueError(f"columnas inesperadas: {sorted(set(row) ^ set(PREDICTION_COLUMNS))}")
        label = int(row["dron"])
        score, threshold = float(row["puntuacion"]), float(row["umbral"])
        if label not in (0, 1) or not (math.isfinite(score) and math.isfinite(threshold)):
            raise ValueError("etiqueta o puntuación no válidas")
        text = {k: str(row[k]) for k in PREDICTION_COLUMNS}
        if any(c in v for v in text.values() for c in "\r\n"):
            raise ValueError("salto de línea en un campo")
        text.update(dron=str(label), puntuacion=f"{score:.9f}", umbral=f"{threshold:.9f}")
        clean.append(text)
    keys = [tuple(r[k] for k in ("modelo", "esquema", "particion", "clip")) for r in clean]
    if len(set(keys)) != len(keys):
        raise ValueError("predicción repetida para el mismo modelo, esquema, partición y clip")
    clean.sort(key=lambda r: tuple(r[k] for k in PREDICTION_COLUMNS))
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=PREDICTION_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(clean)
    data = buffer.getvalue().encode("utf-8")
    return data, hashlib.sha256(data).hexdigest()

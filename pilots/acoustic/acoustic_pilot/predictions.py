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


# Iteración 5: tipo de negativo y puntuaciones sin calibrar e isotónica (la columna
# «puntuacion» es la calibrada con Platt, a la que se aplica «umbral»).
EXTENDED_COLUMNS = (
    "modelo",
    "esquema",
    "particion",
    "fuente",
    "clip",
    "grupo",
    "tipo",
    "dron",
    "puntuacion",
    "puntuacion_cruda",
    "puntuacion_isotonica",
    "umbral",
)
_SCORE_COLUMNS = ("puntuacion", "puntuacion_cruda", "puntuacion_isotonica", "umbral")


def predictions_csv(
    rows: Iterable[Mapping], columns: tuple[str, ...] = PREDICTION_COLUMNS
) -> tuple[bytes, str]:
    """CSV UTF-8 con columnas fijas, filas ordenadas y números con 9 decimales (formato base)
    o con precisión de ida y vuelta (.17g, formato ampliado: las probabilidades calibradas
    saturan cerca de 1 y 9 decimales convertirían en empates decisiones distintas); devuelve
    (bytes, sha256). Mismas predicciones => mismos bytes => mismo hash."""
    if columns not in (PREDICTION_COLUMNS, EXTENDED_COLUMNS):
        raise ValueError("formato de columnas desconocido")
    clean = []
    for row in rows:
        if set(row) != set(columns):
            raise ValueError(f"columnas inesperadas: {sorted(set(row) ^ set(columns))}")
        label = int(row["dron"])
        numbers = {k: float(row[k]) for k in _SCORE_COLUMNS if k in columns}
        if label not in (0, 1) or not all(math.isfinite(v) for v in numbers.values()):
            raise ValueError("etiqueta o puntuación no válidas")
        text = {k: str(row[k]) for k in columns}
        if any(c in v for v in text.values() for c in "\r\n"):
            raise ValueError("salto de línea en un campo")
        fmt = ".17g" if columns == EXTENDED_COLUMNS else ".9f"
        text.update(dron=str(label), **{k: format(v, fmt) for k, v in numbers.items()})
        clean.append(text)
    keys = [tuple(r[k] for k in ("modelo", "esquema", "particion", "clip")) for r in clean]
    if len(set(keys)) != len(keys):
        raise ValueError("predicción repetida para el mismo modelo, esquema, partición y clip")
    clean.sort(key=lambda r: tuple(r[k] for k in columns))
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(clean)
    data = buffer.getvalue().encode("utf-8")
    return data, hashlib.sha256(data).hexdigest()

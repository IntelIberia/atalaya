# Registro del experimento (iteración 5): semillas, configuración, hashes de datos y del
# código del cuaderno, versiones de dependencias y hash de las predicciones exportadas.
# Autocontenido (stdlib): build_colab.py lo incrusta tal cual en el cuaderno.
import hashlib
import importlib.metadata
import json
from collections.abc import Iterable, Sequence


def canonical_json(obj: object) -> tuple[bytes, str]:
    """JSON canónico (claves ordenadas, UTF-8, sin espacios) y su SHA-256."""
    data = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return data, hashlib.sha256(data).hexdigest()


def inventory_sha256(rows: Iterable[tuple[str, str]]) -> str:
    """Hash del inventario de datos: líneas «sha256  clip» ordenadas."""
    lines = sorted(f"{digest}  {clip}\n" for clip, digest in rows)
    return hashlib.sha256("".join(lines).encode()).hexdigest()


def dependency_versions(names: Sequence[str]) -> dict[str, str]:
    out = {}
    for name in names:
        try:
            out[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            out[name] = "no instalado"
    return out


def embedding_cache_key(inventory: str, model_url: str, sr: int, code_version: str) -> str:
    """Clave de la caché de embeddings: cambia si cambian los datos, el modelo, sr o el código."""
    return hashlib.sha256(f"{inventory}|{model_url}|{sr}|{code_version}".encode()).hexdigest()[:16]


def experiment_record(
    *,
    config: dict,
    data: dict,
    dependencies: dict,
    predictions_sha256: str,
    notebook_code_sha256: str,
    extra: dict | None = None,
) -> dict:
    """Registro con hash propio (registro_sha256 sobre el JSON canónico del resto)."""
    record = {
        "config": config,
        "datos": data,
        "dependencias": dependencies,
        "predicciones_csv_sha256": predictions_sha256,
        "codigo_cuaderno_sha256": notebook_code_sha256,
        **(extra or {}),
    }
    record["registro_sha256"] = canonical_json(record)[1]
    return record


def verify_record(record: dict) -> bool:
    body = {k: v for k, v in record.items() if k != "registro_sha256"}
    return canonical_json(body)[1] == record.get("registro_sha256")

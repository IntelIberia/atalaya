"""Carga y validación de escenarios del simulador (T1.9, REQ-FUN-005).

Un escenario es un YAML validado contra `schemas/scenario.schema.json` más su geometría GeoJSON
(`<nombre>.nodes.geo.json`) validada contra `schemas/nodes.geo.schema.json`. Además del esquema se
comprueba lo que JSON Schema no expresa bien:

- privacidad geográfica: ninguna coordenada en grados tiene más de dos decimales (0,01°, ~1 km);
  los nodos y demás posiciones son desplazamientos locales en metros;
- integridad referencial: emplazamientos, nodos y fallos se refieren a identificadores existentes;
- coherencia: el centro de cada emplazamiento coincide en el YAML y en el GeoJSON.

Todo error se señala con `ScenarioError`, que lleva la ruta del dato (`threats/0/class`).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError, best_match

from sim.faults import fault_problems

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
SCENARIO_SCHEMA_PATH = SCHEMA_DIR / "scenario.schema.json"
GEOMETRY_SCHEMA_PATH = SCHEMA_DIR / "nodes.geo.schema.json"
MAX_DEGREE_DECIMALS = 2
ROOT = "<raíz>"


class ScenarioError(ValueError):
    """Escenario o geometría inválidos; `path` indica el dato culpable."""

    def __init__(self, source: str, path: str, message: str) -> None:
        self.source = source
        self.path = path
        super().__init__(f"{source}: {path}: {message}")


@dataclass(frozen=True)
class Scenario:
    name: str
    data: dict[str, Any]
    geometry: dict[str, Any]


def _validator(schema_path: Path) -> Draft202012Validator:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


_SCENARIO_VALIDATOR = _validator(SCENARIO_SCHEMA_PATH)
_GEOMETRY_VALIDATOR = _validator(GEOMETRY_SCHEMA_PATH)


def _join(path: Iterable[object]) -> str:
    return "/".join(str(part) for part in path) or ROOT


def _schema_check(validator: Draft202012Validator, data: object, source: str) -> None:
    error: ValidationError | None = best_match(validator.iter_errors(data))
    if error is not None:
        raise ScenarioError(source, _join(error.absolute_path), error.message)


def _decimals(value: float) -> int:
    exponent = Decimal(repr(value)).normalize().as_tuple().exponent
    return max(0, -exponent) if isinstance(exponent, int) else MAX_DEGREE_DECIMALS + 1


def _check_degrees(value: float, source: str, path: str) -> None:
    if _decimals(float(value)) > MAX_DEGREE_DECIMALS:
        raise ScenarioError(
            source, path, f"{value!r} supera la resolución permitida de 0,01° (privacidad)"
        )


def _require_known(value: str, known: set[str], source: str, path: str, what: str) -> None:
    if value not in known:
        raise ScenarioError(source, path, f"{what} desconocido: {value!r}")


def validate_geometry(raw: object, *, source: str) -> dict[str, Any]:
    """Valida un GeoJSON de nodos y devuelve el mismo diccionario."""
    _schema_check(_GEOMETRY_VALIDATOR, raw, source)
    data = cast(dict[str, Any], raw)  # el esquema exige un objeto
    node_ids: set[str] = set()
    sites: set[str] = set()
    for index, feature in enumerate(data["features"]):
        props = feature["properties"]
        if props["role"] == "site_center":
            for axis, value in enumerate(feature["geometry"]["coordinates"]):
                _check_degrees(value, source, f"features/{index}/geometry/coordinates/{axis}")
            if props["site"] in sites:
                raise ScenarioError(source, f"features/{index}/properties/site", "duplicado")
            sites.add(props["site"])
        else:
            if props["id"] in node_ids:
                raise ScenarioError(source, f"features/{index}/properties/id", "duplicado")
            node_ids.add(props["id"])
    for index, feature in enumerate(data["features"]):
        props = feature["properties"]
        if props["role"] == "node":
            path = f"features/{index}/properties/site"
            _require_known(props["site"], sites, source, path, "emplazamiento")
    return data


def validate_scenario(
    data: object, *, source: str, geometry: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Valida un escenario ya cargado; con `geometry`, también su coherencia con ella."""
    if not isinstance(data, dict):
        raise ScenarioError(source, ROOT, "el escenario debe ser un mapa YAML")
    _schema_check(_SCENARIO_VALIDATOR, data, source)
    sites: set[str] = set()
    for index, site in enumerate(data["sites"]):
        for key in ("lat_deg", "lon_deg"):
            _check_degrees(site["center"][key], source, f"sites/{index}/center/{key}")
        if site["id"] in sites:
            raise ScenarioError(source, f"sites/{index}/id", "duplicado")
        sites.add(site["id"])
    for group in ("threats", "manned_aircraft"):
        ids: set[str] = set()
        for index, item in enumerate(data[group]):
            _require_known(item["site"], sites, source, f"{group}/{index}/site", "emplazamiento")
            if item["id"] in ids:
                raise ScenarioError(source, f"{group}/{index}/id", "duplicado")
            ids.add(item["id"])
    for path, message in fault_problems(data["faults"]):
        raise ScenarioError(source, path, message)
    if geometry is not None:
        _check_against_geometry(data, geometry, source)
    return data


def _check_against_geometry(
    data: Mapping[str, Any], geometry: Mapping[str, Any], source: str
) -> None:
    centers: dict[str, list[float]] = {}
    nodes: set[str] = set()
    for feature in geometry["features"]:
        props = feature["properties"]
        if props["role"] == "site_center":
            centers[props["site"]] = feature["geometry"]["coordinates"]
        else:
            nodes.add(props["id"])
    for index, site in enumerate(data["sites"]):
        expected = [site["center"]["lon_deg"], site["center"]["lat_deg"]]
        if centers.get(site["id"]) != expected:
            raise ScenarioError(
                source, f"sites/{index}/center", "no coincide con el centro de la geometría"
            )
    if set(centers) != {site["id"] for site in data["sites"]}:
        raise ScenarioError(source, "geometry", "emplazamientos distintos de los del escenario")
    for index, fault in enumerate(data["faults"]):
        _require_known(fault["node"], nodes, source, f"faults/{index}/node", "nodo")


def load_scenario(path: Path) -> Scenario:
    """Carga `<nombre>.yaml` y su geometría; el nombre debe coincidir con el del fichero."""
    source = str(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ScenarioError(source, ROOT, f"YAML ilegible: {exc}") from exc
    validate_scenario(data, source=source)
    if data["name"] != path.stem:
        raise ScenarioError(source, "name", f"{data['name']!r} no coincide con {path.name!r}")
    geometry_path = path.parent / data["geometry"]
    geometry_source = str(geometry_path)
    try:
        geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScenarioError(source, "geometry", f"geometría ilegible: {exc}") from exc
    validate_geometry(geometry, source=geometry_source)
    validate_scenario(data, source=source, geometry=geometry)
    return Scenario(name=data["name"], data=data, geometry=geometry)

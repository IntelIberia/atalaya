"""T1.9: esquema de escenarios del simulador y privacidad geográfica (REQ-FUN-005).

Los cuatro escenarios usan centros ficticios (D-8) redondeados a 0,01° y nodos definidos como
desplazamientos locales en metros; ninguna coordenada tiene más resolución que la del centro.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from collections.abc import Callable, Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml

from sim.scenario import (
    SCENARIO_SCHEMA_PATH,
    ScenarioError,
    load_scenario,
    validate_geometry,
    validate_scenario,
)

REPO = Path(__file__).resolve().parents[2]
SCENARIOS = REPO / "sim" / "scenarios"
NAMES = ("prision_ceuta", "puerto_ceuta", "aerodromo", "frontera_8km")
DEGREE_KEYS = {"lat_deg", "lon_deg"}
MAX_DECIMALS = 2


def _raw(name: str) -> dict[str, Any]:
    data = yaml.safe_load((SCENARIOS / f"{name}.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _raw_geometry(name: str) -> dict[str, Any]:
    data = json.loads((SCENARIOS / f"{name}.nodes.geo.json").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _decimals(value: float) -> int:
    exponent = Decimal(repr(value)).normalize().as_tuple().exponent
    assert isinstance(exponent, int)
    return max(0, -exponent)


def _walk(node: object, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], object]]:
    yield path, node
    if isinstance(node, dict):
        for key, child in node.items():
            yield from _walk(child, (*path, str(key)))
    elif isinstance(node, list):
        for index, child in enumerate(node):
            yield from _walk(child, (*path, str(index)))


# --- Los cuatro escenarios validan -------------------------------------------------------------


@pytest.mark.req("REQ-FUN-005")
def test_esquema_cerrado() -> None:
    schema = json.loads(SCENARIO_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    for path, node in _walk(schema):
        if isinstance(node, dict) and node.get("type") == "object":
            assert node.get("additionalProperties") is False, "/".join(path)


@pytest.mark.req("REQ-FUN-005")
@pytest.mark.parametrize("name", NAMES)
def test_escenario_valida(name: str) -> None:
    scenario = load_scenario(SCENARIOS / f"{name}.yaml")
    assert scenario.name == name
    assert scenario.data["seed_policy"]["derivation"] == "sha256-component"
    assert len(scenario.data["threats"]) >= 1
    assert len(scenario.data["manned_aircraft"]) >= 1
    assert len(scenario.data["faults"]) >= 1
    kinds = {
        feature["properties"]["kind"]
        for feature in scenario.geometry["features"]
        if feature["properties"]["role"] == "node"
    }
    assert {"acoustic_android", "acoustic_pps", "remote_id_adsb_receiver"} <= kinds


@pytest.mark.req("REQ-FUN-005")
def test_modos_de_remote_id_entre_los_cuatro() -> None:
    modes = {
        threat["remote_id"]["mode"]
        for name in NAMES
        for threat in load_scenario(SCENARIOS / f"{name}.yaml").data["threats"]
    }
    assert modes == {"none", "compliant", "forged"}


@pytest.mark.req("REQ-FUN-005")
def test_frontera_tiene_dos_emplazamientos() -> None:
    assert len(load_scenario(SCENARIOS / "frontera_8km.yaml").data["sites"]) == 2


@pytest.mark.req("REQ-FUN-005")
@pytest.mark.parametrize("name", NAMES)
def test_aeronaves_tripuladas_sinteticas(name: str) -> None:
    for aircraft in _raw(name)["manned_aircraft"]:
        assert aircraft["id"].startswith("SIM")
        assert aircraft["class"] == "C8"


# --- Privacidad geográfica y sensibilidad -------------------------------------------------------


@pytest.mark.req("REQ-FUN-005", "REQ-LEG-007")
@pytest.mark.parametrize("name", NAMES)
def test_ninguna_coordenada_supera_la_resolucion_del_centro(name: str) -> None:
    raw = _raw(name)
    degree_paths = []
    for path, node in _walk(raw):
        if path and path[-1] in DEGREE_KEYS:
            assert isinstance(node, int | float)
            assert _decimals(float(node)) <= MAX_DECIMALS, "/".join(path)
            degree_paths.append(path)
    centers = {
        ("sites", str(i), "center", key) for i in range(len(raw["sites"])) for key in DEGREE_KEYS
    }
    assert set(degree_paths) == centers, "solo los centros llevan grados"

    for path, node in _walk(_raw_geometry(name)):
        if path and path[-1] == "coordinates":
            assert isinstance(node, list)
            for value in node:
                assert _decimals(float(value)) <= MAX_DECIMALS, "/".join(path)


@pytest.mark.req("REQ-FUN-005", "REQ-LEG-007")
@pytest.mark.parametrize("name", NAMES)
def test_nodos_como_desplazamientos_locales(name: str) -> None:
    nodes = [f for f in _raw_geometry(name)["features"] if f["properties"]["role"] == "node"]
    assert nodes
    for feature in nodes:
        assert feature["geometry"] is None
        assert set(feature["properties"]["offset_m"]) == {"east_m", "north_m", "up_m"}


@pytest.mark.req("REQ-FUN-005", "REQ-LEG-007")
@pytest.mark.parametrize("name", NAMES)
def test_punto_de_despegue_fcse_only(name: str) -> None:
    for threat in _raw(name)["threats"]:
        assert threat["launch_point"]["sensitivity"] == "FCSE_ONLY"


# --- Pruebas negativas --------------------------------------------------------------------------


def _set_center_six_decimals(data: dict[str, Any]) -> None:
    data["sites"][0]["center"]["lat_deg"] = 35.123456


def _add_unknown_key(data: dict[str, Any]) -> None:
    data["unexpected_key"] = 1


def _set_class_c10(data: dict[str, Any]) -> None:
    data["threats"][0]["class"] = "C10"


def _drop_seed_policy(data: dict[str, Any]) -> None:
    del data["seed_policy"]


def _launch_point_public(data: dict[str, Any]) -> None:
    data["threats"][0]["launch_point"]["sensitivity"] = "PUBLIC"


def _launch_point_with_degrees(data: dict[str, Any]) -> None:
    data["threats"][0]["launch_point"]["lat_deg"] = 35.12


def _unknown_fault_node(data: dict[str, Any]) -> None:
    data["faults"][0]["node"] = "no-existe"


def _unknown_threat_site(data: dict[str, Any]) -> None:
    data["threats"][0]["site"] = "no-existe"


def _real_aircraft_id(data: dict[str, Any]) -> None:
    data["manned_aircraft"][0]["id"] = "ECABC"


NEGATIVE: list[tuple[Callable[[dict[str, Any]], None], str, str]] = [
    (_add_unknown_key, "<raíz>", "unexpected_key"),
    (_set_class_c10, "threats/0/class", "C10"),
    (_drop_seed_policy, "<raíz>", "seed_policy"),
    (_set_center_six_decimals, "sites/0/center/lat_deg", "0,01"),
    (_launch_point_public, "threats/0/launch_point/sensitivity", "FCSE_ONLY"),
    (_launch_point_with_degrees, "threats/0/launch_point", "lat_deg"),
    (_unknown_fault_node, "faults/0/node", "no-existe"),
    (_unknown_threat_site, "threats/0/site", "no-existe"),
    (_real_aircraft_id, "manned_aircraft/0/id", "ECABC"),
]


@pytest.mark.req("REQ-FUN-005")
@pytest.mark.parametrize(
    ("mutate", "path", "fragment"), NEGATIVE, ids=lambda v: getattr(v, "__name__", None)
)
def test_escenario_invalido_rechazado_con_ruta(
    tmp_path: Path, mutate: Callable[[dict[str, Any]], None], path: str, fragment: str
) -> None:
    data = copy.deepcopy(_raw("prision_ceuta"))
    mutate(data)
    target = tmp_path / "prision_ceuta.yaml"
    target.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    (tmp_path / "prision_ceuta.nodes.geo.json").write_text(
        json.dumps(_raw_geometry("prision_ceuta")), encoding="utf-8"
    )
    with pytest.raises(ScenarioError) as info:
        load_scenario(target)
    assert info.value.path == path
    assert fragment in str(info.value)
    assert path in str(info.value)


@pytest.mark.req("REQ-FUN-005")
def test_nombre_distinto_del_fichero_rechazado(tmp_path: Path) -> None:
    target = tmp_path / "otro.yaml"
    target.write_text(yaml.safe_dump(_raw("prision_ceuta")), encoding="utf-8")
    (tmp_path / "prision_ceuta.nodes.geo.json").write_text(
        json.dumps(_raw_geometry("prision_ceuta")), encoding="utf-8"
    )
    with pytest.raises(ScenarioError) as info:
        load_scenario(target)
    assert info.value.path == "name"


@pytest.mark.req("REQ-FUN-005")
def test_yaml_no_mapa_rechazado() -> None:
    with pytest.raises(ScenarioError) as info:
        validate_scenario(["no", "es", "un", "mapa"], source="lista")
    assert info.value.path == "<raíz>"


def _node_with_point(data: dict[str, Any]) -> None:
    node = next(f for f in data["features"] if f["properties"]["role"] == "node")
    node["geometry"] = {"type": "Point", "coordinates": [-5.123456, 35.123456]}


def _center_six_decimals(data: dict[str, Any]) -> None:
    data["features"][0]["geometry"]["coordinates"][1] = 35.123456


def _node_without_offset(data: dict[str, Any]) -> None:
    node = next(f for f in data["features"] if f["properties"]["role"] == "node")
    del node["properties"]["offset_m"]


GEOMETRY_NEGATIVE: list[Callable[[dict[str, Any]], None]] = [
    _node_with_point,
    _center_six_decimals,
    _node_without_offset,
]


@pytest.mark.req("REQ-FUN-005", "REQ-LEG-007")
@pytest.mark.parametrize("mutate", GEOMETRY_NEGATIVE, ids=lambda f: f.__name__)
def test_geometria_invalida_rechazada(mutate: Callable[[dict[str, Any]], None]) -> None:
    data = copy.deepcopy(_raw_geometry("prision_ceuta"))
    mutate(data)
    with pytest.raises(ScenarioError) as info:
        validate_geometry(data, source="geo")
    assert info.value.path.startswith("features/")


@pytest.mark.req("REQ-FUN-005")
def test_centro_de_geometria_distinto_del_escenario_rechazado(tmp_path: Path) -> None:
    geometry = _raw_geometry("prision_ceuta")
    geometry["features"][0]["geometry"]["coordinates"][1] += 0.01
    target = tmp_path / "prision_ceuta.yaml"
    target.write_text(yaml.safe_dump(_raw("prision_ceuta")), encoding="utf-8")
    (tmp_path / "prision_ceuta.nodes.geo.json").write_text(json.dumps(geometry), encoding="utf-8")
    with pytest.raises(ScenarioError) as info:
        load_scenario(target)
    assert info.value.path == "sites/0/center"


# --- Guardarraíl sobre YAML de escenario --------------------------------------------------------


def _guard(*paths: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-I",
            str(REPO / "scripts" / "guardrails.py"),
            "--paths",
            *map(str, paths),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.req("REQ-FUN-005", "REQ-LEG-007")
@pytest.mark.subproceso
def test_guardarrail_bloquea_clave_de_piloto_sin_fcse_only(tmp_path: Path) -> None:
    key = "pil" + "ot_lat"
    bad = tmp_path / "escenario.yaml"
    bad.write_text(f"{key}: 35.12\n", encoding="utf-8")
    result = _guard(bad)
    assert result.returncode == 2
    assert "pilot-public" in result.stderr
    data = _raw("prision_ceuta")
    data[key] = 35.12
    with pytest.raises(ScenarioError):
        validate_scenario(data, source="memoria")


@pytest.mark.req("REQ-FUN-005", "REQ-LEG-007")
@pytest.mark.subproceso
def test_guardarrail_acepta_los_escenarios() -> None:
    files = sorted(SCENARIOS.glob("*.yaml")) + sorted(SCENARIOS.glob("*.json"))
    files.append(SCENARIO_SCHEMA_PATH)
    assert len(files) == 2 * len(NAMES) + 1
    result = _guard(*files)
    assert result.returncode == 0, result.stderr

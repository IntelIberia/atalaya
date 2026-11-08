"""La estructura del monorepo coincide con la del MEGAPROMPT (<arquitectura_y_stack>)."""

from __future__ import annotations

from pathlib import Path

import pytest

ESTRUCTURA: dict[str, list[str]] = {
    "apps": ["dashboard", "android-sightings", "incident-radar"],
    "services": [
        "ingest",
        "fusion",
        "tracker",
        "predictor",
        "alerting",
        "evidence",
        "sapient-gateway",
    ],
    "edge": ["acoustic-node-py", "android-acoustic-node", "esp32-remoteid", "rf-presence", "adsb"],
    "ml": ["datasets", "signatures", "training", "eval", "models", "cards"],
    "proto": ["atalaya/v1"],
    "third_party": ["sapient"],
    "sim": [],
    "infra": ["docker", "compose", "terraform"],
    "docs": [
        "requirements",
        "plans",
        "evidence",
        "adr",
        "threat-model",
        "dpia",
        "ens",
        "runbooks",
        "model-cards",
        "data-cards",
    ],
    "scripts": [],
    "evals": ["frozen"],
}


def directorios_faltantes(raiz: Path) -> list[str]:
    faltan: list[str] = []
    for top, subs in ESTRUCTURA.items():
        if not (raiz / top).is_dir():
            faltan.append(top)
        faltan.extend(f"{top}/{s}" for s in subs if not (raiz / top / s).is_dir())
    return faltan


@pytest.mark.req("REQ-NFR-014")
def test_estructura_completa(repo: Path) -> None:
    assert directorios_faltantes(repo) == []


@pytest.mark.req("REQ-NFR-014")
def test_estructura_detecta_directorio_ausente(tmp_path: Path) -> None:
    for top, subs in ESTRUCTURA.items():
        (tmp_path / top).mkdir(parents=True, exist_ok=True)
        for s in subs:
            (tmp_path / top / s).mkdir(parents=True, exist_ok=True)
    (tmp_path / "sim").rmdir()
    assert directorios_faltantes(tmp_path) == ["sim"]

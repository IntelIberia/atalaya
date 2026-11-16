"""T0.1: el extra ``live`` fija versiones exactas y no arrastra TensorFlow (ADR 0017)."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

PILOT_DIR = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.req("REQ-NFR-015", "REQ-NFR-016", "REQ-LEG-016")


def _pyproject() -> dict:
    return tomllib.loads((PILOT_DIR / "pyproject.toml").read_text(encoding="utf-8"))


def _lock_versions() -> dict[str, str]:
    lock = tomllib.loads((PILOT_DIR / "uv.lock").read_text(encoding="utf-8"))
    return {pkg["name"]: pkg["version"] for pkg in lock["package"] if "version" in pkg}


def test_live_extra_pins_exact_versions() -> None:
    live = _pyproject()["project"]["optional-dependencies"]["live"]
    assert sorted(live) == ["onnxruntime==1.23.2", "sounddevice==0.5.6"]
    for spec in live:
        assert re.fullmatch(r"[a-z0-9_-]+==\d+(\.\d+)+", spec), spec


def test_lock_matches_live_pins() -> None:
    versions = _lock_versions()
    assert versions["onnxruntime"] == "1.23.2"
    assert versions["sounddevice"] == "0.5.6"


def test_live_extra_does_not_pull_tensorflow() -> None:
    # Prueba negativa: el extra live no contiene TensorFlow ni sus satélites.
    live = " ".join(_pyproject()["project"]["optional-dependencies"]["live"]).lower()
    assert "tensorflow" not in live and "keras" not in live
    lock = tomllib.loads((PILOT_DIR / "uv.lock").read_text(encoding="utf-8"))
    for pkg in lock["package"]:
        if pkg["name"] in {"onnxruntime", "sounddevice"}:
            deps = {d["name"] for d in pkg.get("dependencies", [])}
            assert not {"tensorflow", "tf-keras", "tensorflow-hub"} & deps

"""Fixtures de los tests de ``live``."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from live_helpers import write_artifact


@pytest.fixture
def make_artifact(tmp_path: Path) -> Callable[..., tuple[Path, Path]]:
    def _make(*args: Any, **kwargs: Any) -> tuple[Path, Path]:
        return write_artifact(tmp_path / "model", *args, **kwargs)

    return _make

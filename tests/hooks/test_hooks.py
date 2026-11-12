"""Tests de los hooks de Claude Code (scripts/hooks/). Se prueban SIN activarlos."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOKS = REPO / "scripts" / "hooks"


def run_hook(
    nombre: str, payload: dict[str, object], env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(HOOKS / nombre)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(REPO), **(env or {})},
        cwd=REPO,
    )


def bash(cmd: str) -> dict[str, object]:
    return {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": cmd}}


@pytest.mark.req("REQ-SEC-002")
@pytest.mark.parametrize(
    ("cmd", "codigo"),
    [
        ("cat .env", 2),
        ("rpi" + "tx -f 434000", 2),
        ("git push --force", 2),
        ("git commit --no-verify -m x", 2),
        ("cat README.md", 0),
        ("make check", 0),
    ],
)
def test_pre_bash(cmd: str, codigo: int) -> None:
    r = run_hook("pre_bash.py", bash(cmd))
    assert r.returncode == codigo, r.stderr
    if codigo == 2:
        assert "GUARDARRAÍL" in r.stderr


@pytest.mark.req("REQ-SEC-002")
def test_pre_bash_json_invalido_bloquea() -> None:
    r = subprocess.run(
        [str(HOOKS / "pre_bash.py")], input="{no json", capture_output=True, text=True
    )
    assert r.returncode == 2  # fallo cerrado


@pytest.mark.req("REQ-SEC-002")
def test_pre_bash_sin_comando_no_bloquea() -> None:
    assert run_hook("pre_bash.py", {"tool_name": "Bash", "tool_input": {}}).returncode == 0


@pytest.mark.req("REQ-SEC-001")
def test_post_edit_python_con_error_avisa(tmp_path: Path) -> None:
    f = tmp_path / "malo.py"
    f.write_text("import os\n")  # F401: import sin usar
    r = run_hook("post_edit.sh", {"tool_name": "Edit", "tool_input": {"file_path": str(f)}})
    assert r.returncode == 2
    assert "F401" in r.stderr


@pytest.mark.req("REQ-SEC-001")
def test_post_edit_python_correcto_se_formatea(tmp_path: Path) -> None:
    f = tmp_path / "bien.py"
    f.write_text("x=1\n")
    r = run_hook("post_edit.sh", {"tool_name": "Write", "tool_input": {"file_path": str(f)}})
    assert r.returncode == 0, r.stderr
    assert f.read_text() == "x = 1\n"


@pytest.mark.req("REQ-SEC-001", "REQ-LEG-001")
def test_post_edit_aplica_guardarrailes(tmp_path: Path) -> None:
    f = tmp_path / "m.py"
    f.write_text("MODE = 'ja" + "mming'\n")
    r = run_hook("post_edit.sh", {"tool_name": "Write", "tool_input": {"file_path": str(f)}})
    assert r.returncode == 2
    assert "offensive-term" in r.stderr


@pytest.mark.req("REQ-SEC-001")
def test_post_edit_shell_con_error_avisa(tmp_path: Path) -> None:
    f = tmp_path / "s.sh"
    f.write_text("#!/usr/bin/env bash\necho $1\n")  # SC2086
    r = run_hook("post_edit.sh", {"tool_name": "Edit", "tool_input": {"file_path": str(f)}})
    assert r.returncode == 2
    assert "SC2086" in r.stderr


@pytest.mark.req("REQ-SEC-001")
def test_post_edit_markdown_no_hace_nada(tmp_path: Path) -> None:
    f = tmp_path / "n.md"
    f.write_text("# nota\n")
    r = run_hook("post_edit.sh", {"tool_name": "Edit", "tool_input": {"file_path": str(f)}})
    assert r.returncode == 0


@pytest.mark.req("REQ-SEC-003")
def test_stop_con_check_en_rojo_pide_informar() -> None:
    r = run_hook(
        "stop_check.sh", {"stop_hook_active": False}, env={"ATALAYA_STOP_CHECK_CMD": "false"}
    )
    assert r.returncode == 2
    assert "make check" in r.stderr
    assert "informa" in r.stderr.lower()


@pytest.mark.req("REQ-SEC-003")
def test_stop_con_check_en_verde_termina() -> None:
    r = run_hook(
        "stop_check.sh", {"stop_hook_active": False}, env={"ATALAYA_STOP_CHECK_CMD": "true"}
    )
    assert r.returncode == 0


@pytest.mark.req("REQ-SEC-003")
def test_stop_activo_no_entra_en_bucle() -> None:
    r = run_hook(
        "stop_check.sh", {"stop_hook_active": True}, env={"ATALAYA_STOP_CHECK_CMD": "false"}
    )
    assert r.returncode == 0


@pytest.mark.req("REQ-SEC-002")
def test_settings_json_valido_y_con_denegaciones() -> None:
    s = json.loads((REPO / ".claude" / "settings.json").read_text())
    deny = set(s["permissions"]["deny"])
    for regla in (
        "Read(./.env)",
        "Read(./.env.*)",
        "Read(./secrets/**)",
        "Edit(/evals/frozen/**)",
        "Edit(/data/raw/**)",
    ):
        assert regla in deny
    assert any(r.startswith("Bash(git push --force") for r in deny)
    eventos = s["hooks"]
    assert {"PreToolUse", "PostToolUse", "Stop"} <= set(eventos)
    comandos = json.dumps(eventos)
    for script in ("pre_bash.py", "post_edit.sh", "stop_check.sh"):
        assert script in comandos
        assert (HOOKS / script).stat().st_mode & 0o111, f"{script} no es ejecutable"


@pytest.mark.req("REQ-SEC-002")
def test_p5_pre_bash_con_guardarrail_roto_bloquea(tmp_path: Path) -> None:
    (tmp_path / "scripts" / "hooks").mkdir(parents=True)
    (tmp_path / "scripts" / "__init__.py").write_text("")
    (tmp_path / "scripts" / "guardrails.py").write_text("def roto(:\n")
    hook = tmp_path / "scripts" / "hooks" / "pre_bash.py"
    hook.write_text((HOOKS / "pre_bash.py").read_text())
    hook.chmod(0o755)
    r = subprocess.run([str(hook)], input=json.dumps(bash("ls")), capture_output=True, text=True)
    assert r.returncode == 2
    assert "GUARDARRAÍL" in r.stderr


@pytest.mark.req("REQ-SEC-002")
def test_p5_post_edit_settings_con_ruta_absoluta_sin_falso_positivo() -> None:
    f = REPO / ".claude" / "settings.json"
    r = run_hook("post_edit.sh", {"tool_name": "Edit", "tool_input": {"file_path": str(f)}})
    assert r.returncode == 0, r.stderr


@pytest.mark.req("REQ-SEC-002", "REQ-LEG-002")
def test_p5_settings_deniega_herramientas_de_tx() -> None:
    deny = set(json.loads((REPO / ".claude" / "settings.json").read_text())["permissions"]["deny"])
    for herramienta in ("hackrf" + "_transfer", "rpi" + "tx", "SoapySDR" + "Util", "send" + "iq"):
        assert f"Bash({herramienta} *)" in deny

#!/usr/bin/env python3
"""Hook PreToolUse (Bash) de Claude Code: bloquea comandos peligrosos (exit 2).

Lee el JSON del hook por stdin (tool_input.command). Fallo cerrado: un JSON
ilegible también bloquea. Reglas en scripts/guardrails.py (check_command).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.guardrails import check_command


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        command = str(payload.get("tool_input", {}).get("command", ""))
    except (json.JSONDecodeError, AttributeError) as exc:
        print(f"GUARDARRAÍL: entrada del hook ilegible ({exc}); bloqueado.", file=sys.stderr)
        return 2
    violations = check_command(command)
    if violations:
        print("GUARDARRAÍL: comando bloqueado (ver CLAUDE.md):", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

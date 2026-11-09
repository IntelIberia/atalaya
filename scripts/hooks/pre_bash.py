#!/usr/bin/env python3
"""Hook PreToolUse (Bash) de Claude Code: bloquea comandos peligrosos (exit 2).

Lee el JSON del hook por stdin (tool_input.command). FALLO CERRADO: cualquier error
(JSON ilegible, guardarraíl roto o ausente, excepción inesperada) bloquea con exit 2,
porque Claude Code trata cualquier otro código como error NO bloqueante.
"""

import json
import sys
from pathlib import Path


def main() -> int:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from scripts.guardrails import check_command

        payload = json.load(sys.stdin)
        command = str(payload.get("tool_input", {}).get("command", ""))
        violations = check_command(command)
    except BaseException as exc:  # fallo cerrado
        print(
            f"GUARDARRAÍL: no se pudo verificar el comando ({exc!r}); bloqueado.", file=sys.stderr
        )
        return 2
    if violations:
        print("GUARDARRAÍL: comando bloqueado (ver CLAUDE.md):", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env bash
# Hook PostToolUse (Edit|Write) de Claude Code: formatea y analiza el fichero editado.
# Exit 2 = aviso visible para Claude (la edición ya está hecha; hay que corregirla).
set -u
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
PY="$(command -v python3.12 || command -v python3)"
file="$("$PY" -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)"
[ -n "$file" ] && [ -f "$file" ] || exit 0

problems=0
case "$file" in
  *.py)
    uv run --project "$ROOT" --frozen -q ruff format -q "$file" >&2 || problems=1
    uv run --project "$ROOT" --frozen -q ruff check --no-cache "$file" >&2 || problems=1
    ;;
  *.sh)
    shellcheck "$file" >&2 || problems=1
    ;;
esac
"$PY" -I "$ROOT/scripts/guardrails.py" --paths "$file" || problems=1

if [ "$problems" -ne 0 ]; then
  echo "post_edit: corrige los avisos anteriores en $file" >&2
  exit 2
fi
exit 0

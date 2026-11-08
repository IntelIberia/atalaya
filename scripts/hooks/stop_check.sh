#!/usr/bin/env bash
# Hook Stop de Claude Code (ADR 0006): antes de terminar, `make check` debe pasar.
# Si falla, devuelve el control UNA vez (exit 2) para que Claude lo corrija o, si no
# puede, INFORME del fallo al usuario. Con stop_hook_active=true no vuelve a bloquear
# (evita bucles: nunca se oculta un fallo, pero tampoco se insiste indefinidamente).
set -u
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
PY="$(command -v python3.12 || command -v python3)"
active="$("$PY" -c 'import json,sys; print(str(json.load(sys.stdin).get("stop_hook_active", False)).lower())' 2>/dev/null)"
[ "$active" = "true" ] && exit 0

CMD="${ATALAYA_STOP_CHECK_CMD:-make -C "$ROOT" check}"
if out="$(bash -c "$CMD" 2>&1)"; then
  exit 0
fi
{
  echo "make check está en ROJO. Corrígelo o, si no es posible ahora, informa del fallo"
  echo "al usuario con la salida real (nunca lo ocultes). Últimas líneas:"
  printf '%s\n' "$out" | tail -n 25
} >&2
exit 2

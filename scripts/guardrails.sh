#!/usr/bin/env bash
# Envoltorio de los guardarraíles (REQ-SEC-001). Exit 2 = bloqueado.
# Uso: scripts/guardrails.sh --staged | --range A..B | --paths F... | --command "CMD"
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$(command -v python3.12 || command -v python3)"

"$PY" -I "$ROOT/scripts/guardrails.py" "$@"
status=$?
if [ "$status" -ne 0 ]; then
  # Fallo cerrado: cualquier error distinto de 2 también bloquea.
  exit 2
fi

# Capa adicional de secretos con gitleaks (si está instalado) en modo --staged.
if [ "${1:-}" = "--staged" ] && command -v gitleaks >/dev/null 2>&1; then
  if ! gitleaks git --pre-commit --staged --no-banner --redact --log-level error --exit-code 2 "$ROOT" >&2; then
    echo "GUARDARRAÍL: gitleaks ha detectado un posible secreto." >&2
    exit 2
  fi
fi
exit 0

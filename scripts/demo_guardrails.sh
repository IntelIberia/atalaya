#!/usr/bin/env bash
# Prueba documentada (FASE 0): el hook pre-commit bloquea tres commits prohibidos
# y deja pasar uno limpio. Trabaja en un repositorio temporal; no toca este repo.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cd "$TMP" || exit 1
git init -q && git config user.email demo@example.invalid && git config user.name demo
mkdir -p .githooks scripts
cp "$ROOT/scripts/guardrails.py" "$ROOT/scripts/guardrails.sh" "$ROOT/scripts/guardrails_allowlist.txt" scripts/
cp "$ROOT/.githooks/pre-commit" .githooks/
git config core.hooksPath .githooks
git add -A
if ! git commit -qm "base"; then echo "FALLO: el commit base no debería bloquearse"; exit 1; fi

fails=0
intento() {  # $1 = descripción, $2 = esperado (bloqueado|permitido)
  if git commit -qm "$1" 2>"$TMP/err.txt"; then resultado=permitido; else resultado=bloqueado; fi
  printf '%-48s esperado=%-10s real=%-10s\n' "$1" "$2" "$resultado"
  sed 's/^/    /' "$TMP/err.txt" | grep -E 'GUARDARRAÍL|\[' | head -3
  [ "$resultado" = "$2" ] || fails=$((fails + 1))
  git reset -q --hard HEAD
}

printf 'RIFF\x24\x00\x00\x00WAVEfmt ' > grabacion.wav && git add -f grabacion.wav
intento "1. commit con un .wav" bloqueado

printf 'MODE = "%s"\n' "jam""ming" > modo.py && git add modo.py
intento "2. commit con el término prohibido en código" bloqueado

printf 'message Pista {\n  double pilot_lat = 1 [(atalaya.v1.sensitivity) = PUBLIC];\n}\n' > pista.proto && git add pista.proto
intento "3. commit con pilot_lat en un esquema PUBLIC" bloqueado

printf 'def detect_forged_remote_id(msg):\n    return False\n' > limpio.py && git add limpio.py
intento "4. commit limpio (vocabulario defensivo)" permitido

if [ "$fails" -eq 0 ]; then echo "demo_guardrails: OK (4/4 como se esperaba)"; else echo "demo_guardrails: FALLO ($fails)"; exit 1; fi

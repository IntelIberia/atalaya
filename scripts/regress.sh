#!/usr/bin/env bash
# Regresión acumulada (puerta P3): ejecuta la verificación de cierre de cada fase cerrada
# (docs/requirements/FASES-CERRADAS.txt → scripts/regress.d/fase<N>.sh).
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1
fails=0
while read -r fase; do
  fase="${fase%%#*}"; fase="${fase// /}"
  [ -z "$fase" ] && continue
  script="scripts/regress.d/fase${fase}.sh"
  if [ ! -x "$script" ]; then
    echo "regress: FALTA $script para la fase cerrada $fase"; fails=$((fails + 1)); continue
  fi
  if "$script" > "reports/regress-fase${fase}.log" 2>&1; then
    echo "regress: fase $fase OK"
  else
    echo "regress: fase $fase FALLO (ver reports/regress-fase${fase}.log)"; fails=$((fails + 1))
  fi
done < docs/requirements/FASES-CERRADAS.txt
if [ "$fails" -ne 0 ]; then echo "make regress: $fails fallos"; exit 1; fi
echo "make regress: OK"

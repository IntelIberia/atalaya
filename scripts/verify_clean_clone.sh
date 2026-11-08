#!/usr/bin/env bash
# Reproducibilidad (puerta P4): clona HEAD en un directorio nuevo y ejecuta
# `make bootstrap && make check` sin pasos manuales.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -n "$(git -C "$ROOT" status --porcelain)" ]; then
  echo "verify_clean_clone: AVISO: hay cambios sin commit; se verifica solo HEAD ($(git -C "$ROOT" rev-parse --short HEAD))."
fi
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git clone -q "$ROOT" "$TMP/atalaya" || exit 1
cd "$TMP/atalaya" || exit 1
echo "verify_clean_clone: clon en $TMP/atalaya ($(git rev-parse --short HEAD))"
if make bootstrap > "$TMP/bootstrap.log" 2>&1 && make check > "$TMP/check.log" 2>&1; then
  tail -1 "$TMP/check.log"
  echo "verify_clean_clone: OK"
else
  echo "verify_clean_clone: FALLO"; tail -20 "$TMP/bootstrap.log" "$TMP/check.log"; exit 1
fi

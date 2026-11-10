#!/usr/bin/env bash
# Comprueba que las herramientas de desarrollo de Atalaya están instaladas.
# Uso: scripts/doctor.sh   (exit 0 si todo está; exit 1 nombrando lo que falta)
set -u

# herramienta | comando de versión | obligatoria (1) u opcional (0)
TOOLS=(
  "uv|uv --version|1"
  "python3.12|python3.12 --version|1"
  "git|git --version|1"
  "make|make --version|1"
  "docker|docker --version|1"
  "buf|buf --version|1"
  "gitleaks|gitleaks version|1"
  "shellcheck|shellcheck --version|1"
  "gh|gh --version|0"
)

missing=0
printf "%-12s %-8s %s\n" "HERRAMIENTA" "ESTADO" "VERSIÓN"
for entry in "${TOOLS[@]}"; do
  IFS='|' read -r name cmd required <<<"$entry"
  if command -v "$name" >/dev/null 2>&1; then
    version=$($cmd 2>&1 | grep -m1 -Eo '[0-9]+\.[0-9]+(\.[0-9]+)?' || echo "?")
    printf "%-12s %-8s %s\n" "$name" "OK" "$version"
  elif [ "$required" = "1" ]; then
    printf "%-12s %-8s %s\n" "$name" "FALTA" "(obligatoria)"
    missing=$((missing + 1))
  else
    printf "%-12s %-8s %s\n" "$name" "FALTA" "(opcional)"
  fi
done

if [ "$missing" -gt 0 ]; then
  echo "doctor: faltan $missing herramientas obligatorias. Ver CLAUDE.md (Comandos)." >&2
  exit 1
fi

if command -v uv >/dev/null 2>&1; then
  protoc_version=$(uv run --frozen python -m grpc_tools.protoc --version 2>&1) || {
    printf "%-12s %-8s %s\n" "grpc-protoc" "FALTA" "(uv run --frozen python -m grpc_tools.protoc --version falló)" >&2
    exit 1
  }
  printf "%-12s %-8s %s\n" "grpc-protoc" "OK" "$protoc_version"
else
  echo "grpc-protoc: FALTA (uv no está disponible)" >&2
  exit 1
fi

echo "doctor: OK"

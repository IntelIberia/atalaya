#!/usr/bin/env bash
# Comprueba la compatibilidad Protobuf con una referencia Git anterior.
# Uso: scripts/proto_breaking.sh [REF] (por defecto origin/main).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ "$#" -gt 1 ]; then
  echo "uso: scripts/proto_breaking.sh [REF]" >&2
  exit 2
fi
ref="${1:-origin/main}"

if ! baseline_commit="$(git rev-parse --verify --end-of-options "${ref}^{commit}" 2>/dev/null)"; then
  echo "proto-breaking: referencia inválida: $ref" >&2
  exit 2
fi

paths="$(git ls-tree -r --name-only "$baseline_commit" -- proto)"
if ! grep -qE '^proto/.*\.proto$' <<<"$paths"; then
  echo "proto-breaking: sin línea base en $ref (no hay .proto)"
  exit 0
fi
if ! git cat-file -e "${baseline_commit}:buf.yaml" 2>/dev/null; then
  echo "proto-breaking: falta buf.yaml en $ref" >&2
  exit 2
fi

baseline="$(mktemp -d "${TMPDIR:-/tmp}/atalaya-buf-breaking.XXXXXXXX")"
trap 'rm -rf "$baseline"' EXIT
git archive --format=tar "$baseline_commit" -- buf.yaml proto | tar -xf - -C "$baseline"
buf breaking proto --against "$baseline/proto"

#!/usr/bin/env bash
# Verificación de cierre de la FASE 0 (docs/evidence/FASE-0/CIERRE.md).
set -eu
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
uv run --frozen python -m scripts.evidence --verify docs/evidence/FASE-0
make check
scripts/demo_guardrails.sh
uv run --frozen python -m scripts.traceability --fase 0 --out reports/trazabilidad-fase0.md

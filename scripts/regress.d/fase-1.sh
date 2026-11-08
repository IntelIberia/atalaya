#!/usr/bin/env bash
# Verificación de cierre de la FASE -1 (docs/evidence/FASE--1/CIERRE.md).
set -eu
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
python3 -I scripts/check_spec.py
python3 -I -m unittest discover -s scripts -p 'test_check_spec.py'

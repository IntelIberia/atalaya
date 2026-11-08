# Makefile de Atalaya. Objetivos documentados en CLAUDE.md. (Versión provisional de T0.5;
# se completa en T0.9 con bootstrap, regress, trace y evidence.)
SHELL := /bin/bash
UV := uv run --frozen

.PHONY: doctor check lint typecheck test spec

doctor: ## Comprueba las herramientas de desarrollo
	@scripts/doctor.sh

lint: ## Lint y formato (sin modificar)
	@$(UV) ruff check .
	@$(UV) ruff format --check .
	@shellcheck scripts/*.sh scripts/hooks/*.sh .githooks/*

typecheck: ## Tipos estrictos
	@$(UV) mypy --strict scripts tests

test: ## Tests
	@$(UV) pytest -q

spec: ## Coherencia de la especificación (FASE -1)
	@python3 -I scripts/check_spec.py > /dev/null && echo "check_spec: OK" || python3 -I scripts/check_spec.py
	@python3 -I -m unittest discover -s scripts -p 'test_check_spec.py' 2>&1 | tail -1

check: lint typecheck test spec ## Verificación completa
	@echo "make check: OK"

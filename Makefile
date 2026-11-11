# Makefile de Atalaya. Objetivos documentados en CLAUDE.md.
SHELL := /bin/bash
# OJO: GNU Make 3.81 (macOS) ignora .SHELLFLAGS: sin pipefail. Prohibido `| tail` en recetas
# (ocultaría fallos); lo comprueba tests/test_makefile.py.
UV := uv run --frozen
PY := python3 -I
FASE ?= 0
CRITICAL_COV := $(shell $(PY) -c "import tomllib;c=tomllib.load(open('pyproject.toml','rb'))['tool']['atalaya'];print(','.join(c['coverage_critical']))")
COV_MIN := $(shell $(PY) -c "import tomllib;print(tomllib.load(open('pyproject.toml','rb'))['tool']['atalaya']['coverage_branch_min'])")
MUT_FILES := $(shell $(PY) -c "import tomllib;print(' '.join(tomllib.load(open('pyproject.toml','rb'))['tool']['atalaya']['mutation_critical']))")

.PHONY: help bootstrap doctor check lint typecheck test coverage guard spec trace regress \
        evidence mutation fmt up smoke down proto-breaking

COMPOSE := docker compose --env-file .env -f infra/compose/compose.yaml

help: ## Lista los objetivos
	@sed -nE 's/^([a-z-]+):.*## (.*)/\1\t\2/p' Makefile

bootstrap: ## Entorno completo: dependencias, hooks de git y secretos locales
	uv sync --frozen
	git config core.hooksPath .githooks
	@if [ -x scripts/gen_local_secrets.sh ]; then scripts/gen_local_secrets.sh; fi
	@echo "bootstrap: OK"

doctor: ## Comprueba las herramientas de desarrollo
	@scripts/doctor.sh

proto-breaking: ## Comprueba cambios incompatibles de Protobuf contra origin/main
	@scripts/proto_breaking.sh

check: lint typecheck test coverage guard spec trace ## Verificación completa (la exige el hook Stop)
	@echo "make check: OK"

lint: ## Lint y formato (sin modificar ficheros)
	@buf lint
	@$(UV) ruff check -q .
	@$(UV) ruff format --check -q .
	@shellcheck scripts/*.sh scripts/hooks/*.sh scripts/regress.d/*.sh .githooks/*
	@echo "lint: OK"

typecheck: ## Tipos estrictos
	@$(UV) mypy --strict scripts tests proto/python

test: ## Tests (+ JUnit para trazabilidad y cobertura de ramas)
	@mkdir -p reports
	@$(UV) pytest -q -p no:cacheprovider --junitxml=reports/junit.xml \
		--cov=scripts --cov=atalaya_contracts --cov-branch --cov-report=

coverage: test ## Cobertura de ramas del código crítico ≥ umbral (ADR 0006)
	@$(UV) coverage json --include="$(CRITICAL_COV)" -o reports/coverage-critical.json -q
	@$(UV) python -m scripts.branch_coverage reports/coverage-critical.json $(COV_MIN)

guard: ## Guardarraíles sobre todo el árbol versionable
	@git ls-files -z --cached --others --exclude-standard | xargs -0 $(PY) scripts/guardrails.py --paths
	@echo "guard: OK"

spec: ## Coherencia de la especificación (FASE -1)
	@mkdir -p reports
	@$(PY) scripts/check_spec.py > reports/check_spec.log || { cat reports/check_spec.log; exit 1; }
	@$(PY) -m unittest discover -s scripts -p 'test_check_spec.py' -q 2> reports/unittest_spec.log || { cat reports/unittest_spec.log; exit 1; }
	@echo "spec: OK"

trace: test ## Trazabilidad requisito → tests
	@$(UV) python -m scripts.traceability

regress: ## Verificaciones de cierre de todas las fases cerradas
	@scripts/regress.sh

evidence: ## Paquete de evidencias de la fase: make evidence FASE=N
	@$(UV) python -m scripts.evidence --fase $(FASE)

mutation: ## Mutation testing del código crítico (lento): make mutation FASE=N
	rm -rf mutants
	$(UV) python -m scripts.mutation_report --snapshot reports/mutation-inputs.json $(MUT_FILES)
	$(UV) mutmut run --max-children 4 > reports/mutmut.log 2>&1 || true
	$(UV) python -m scripts.mutation_report --inputs reports/mutation-inputs.json --out docs/evidence/FASE-$(FASE)/mutacion.json $(MUT_FILES)

fmt: ## Formatea el código (modifica ficheros)
	$(UV) ruff format .
	$(UV) ruff check --fix .

up: ## Arranca el stack local (Docker Compose) y espera a que esté sano
	@scripts/gen_local_secrets.sh
	$(COMPOSE) up -d --wait

smoke: ## Tests de integración con el stack en marcha (JUnit para trazabilidad)
	@mkdir -p reports
	@$(UV) pytest -q -p no:cacheprovider -m integracion tests/integracion -s \
		--junitxml=reports/junit-integracion.xml

down: ## Para el stack (conserva los volúmenes)
	$(COMPOSE) down

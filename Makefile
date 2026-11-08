# Makefile de Atalaya. Objetivos documentados en CLAUDE.md.
.PHONY: doctor

doctor: ## Comprueba las herramientas de desarrollo
	@scripts/doctor.sh

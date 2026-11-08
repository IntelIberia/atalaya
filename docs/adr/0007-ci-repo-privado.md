# 0007 — CI en repositorio privado gratuito: ligera, sin CodeQL

- Estado: aceptado (pendiente de confirmar límites exactos de GitHub: NO VERIFICADO)
- Fecha: 2026-11-08
- Decisores: usuario, Claude Code (discrepancias D3 y D4)

## Contexto
REQ-SEC-012 pide SBOM, vulnerabilidades, secretos y análisis estático (el MEGAPROMPT cita semgrep y
CodeQL). El repo es privado en una cuenta gratuita: minutos de Actions limitados y code scanning de
GitHub de pago en privados (pendiente de confirmación por fuente primaria).

## Opciones consideradas
1. CI completa (incluida mutación, e2e y Android) en cada push: agota los minutos gratuitos.
2. **CI ligera** en cada push/PR + pruebas pesadas en local con evidencia en el paquete de la fase.
3. Hacer público el repo para tener CodeQL gratis: expone modelo de amenazas y cobertura (rechazado).

## Decisión
Opción 2. `ci.yml`: `make check`, `make regress` y guardarraíles sobre el rango del PR.
`security.yml`: gitleaks (binario verificado por SHA-256), SBOM syft + grype (falla en críticas),
semgrep CE (`p/python`, `p/github-actions`, `p/secrets`) y licencias. **Sin CodeQL.** Acciones fijadas
por SHA. Mutación, compose y e2e en local (`make mutation`, `make smoke`).

## Consecuencias
- Pruebas negativas en CI realizadas (G-08, G-06, G-12): las tres en rojo.
- gitleaks con `fetch-depth: 0` analiza todas las ramas: una rama con un secreto contamina las demás
  ejecuciones (observado en T0.11). Aceptado: es conservador.

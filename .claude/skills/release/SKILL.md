---
description: "Prepara una versión (SemVer) de Atalaya con SBOM, escaneo de vulnerabilidades, notas y etiqueta firmada. Solo manual."
disable-model-invocation: true
---
# Release $ARGUMENTS

Solo la invoca el usuario (`/release X.Y.Z`).
1. `make check`, `make regress` y `scripts/verify_clean_clone.sh` en verde; CI en verde en `main`.
2. SBOM (syft) por artefacto y escaneo (grype/trivy) sin vulnerabilidades críticas abiertas.
3. Notas de versión desde los Conventional Commits, con impacto legal y de privacidad.
4. Etiqueta `vX.Y.Z` anotada; no publicar artefactos ni hacer push sin confirmación explícita del usuario.

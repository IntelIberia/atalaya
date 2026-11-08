# Registro de tareas — FASE 0

| Fecha | Commit | Tarea | Comando de verificación | Resultado real | Prueba negativa | Estado |
|---|---|---|---|---|---|---|
| 2026-11-08 | — | Preparación: liberar disco (aprobado por el usuario) | `df -h ~` | De 14 a 31 GB libres. Borrado: cachés de NetBeans, pip, go-build, selenium, Homebrew, npm y uv (sin usar); caché de construcción e imágenes dangling de Docker. **No tocado:** documentos, proyectos, navegadores, Spotify, Playwright, Papelera, Descargas, imágenes, contenedores y volúmenes de Docker de otros proyectos | — | OK |
| 2026-11-08 | (este) | T0.1 Herramientas y `make doctor` | `make doctor` | exit 0; buf 1.75.0, gitleaks 8.30.1, shellcheck 0.11.0 instalados con Homebrew | `PATH=/usr/bin:/bin make doctor` → exit 2 (make) / 1 (script), con 6 obligatorias como FALTA | OK |

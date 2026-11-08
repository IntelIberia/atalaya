# Registro de tareas — FASE -1

| Fecha | Commit | Tarea | Comando de verificación | Resultado real | Prueba negativa | Estado |
|---|---|---|---|---|---|---|
| 2026-11-08 | — | Crear el repositorio privado y copiar el MEGAPROMPT | `gh repo create IntelIberia/atalaya --private --clone`; `shasum -a 256 docs/MEGAPROMPT.md` | Repo creado; hash `9ed57e4c…0ed34b74`, igual que el original del Escritorio | `gh repo view` antes de crear: el repo no existía (sin sobrescritura) | OK |
| 2026-11-08 | — | Entrevista en 4 bloques | Respuestas registradas en `ENTREVISTA-FASE--1.md` | 16 preguntas respondidas, más una corrección del usuario (alojamiento: solo local) | — (no aplica) | OK |
| 2026-11-08 | 4039896 | SPEC, requisitos, plan de pruebas y riesgos | `python3 -I scripts/check_spec.py` | 130 requisitos, 24 casos de uso, 0 huérfanos, 22/22 filas de correspondencia, 34/34 menciones revisadas, exit 0 | 4 fallos inyectados en una copia: los 4 detectados, exit 1 (primera versión del script) | OK |
| 2026-11-08 | 4039896 | Revisión independiente P5 y correcciones | Subagente revisor sin contexto | 20 hallazgos (4 ALTA), todos resueltos (`revision-independiente.md`) | — | OK |
| 2026-11-08 | 4039896 | Tests del verificador | `python3 -I -m unittest discover -s scripts -p 'test_check_spec.py' -v` | 21 tests, 21 OK, exit 0 | 20 de los 21 tests son pruebas negativas (inyectan un fallo y exigen exit 1). Primera ejecución: 2 FALLO por un defecto real del patrón, corregido antes del commit | OK |
| 2026-11-08 | 4039896 | Reproducibilidad en un clon limpio | `git clone` en un directorio nuevo + check + tests | Ambos con exit 0 (`clon_limpio.txt`) | — | OK |

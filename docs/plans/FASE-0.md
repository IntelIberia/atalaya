# Plan FASE 0 — Arranque, gobernanza y guardarraíles

Versión 1 · 2026-11-08 · Estado: **pendiente de aprobación (STOP de plan, puerta P0)**

## 1. Objetivo
Dejar el monorepo listo para construir con seguridad: estructura, herramientas, `make` con todos sus objetivos, CI, trazabilidad, evidencias reproducibles y **guardarraíles legales que no se puedan desactivar en silencio**. También gobernanza para Claude Code (CLAUDE.md, reglas, permisos, hooks, subagentes, skills) y los documentos v0 de arquitectura, legal, amenazas, DPIA y ENS.

## 2. Requisitos que cubre
MUST de la FASE 0: REQ-SEC-001, REQ-SEC-002, REQ-SEC-003, REQ-SEC-005, REQ-SEC-012, REQ-SEC-015, REQ-SEC-016, REQ-LEG-001, REQ-LEG-002, REQ-LEG-016, REQ-LEG-017, REQ-NFR-014, REQ-NFR-015, REQ-NFR-016, REQ-NFR-018 (parte de guardarraíles), REQ-PRIV-003, REQ-PRIV-006, REQ-PRIV-007.

## 3. Hallazgos de la exploración (2026-11-08)

| Hallazgo | Efecto |
|---|---|
| Ya instalados: uv 0.11.7, Python 3.12.13, Docker 29.0.1, Node 24.9, Java 21, GNU Make 3.81, Homebrew, adb | Base suficiente para la FASE 0 |
| Faltan: buf, gitleaks, shellcheck, syft, grype, trivy, semgrep, mosquitto, clang-format, ESP-IDF, Android SDK, Gradle | En la FASE 0 solo se instalan con Homebrew **buf, gitleaks y shellcheck** (pequeños). syft, grype y semgrep corren en CI. Android y ESP-IDF se instalan en sus fases |
| **Disco: 14 GB libres de 195 GB (93 % ocupado)** | Riesgo alto (R-28): Docker Desktop, imágenes, Android SDK (~10 GB) y datasets no caben. Pido liberar espacio antes de T0.10 |
| **RAM: 8 GB** | Docker Desktop limitado a ~3 GB; compose mínimo |
| Docker Desktop instalado pero **parado** | T0.10 necesita arrancarlo (`open -a Docker`) |
| Documentación oficial de Claude Code verificada (settings, permissions, hooks, skills, sub-agents, memory) | Las reglas `deny` de `Read` **no** impiden leer con `cat` desde Bash, y los patrones `Bash(...)` no son una barrera de seguridad → defensa en profundidad con un hook PreToolUse sobre Bash. El hook Stop protege contra bucles con `stop_hook_active`. `.claude/rules/` con `paths:` existe. Skills: `disable-model-invocation: true`. Subagentes: `tools` y `disallowedTools` |
| Partes de hooks y skills leídas solo como resumen (el JSON de salida de Stop y la tabla completa del frontmatter de skills) | Se vuelven a verificar en T0.5 y T0.7 antes de escribirlas |

## 4. Tareas

Orden estricto. Cada tarea: TDD (primero el test que falla), verificación más prueba negativa registradas en `docs/evidence/FASE-0/registro-tareas.md` y un commit con los IDs. **Un FALLO bloquea la tarea siguiente.**

### T0.1 — Herramientas y `make doctor`
- **Qué:** instalar con Homebrew `buf`, `gitleaks` y `shellcheck`. `scripts/doctor.sh` comprueba las herramientas y sus versiones mínimas, y `make doctor` lo ejecuta.
- **Requisitos:** REQ-NFR-015
- **Verificación:** `make doctor`
- **Resultado esperado:** exit 0 y una tabla con uv, python3.12, docker, buf, gitleaks y shellcheck y sus versiones.
- **Prueba negativa:** `PATH=/usr/bin:/bin make doctor` → exit ≠ 0 nombrando cada herramienta que falta.

### T0.2 — Esqueleto del monorepo y entorno Python
- **Qué:** directorios del MEGAPROMPT con un README de una línea cada uno; `pyproject.toml` raíz (uv, Python 3.12) con ruff, `mypy --strict`, pytest, hypothesis y mutmut fijados en `uv.lock`; `.gitignore` (incluye `.env*`, `secrets/`, `data/raw/`, audio); `.editorconfig`; marcador de pytest `req`.
- **Requisitos:** REQ-NFR-014, REQ-NFR-015
- **Verificación:** `uv sync --frozen && uv run pytest tests/test_estructura.py -v && uv run ruff check . && uv run mypy --strict scripts tests`
- **Resultado esperado:** todo en verde; el test de estructura comprueba los 10 directorios raíz y sus subdirectorios.
- **Prueba negativa:** borrar `sim/` en una copia temporal → el test de estructura falla nombrando `sim/`.

### T0.3 — Motor de guardarraíles (`scripts/guardrails.py` + `scripts/guardrails.sh`)
- **Qué:** analiza el diff (`--staged`, `--range A..B` para CI) o rutas concretas (`--paths`). Bloquea con exit 2:
  - (a) APIs y comandos de transmisión SDR (`hackrf_transfer -t`/`-c`, `writeStream` y `SOAPY_SDR_TX` de SoapySDR, `tx_*` y `tx()` de pyadi-iio/Pluto, `osmocom_siggen`, `rpitx`…);
  - (b) términos ofensivos en código (`jamming`, `jammer`, `spoofing`, `deauth`, `takeover` y equivalentes en español);
  - (c) ficheros de audio (`.wav .flac .mp3 .ogg .m4a .opus .aac .aiff`) fuera de `tests/fixtures/sinteticos/`;
  - (d) campos `pilot_*` u `operator_id` en mensajes o esquemas marcados `PUBLIC`;
  - (e) secretos (gitleaks, más reglas internas cuando no está instalado).
  
  Lista blanca de identificadores defensivos en `scripts/guardrails_allowlist.txt` (ADR 0005).
- **Requisitos:** REQ-SEC-001, REQ-LEG-001, REQ-LEG-002, REQ-LEG-007, REQ-NFR-018
- **Verificación:** `uv run pytest tests/guardrails -v` y `uv run mutmut run --paths-to-mutate scripts/guardrails.py` (umbral del ADR 0006)
- **Resultado esperado:** ≥ 25 tests en verde, que cubren G-01 a G-06 con varios casos por categoría; puntuación de mutación ≥ 80 % (propuesta del ADR 0006); cobertura de ramas ≥ 90 %.
- **Prueba negativa:** cada muestra prohibida → exit 2 con el motivo; `detect_forged_remote_id` → exit 0; `spoof_remote_id` (no está en la lista blanca) → exit 2; un `.wav` dentro de `tests/fixtures/sinteticos/` → exit 0.

### T0.4 — Hook de git `pre-commit`
- **Qué:** `.githooks/pre-commit` → `scripts/guardrails.sh --staged`; `make bootstrap` configura `core.hooksPath`.
- **Requisitos:** REQ-SEC-001
- **Verificación:** `scripts/demo_guardrails.sh` crea un repo temporal e intenta tres commits (un `.wav`; `jamming` en un `.py`; `pilot_lat` en un `.proto` `PUBLIC`).
- **Resultado esperado:** los tres commits se rechazan; la salida se guarda como evidencia (es la «prueba documentada» que pide el MEGAPROMPT).
- **Prueba negativa:** un commit limpio en el mismo repo temporal pasa. Limitación documentada: `git commit --no-verify` se salta el hook en local, y por eso la CI (T0.11) repite el análisis.

### T0.5 — `.claude/settings.json` y hooks de Claude Code
- **Qué:**
  - **Reglas `deny`:** `Read(./.env)`, `Read(./.env.*)`, `Read(./secrets/**)`, `Edit(/evals/frozen/**)`, `Edit(/data/raw/**)`, `Bash(git push --force *)`, `Bash(git push -f *)`, `Bash(hackrf_transfer *)`, `Bash(SoapySDRUtil *)`, `Bash(iio_attr *)`, `Bash(rpitx *)`.
  - **PreToolUse Bash** (`scripts/hooks/pre_bash.py`): bloquea comandos que tocan `.env`/`secrets/`, que transmiten por SDR o que fuerzan un push, y con `if: "Bash(git commit *)"` ejecuta `guardrails.sh --staged`.
  - **PostToolUse `Edit|Write`** (`scripts/hooks/post_edit.sh`): `ruff format` + `ruff check` en `.py`, `shellcheck` en `.sh`; exit 2 con el aviso si falla.
  - **Stop** (`scripts/hooks/stop_check.sh`): si `stop_hook_active` es true → exit 0; si no, ejecuta `make check` y, si falla, exit 2 pidiendo **informar del fallo o corregirlo**, nunca ocultarlo (ADR 0006).
  
  Antes de escribir: volver a verificar en la documentación el JSON de salida y el exit 2 del hook Stop. Los scripts se prueban sin conexión **antes** de activarlos, para no bloquear la sesión.
- **Requisitos:** REQ-SEC-002, REQ-LEG-002
- **Verificación:** `uv run pytest tests/hooks -v` (stdin JSON de ejemplo, uno por caso); `python3 -m json.tool .claude/settings.json`; demostración en vivo con la salida en la evidencia: el Read de `.env` se deniega y `cat .env` por Bash se bloquea.
- **Resultado esperado:** los tests en verde, el JSON válido y las dos denegaciones en vivo registradas.
- **Prueba negativa:** `cat README.md` se permite (sin falso positivo); con `stop_hook_active: true` el hook Stop sale con 0 aunque `make check` falle.

### T0.6 — `CLAUDE.md` y reglas por ruta
- **Qué:**
  - `CLAUDE.md` de menos de 150 líneas: comandos exactos, restricciones legales resumidas, lo que confunde del repo y el puntero al MEGAPROMPT.
  - `.claude/rules/legal.md`, sin `paths`, siempre cargada; incluye REQ-LEG-017 (detenerse ante peticiones contrarias).
  - `edge.md` (`paths: edge/**`; el audio nunca toca disco).
  - `ml.md` (`paths: ml/**, evals/**`; no tocar `evals/frozen/`).
  - `rf.md` (`paths: edge/rf-presence/**, edge/adsb/**, edge/esp32-remoteid/**`; solo recepción).
- **Requisitos:** REQ-LEG-017, REQ-LEG-001
- **Verificación:** `uv run pytest tests/test_gobernanza.py -v`
- **Resultado esperado:** los tests comprueban que `CLAUDE.md` tiene menos de 150 líneas y las secciones obligatorias, y que cada regla tiene un frontmatter válido con los globs esperados.
- **Prueba negativa:** en una copia, `CLAUDE.md` con 150 líneas o sin la sección legal → el test falla.

### T0.7 — Subagentes y skills
- **Qué:**
  - **Subagentes** en `.claude/agents/`: `independent-reviewer`, `security-reviewer`, `legal-guardrail-reviewer`, `test-auditor`, `ml-eval-reviewer`, `sapient-conformance` y `privacy-reviewer`. Herramientas `Read, Grep, Glob`. `test-auditor` y `independent-reviewer` además `Bash` (para ejecutar tests) con `disallowedTools: Write, Edit, NotebookEdit`.
  - **Skills** en `.claude/skills/`: `phase-plan`, `phase-close`, `new-adr`, `dataset-intake` y `release` (`disable-model-invocation: true`).
- **Requisitos:** REQ-SEC-003 (revisión independiente como parte de las puertas), REQ-LEG-017
- **Verificación:** `uv run pytest tests/test_agentes_skills.py -v`
- **Resultado esperado:** los 7 agentes tienen `name` y `description` y ninguno tiene herramientas de escritura; las 5 skills tienen `description`; `release` tiene `disable-model-invocation: true`.
- **Prueba negativa:** en una copia, añadir `Write` a un revisor → el test falla.

### T0.8 — Trazabilidad (`scripts/traceability.py`)
- **Qué:**
  - Lee REQUIREMENTS.md (columna Fase), `docs/requirements/FASES-CERRADAS.txt` y el JUnit XML de pytest con los marcadores `req`, y genera `docs/requirements/TRAZABILIDAD.md`.
  - Falla si un MUST de una fase cerrada no tiene ningún test en verde, salvo un bloqueo **B** aprobado.
  - Los requisitos de inspección se cubren con tests de estructura de documentos.
  - Integra `check_spec.py`.
- **Requisitos:** REQ-NFR-014, REQ-SEC-003
- **Verificación:** `make trace`
- **Resultado esperado:** `TRAZABILIDAD.md` generado, sin huecos MUST en las fases cerradas (-1, y 0 al cerrar).
- **Prueba negativa:** fixture con un MUST de una fase cerrada sin test → exit 1 con su ID; fixture con el test en rojo → exit 1.

### T0.9 — Makefile, evidencias, regresión y clon limpio
- **Qué:**
  - Objetivos `bootstrap`, `check`, `test`, `lint`, `typecheck`, `fmt`, `regress`, `trace`, `evidence` y `doctor`.
  - `scripts/evidence.py` genera `docs/evidence/FASE-N/` con las salidas, `MANIFEST.sha256` y el commit exacto.
  - `scripts/regress.sh` ejecuta `scripts/regress.d/<fase>.sh` de cada fase cerrada.
  - `scripts/verify_clean_clone.sh` clona en un directorio nuevo y ejecuta `make bootstrap && make check`.
- **Requisitos:** REQ-NFR-014
- **Verificación:** `make check && make regress && make evidence FASE=0 && (cd docs/evidence/FASE-0 && shasum -a 256 -c MANIFEST.sha256) && scripts/verify_clean_clone.sh`
- **Resultado esperado:** todo con exit 0; `make check` en < 60 s (para que el hook Stop sea viable).
- **Prueba negativa:** alterar un byte de un fichero del paquete → la verificación del manifiesto falla; si `verify_clean_clone.sh` encuentra el árbol con cambios sin commit, avisa y verifica solo `HEAD`.

### T0.10 — Docker Compose mínimo, sin credenciales por defecto
- **Qué:** `infra/compose/compose.yaml` con Mosquitto 2 (sin anónimos, contraseñas generadas en `make bootstrap` en `.env`, que está en `.gitignore` y tiene Read denegado), NATS con JetStream, Redis con `requirepass` generado y PostgreSQL (la imagen la decide el ADR 0003: PostGIS + TimescaleDB, eligiendo la de menor tamaño por el disco). Healthchecks en todos. Requiere Docker arrancado y ~1-2 GB libres.
- **Requisitos:** REQ-SEC-005, REQ-NFR-015
- **Verificación:** `make up && make smoke`: publica y consume un mensaje en MQTT y en NATS, `SELECT postgis_version()` y la extensión timescaledb, y `PING` en Redis con contraseña.
- **Resultado esperado:** los 4 servicios sanos y el smoke en verde.
- **Prueba negativa:** conexión anónima a Mosquitto → rechazada; Redis sin contraseña → `NOAUTH`; un test analiza `compose.yaml` y falla si encuentra contraseñas en claro o valores por defecto.

### T0.11 — CI en GitHub Actions
- **Qué:**
  - Workflow `ci.yml` en cada push y PR: lint, tipos, tests, guardarraíles sobre el rango del PR, check_spec, trazabilidad y regresión.
  - Workflow `security.yml`: gitleaks, SBOM con syft, grype (falla en crítico), semgrep CE y comprobación de licencias (lista de bloqueo AGPL/GPL, G-12).
  - Acciones fijadas por SHA. Ligero por los minutos limitados en repos privados (ADR 0007).
- **Requisitos:** REQ-SEC-003, REQ-SEC-012, REQ-LEG-016
- **Verificación:** `git push` y `gh run watch` → los dos workflows en verde.
- **Resultado esperado:** CI en verde en `main`, con el SBOM como artefacto.
- **Prueba negativa (G-08, G-06, G-12):** tres ramas de prueba en PR borrador, cada una de las cuales debe poner la CI en **rojo**: una desactiva un guardarraíl (cambia una regla de `guardrails.py`), otra añade un secreto falso y otra añade una dependencia GPL. Se registra el enlace a cada ejecución, y después se cierran los PR y se borran las ramas.

### T0.12 — ADR y documentos v0
- **Qué:** ADR (MADR):
  - **0001** arquitectura (monolito modular hexagonal orientado a eventos);
  - **0002** restricciones legales (con el texto del art. 82.4 de la Ley 11/2022 comprobado en el BOE, o marcado NO VERIFICADO si no se puede);
  - **0003** stack (incluida la imagen de PostgreSQL y el framework del dashboard, aplazable a la FASE 10);
  - **0004** presupuesto de 0 € y alcance v1 (D5, D8);
  - **0005** guardarraíl con lista blanca defensiva (D1);
  - **0006** hook Stop con protección contra bucles y umbrales de cobertura y mutación (D2);
  - **0007** CI en repo privado: sin CodeQL y CI ligera (D3, D4).
  
  Además: `docs/threat-model/v0.md` (STRIDE, incluidos los ataques a la red de sensores), `docs/dpia/v0.md` con el registro de actividades v0, `docs/ens/v0.md` (mapa inicial de medidas, categoría MEDIA), `docs/tech-debt.md`, plantillas `docs/plans/PLANTILLA-FASE.md` y `docs/evidence/PLANTILLA-registro-tareas.md`, y R-28/R-29 en `RIESGOS.md`. Las discrepancias D6, D7 y D9 a D12 se resuelven con ADR en sus fases (6, 4/6, 5, 3, 5 y 10).
- **Requisitos:** REQ-SEC-015, REQ-SEC-016, REQ-PRIV-006, REQ-PRIV-007, REQ-NFR-016, REQ-LEG-001
- **Verificación:** `uv run pytest tests/test_documentos.py -v && python3 -I scripts/check_spec.py`
- **Resultado esperado:** cada ADR tiene Estado, Contexto, Decisión y Consecuencias; el modelo de amenazas tiene las 6 categorías STRIDE; la DPIA tiene la base jurídica por tratamiento; check_spec OK (las líneas sensibles nuevas se añaden a la lista blanca solo tras leerlas).
- **Prueba negativa:** en una copia, quitar «Consecuencias» de un ADR o la categoría «Repudio» de STRIDE → el test falla.

### T0.13 — Cierre de fase
- **Qué:**
  - Puertas P2 a P5: `make check`, `make regress`, `verify_clean_clone.sh`.
  - Subagentes `independent-reviewer`, `test-auditor`, `security-reviewer`, `legal-guardrail-reviewer` y `privacy-reviewer`, sin contexto de la implementación; hallazgos corregidos o justificados.
  - `make evidence FASE=0` y `CIERRE.md`.
- **Requisitos:** todos los de §2
- **Verificación:** los comandos de P2-P4, con su salida pegada en el paquete.
- **Resultado esperado:** todo en verde y `TRAZABILIDAD.md` sin huecos MUST de las fases -1 y 0.
- **Prueba negativa:** la ya incluida en cada puerta.

## 5. Riesgos de la fase

| ID | Riesgo | Mitigación |
|---|---|---|
| R-28 (nuevo) | Disco casi lleno (14 GB libres) y 8 GB de RAM | Liberar espacio (decisión del usuario); compose mínimo; herramientas pesadas solo en CI |
| R-29 (nuevo) | Un hook mal escrito bloquea la propia sesión de Claude Code (por ejemplo, un PreToolUse que deniega todo Bash) | Scripts probados sin conexión antes de activarlos; activación en el último paso de T0.5; `make check` rápido; el usuario puede desactivar los hooks desde `/hooks` |
| R-19 | Minutos de Actions limitados | CI ligera; mutación y e2e en local (ADR 0007) |
| R-23 | Guardarraíl con falsos positivos | Lista blanca probada (G-04) |
| — | Las reglas `deny` de Bash no son una barrera de seguridad (según la documentación oficial) | Defensa en profundidad: deny + hook PreToolUse + pre-commit + CI. Se documenta que el aislamiento a nivel de sistema operativo (sandbox) es la medida fuerte |

## 6. Estimación
1-2 semanas de trabajo efectivo (13 tareas). Coste: 0 €. Instalaciones con Homebrew: buf, gitleaks y shellcheck (~100-200 MB, NO VERIFICADO).

## 7. Decisiones que necesita el usuario (antes o durante la fase)
1. Aprobar este plan (P0).
2. Aprobar las instalaciones con Homebrew de T0.1.
3. **Liberar espacio en disco** antes de T0.10: recomiendo ≥ 25 GB libres. Por debajo de 10 GB, T0.10 queda bloqueada.
4. Permitir que arranque Docker Desktop en T0.10.
5. Aprobar las tres ramas y PR borradores de prueba de T0.11 (se borran al terminar).

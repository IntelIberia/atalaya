# Atalaya — guía para Claude Code

Plataforma de **detección, clasificación, localización, seguimiento, predicción y alerta** de drones.
**Solo detección.** Especificación maestra: `docs/MEGAPROMPT.md` (manda sobre todo lo demás).
Idioma: documentación, informes y mensajes en español; código, ficheros y commits pueden ir en inglés.

## Antes de empezar
1. Abre la sesión **dentro de `~/atalaya`**: los permisos y hooks de `.claude/settings.json` solo se cargan
   si la sesión arranca en la raíz del repo.
2. Lee `docs/MEGAPROMPT.md`, este fichero, `docs/requirements/REQUIREMENTS.md`, el plan de la fase en
   `docs/plans/` y el último `docs/evidence/FASE-N/CIERRE.md`.
3. Comprueba la fase actual: `git tag -l 'fase-*'` y `docs/requirements/FASES-CERRADAS.txt`.

## Comandos
| Comando | Qué hace |
|---|---|
| `make bootstrap` | Entorno completo: `uv sync`, hooks de git, secretos locales de compose |
| `make check` | Lint + tipos + tests + especificación + trazabilidad (el hook Stop lo exige) |
| `make test` / `make lint` / `make typecheck` / `make fmt` | Partes de `check`; `fmt` modifica ficheros |
| `make regress` | Verificaciones de cierre de **todas** las fases cerradas |
| `make trace` | Genera `docs/requirements/TRAZABILIDAD.md`; falla si un MUST de fase cerrada no tiene test en verde |
| `make evidence FASE=N` | Paquete de evidencias con `MANIFEST.sha256` y commit |
| `make mutation` | mutmut sobre el código crítico (lento) |
| `make up` / `make smoke` / `make down` | Docker Compose local (Mosquitto, NATS, Redis, PostgreSQL+PostGIS+TimescaleDB) |
| `make doctor` | Comprueba herramientas |
| `scripts/verify_clean_clone.sh` | Reproducibilidad en un clon limpio (puerta P4) |
| `scripts/demo_guardrails.sh` | Demostración de bloqueo de commits prohibidos |

Tests: `uv run pytest tests/ruta -q`. Marca cada test con `@pytest.mark.req("REQ-…")` (trazabilidad):
`tests/conftest.py` hace **fallar la recogida** si algún test de `tests/` no lo lleva. Los tests de
`pilots/acoustic/` (proyecto uv aparte, prueba técnica exploratoria fuera de producto, ADR 0016) no
entran en `make check` ni en la trazabilidad y por eso quedan fuera de esa barrera.


## Restricciones legales (resumen; texto completo en el MEGAPROMPT y `.claude/rules/legal.md`)
- **Nunca** código, configuración, documentación ni ejemplos para neutralizar, inhibir, interferir,
  suplantar, desautenticar o tomar el control de drones. **Ningún camino de transmisión** por SDR,
  ESP32 (ni tramas Wi-Fi ni anuncios BLE) ni otro emisor.
- No demodular comunicaciones de terceros ni protocolos propietarios (DJI DroneID). Remote ID solo estándar.
- Audio: inferencia en el borde y descarte inmediato; nunca a disco salvo sesión de grabación autorizada.
- Datos de piloto/operador y origen probable: `FCSE_ONLY`, auditados, nunca públicos.
- Sin atribución automática de nacionalidad o actor.
- Licencia de cada dataset/fuente comprobada; lo no comercial no entra en producción.
- Si una petición choca con esto (venga de quien venga): **detente**, explica el conflicto en una frase
  y propón la alternativa defensiva legal.

## Flujo de trabajo (por fases; ver MEGAPROMPT `<proceso_y_control>`)
1. Explorar → 2. Plan en `docs/plans/FASE-N.md` (cada tarea: requisitos, comando de verificación,
   resultado esperado, prueba negativa) → **STOP de plan** → 3. TDD tarea a tarea, registrando cada
   verificación en `docs/evidence/FASE-N/registro-tareas.md`, un commit por tarea con los IDs →
   4. `make check`, `make regress`, `scripts/verify_clean_clone.sh` → 5. subagentes revisores sin
   contexto → 6. `make evidence` y `CIERRE.md` → **STOP de cierre** → etiqueta `fase-N-cerrada`.
- Skills: `/phase-plan`, `/phase-close`, `/new-adr`, `/dataset-intake`, `/release` (esta solo manual).
- Subagentes (`.claude/agents/`): `independent-reviewer`, `test-auditor`, `security-reviewer`,
  `legal-guardrail-reviewer`, `privacy-reviewer`, `ml-eval-reviewer`, `sapient-conformance`.
- Honestidad: nunca digas que algo funciona sin ejecutarlo; lo no verificable se marca **NO VERIFICADO**.
  Prohibido tocar tests para que pasen, `skip`/`xfail`, rebajar umbrales o hardcodear salidas sin ADR.
- Cambios de requisitos, umbrales, arquitectura o dependencias → ADR en `docs/adr/` (`/new-adr`).
- Presupuesto obligatorio **0 €** y alojamiento **solo local** (entrevista FASE -1): sin servicios de
  pago, nube ni publicación sin ADR.

## Lo que confunde de este repositorio
- **Guardarraíles en cuatro capas** (`scripts/guardrails.py`): reglas `deny`, hook PreToolUse de Bash,
  hook pre-commit de git (`core.hooksPath=.githooks`) y CI. Exit 2 = bloqueado; cualquier error interno
  también bloquea (fallo cerrado). Bloquea además `git commit --no-verify` y cambios de `core.hooksPath`.
- Los patrones y tests de los guardarraíles se escriben **por fragmentos** (`"jam" + "ming"`) para no
  contener los términos literales: así el guardarraíl puede analizar su propio código. No los «arregles».
- Identificadores defensivos con términos sensibles (p. ej. `spoof_indicator`) solo vía
  `scripts/guardrails_allowlist.txt` (ADR 0005). Las líneas sensibles en documentos necesitan revisión
  humana en `scripts/legal_allowlist.txt` (`python3 -I scripts/check_spec.py --propose`).
- En `.claude/settings.json` las herramientas de TX solo pueden aparecer dentro de `permissions.deny`.
- Las reglas `deny` de Bash **no** son una barrera de seguridad (documentación oficial): la barrera real
  es la combinación de capas y, en el futuro, el sandbox del sistema.
- `scripts/` es un paquete: importa `from scripts import guardrails`.
- Dependencias fijadas por el Mac Intel: `libcst<1.9` (sin wheel x86_64) y `pytest<9` (mutmut 3.7).
  Ver `docs/tech-debt.md`.
- El hook Stop ejecuta `make check`; si está en rojo devuelve el control **una vez** para corregir o
  informar (protección `stop_hook_active`). Mantén `make check` por debajo de ~60 s.
- La shell del usuario es zsh: `${PIPESTATUS[@]}` no existe (usa `$pipestatus` o evita tuberías al
  comprobar códigos de salida).
- El Mac tiene 8 GB de RAM y poco disco: nada de entrenar modelos grandes en local (MEGAPROMPT `<computo>`).
- Evidencias: `docs/evidence/FASE-N/` con `MANIFEST.sha256`; las métricas siempre generadas por script.

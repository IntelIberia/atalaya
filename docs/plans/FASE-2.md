# Plan FASE 2 — Capa 1: radar de incidentes (solo local)

Versión 1.1 · 2026-11-10 · Estado: **pendiente de aprobación (STOP de plan, puerta P0)**

## 1. Objetivo
Construir y probar **en local** el radar de incidentes con drones en España y Europa a partir de fuentes
abiertas: ingesta respetuosa con los términos de cada fuente, deduplicación, geocodificación solo a
municipio o instalación (precisión pública ≥ 1 km), clasificación por reglas con un adaptador opcional
para LLM, estados Reportado / Probable / Confirmado / Descartado con fiabilidad Admiralty, revisión humana
obligatoria para «Confirmado», exportación STIX 2.1, API de solo lectura con límite de peticiones y web con
mapa (MapLibre), cronología y metodología.

En la v1 **nada se publica en Internet** (decisión D8 de `docs/SPEC.md` §10, REQ-LEG-013): el servidor
solo escucha en `127.0.0.1` y no existe ningún mecanismo de despliegue. Esta es la decisión global sobre
alojamiento; no debe confundirse con D-8 de FASE 1, que limita a coordenadas ficticias los escenarios del
simulador. Coste: 0 €.

## 2. Requisitos que cubre
- **MUST de la FASE 2:** REQ-FUN-007, REQ-FUN-008, REQ-FUN-009, REQ-FUN-010, REQ-FUN-011, REQ-FUN-012,
  REQ-FUN-015, REQ-LEG-010, REQ-LEG-011, REQ-LEG-013, REQ-PRIV-004.
- **SHOULD de la FASE 2:** REQ-FUN-013 (STIX 2.1), REQ-FUN-014 (API con límite de peticiones).
- **Transversales que esta fase debe mantener (0→ / 1→):** REQ-LEG-001, REQ-LEG-007, REQ-LEG-016,
  REQ-PRIV-003, REQ-PRIV-006, REQ-SEC-015, REQ-SEC-016, REQ-NFR-014, REQ-NFR-015, REQ-NFR-016.
- **Verificaciones de la fase en el MEGAPROMPT:** precisión geográfica y ausencia de nombres de personas
  en los campos públicos (G-15), e2e con Playwright, latencia fuente → publicación medida y precisión del
  clasificador auditada en una muestra.
- **Fuera de esta fase (no se adelantan):** RBAC con MFA (REQ-SEC-006, FASE 10), auditoría append-only
  general (REQ-SEC-008, FASE 10) y retención con borrado auditado (REQ-PRIV-005, FASE 10). El radar aplica
  ya un registro de revisiones encadenado por hash y una retención corta del material de las fuentes, sin
  darlos por cumplidos.

## 3. Hallazgos de la exploración (snapshot inicial 2026-11-08; estado actualizado 2026-11-10)

| Hallazgo | Efecto |
|---|---|
| **Estado actualizado al 2026-11-10** (árbol principal `codex/relevo-2026-11-09`, HEAD `069a4c7`; T1.6 ya integrada y publicada en la rama de trabajo): FASE 0 aprobada por P6 y con etiqueta `fase-0-cerrada`; la FASE 1 mantiene el P0 aprobado para la versión 3 y el plan actual v3.1 documenta la instalación de Buf, corrige los IDs de riesgos y registra el STOP de T1.8; decisiones D-1–D-8 registradas. T1.0–T1.6 constan como OK en el registro de tareas. La FASE 1 sigue abierta: no existe `fase-1-cerrada` ni está incluida `1` en `FASES-CERRADAS.txt`. | El hallazgo de 2026-11-08 sobre la FASE 0 abierta y la falta de plan/código de FASE 1 es histórico. **T2.0 sigue bloqueando** hasta que FASE 1 se cierre y se registren su etiqueta y estado. D-8 de FASE 1 trata de coordenadas ficticias en el simulador; la decisión global D8 de SPEC §10 mantiene el radar solo local |
| **FASE 1 ya establece contratos y sensibilidad**: existen los `.proto`, bindings y `docs/contracts/SENSIBILIDAD.md`; el STOP T1.3 aprobó 437 rutas. T1.7 debe probar sanitización de texto libre y controles de acceso antes de logs y salidas; ese trabajo aún no figura como cerrado | El radar debe heredar la convención y los controles aprobados; `OPERATOR` por sí solo no sanea datos personales. No dar por disponible el control de T1.7 hasta que FASE 1 lo cierre |
| En el snapshot actual, `apps/incident-radar/` y `services/ingest/` solo tienen un README. FASE 1 prevé implementar en `services/ingest/` la ingesta de sensores por MQTT | El radar de fuentes públicas sigue siendo nuevo y vivirá en `apps/incident-radar/` (backend Python y web TypeScript); mantenerlo separado del servicio de ingesta de sensores |
| `scripts/check_spec.py` revisa también `docs/plans/*.md`, `docs/adr`, `docs/dpia`, `docs/ens` y `docs/threat-model` | Este plan y los documentos de la fase se redactan sin menciones sensibles no revisadas |
| El guardarraíl trata `.yaml`, `.json`, `.toml` y `.sql` como código y bloquea términos ofensivos | Los fixtures del radar serán **sintéticos y neutros**; los titulares reales (que pueden contener vocabulario bloqueado) solo existen en la base de datos local, nunca en git |
| `scripts/license_check.py` solo mira dependencias Python | Hay que extenderlo a npm (G-12) antes de instalar el frontend |
| `scripts/pii_scan.py` detecta correos, teléfonos, DNI/NIE, IBAN e IP públicas | Se reutiliza en logs y salidas (REQ-PRIV-003); falta un detector de **nombres de persona** (REQ-PRIV-004) |
| Node 24.9 y npm 11.6 instalados; navegadores de Playwright en caché (chromium-1187, versión distinta a la que se fijará) | Habrá que descargar el Chromium de la versión fijada (~150-250 MB, NO VERIFICADO el tamaño) |
| **Snapshot histórico (2026-11-08):** disco 23 GB libres; RAM 8 GB | La capacidad se mide de nuevo en T2.0; sin modelos LLM locales por defecto (un modelo de 7B no cabe con holgura en RAM) |
| `make check` debe quedar por debajo de ~60 s (hook Stop) | Las pruebas web (vitest, eslint) y el e2e van en objetivos aparte (`make radar-web`, `make radar-e2e`), obligatorios en las puertas de fase |

### 3.1 Fuentes propuestas y estado de sus términos (consultado el 2026-11-08)

Regla general: **fallo cerrado**. Una fuente solo se activa si sus términos están archivados con fecha y
SHA-256 y el usuario la aprueba. Nunca se descarga el artículo enlazado (solo lo que la fuente sindica);
se respeta `robots.txt` y su `Content-Signal`.

| Fuente | Acceso | Términos | Propuesta |
|---|---|---|---|
| **Plataforma de Contratación del Sector Público** (licitaciones, Ministerio de Hacienda) | ATOM diario verificado en datos.gob.es: `contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom` | **VERIFICADO en la consulta del 2026-11-08; debe archivarse en T2.3.** Aviso legal de Hacienda (Ley 37/2007, RD 1495/2011): reutilización comercial permitida; citar «Origen de los datos: Ministerio de Hacienda»; no desnaturalizar; indicar la última actualización; no sugerir respaldo oficial | **Candidata**, pendiente de aprobación del usuario y archivo/hash de términos; capa «contratación pública», separada de los incidentes |
| **BOE, API de datos abiertos** (sumario diario; anuncios de licitación y normativa) | `boe.es/datosabiertos/api/boe/sumario/{aaaammdd}` (XML/JSON) verificado en su documentación | **VERIFICADO en la consulta del 2026-11-08; debe archivarse en T2.3.** Aviso legal de la AEBOE: reutilización comercial permitida; «Basado en datos de la Agencia Estatal Boletín Oficial del Estado» para obras derivadas; enlace a boe.es; no desnaturalizar; fecha de actualización | **Candidata**, pendiente de aprobación del usuario y archivo/hash de términos |
| **AESA** (noticias) | RSS verificado en `seguridadaerea.gob.es/es/rss.xml` (10 elementos; el último del 2026-10-30) | **VERIFICADO en la consulta del 2026-11-08; debe archivarse en T2.3.** Aviso legal: se permite la reproducción citando la fuente | **Candidata**, pendiente de aprobación del usuario y archivo/hash de términos (pocas noticias de incidentes; valor de contexto) |
| **GDELT DOC 2.0** (descubre artículos de medios por consulta) | API `api.gdeltproject.org/api/v2/doc/doc`, salida JSON/RSS, ventana de 3 meses; sin clave según su documentación (límite de uso NO VERIFICADO) | **VERIFICADO en la consulta del 2026-11-08; debe archivarse en T2.3.** Uso comercial gratuito con cita a The GDELT Project y enlace a gdeltproject.org | **Candidata**, pendiente de aprobación del usuario y archivo/hash de términos; propuesta como vía para medios con solo URL, dominio, fecha y titular interno |
| **ENAIRE, NOTAM Geospatial Service** (registro EUR SWIM) | REST JSON/GeoJSON; **requiere autorización previa** y credenciales | Parciales (uso operativo e informativo); licencia de redistribución y coste **NO VERIFICADOS** | **Pendiente de autorización.** Adaptador probado solo con NOTAM sintéticos; desactivado |
| **ENAIRE, web** (notas de prensa) | Accesible | **Restrictivos:** prohíbe reproducir contenidos y enlazar más allá de la portada sin autorización escrita | **No se ingiere.** El registro marca `enlace_profundo: false` |
| **Ministerio del Interior** | La web devuelve 403 a clientes automáticos; RSS **NO VERIFICADO** | `robots.txt` con `Content-Signal: search=yes, ai-train=no, use=reference`; aviso legal **NO VERIFICADO** | **Solo entrada manual** del analista (hechos + enlace); su contenido nunca va a un LLM |
| **Guardia Civil** | Portal accesible; el canal RSS aparece en menús antiguos pero **no se ha encontrado** en el portal actual (NO VERIFICADO) | **Restrictivos:** su nota legal limita el uso al privado y exige autorización expresa para cualquier otro (el texto habla de «Intranet»: ambiguo) | **Solo entrada manual** (hechos + enlace) hasta obtener autorización |
| Policía Nacional, Ministerio de Defensa, Instituciones Penitenciarias | Rutas probadas con 404 | **NO VERIFICADO** | Candidatas; se verifican en T2.3 |
| **Medios** (RTVE, Europa Press, El Faro de Ceuta, El Pueblo de Ceuta, 20minutos…) | RSS existentes en general | **NO VERIFICADO** (de RTVE solo hay referencias de segunda mano a condiciones restrictivas para sus RSS) | **Desactivados por defecto.** Se cubren con GDELT (enlace) salvo que se archiven sus términos y el usuario los apruebe |
| Comisión Europea y EASA (salas de prensa) | NO VERIFICADO | NO VERIFICADO | Candidatas europeas para T2.3 |

**Datos de referencia (no son fuentes de incidentes):**

| Dato | Uso | Licencia |
|---|---|---|
| IGN/CNIG, Nomenclátor Geográfico de Municipios y Entidades de Población | Municipios y centroides | CC BY 4.0 (indirecto: datos.gob.es enlaza las condiciones del IGN; el PDF de condiciones se lee en T2.7) |
| Wikidata (prisiones, aeropuertos, aeródromos, puertos, instalaciones) | Instalaciones | CC0 (**VERIFICADO**) |
| Natural Earth | Mapa base sin teselas externas | Dominio público (**VERIFICADO**) |
| INE, nombres y apellidos más frecuentes | Detector de nombres de persona | CC BY 4.0 según el aviso legal del INE (verificado por resumen de búsqueda; se relee en T2.13) |

### 3.2 Dependencias verificadas (PyPI y npm, 2026-11-08)

Política propuesta (ADR de T2.1): fijar la última versión publicada **hace al menos 14 días** y sin
copyleft fuerte en ejecución. Las versiones se vuelven a comprobar al instalar.

| Paquete | Versión a fijar | Licencia | Nota |
|---|---|---|---|
| feedparser | 6.0.14 | BSD-2-Clause | RSS/Atom |
| httpx | 0.28.1 | BSD-3-Clause | Cliente HTTP |
| pydantic | última ≥ 14 días (2.14.3 es del 2026-11-05) | MIT | Modelos y JSON estricto |
| fastapi / uvicorn | última ≥ 14 días (0.162.2 es del 2026-11-07) / 0.54.0 | MIT / BSD-3-Clause | API |
| asyncpg | 0.32.0 | Apache-2.0 | Rueda macOS x86_64 cp312 disponible. Se evita psycopg (LGPL según su repositorio; NO VERIFICADO hoy) |
| pyproj | 3.8.0 | MIT | Rejilla de 1 km EPSG:3035; rueda x86_64 disponible |
| rapidfuzz | 3.14.6 | MIT | Deduplicación; rueda x86_64 disponible |
| jsonschema | 4.26.0 | MIT | Validación del JSON del clasificador |
| stix2 | 3.0.2 | BSD | Dependencias: pytz, requests, simplejson (MIT/AFL-2.1), stix2-patterns (BSD) → antlr4-python3-runtime (BSD) |
| stix2-validator (validador oficial OASIS) | **3.3.1** (la 3.3.2 es del 2026-11-06) | BSD | **Solo en el grupo `dev`**: depende de `cpe` 1.3.1, que es **LGPLv3** |
| react / react-dom | 19.3.1 | MIT | |
| vite / @vitejs/plugin-react | 8.3.5 / 6.1.2 | MIT | Node ^20.19 o ≥ 22.12 (hay 24.9) |
| maplibre-gl | 6.15.0 (la 6.17.0 es del 2026-11-07) | BSD-3-Clause | |
| typescript | **6.0.3** | Apache-2.0 | La 7.0.2 no la admite typescript-eslint 8.72 (`<6.1.0`) |
| typescript-eslint / eslint / prettier | 8.72.0 / 10.13.0 / 3.9.10 | MIT | |
| vitest | 4.1.12 (la 5.1.0 es del 2026-11-02) | MIT | |
| @playwright/test | 1.64.1 (la 1.65.0 es del 2026-11-05) | Apache-2.0 | |
| pmtiles | 4.5.0 | BSD-3-Clause | Solo si se elige mapa base PMTiles (opcional) |

### 3.3 Stack del frontend del radar (propuesta para ADR)

| Opción | A favor | En contra |
|---|---|---|
| **A. React 19 + Vite 8 + TypeScript estricto + maplibre-gl directo (recomendada)** | El mismo stack servirá para el dashboard de la FASE 10 (deck.gl tiene integración oficial con React) → un solo stack de frontend en el producto; ecosistema y documentación más amplios (menos riesgo de que la IA invente APIs, R-17); SPA estática servida por la propia API en `127.0.0.1`; todo MIT/BSD/Apache | Paquete algo mayor que Svelte |
| B. SvelteKit 3 + Svelte 5 con `adapter-static` | Paquetes pequeños; buena ergonomía | Orientado a SSR; exige TypeScript ^6 y su propio plugin de Vite; segundo stack si el dashboard acaba en React |
| C. TypeScript sin framework + Vite | Mínimas dependencias | Filtros, cronología y accesibilidad a mano; no reutilizable en la FASE 10 |

Mapa base por defecto: **Natural Earth (dominio público) en GeoJSON local**, sin teselas externas; la CSP
impide cualquier petición fuera de `127.0.0.1`. PMTiles de OpenStreetMap queda como opción con ADR
(atribución ODbL y tamaño en disco).

## 4. Tareas

Orden estricto. TDD; verificación y prueba negativa registradas en `docs/evidence/FASE-2/registro-tareas.md`;
un commit por tarea con los IDs. **Un FALLO bloquea la tarea siguiente.** Rutas: backend en
`apps/incident-radar/backend/atalaya_radar/` (tests en `apps/incident-radar/backend/tests/`), web en
`apps/incident-radar/web/`. Ningún test unitario usa la red: las fuentes se simulan con un servidor HTTP local.

### T2.0 — Precondiciones
- **Qué:** comprobar que las FASES 0 y 1 están cerradas, que `make check` y `make regress` están en verde,
  que hay ≥ 10 GB libres y que Node cumple el rango de Vite. Volver a comprobar las versiones de §3.2.
- **Requisitos:** REQ-NFR-014, REQ-NFR-015
- **Verificación:** `git show-ref --tags --verify --quiet refs/tags/fase-0-cerrada && git show-ref --tags --verify --quiet refs/tags/fase-1-cerrada && grep -qx '0' docs/requirements/FASES-CERRADAS.txt && grep -qx '1' docs/requirements/FASES-CERRADAS.txt && python3 -c 'import pathlib,shutil,sys; sys.exit(0 if shutil.disk_usage(pathlib.Path.home()).free >= 10_000_000_000 else 1)' && node -e 'const [major, minor] = process.versions.node.split(".").map(Number); process.exit(major > 22 || (major === 22 && minor >= 12) ? 0 : 1)' && make check && make regress`
- **Resultado esperado:** ambas etiquetas y ambos registros de cierre presentes; `make check` y `make regress` con exit 0; al menos 10 GB (10.000.000.000 bytes) disponibles; Node ≥ 22.12. La cadena de comprobaciones termina con error ante cualquier incumplimiento.
- **Prueba negativa:** en un clon temporal sin cualquiera de las etiquetas o sin la fila correspondiente en `FASES-CERRADAS.txt`, la cadena falla antes de `make check`; con menos de 10 GB libres (10.000.000.000 bytes) o Node < 22.12, falla la comprobación correspondiente. No se empieza el código.

### T2.1 — ADR de la fase
- **Qué:** ADR (MADR; asignar el siguiente número libre después de resolver la propuesta 0014 de T1.8, con revisión técnica independiente, pendiente de revisión jurídica y decisión del usuario, y comprobar `docs/adr/` antes de crearla):
  - stack del frontend (§3.3) y mapa base local;
  - ubicación del código, almacenamiento (PostgreSQL del compose con asyncpg y migraciones SQL propias) y
    puertos/adaptadores (repositorio en memoria para tests unitarios);
  - política de fuentes: fallo cerrado, términos archivados, `robots.txt` y `Content-Signal`, sin descargar
    artículos, intervalo mínimo de sondeo, identificación del cliente;
  - umbrales: deduplicación (propuesta: precisión ≥ 0,95 y recall ≥ 0,85, REQ-FUN-008), solapamiento del
    resumen (propuesta: ninguna secuencia común de ≥ 8 palabras y contención de 4-gramas ≤ 0,20), precisión
    geográfica (celda de 1 km de la rejilla EPSG:3035; mínimo configurable 1 km), límite de peticiones
    (propuesta: 60 por minuto y cliente), retención del material de las fuentes (propuesta: 30 días);
  - LLM opcional desactivado por defecto; cualquier adaptador real (local o externo) exige ADR propio;
  - política de versiones (≥ 14 días) y añadir los módulos críticos del radar a `coverage_critical` y
    `mutation_critical` de `pyproject.toml` (cambiar esos umbrales exige ADR, ADR 0006).
- **Requisitos:** REQ-FUN-008, REQ-LEG-010, REQ-PRIV-004, REQ-NFR-016, REQ-LEG-016
- **Verificación:** `uv run pytest tests/test_documentos.py -v && python3 -I scripts/check_spec.py`
- **Resultado esperado:** los ADR nuevos con Estado, Contexto, Opciones, Decisión y Consecuencias; check_spec OK.
- **Prueba negativa:** en una copia, un ADR sin «Consecuencias» → el test falla.

### T2.2 — Dependencias y comprobación de licencias npm
- **Qué:** añadir las dependencias de §3.2 (ejecución en `dependencies`; stix2-validator en `dev`);
  `apps/incident-radar/web/package.json` con `package-lock.json` y versiones exactas; ampliar
  `scripts/license_check.py` con `--npm <dir>` que lee `package-lock.json` y el `package.json` de cada paquete
  instalado (sin herramientas de terceros) y bloquea GPL/AGPL o licencia desconocida en dependencias de
  producción; añadirlo a `security.yml`.
- **Requisitos:** REQ-LEG-016, REQ-NFR-015
- **Verificación:** `uv sync --frozen && uv run python -m scripts.license_check && npm ci --prefix apps/incident-radar/web && uv run python -m scripts.license_check --npm apps/incident-radar/web && uv run pytest tests/test_license_check.py -v`
- **Resultado esperado:** exit 0; informe con las licencias de producción (MIT, BSD, Apache, ISC); `cpe` (LGPLv3) aparece solo como dependencia de desarrollo.
- **Prueba negativa:** fixture de `package-lock.json` con un paquete GPL-3.0 o sin licencia en producción → exit 1 nombrándolo; mover stix2-validator a ejecución → el informe lo marca (LGPL en ejecución exige ADR).

### T2.3 — Registro de fuentes y archivo de términos
- **Qué:** `apps/incident-radar/backend/fuentes.yaml` validado con un esquema estricto. Por fuente: id, tipo
  (`rss`, `atom`, `api`, `manual`), URL, URL de términos, ruta del archivo de términos, SHA-256, fecha de
  consulta, resumen de la licencia, atribución obligatoria (texto literal), usos permitidos
  (`hechos_y_enlace`, `enlace_profundo`, `entrada_llm`), intervalo mínimo de sondeo, fiabilidad Admiralty por
  defecto (A-F) y estado (`activa`, `pendiente`, `manual`, `desactivada`), más quién la aprobó y cuándo.
  Comando `python -m atalaya_radar.fuentes archivar <id>` que guarda la página de términos en
  `docs/legal/fuentes/<id>/<fecha>.html` con su hash. Se rellenan las fuentes de §3.1 y se verifican las
  candidatas marcadas NO VERIFICADO (Policía Nacional, Defensa, Instituciones Penitenciarias, Comisión
  Europea, EASA y los medios que el usuario indique).
- **Requisitos:** REQ-FUN-007, REQ-LEG-011
- **Verificación:** `uv run pytest apps/incident-radar/backend/tests/test_fuentes.py -v && uv run python -m atalaya_radar.fuentes verificar`
- **Resultado esperado:** ≥ 10 tests en verde; `verificar` lista cada fuente con estado, fecha y hash coincidente; solo las aprobadas quedan `activa`.
- **Prueba negativa:** fuente sin archivo de términos, con hash alterado o sin aprobación → rechazada al cargar (exit 1); una fuente con `enlace_profundo: false` no puede generar un enlace que no sea su portada.

### T2.4 — Cliente de ingesta respetuoso
- **Qué:** cliente `httpx` que solo pide las URL registradas: `User-Agent` identificable, `robots.txt`
  (`urllib.robotparser`) y lectura de `Content-Signal`, `ETag`/`If-Modified-Since`, intervalo mínimo por
  fuente, tiempo de espera, tamaño máximo, redirecciones solo dentro del mismo dominio, XML analizado sin
  entidades externas (se comprueba cómo lo hace feedparser y, si hace falta, se analiza antes con
  `defusedxml`). Nunca sigue los enlaces de los artículos. El estado de cada fuente (`ok`, `degradada`,
  `caida`) se guarda y se muestra (fallo visible).
- **Requisitos:** REQ-FUN-007, REQ-LEG-011
- **Verificación:** `uv run pytest apps/incident-radar/backend/tests/test_cliente.py -v`
- **Resultado esperado:** ≥ 12 tests en verde contra un servidor HTTP local.
- **Prueba negativa:** `Disallow` en `robots.txt` → no se pide nada; `Content-Signal` con `ai-input=no` → la fuente queda marcada sin entrada a LLM; respuesta mayor que el máximo → abortada; redirección a otro dominio → rechazada; sondeo antes del intervalo → omitido; XML con entidades externas → rechazado; tres fallos seguidos → estado `caida`.

### T2.5 — Adaptadores de fuente y modelo normalizado
- **Qué:** adaptadores RSS/Atom (AESA y medios aprobados), ATOM de la Plataforma de Contratación (campos
  CODICE: título, órgano, CPV, enlace, fechas), API del BOE (sumario JSON), GDELT DOC 2.0 (JSON `artlist`),
  NOTAM (solo fixtures sintéticos en formato OACI, desactivado) y entrada manual del analista. Todos producen
  un `ItemFuente` (fuente, URL canónica, fecha, titular y extracto **internos**, hash). Las licitaciones se
  filtran con términos neutros (dron, UAS, RPAS, detección) y van a la capa de contratación, no a incidentes.
- **Requisitos:** REQ-FUN-007
- **Verificación:** `uv run pytest apps/incident-radar/backend/tests/test_adaptadores.py -v`
- **Resultado esperado:** ≥ 1 test positivo y ≥ 1 negativo por adaptador (≥ 14 en total) sobre fixtures sintéticos versionados.
- **Prueba negativa:** fuente mal formada → elemento rechazado con error registrado y la ingesta sigue; elemento sin fecha o sin enlace → rechazado; la fuente NOTAM con estado `pendiente` no se consulta aunque se configure su URL.

### T2.6 — Deduplicación
- **Qué:** URL canónica (sin parámetros de seguimiento ni versiones AMP), hash exacto y agrupación aproximada
  (rapidfuzz sobre el titular normalizado + misma instalación o municipio + ventana de ±72 h). Un incidente
  agrupa varios informes de fuente. Conjunto etiquetado sintético de pares duplicados y no duplicados en
  `apps/incident-radar/backend/tests/fixtures/dedup/`; métricas con un script y recalculadas por un segundo
  script independiente.
- **Requisitos:** REQ-FUN-008
- **Verificación:** `uv run pytest apps/incident-radar/backend/tests/test_dedup.py -v && uv run python -m atalaya_radar.eval.dedup --out docs/evidence/FASE-2/dedup.json && uv run python -m atalaya_radar.eval.dedup_check docs/evidence/FASE-2/dedup.json`
- **Resultado esperado:** precisión y recall ≥ los umbrales del ADR de T2.1, con intervalo de confianza al 95 %; los dos scripts coinciden.
- **Prueba negativa:** dos incidentes del mismo municipio y día en instalaciones distintas → no se fusionan; propiedad (hypothesis): ingerir el mismo lote dos veces o en otro orden da los mismos grupos.

### T2.7 — Nomenclátor y geocodificación a municipio o instalación
- **Qué:** nomenclátor local construido por script desde el IGN (municipios) y Wikidata (instalaciones), con
  data card en `docs/data-cards/`, procedencia, licencia y hash. Geocodificador por reglas sobre el texto
  (sin servicios externos ni Nominatim): devuelve un municipio o una instalación, nunca una calle. La
  coordenada pública es el centro de la celda de 1 km de la rejilla EPSG:3035 que contiene el centroide o
  la instalación; la precisión es configurable solo hacia arriba (≥ 1 km). Las etiquetas públicas de
  instalación se curan para no contener nombres de persona (p. ej., «Aeropuerto de Madrid-Barajas»).
- **Requisitos:** REQ-FUN-009, REQ-PRIV-004
- **Verificación:** `uv run pytest apps/incident-radar/backend/tests/test_geo.py -v && uv run python -m atalaya_radar.geo.nomenclator --verificar`
- **Resultado esperado:** ≥ 15 tests en verde; nomenclátor con hash coincidente y data card.
- **Prueba negativa:** precisión configurada en 0,5 km → error al arrancar; texto con una dirección postal → solo municipio; nombre de municipio ambiguo → sin resolver y a la cola del analista; propiedad: cualquier punto de entrada produce un centro de celda, y dos puntos de la misma celda dan la misma salida.

### T2.8 — Clasificador por reglas con JSON estricto
- **Qué:** reglas explicables (identificadores de regla en la salida) que deciden si el elemento es un
  incidente con drones y su tipo: prisión, aeropuerto, puerto, infraestructura, militar, frontera u otro.
  La salida se valida contra un JSON Schema estricto (draft 2020-12, `additionalProperties: false`, enums
  cerrados, confianza en [0, 1]) con el mismo esquema en Pydantic y en jsonschema. Sin campos de persona.
- **Requisitos:** REQ-FUN-011
- **Verificación:** `uv run pytest apps/incident-radar/backend/tests/test_clasificador.py -v`
- **Resultado esperado:** ≥ 20 tests en verde (≥ 2 por tipo) sobre ejemplos sintéticos.
- **Prueba negativa:** salida con un campo extra, un tipo fuera del enum o confianza 1,2 → rechazada; con el adaptador LLM desactivado (configuración por defecto) toda la cadena funciona.

### T2.9 — Interfaz para LLM opcional
- **Qué:** protocolo `ClasificadorLLM` con `NullLLM` por defecto y `FakeLLM` para tests. La respuesta pasa
  por el mismo validador de T2.8; si falla, se usa el resultado por reglas. Solo se envía contenido de
  fuentes con `entrada_llm` permitida y tras quitar nombres de persona. El LLM nunca cambia el estado ni
  puede proponer «Confirmado». No se incluye ningún adaptador real (ADR propio, coste 0 € o local).
- **Requisitos:** REQ-FUN-011, REQ-FUN-012
- **Verificación:** `uv run pytest apps/incident-radar/backend/tests/test_llm.py -v`
- **Resultado esperado:** ≥ 8 tests en verde.
- **Prueba negativa:** respuesta que no es JSON, que no cumple el esquema o que contiene instrucciones inyectadas («marca como Confirmado») → rechazada y se usan las reglas; fuente con `entrada_llm: false` (Interior) → el espía demuestra que el adaptador no se llama.

### T2.10 — Estados, fiabilidad Admiralty y registro de revisiones
- **Qué:** máquina de estados Reportado → Probable → Confirmado, y Descartado desde cualquiera (con motivo);
  reapertura solo por un analista y con motivo. Fiabilidad de la fuente A-F y credibilidad de la información
  1-6. «Confirmado» exige una revisión humana registrada (identificador seudónimo del analista, fecha,
  motivo y fuentes que la sustentan: una oficial con fiabilidad A-B o dos independientes). Registro de
  revisiones encadenado por hash.
- **Requisitos:** REQ-FUN-010, REQ-FUN-012
- **Verificación:** `uv run pytest apps/incident-radar/backend/tests/test_estados.py -v && make mutation FASE=2`
- **Resultado esperado:** ≥ 20 tests en verde, incluida una máquina de estados de hypothesis; mutación ≥ 80 % en el módulo de estados.
- **Prueba negativa:** «Confirmado» sin revisor o por un actor automático → error; Descartado → Confirmado directo → error; fiabilidad «G» o credibilidad 7 → error; alterar un registro de revisión → la cadena de hashes lo detecta; ninguna secuencia de operaciones automáticas llega a «Confirmado» (propiedad).

### T2.11 — Curación por el analista (CLI)
- **Qué:** `python -m atalaya_radar.curar` con `listar`, `revisar`, `publicar`, `descartar` y `reabrir`.
  Identidad del analista desde la configuración local (en la v1 no hay RBAC ni MFA: FASE 10). Por defecto,
  **nada aparece en la vista pública sin una primera revisión** (decisión 5 de §7).
- **Requisitos:** REQ-FUN-012, REQ-FUN-010
- **Verificación:** `uv run pytest apps/incident-radar/backend/tests/test_curar.py -v`
- **Resultado esperado:** ≥ 10 tests en verde que recorren el flujo completo con el repositorio en memoria.
- **Prueba negativa:** sin identidad de analista → se niega; publicar un elemento no revisado → se niega; un resumen editado que copia texto de la fuente → se niega (T2.12).

### T2.12 — Resumen propio y prueba de solapamiento
- **Qué:** resumen generado desde los campos estructurados (fecha, tipo, instalación o municipio, estado,
  número de fuentes) con plantillas propias; el analista puede editarlo. Comprobación de solapamiento contra
  el titular y el extracto de cada fuente con los umbrales del ADR. Nunca se guarda ni se publica el texto
  completo de un artículo; el extracto sindicado es interno y se borra a los 30 días.
- **Requisitos:** REQ-LEG-010
- **Verificación:** `uv run pytest apps/incident-radar/backend/tests/test_resumen.py -v`
- **Resultado esperado:** ≥ 10 tests en verde, con una propiedad sobre resúmenes generados.
- **Prueba negativa:** un resumen que copia 10 palabras seguidas de la fuente → rechazado; el titular de la fuente nunca aparece en la vista pública; un extracto con más de 30 días se purga.

### T2.13 — Vista pública y filtro de privacidad (G-15)
- **Qué:** un único modelo `IncidentePublico` con lista blanca de campos, cada uno con sensibilidad `PUBLIC`
  según la convención de la FASE 1, y su JSON Schema versionado (que el guardarraíl ya analiza). Detector de
  nombres de persona con la lista del INE (nombres y apellidos frecuentes) y patrones de nombre propio, con
  excepciones curadas para instituciones. El filtro rechaza además coordenadas que no sean centros de celda,
  direcciones, correos, teléfonos y documentos de identidad (reutiliza `scripts/pii_scan.py`).
- **Requisitos:** REQ-PRIV-004, REQ-FUN-009, REQ-LEG-007
- **Verificación:** `uv run pytest apps/incident-radar/backend/tests/test_publico.py -v && make mutation FASE=2`
- **Resultado esperado:** ≥ 20 tests en verde; propiedad de hypothesis con ≥ 500 incidentes generados y cero fugas; mutación ≥ 80 % en el filtro.
- **Prueba negativa (G-15):** un nombre de persona en el resumen → rechazado; una coordenada que no es centro de celda → rechazada; un campo fuera de la lista blanca (revisor, titular, extracto) → ausente de la salida; un campo `pilot_*` en el esquema público → el guardarraíl bloquea el commit.

### T2.14 — Exportación STIX 2.1
- **Qué:** bundle con `identity` (Atalaya), `incident`, `location` (municipio o instalación, con
  `precision` ≥ 1000 m), relaciones, `external_references` a la fuente con su atribución y marcado TLP:CLEAR.
  Estado y Admiralty en una extensión propia (`extension-definition`). Solo sale lo que pasa por
  `IncidentePublico`. Antes de escribirlo se comprueban en la especificación de OASIS las propiedades de
  `incident` y las relaciones admitidas.
- **Requisitos:** REQ-FUN-013, REQ-PRIV-004
- **Verificación:** `uv run pytest apps/incident-radar/backend/tests/test_stix.py -v && uv run python -m atalaya_radar.stix --out reports/radar.stix.json && uv run stix2_validator --strict reports/radar.stix.json`
- **Resultado esperado:** el validador oficial 3.3.1 sin errores ni avisos en modo estricto.
- **Prueba negativa:** un bundle con una propiedad no válida → el validador falla (el test comprueba que el fallo se detecta); un incidente no publicado o descartado no aparece en el bundle.

### T2.15 — API de solo lectura con límite de peticiones
- **Qué:** FastAPI con `GET /api/v1/incidentes` (filtros: tipo, estado, fechas, caja), `/incidentes/{id}`,
  `/stix`, `/fuentes` (atribuciones), `/estado` (salud de las fuentes) y `/metodologia`. Límite por cliente
  con cubo de fichas propio (429 y `Retry-After`). Escucha solo en `127.0.0.1`; cabeceras de seguridad y CSP.
  Logs JSON sin datos personales (sin IP en claro).
- **Requisitos:** REQ-FUN-014, REQ-PRIV-003, REQ-PRIV-004
- **Verificación:** `uv run pytest apps/incident-radar/backend/tests/test_api.py -v`
- **Resultado esperado:** ≥ 15 tests en verde; la lista de rutas registradas contiene solo GET/HEAD.
- **Prueba negativa:** POST, PUT, PATCH o DELETE → 405; la petición 61 en un minuto → 429; un parámetro inválido → 422; `pii_scan` sobre los logs de los tests → cero hallazgos.

### T2.16 — Web del radar
- **Qué:** React + Vite + TypeScript estricto con mapa MapLibre sobre GeoJSON local, cronología con filtros
  (tipo, estado, fechas), página de metodología (estados, Admiralty, precisión de 1 km, fuentes con su
  atribución literal, licencias de IGN, INE, Natural Earth, Wikidata y GDELT) y página de estado de las
  fuentes. Modo oscuro y contraste alto. La compila Vite y la sirve la API.
- **Requisitos:** REQ-FUN-015
- **Verificación:** `make radar-web` (eslint sin avisos, prettier, `tsc --noEmit` y vitest)
- **Resultado esperado:** exit 0; ≥ 15 tests de vitest en verde.
- **Prueba negativa:** un componente que pide un recurso externo → la CSP lo bloquea y un test lo detecta; un incidente «Reportado» se muestra con la etiqueta «sin verificar», nunca como confirmado.

### T2.17 — e2e con Playwright en local
- **Qué:** `make radar-e2e` levanta PostgreSQL del compose, sirve fuentes sintéticas desde un servidor local,
  ejecuta la cadena (ingesta → deduplicación → clasificación → curación por CLI → API → web) y lanza
  Playwright con Chromium.
- **Requisitos:** REQ-FUN-015, REQ-PRIV-004, REQ-PRIV-003, REQ-FUN-012
- **Verificación:** `make radar-e2e`
- **Resultado esperado:** el mapa carga con N marcadores; los filtros cambian el número; la metodología existe; todas las peticiones van a `127.0.0.1`; el texto del DOM y las respuestas pasan el detector de nombres y la comprobación de celdas; `pii_scan` sobre los logs → cero; capturas fechadas con el commit.
- **Prueba negativa:** un incidente sin revisión no aparece; uno descartado no aparece; una fuente caída se ve como «degradada» en la página de estado.

### T2.18 — Latencia fuente → publicación
- **Qué:** script que calcula, desde las marcas de tiempo de la base de datos, la latencia de la parte
  automática (fecha de la fuente → cola del analista) y la total (→ visible en la API), con p50 y p95;
  un segundo script independiente la recalcula. Objetivo propuesto para la parte automática: p95 ≤ intervalo
  de sondeo + 120 s. Se mide sobre la ingesta real de las fuentes activas durante ≥ 7 días.
- **Requisitos:** REQ-FUN-007, REQ-FUN-015
- **Verificación:** `uv run python -m atalaya_radar.eval.latencia --out docs/evidence/FASE-2/latencia.json && uv run python -m atalaya_radar.eval.latencia_check docs/evidence/FASE-2/latencia.json`
- **Resultado esperado:** los dos scripts coinciden; p95 automático dentro del objetivo o FALLO registrado.
- **Prueba negativa:** un elemento sin marca de tiempo → error explícito, nunca se excluye en silencio.

### T2.19 — Precisión del clasificador auditada en una muestra
- **Qué:** tras ≥ 2 semanas de ingesta real, muestra aleatoria con semilla documentada (n ≥ 150) que el
  usuario etiqueta a ciegas (incidente sí/no y tipo). Precisión, recall y F1 por tipo con intervalo de
  Wilson al 95 %, calculados por dos scripts. Conjunto congelado en `evals/frozen/radar-v1/` con hash (solo
  URL, hash del elemento y etiquetas; el texto queda fuera de git, decisión 6).
- **Requisitos:** REQ-FUN-011
- **Verificación:** `uv run python -m atalaya_radar.eval.clasificador --frozen evals/frozen/radar-v1 --out docs/evidence/FASE-2/clasificador.json && uv run python -m atalaya_radar.eval.clasificador_check docs/evidence/FASE-2/clasificador.json`
- **Resultado esperado:** métricas con intervalos y casos de fallo documentados; sin umbral MUST (la primera medida es la línea base).
- **Prueba negativa:** hash del conjunto alterado → la evaluación se niega a ejecutarse.

### T2.20 — Inspección de no publicación
- **Qué:** test que comprueba que no hay mecanismo de despliegue público: el servidor se niega a escuchar
  en una dirección que no sea de loopback, el compose no expone el radar fuera de `127.0.0.1` y ningún
  workflow publica nada (Pages, despliegues, subidas a registros).
- **Requisitos:** REQ-LEG-013
- **Verificación:** `uv run pytest apps/incident-radar/backend/tests/test_no_publicacion.py -v`
- **Resultado esperado:** ≥ 4 tests en verde.
- **Prueba negativa:** configurar `host: 0.0.0.0` → el servidor no arranca; un workflow de prueba con un paso de despliegue a Pages → el test falla.

### T2.21 — Documentos de la fase
- **Qué:** DPIA v2 (tratamiento de noticias que pueden contener datos personales: minimización, retención de
  30 días, base jurídica propuesta pendiente de asesoría, B-01), STRIDE del radar (fuentes envenenadas,
  inyección en el LLM, SSRF por redirecciones, XML malicioso, abuso de la API), medidas ENS, data cards del
  nomenclátor y de la lista de nombres, `docs/radar/metodologia.md` (la que muestra la web), riesgos nuevos
  en RIESGOS, deuda técnica y la lista de comprobación de la revisión legal y editorial previa a cualquier
  publicación futura.
- **Requisitos:** REQ-PRIV-006, REQ-SEC-015, REQ-SEC-016, REQ-LEG-013
- **Verificación:** `uv run pytest tests/test_documentos.py -v && python3 -I scripts/check_spec.py`
- **Resultado esperado:** todo en verde; las líneas sensibles nuevas revisadas por una persona antes de entrar en la lista blanca.
- **Prueba negativa:** en una copia, la DPIA sin base jurídica del tratamiento del radar → el test falla.

### T2.22 — Cierre de fase
- **Qué:** `scripts/regress.d/2.sh`; puertas P2 a P5 (`make check`, `make radar-web`, `make radar-e2e`,
  `make regress`, `scripts/verify_clean_clone.sh`); subagentes sin contexto `independent-reviewer`,
  `test-auditor`, `security-reviewer`, `legal-guardrail-reviewer` y `privacy-reviewer`; `make evidence FASE=2`
  y `CIERRE.md`.
- **Requisitos:** todos los de §2
- **Verificación:** los comandos de P2-P4, con su salida en el paquete.
- **Resultado esperado:** todo en verde y `TRAZABILIDAD.md` sin huecos MUST de las fases -1, 0, 1 y 2.
- **Prueba negativa:** la de cada puerta. **STOP:** revisión legal y editorial; la publicación sigue fuera
  de la v1 (B-01).

## 5. Riesgos de la fase

| ID | Riesgo | Mitigación |
|---|---|---|
| R-40 (nuevo, ID de trabajo del borrador) | Los términos de una fuente cambian o una fuente oficial bloquea el acceso automatizado (Interior ya lo hace) | Hash de los términos y revisión en cada cierre; fallo cerrado; entrada manual; estado de fuente visible |
| R-41 (nuevo, ID de trabajo del borrador) | Fuentes envenenadas o inyección de instrucciones en el LLM | LLM desactivado por defecto; salida validada; nunca decide el estado; revisión humana para publicar |
| R-42 (nuevo, ID de trabajo del borrador) | Datos personales en noticias (nombres de detenidos o de quien pilota) | Sin campos de persona en el modelo; detector de nombres; extractos internos borrados a los 30 días; nada al LLM sin filtrar |
| R-43 (nuevo, ID de trabajo del borrador) | Nombres de persona dentro de nombres de instalaciones | Etiquetas públicas curadas; el detector se aplica también a esas etiquetas |
| R-44 (nuevo, ID de trabajo del borrador) | Pocos incidentes reales: muestra de evaluación pequeña e intervalos anchos | Muestra ≥ 150 elementos (incluidos negativos); métricas con intervalo; se reevalúa en cada cierre |
| R-45 (nuevo, ID de trabajo del borrador) | Fixtures con vocabulario que bloquea el guardarraíl | Fixtures sintéticos y neutros; datos reales solo en la base de datos local |
| R-46 (nuevo, ID de trabajo del borrador) | Cadena de suministro npm | Versiones exactas ≥ 14 días, `npm ci`, licencias comprobadas, SBOM y grype en CI |
| R-12 | Sin asesoría jurídica | Nada se publica; DPIA y lista de comprobación legal como borradores |
| R-17 | La IA inventa APIs (STIX, MapLibre) | Verificar en la documentación oficial antes de escribir; validador oficial de STIX |

Los IDs R-40–R-46 son identificadores de trabajo reservados en este borrador; su unicidad y su incorporación
al registro global se comprueban en T2.21.

## 6. Estimación
**3-4 semanas de trabajo efectivo** (23 tareas), por encima de las 2-3 de la SPEC: la política de fuentes,
el filtro de privacidad y el frontend son más grandes de lo previsto. Además hacen falta **≥ 2 semanas de
calendario** de ingesta real en paralelo para T2.18 y T2.19, y unas 3-4 h del usuario para etiquetar la
muestra. Coste: 0 €. Descargas: dependencias npm (~300-400 MB) y Chromium de Playwright (NO VERIFICADO el
tamaño exacto).

## 7. Decisiones que necesita el usuario
1. Aprobar este plan (P0). La fase no empieza hasta cerrar las FASES 0 y 1 (T2.0).
2. Stack del frontend: **A (React + Vite, recomendada)**, B (SvelteKit) o C (sin framework).
3. Fuentes: decidir en P0 cuáles de las candidatas de §3.1 (Plataforma de Contratación, BOE, AESA y GDELT)
   se autorizan a incluir en T2.3. La decisión P0 no las activa: cada una solo se activa cuando sus términos
   y hash estén archivados y exista aprobación explícita. Si quiere,
   pedir por correo la autorización del servicio NOTAM de ENAIRE y la de la Guardia Civil (gratis; sin
   ellas quedan desactivadas o como entrada manual).
4. Medios: mantenerlos desactivados y cubrirlos con GDELT (recomendado) o darme una lista de medios para
   verificar sus términos uno a uno.
5. ¿Pueden aparecer en la vista local incidentes «Reportado» sin una primera revisión? Recomiendo **no**.
6. Muestra de evaluación: el texto de los elementos queda fuera de git (recomendado) o en el repositorio
   privado; y quién etiqueta (el usuario, ~150 elementos).
7. Umbrales propuestos para el ADR de T2.1: deduplicación P ≥ 0,95 y R ≥ 0,85; solapamiento < 8 palabras
   seguidas y ≤ 0,20 de 4-gramas; celda de 1 km; 60 peticiones por minuto; retención de extractos 30 días.
8. LLM: desactivado (recomendado). Un adaptador local o externo, más adelante y con ADR.
9. Curación por CLI en la v1 (recomendado) o una pequeña página interna (añade alcance).

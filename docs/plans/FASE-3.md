# Plan FASE 3 — Capa 2: app de avistamientos (sensor humano)

Versión 1.1 · 2026-11-10 · Estado: **PENDIENTE DE APROBACIÓN (P0)**

## 1. Objetivo
Una app Android (Kotlin + Jetpack Compose) con la que un vigilante registra un avistamiento de dron en **3 toques como máximo**, con rumbo de brújula, altura y distancia asistidas y foto o vídeo con SHA-256 calculado en la captura. Funciona sin conexión gracias a una cola cifrada y se autentica ante el backend con **mTLS por dispositivo** (versión básica). El backend convierte cada avistamiento en `Detection(sensor_type=HUMAN)` con su incertidumbre, de modo que la fusión lo trata como un sensor más. Además añade contexto (zonas y NOTAM, aeronaves tripuladas, incidentes previos) y genera un **informe PDF para las FCSE** con evidencias, cadena de custodia, firma del supervisor y sello RFC 3161 de una **TSA local de prueba, sin valor probatorio y marcada así**.

Todo a 0 €, solo en local (Mac Intel con 8 GB de RAM más el Android del usuario por USB) y sin Android Studio.

## 2. Requisitos que cubre

| Tipo | Requisitos |
|---|---|
| MUST de la FASE 3 | REQ-FUN-016, REQ-FUN-017, REQ-FUN-018, REQ-FUN-019, REQ-FUN-020, REQ-FUN-022, REQ-FUN-059, REQ-NFR-010 (parte de la app), REQ-PRIV-008, REQ-SEC-018 |
| SHOULD de la FASE 3 | REQ-FUN-021, REQ-PRIV-011, REQ-SEC-017 (MASVS en la app y ASVS en la API de avistamientos) |
| Transversales que se mantienen | REQ-NFR-014, REQ-NFR-015, REQ-NFR-016, REQ-LEG-001, REQ-LEG-007, REQ-LEG-016, REQ-SEC-005, REQ-SEC-015, REQ-SEC-016, REQ-PRIV-003, REQ-PRIV-006 |
| Se adelantan en parte (no se cierran aquí) | REQ-SEC-004 (mTLS básico por dispositivo; su fase es la 5), REQ-SEC-010 (solo dispositivos registrados), REQ-SEC-006 (solo los roles vigilante y supervisor; el RBAC completo y el MFA, REQ-SEC-007, son de la FASE 10) |
| Bloqueado | Validación del formato del informe con la Guardia Civil (REQ-FUN-022, bloqueo **B-02**: sin contacto con FCSE). Se cierra con el bloqueo documentado, no como cumplido |

Pruebas de guardarraíl del plan maestro que se activan: **G-14** (la app declara el permiso de micrófono → el test falla) y **G-12** ampliada a las dependencias de Gradle.

## 3. Hallazgos de la exploración (2026-11-08)

| Hallazgo | Fuente | Efecto |
|---|---|---|
| **Disco: 23 GB libres** de 195 GB (`df -h ~`), no ~30 GB | Medido | Suficiente para la FASE 3 sin emulador (§6). Con emulador y Android Studio, justo |
| RAM 8 GB; Docker Desktop limitado a ~3 GB (FASE 0) | Medido / FASE-0 | Gradle con límites de memoria; Docker parado mientras se compila Android; **sin emulador**: las pruebas instrumentadas van al móvil real |
| JDK instalados: Oracle 21.0.8 (por defecto), Temurin 11 y 8 | `/usr/libexec/java_home -V` | AGP 9.5 exige **JDK 17** como mínimo. Se usa el 21 instalado, o Temurin 17/21 si el usuario prefiere un JDK libre (decisión 3, §8) |
| `adb` 1.0.41 (platform-tools 37.0.1) ya está en `/usr/local/bin` | Medido | Sirve para el móvil; el SDK instalará otra copia, así que hay que fijar cuál va primero en el `PATH` |
| Sin Android SDK, Gradle, ktlint ni detekt | `which` | Se instalan en T3.1-T3.2 |
| Diagnóstico histórico (2026-11-08): `proto/atalaya/v1/` solo tenía un README; FASE 1 no había empezado y FASE 0 seguía abierta | Repo | Ya no describe el estado actual. Al 2026-11-10, FASE 0 está cerrada (`fase-0-cerrada`); FASE 1 mantiene el P0 aprobado para la versión 3, tiene T1.3 con STOP aprobado y T1.0–T1.6 constan como OK en el registro de tareas. FASE 1 aún no está cerrada ni tiene P6. El contrato actual contiene `Sighting`, `Detection` y `Evidence`; su compatibilidad con las necesidades de FASE 3 queda abierta en §4.1. FASE 2 sigue como plan pendiente de P0 y no puede empezar hasta cerrar FASE 1. |
| `check_spec.py` no analiza `docs/plans/`, pero este plan se ha escrito sin menciones sensibles y se comprobó con su misma expresión regular | Código | — |
| `sdkmanager` figura como **deprecado** en la documentación oficial, que remite a la nueva «Android CLI» (`android sdk install`) | developer.android.com/tools/sdkmanager | El paquete oficial de command-line tools sigue publicado y es lo que se usa. Android CLI: no está documentado que funcione en Mac Intel → **NO VERIFICADO**, no se usa |
| `androidx.security:security-crypto` 1.1.0: «Deprecated all APIs in favour of existing platform APIs and direct use of Android Keystore» | developer.android.com/jetpack/androidx/releases/security | No se usa. Cifrado con Android Keystore más Tink |

### 3.1 Versiones y licencias comprobadas (2026-11-08)

Las versiones se fijan en `gradle/libs.versions.toml` con *dependency locking*. Antes de fijarlas, T3.2 las vuelve a comprobar, porque pueden salir versiones nuevas.

| Componente | Versión estable | Fuente | Licencia | ¿Se distribuye? |
|---|---|---|---|---|
| Android Gradle Plugin | **9.5.1** (9.6.0 solo en alpha) | Notas de AGP + `maven-metadata.xml` de Google Maven | Apache-2.0 (NO VERIFICADO en esta sesión; es la del AOSP) | No (compilación) |
| Requisitos de AGP 9.5 | Gradle ≥ 9.6.0, Build Tools 36.0.0, JDK 17, API máxima 37 | Notas de AGP 9.5 | — | — |
| Gradle | 9.6.0 (exigida por AGP 9.5). La última es la 9.8.2; usar otra que no sea la 9.6.0 se decide en T3.2 | gradle.org/releases; `gradle-9.6.0-bin.zip` = 140.681.093 bytes | Apache-2.0 (NO VERIFICADO en esta sesión) | No |
| Kotlin (plugin) | **2.4.21** (8-10-2026) | kotlinlang.org/docs/releases + Maven Central | Apache-2.0 (NO VERIFICADO en esta sesión) | Runtime: sí |
| Compose BOM | **2026.09.00** (Material3 1.4.0, según la tabla de correspondencias; correspondencia exacta **NO VERIFICADA**) | Google Maven + tabla del BOM | Apache-2.0 (AndroidX) | Sí |
| CameraX | 1.6.2 (1.7.0 en rc) | Google Maven | Apache-2.0 | Sí |
| Room / WorkManager / activity-compose | 2.8.5 / 2.12.0 / 1.13.0 | Google Maven | Apache-2.0 | Sí |
| Tink (`tink-android`) | 1.24.0 | Maven Central; licencia en el repo de GitHub | **Apache-2.0** (comprobada) | Sí |
| SQLCipher (`net.zetetic:sqlcipher-android`), alternativa | 4.20.0; API ≥ 23 | Maven Central + README del repo | **BSD de 3 cláusulas** (fichero LICENSE leído) | Sí, si se elige |
| OkHttp | 5.5.1 | Maven Central | **Apache-2.0** (comprobada) | Sí |
| protobuf-javalite | 4.36.2 (4.37 en RC) | Maven Central | BSD-3-Clause (NO VERIFICADO en esta sesión) | Sí |
| Robolectric (solo tests) | 4.17 | Maven Central | **MIT** (comprobada) | No |
| ktlint (solo desarrollo) | 1.8.0 | Maven Central | MIT (NO VERIFICADO; el LICENSE leído solo muestra el copyright) | No |
| detekt (solo desarrollo) | 1.23.8 estable; 2.0.0 en alpha | Maven Central | Apache-2.0 (NO VERIFICADO en esta sesión) | No. **Riesgo:** que detekt 1.23.8 analice bien código de Kotlin 2.4 está **NO VERIFICADO** (T3.2) |
| reportlab (PDF, backend) | 5.1.0 | PyPI | **BSD** | Sí (backend) |
| pyHanko + pyhanko-certvalidator (firma PAdES y cliente RFC 3161, `HTTPTimeStamper`) | 0.38.1 / 0.33.0 | PyPI + docs.pyhanko.eu | **MIT** | Sí (backend) |
| cryptography / asn1crypto | 50.0.2 / 1.5.1 | PyPI | Apache-2.0 o BSD-3 / MIT | Sí |
| pypdf (lectura del PDF en tests) | 7.0.0 (publicada el 6-11-2026: se fija una versión con ≥ 2 semanas) | PyPI | BSD-3-Clause | No |
| OpenSSL `ts` (TSA local) | 3.6.2 (Homebrew, instalado) | `openssl version` | Apache-2.0 (NO VERIFICADO en esta sesión) | No en la v1 (herramienta local) |
| **Descartada** fpdf2 | 2.9.0 | PyPI | **LGPL-3.0** | Descartada por copyleft (REQ-LEG-016) |

## 4. Precondiciones y dependencias

**FASE 0:** cerrada el 2026-11-10 (etiqueta `fase-0-cerrada`). Esta precondición está satisfecha.

**Puertas de esta fase:** el P0 de FASE 3 sigue pendiente. No se inicia ninguna tarea hasta que el propietario apruebe explícitamente este plan. Además, la secuencia del proyecto exige el P6 de cada fase anterior antes de iniciar la implementación: FASE 1 y FASE 2 deben estar cerradas, con sus etiquetas y registros de cierre, aunque una tarea sea técnicamente independiente. La aprobación P0 de FASE 1 no aprueba este plan ni sustituye su P6.

**Preparación paralela permitida:** mientras terminan las fases anteriores solo se puede revisar o preparar documentación de planificación, como esta matriz de dependencias y las preguntas abiertas de §4.1. No se instalan herramientas, se consulta el móvil, se ejecutan pruebas o se implementa código de FASE 3 antes del P0 propio y de los P6 de FASE 1 y 2.

**FASE 1** (contratos Protobuf, bus e ingesta, simulador):

| Tarea | Qué necesita de la FASE 1 | Estado y puerta |
|---|---|---|
| T3.4 Bindings del contrato | Contratos F1 estables y aprobados, bindings Kotlin/Python generados, y sensibilidad por campo | Los tipos base ya existen, pero FASE 1 sigue abierta y hay diferencias por resolver en §4.1. **Bloqueada hasta P6 y cierre de FASE 1.** |
| T3.11 Backend de avistamientos | Contrato estable, publicación de `Detection` en el bus e ingesta de REQ-FUN-001; `buf lint` y `buf breaking` | FASE 1 sigue en curso; el backend y la integración del bus aún no están disponibles. **Bloqueada hasta P6 y cierre de FASE 1.** |
| T3.12 Adaptador ADS-B | ADS-B simulado o en replay (`.pb.zst`) de FASE 1 | **Solo fixtures** hasta P6 y cierre de FASE 1; el adaptador ADS-B real queda NO VERIFICADO. El contexto de incidentes queda en fixtures hasta P6 y cierre de FASE 2. |
| T3.15 Demostración de extremo a extremo | Todo lo anterior, además de la app/backend de FASE 3 | **Bloqueada** hasta P6 y cierre de FASE 1 y 2, y hasta completar las dependencias de FASE 3. |
| T3.1-T3.3, T3.5-T3.10, T3.13 | No requieren contratos ni servicios de FASE 1; pueden usar interfaces locales | Técnicamente independientes de FASE 1, pero su ejecución también espera P0 de FASE 3 y P6/cierre de FASE 1 y 2. En paralelo solo se permite preparación documental. |
| T3.14 Informe PDF | Datos de entrada, contexto y paquete de evidencias | En paralelo solo se puede revisar documentalmente el alcance con fixtures; no se genera el PDF. Implementación y verificación esperan P0 de FASE 3, P6/cierre de FASE 1 y 2, T3.12/T3.13 y la decisión sobre firma del supervisor. |

**Lo que la FASE 3 necesita que contenga el contrato** (se lleva a la revisión del STOP de la FASE 1; si falta, se propone un ADR y se comprueba con `buf breaking`):
- `Sighting`: UUID (idempotencia), hora UTC de captura, id del dispositivo, posición del observador con precisión, rumbo verdadero e incertidumbre, ángulo de elevación, rangos de distancia y de altura estimadas, clase estimada (C1-C9 o desconocida), número de drones, descripción, referencias a la evidencia (SHA-256, tipo MIME, tamaño, hora de captura) y rol del autor. Sensibilidad: la posición del observador y la evidencia, `OPERATOR`.
- `Detection`: `sensor_type = HUMAN`, posición estimada con covarianza o elipse (o, si no hay distancia, una línea de rumbo con su incertidumbre), confianza, marcas de tiempo y referencia al `Sighting`.
- `Evidence`: hash, entradas de la cadena de custodia y token de sello de tiempo.

### 4.1 Compatibilidad abierta con los contratos actuales de FASE 1

Contraste documental del plan con los `.proto` actuales de la rama de trabajo de FASE 1, consultados el 2026-11-10 (`sighting.proto`, `detection.proto`, `evidence.proto` y `common.proto`). La tabla no cambia el contrato ni aprueba nuevos campos; enumera asuntos que deben resolverse en el STOP de FASE 1. Las adiciones, si se proponen, requieren revisión de compatibilidad (`buf breaking`) y de sensibilidad antes de cerrar esa fase.

| Necesidad de FASE 3 | Contrato actual de FASE 1 | Estado | Asunto abierto para la revisión de FASE 1 |
|---|---|---|---|
| Identidad e idempotencia del avistamiento; hora UTC; origen del dispositivo | `Sighting.sighting_id` (presencia requerida), `observed_at`; `Envelope.node_id` | Parcialmente cubierto | Confirmar formato UUID, semántica de idempotencia y si `observed_at` satisface la hora de captura solicitada. El ID de dispositivo está fuera de `Sighting`; decidir si basta `Envelope.node_id` y si el transporte de FASE 3 lleva `Envelope` o un `Sighting` aislado. |
| Posición del observador y precisión | `Sighting.observer_position: GeoPoint` | Parcialmente cubierto | `GeoPoint` da coordenadas y altitud opcional, pero no expresa precisión/incertidumbre de la posición del observador. |
| Rumbo, elevación, distancia y altura estimadas con incertidumbre | `bearing_deg`, `bearing_uncertainty_deg`, `estimated_altitude_m`, `estimated_distance_m` | Parcialmente cubierto | No hay ángulo de elevación ni rangos/intervalos de altura y distancia; las estimaciones actuales son escalares opcionales. |
| Clase estimada y número de drones | `Sighting` no contiene estos datos; `Detection` admite `class_scores` | Pendiente | Determinar si son datos del avistamiento, de la detección derivada o no se recogen en v1. No asignar valores por defecto sin decisión. |
| Descripción y referencias a evidencia | `Sighting.description`, `Sighting.evidence_ids` | Cubierto en estructura | Revisar que el flujo de evidencia vincule los IDs de forma verificable. |
| Evidencia: hash, MIME, tamaño y hora de captura | `Evidence` contiene `sha256`, `media_type` y `captured_at` | Parcialmente cubierto | No hay tamaño de medio. Resolver si se añade al contrato o queda en el manifiesto/almacén de evidencia. |
| Autor/rol y custodia | `Evidence.custodian_pseudonym` y `custody_signature`; no hay rol en `Sighting` ni eventos de custodia | Parcialmente cubierto | Definir si el rol se obtiene de autenticación del backend y si los eventos append-only viven solo en el servicio de evidencia. No duplicar identidad personal en el contrato. |
| Sello RFC 3161 | No hay token de sello en `Evidence` | Pendiente de diseño | Resolver si el token se conserva como artefacto separado del mensaje Protobuf, junto con su hash y manifiesto. |
| Detección humana derivada | `SensorType.SENSOR_TYPE_HUMAN`, `HumanObservation.sighting_id`, campos de posición/covarianza/elipse, rumbo/incertidumbre, `class_scores`, confianza y hora | Mayormente cubierto | T1.4 de FASE 1 está cerrado con validación de presencia e incertidumbre; confirmar que los casos de posición y línea de rumbo representan el criterio de FASE 3. |

La tabla de sensibilidad aprobada en T1.3 cubre el esquema actual. `Sighting.description` tiene nivel `OPERATOR`; el usuario condicionó su uso a la sanitización del texto libre y a controles de acceso probados en T1.7. Todo consumidor debe aplicar esos controles antes de logs y salidas; la sensibilidad `OPERATOR` por sí sola no sanea el contenido. Cualquier campo nuevo debe recibir una sensibilidad explícita y seguir el proceso de revisión correspondiente; esta tabla no implica aprobación de cambios.

**FASE 2** (radar de incidentes): el contexto «incidentes previos cercanos» (REQ-FUN-021) solo usa fixtures hasta cerrar FASE 2. Su plan sigue pendiente de P0 y T2.0 exige que FASE 1 esté cerrada antes de empezar FASE 2.

La FASE 2 propone una API local de solo lectura (`GET /api/v1/incidentes`, `/api/v1/incidentes/{id}` y otras rutas, T2.15). El punto de integración propuesto para T3.12 es un adaptador de lectura sobre esa API y la vista que esta exponga; el contrato de consulta, los estados visibles, el filtro geográfico y la forma de expresar «incidente cercano» quedan por definir en la planificación/ADR de FASE 2. Se respetará su lista blanca de campos y filtros de privacidad. El acoplamiento directo a tablas internas de PostgreSQL no se presupone. La API aún no está implementada ni sus datos disponibles. La prueba con incidentes sintéticos de T3.12 se mantiene como fixture hasta que ambas fases estén cerradas.

**Otras:** el móvil del usuario con la depuración USB activada (§8, pregunta 1). La validación con la Guardia Civil: **B-02**.

## 5. Tareas

Orden estricto dentro de cada bloque. Cada tarea: TDD (primero el test que falla), verificación y prueba negativa registradas en `docs/evidence/FASE-3/registro-tareas.md`, y un commit con los IDs. **Un FALLO bloquea la tarea siguiente.**

Convenciones:
- `make android-check` = `./gradlew --no-parallel ktlintCheck detekt testDebugUnitTest lintDebug` dentro de `apps/android-sightings`. **No** entra en `make check`, que debe seguir por debajo de ~60 s (hook Stop).
- `make android-device-test` = `./gradlew connectedDebugAndroidTest` en el móvil conectado (`adb devices` con un único dispositivo).
- Los tests de Kotlin llevan el ID en el nombre (`req_FUN_016_…`) para la trazabilidad (T3.3).

### T3.0 — Precondiciones y datos del móvil
- **Qué:** comprobar que la FASE 0 está cerrada y, para las tareas que dependen de ella, la FASE 1; registrar el modelo, la versión de Android, el nivel de API, el ABI y los sensores del móvil (con permiso del usuario). Con eso se fijan `minSdk` y `targetSdk` y se sabe si hay magnetómetro, del que depende la brújula.
- **Requisitos:** REQ-NFR-015, REQ-FUN-017
- **Verificación:** `git tag -l 'fase-*' && cat docs/requirements/FASES-CERRADAS.txt && adb devices -l && adb shell getprop ro.product.model && adb shell getprop ro.build.version.release && adb shell getprop ro.build.version.sdk && adb shell getprop ro.product.cpu.abi && adb shell dumpsys sensorservice` (filtrando después las líneas de magnetómetro y vector de rotación)
- **Resultado esperado:** `fase-0-cerrada` presente; un dispositivo `device` (no `unauthorized`); API ≥ 26 (propuesta de `minSdk`, a confirmar con el dato real); al menos un sensor de campo magnético y uno de vector de rotación.
- **Prueba negativa:** sin etiqueta `fase-0-cerrada`, el script de precondiciones sale con 1 nombrando la fase; con el móvil sin autorizar, informa `unauthorized` y no sigue. **Sin magnetómetro:** REQ-FUN-017 pasa a rumbo manual sobre el mapa y se avisa al usuario (decisión, no se oculta).

### T3.1 — Android SDK y Gradle por línea de comandos (sin Android Studio)
- **Qué:**
  - Descargar `commandlinetools-mac_x86_64-15859902_latest.zip` (156,3 MB) desde developer.android.com/studio y **comprobar su SHA-256** antes de descomprimirlo: `c5a6378ab5cf7e0d5701921405115befff13e9ff7417fb588389338f8bd050f3`. Descomprimirlo en `~/Library/Android/sdk/cmdline-tools/latest/` (estructura de la documentación oficial).
  - `sdkmanager "platform-tools" "platforms;android-36" "build-tools;36.0.0"` y `sdkmanager --licenses` (el usuario acepta las licencias del SDK: decisión 2).
  - **Sin emulador ni imágenes de sistema** (emulador x64: 488,7 MB de descarga, más la imagen, más RAM).
  - `ANDROID_HOME` en `apps/android-sightings/local.properties` (en `.gitignore`), no en el perfil global.
  - `scripts/doctor.sh` gana la sección Android (JDK ≥ 17, `sdkmanager`, `adb`, plataforma 36, build-tools 36.0.0) como opcional, para no romper `make doctor` en otras fases.
  - Medir el disco antes y después.
- **Requisitos:** REQ-NFR-015, REQ-NFR-016
- **Verificación:** `shasum -a 256 <zip> && make doctor && sdkmanager --list_installed && du -sh ~/Library/Android/sdk && df -h ~`
- **Resultado esperado:** el hash coincide; `make doctor` en verde con la sección Android; los tres paquetes instalados; SDK ≤ 1 GB en disco (estimación NO VERIFICADA, se registra la cifra real).
- **Prueba negativa:** un zip con un byte alterado → el script de instalación se niega a descomprimir (exit ≠ 0); `ANDROID_HOME` vacío → `make doctor` señala Android como FALTA sin fallar las secciones obligatorias.

### T3.2 — Esqueleto del proyecto Android y calidad
- **Qué:**
  - `apps/android-sightings/` con Gradle Kotlin DSL y *wrapper* fijado con `distributionSha256Sum`.
  - `gradle/libs.versions.toml` con las versiones de §3.1, comprobadas de nuevo, y *dependency locking* (`gradle.lockfile`).
  - Módulos: `:app` (UI Compose), `:core-geo` (geometría pura, JVM), `:core-queue` (cola cifrada) y `:core-capture` (captura y hash).
  - Memoria: `org.gradle.jvmargs=-Xmx1536m`, `kotlin.daemon.jvmargs=-Xmx1g`, `org.gradle.parallel=false` y `org.gradle.workers.max=2`. `make android-check` detiene el *daemon* al terminar (`--stop`).
  - ktlint y detekt sin avisos. Comprobar que detekt 1.23.8 funciona con Kotlin 2.4; si no, ADR (detekt 2.0 alpha o aplazarlo).
  - Comprobar en la documentación de AGP 9 si el plugin de Kotlin viene integrado y qué plugin de Compose hace falta (**NO VERIFICADO**).
- **Requisitos:** REQ-NFR-014, REQ-NFR-015
- **Verificación:** `make android-check` y `/usr/bin/time -l ./gradlew assembleDebug` (memoria residente máxima)
- **Resultado esperado:** compilación y tests de ejemplo en verde; APK debug generado; pico de memoria de Gradle por debajo de ~3 GB (se registra la cifra); `du -sh ~/.gradle` registrado.
- **Prueba negativa:** un fichero con una infracción de ktlint → `make android-check` falla; cambiar una versión sin actualizar el *lockfile* → la compilación falla por el bloqueo de dependencias.

### T3.3 — Licencias, SBOM y trazabilidad de Kotlin
- **Qué:**
  - `scripts/license_check.py` amplía G-12 al `runtimeClasspath` de release de la app (lo que se distribuye): lista los artefactos desde el `gradle.lockfile` y su licencia desde el POM, y bloquea GPL y AGPL. LGPL se marca para revisión. Las dependencias solo de test o de compilación se listan aparte.
  - `scripts/traceability.py` lee también los JUnit XML de Gradle (`build/test-results/**` y `build/outputs/androidTest-results/**`), copiados a `reports/android/` con el commit en el nombre, y reconoce los IDs en los nombres de los tests.
  - Decidir con un ADR qué hacer cuando los resultados de Android son de un commit anterior a cambios en `apps/android-sightings/`. Propuesta: la trazabilidad los marca **caducados** y no los cuenta.
- **Requisitos:** REQ-LEG-016, REQ-NFR-014, REQ-SEC-012
- **Verificación:** `uv run pytest tests/test_license_check.py tests/test_traceability.py -v && make trace`
- **Resultado esperado:** tests en verde; `TRAZABILIDAD.md` muestra los tests de Kotlin con su requisito; sin GPL ni AGPL en el classpath de release.
- **Prueba negativa (G-12):** fixture con un artefacto GPL en el *lockfile* → exit 1 nombrándolo; JUnit de Android de un commit antiguo → tratado como caducado, y el MUST queda como hueco.

### T3.4 — Bindings del contrato en Kotlin y Python  *(depende de la FASE 1)*
- **Qué:** generar desde `proto/atalaya/v1` los bindings `protobuf-javalite` para la app (plugin de Gradle de protobuf con `protoc` fijado por versión y hash) y Python para el backend. Nunca escritos a mano. Test de *round-trip* Kotlin → bytes → Python y al revés con vectores compartidos en `tests/fixtures/contrato/`.
- **Requisitos:** REQ-FUN-020, REQ-LEG-007
- **Verificación:** `buf lint && buf breaking --against '.git#branch=main' && make android-check && uv run pytest tests/contrato -v`
- **Resultado esperado:** *round-trip* idéntico en ambos sentidos; todos los campos de `Sighting` declaran sensibilidad; ninguno `FCSE_ONLY` sale en la app.
- **Prueba negativa:** un vector con un campo desconocido o mal tipado → se rechaza en la validación; quitar la sensibilidad de un campo en una copia → el test de la FASE 1 falla.

### T3.5 — Geometría asistida: rumbo, altura y distancia
- **Qué:** módulo `:core-geo` en Kotlin puro (sin Android) y su gemelo en Python para el backend, con vectores de prueba compartidos:
  - **Rumbo:** azimut magnético del vector de rotación más la declinación del modelo geomagnético (`GeomagneticField` en el adaptador de Android) → rumbo verdadero. Incertidumbre según la precisión que informa el sensor; si está en `UNRELIABLE`, se avisa para calibrar.
  - **Altura y distancia asistidas:** con el ángulo de elevación del móvil al apuntar al dron, la altura del observador y una de dos referencias, (a) la distancia estimada (con preajustes de 50, 100, 200 y 500 m) o (b) el tamaño aparente frente a la envergadura típica de la clase, se calcula la otra magnitud por trigonometría con propagación de incertidumbre (rangos, nunca un valor único).
  - **Posición estimada:** punto a la distancia y el rumbo dados desde el observador (geodésica) con su elipse.
- **Requisitos:** REQ-FUN-017, REQ-FUN-020
- **Verificación:** `./gradlew :core-geo:test` y `uv run pytest tests/sightings/test_geo.py -v` (incluye `hypothesis`)
- **Resultado esperado:** casos con solución conocida (elevación 45° y distancia 100 m → altura 100 m más la del observador, ± tolerancia); propiedades: el rumbo siempre queda en [0, 360), la incertidumbre nunca se encoge al añadir ruido y Kotlin y Python coinciden en todos los vectores hasta 1e-9.
- **Prueba negativa:** elevación < 0° o > 90°, distancia negativa o NaN → error explícito; precisión de brújula `UNRELIABLE` → el avistamiento lleva la incertidumbre máxima (180°) y un aviso visible, nunca un rumbo con aspecto preciso.

### T3.6 — Captura de foto y vídeo con SHA-256 en el momento de la captura
- **Qué:**
  - CameraX. Foto: se captura en memoria, se calcula el SHA-256 de los bytes y se cifran antes de tocar disco. Vídeo: CameraX escribe en un fichero privado de la app; al recibir el evento de fin de grabación se calcula el SHA-256 en flujo, se cifra (Tink, AEAD por flujo) y se borra el claro. Esa ventana se documenta como riesgo y se mide.
  - **Vídeo sin pista de audio:** no se llama a la API que activa el audio en CameraX.
  - Registro de captura: hash, tamaño, MIME, hora UTC del sistema y hora del GNSS si existe.
  - Aviso al vigilante para no captar personas innecesariamente (REQ-PRIV-011).
- **Requisitos:** REQ-FUN-018, REQ-PRIV-008, REQ-PRIV-011
- **Verificación:** `./gradlew :core-capture:test` (hash en flujo frente a vectores conocidos) y `make android-device-test` con el filtro de clase `CaptureInstrumentedTest`
- **Resultado esperado:** el hash guardado coincide con el del fichero que llega al backend; el vídeo producido no tiene pista de audio (comprobado con `MediaExtractor` en el test); el fichero en claro no existe tras el cifrado.
- **Prueba negativa:** alterar un byte del medio después de la captura → la verificación del backend lo rechaza (`hash_mismatch`); fichero truncado → rechazado.

### T3.7 — Cola cifrada sin conexión
- **Qué:**
  - Cola en Room. El cuerpo de cada elemento (el `Sighting` serializado, que la cola trata como bytes opacos) y los medios se cifran con Tink AEAD, con el *keyset* envuelto por una clave de Android Keystore no exportable. Alternativa con SQLCipher si el ADR lo prefiere (decisión 4).
  - Envío con WorkManager (restricción de red) y reintentos con espera exponencial. UUID de idempotencia: el backend descarta duplicados.
  - Estado visible en la UI: «N pendientes», «error de envío».
- **Requisitos:** REQ-FUN-019
- **Verificación:** `./gradlew :core-queue:testDebugUnitTest` (Robolectric) y `make android-device-test` con el filtro `OfflineQueueInstrumentedTest`
- **Resultado esperado:** N = 20 avistamientos creados sin red → 20 recibidos y 0 duplicados al reconectar (backend falso en el test y backend real en T3.15); un marcador conocido no aparece en ningún byte de los ficheros de la base ni de los medios.
- **Prueba negativa:** texto cifrado alterado → el elemento queda en «error de integridad», visible y sin enviar (nunca se pierde en silencio); backend que responde 500 → los elementos siguen en la cola; reenviar el mismo UUID → el backend lo acepta una sola vez.

### T3.8 — Permisos y manifiesto: sin micrófono (G-14)
- **Qué:** el manifiesto declara solo `CAMERA`, `ACCESS_FINE_LOCATION`, `INTERNET` y `ACCESS_NETWORK_STATE`. Tres capas:
  - test sobre el **APK compilado** con `aapt2 dump permissions` (incluye lo que añada la fusión de manifiestos de las bibliotecas), con `tools:node="remove"` si alguna biblioteca lo pidiera;
  - test instrumentado de que `RECORD_AUDIO` no está concedido ni se solicita;
  - nueva regla del guardarraíl de commit: un `AndroidManifest.xml` bajo `apps/android-sightings/` con ese permiso se bloquea (con tests y mutación del guardarraíl).
- **Requisitos:** REQ-PRIV-008, REQ-SEC-001
- **Verificación:** `make android-check && uv run pytest tests/sightings/test_manifest.py tests/guardrails -v && make android-device-test` con el filtro `PermissionsInstrumentedTest`
- **Resultado esperado:** la lista de permisos del APK es exactamente la esperada; el test instrumentado lo confirma en el móvil.
- **Prueba negativa (G-14):** en una copia, añadir `RECORD_AUDIO` al manifiesto → el test del APK falla y el guardarraíl bloquea el commit (exit 2); una dependencia de prueba que lo añade por fusión → el test del APK falla.

### T3.9 — UI Compose: alta en 3 toques, roles y accesibilidad
- **Qué:**
  - **Camino principal:** (1) botón grande «Avistamiento» (toma posición y rumbo); (2) «Foto» o «Vídeo» apuntando al dron (fija la elevación); (3) «Enviar». Distancia y altura llevan valores por defecto asistidos y editables, que suman toques **opcionales**. Sin teclado en el camino principal.
  - **Roles:** el vigilante crea y ve los suyos; el supervisor además valida, añade observaciones y firma (T3.14). La autorización real la hace el backend (T3.11).
  - **Accesibilidad:** modo nocturno (fondo oscuro con texto rojo atenuado, para conservar la visión nocturna), tema de contraste alto, objetivos táctiles ≥ 48 dp, texto escalable y descripciones de contenido.
- **Requisitos:** REQ-FUN-016, REQ-NFR-010, REQ-PRIV-011
- **Verificación:** `./gradlew :app:testDebugUnitTest` (Compose UI test con Robolectric) y `make android-device-test` con el filtro `MainFlowInstrumentedTest`
- **Resultado esperado:**
  - Un contador de interacciones registra ≤ 3 clics desde la pantalla inicial hasta «avistamiento en cola».
  - Un recorrido del árbol semántico confirma que **todos** los nodos pulsables miden ≥ 48 × 48 dp.
  - Los modos nocturno y de contraste alto se aplican (se comprueban los colores del tema en los nodos).
  - Comprobaciones automáticas de accesibilidad (Accessibility Test Framework en los tests de Compose; API **NO VERIFICADA**, se comprueba en T3.9) sin fallos críticos.
  - Si el usuario lo aprueba (decisión 6), una pasada manual de Accessibility Scanner en el móvil, con captura fechada y el commit.
- **Prueba negativa:** en una copia del flujo con un diálogo de confirmación añadido → el test de 3 toques falla; un botón de 40 dp → el test de tamaño falla nombrándolo; el vigilante no ve la acción «Firmar».

### T3.10 — PKI local y mTLS por dispositivo (básico)
- **Qué:**
  - `scripts/pki_local.py` (con `cryptography`): CA local de prueba, certificado de servidor para `127.0.0.1` y certificados de dispositivo con su número de serie. Claves en `secrets/` (lectura denegada a Claude Code), nunca en git.
  - **Alta del dispositivo:** se genera un PKCS#12 de un solo uso, se copia con `adb push`, la app lo importa en Android Keystore (clave no exportable) y lo borra.
  - Servidor de avistamientos con `uvicorn` exigiendo certificado de cliente (opciones de TLS **NO VERIFICADAS**, se comprueban en T3.10) y lista de revocación local.
  - **Conexión del móvil sin exponer el Mac a la red:** `adb reverse tcp:8443 tcp:8443` por USB, de modo que el servicio sigue en `127.0.0.1` (coherente con T0.10).
  - La rotación y la revocación completas quedan para las FASES 5 y 12.
- **Requisitos:** REQ-SEC-004 (básico), REQ-SEC-010 (parte), REQ-SEC-005, REQ-SEC-017
- **Verificación:** `uv run pytest tests/sightings/test_mtls.py -v` (cliente Python contra el servidor real en loopback) y `make android-device-test` con el filtro `MtlsInstrumentedTest`
- **Resultado esperado:** un cliente con certificado válido → 200; la app en el móvil completa el *handshake* a través de `adb reverse`.
- **Prueba negativa:** sin certificado → *handshake* rechazado; certificado de otra CA → rechazado; certificado revocado → rechazado y evento registrado (sin datos personales en el log, REQ-PRIV-003); certificado caducado → rechazado.

### T3.11 — Backend: avistamiento → `Detection(sensor_type=HUMAN)`  *(depende de la FASE 1)*
- **Qué:**
  - `services/ingest/sightings/` (FastAPI, arquitectura hexagonal): recibe `Sighting` en Protobuf y los medios por partes, verifica el SHA-256 de cada medio, guarda en PostgreSQL y en el almacén de evidencias, y abre la cadena de custodia (T3.13).
  - Convierte el avistamiento en `Detection(sensor_type=HUMAN)` con posición y covarianza (T3.5) o, sin distancia, una línea de rumbo con su incertidumbre, y lo publica en el bus del contrato de la FASE 1.
  - **Autorización mínima** por rol: el vigilante crea; el supervisor valida y firma.
  - **Medios:** acceso por rol y retención configurable con borrado auditado y reloj simulado (REQ-PRIV-011).
  - El texto libre lleva un aviso: no incluir datos que identifiquen o sitúen a quien maneja el dron, que son `FCSE_ONLY` (REQ-LEG-007). La decisión 7 (§8) sobre añadir un campo estructurado sigue pendiente; hasta resolverla no se crea ese campo. Si se elige recopilarlo como `FCSE_ONLY`, se actualizarán el alcance y los controles de RBAC/auditoría antes de recoger datos.
  - Antes de registrar texto en logs o emitirlo a cualquier salida, aplicar la sanitización y los controles de acceso de T1.7 a `Sighting.description`. `OPERATOR` no sustituye a la sanitización. Si T1.7 no puede certificar una salida segura, rechazar la petición o suprimir el texto; no registrar ni emitir el contenido original.
- **Requisitos:** REQ-FUN-020, REQ-FUN-018, REQ-PRIV-011, REQ-PRIV-003, REQ-LEG-007
- **Verificación:** `make up && uv run pytest tests/sightings/test_ingest.py tests/sightings/test_to_detection.py -v` (integración con el bus de compose)
- **Resultado esperado:** un avistamiento produce exactamente una `Detection` HUMAN en el bus, con la incertidumbre esperada para los vectores de T3.5; idempotente por UUID; logs JSON sin datos personales. La descripción solo llega a logs o salidas tras pasar los controles de T1.7.
- **Prueba negativa:** medio con hash distinto → 422 y nada publicado; el vigilante intenta firmar → 403; la retención vencida borra el medio y deja registro; un `Sighting` sin rumbo ni posición → rechazado, nunca una detección inventada; si la descripción no supera la sanitización/control de T1.7, no aparece en logs ni se emite a la detección o a otra salida.

### T3.12 — Contexto del avistamiento (REQ-FUN-021, SHOULD)
- **Qué:** puerto `ContextProvider` con cuatro adaptadores. Para cerrar T3.12 en FASE 3, todos se prueban con fixtures; no se habilitan fuentes reales en esta fase. La ingesta real queda diferida hasta que exista y esté disponible `dataset-intake` de FASE 4 (T4.4), y cada fuente deberá pasar por esa herramienta con sus términos verificados y archivados:
  - **Zonas UAS:** instantánea local del servicio WFS de ENAIRE de zonas geográficas UAS. **Licencia y términos NO VERIFICADOS**: sin verificar, solo se usan fixtures sintéticas.
  - **NOTAM:** no se ha encontrado una fuente a 0 € con términos verificados → **NO VERIFICADO**; solo fixtures.
  - **ADS-B:** replay o simulador de la FASE 1. Sin fuente en vivo (SPEC D7); hasta cerrar FASE 1, solo fixture y estado NO VERIFICADO.
  - **Incidentes:** adaptador de lectura a la interfaz local de FASE 2 descrita en §4.1. Hasta cerrar FASE 2, solo fixtures; no consultar directamente su base de datos.
  
  Respuesta con lo que hay y **«fuente no disponible»** de forma explícita, nunca «sin restricciones» por falta de datos (principio de fallo visible).
- **Requisitos:** REQ-FUN-021, REQ-LEG-009
- **Verificación:** `uv run pytest tests/sightings/test_context.py -v`
- **Resultado esperado:** con fixtures conocidas (zona activa que contiene el punto, aeronave a 3 km y 500 m de altura, 2 incidentes en 5 km), el contexto devuelto coincide exactamente.
- **Prueba negativa:** fuente caída → el contexto dice «no disponible» para esa fuente y no «ninguna zona»; zona fuera de su horario de actividad → no se marca como activa.

### T3.13 — Cadena de custodia y TSA local RFC 3161 (REQ-SEC-018)
- **Qué:**
  - `services/evidence/`: registro **append-only** de custodia encadenado por hash (captura, recepción, validación, firma y exportación, con quién, cuándo y el hash), detrás de una interfaz.
  - `TimeStamper` con dos implementaciones: la **TSA local de prueba**, que envuelve `openssl ts -reply` con una CA de prueba generada en local y llamado sin `shell=True` (semgrep), y una TSA externa futura, solo con ADR.
  - El certificado y la política de la TSA local llevan en su nombre «PRUEBA — SIN VALOR PROBATORIO».
  - Paquete de evidencia: medios, `Sighting`, registro de custodia, tokens y `MANIFEST.sha256`.
- **Requisitos:** REQ-SEC-018, REQ-FUN-059
- **Verificación:** `uv run pytest tests/evidence -v` (sin red) y `openssl ts -verify` sobre un token generado
- **Resultado esperado:** el sello de la TSA local se verifica sin conexión; la cadena de custodia se verifica de extremo a extremo.
- **Prueba negativa:** alterar un byte de la evidencia, del token o de una entrada de custodia, o borrar o reordenar una entrada → la verificación falla nombrando el elemento; un token de una TSA no confiable → rechazado.

### T3.14 — Informe PDF para las FCSE
- **Qué:**
  - reportlab en modo invariante (salida reproducible). Contenido: hora UTC y local (zona del emplazamiento, p. ej. `Africa/Ceuta` o `Europe/Madrid`), posición del observador, rumbo con incertidumbre, altura y distancia estimadas (rangos), **solo la descripción ya sanitizada por los controles de T1.7**, contexto (T3.12, con las fuentes no disponibles indicadas), evidencias con SHA-256, cadena de custodia y validación del supervisor. No se copia el texto original directamente al PDF.
  - Si T1.7 no puede certificar que la descripción es segura para ese destinatario, se falla cerrado y no se genera ni firma el informe; el control de acceso al rol no reemplaza la sanitización.
  - **Firma del supervisor** con pyHanko (PAdES) y sello de la TSA local. Marca visible en cada página: «Sello de tiempo de TSA LOCAL DE PRUEBA — SIN VALOR PROBATORIO».
  - Opción A, preferida: la clave del supervisor está en el Keystore del móvil y firma el resumen del documento (firma externa con pyHanko; viabilidad **NO VERIFICADA**, se prueba primero con un *spike* acotado).
  - Opción B, alternativa: certificado del supervisor expedido por la CA local y custodiado en el backend, con la aprobación del supervisor desde la app como entrada auditada de custodia.
- **Requisitos:** REQ-FUN-022, REQ-SEC-018, REQ-FUN-059
- **Verificación:** `uv run pytest tests/sightings/test_report_pdf.py -v`
- **Resultado esperado:**
  - El PDF sin firmar tiene el mismo SHA-256 que la referencia en `tests/fixtures/informe/`.
  - El texto extraído (pypdf) contiene todos los campos obligatorios y la marca de prueba.
  - La firma y el sello validan con pyHanko frente a la CA local.
  - **Inspección humana de la referencia** por el usuario, con la captura en la evidencia.
- **Prueba negativa:** modificar un byte del PDF firmado → la firma no valida; un informe sin firma del supervisor o sin la marca de prueba → el generador se niega; firma con un certificado de vigilante → rechazada; descripción que no supera T1.7 → no se genera ni firma el PDF y el texto original no aparece en logs ni artefactos.

### T3.15 — Demostración en el móvil del usuario  *(depende de la FASE 1)*
- **Qué:** guion `scripts/demo_fase3.sh`, ejecutado con el móvil por USB:
  1. Instala el APK firmado en debug (`adb install -r`).
  2. Corta la red de la app (sin `adb reverse` y en modo avión, que activa el usuario).
  3. Crea 3 avistamientos (uno con vídeo) en ≤ 3 toques cada uno.
  4. Restaura la red; los 3 llegan.
  5. Muestra la `Detection` HUMAN en el bus.
  6. El supervisor valida y firma; se genera el PDF.
  7. Se verifican el paquete de evidencias y el sello.
  
  Capturas con `adb exec-out screencap` (solo pantalla) con la fecha y el commit. Comprobar los sensores reales: rumbo frente a una referencia conocida (p. ej. una calle orientada según el mapa), con el error anotado.
- **Requisitos:** REQ-FUN-016 a REQ-FUN-020, REQ-FUN-022, REQ-FUN-059, REQ-NFR-010, REQ-PRIV-008, REQ-SEC-018
- **Verificación:** `make up && scripts/demo_fase3.sh` más `make android-device-test` (todos los tests instrumentados)
- **Resultado esperado:** los 7 pasos en OK en `demo-fase3.txt`; JUnit de los tests instrumentados en verde; error de rumbo medido y registrado (sin umbral fijado: se propone uno por ADR con este dato).
- **Prueba negativa:** con el certificado del dispositivo revocado, la app no puede enviar y muestra el error, y la cola conserva los elementos; quitar el permiso de cámara → la app permite el avistamiento sin medio y lo indica.

### T3.16 — ADR y documentos de la fase
- **Qué:** ADR (MADR, numerados al crearlos):
  - toolchain Android sin Android Studio y sin emulador;
  - transporte de la app: HTTPS con mTLS y Protobuf frente a MQTT (los medios grandes no encajan bien en MQTT);
  - cifrado de la cola (Keystore más Tink, o SQLCipher);
  - firma del supervisor (opción A o B) y TSA local;
  - JUnit de Android en la trazabilidad (resultados caducados);
  - umbral de error de rumbo.
  
  Además: `docs/threat-model/` de la FASE 3 (robo del móvil, dispositivo falso, reenvío de avistamientos, manipulación de medios, avistamientos falsos de un vigilante); DPIA (posición del observador como dato del trabajador, terceros en fotos y vídeos, retención); ENS; lista de comprobación MASVS y ASVS con evidencias (REQ-SEC-017); riesgos nuevos en `docs/RIESGOS.md`; deuda técnica.
- **Requisitos:** REQ-SEC-015, REQ-SEC-016, REQ-SEC-017, REQ-PRIV-006, REQ-PRIV-011
- **Verificación:** `uv run pytest tests/test_documentos.py -v && python3 -I scripts/check_spec.py`
- **Resultado esperado:** cada ADR con Estado, Contexto, Decisión y Consecuencias; STRIDE con las 6 categorías para la app; DPIA con base jurídica de cada tratamiento nuevo; `check_spec` en OK (las líneas sensibles nuevas solo entran en la lista blanca tras leerlas una persona).
- **Prueba negativa:** en una copia, quitar «Consecuencias» de un ADR o el tratamiento «posición del observador» de la DPIA → el test falla.

### T3.17 — Cierre de fase
- **Qué:**
  - Puertas P2 a P5: `make check`, `make android-check`, `make regress` (con `scripts/regress.d/fase-3.sh`, que vuelve a compilar y pasar los tests JVM de Android y los del backend), `scripts/verify_clean_clone.sh`.
  - Subagentes `independent-reviewer`, `test-auditor`, `security-reviewer`, `legal-guardrail-reviewer` y `privacy-reviewer`; hallazgos corregidos o justificados.
  - Mutación del control de acceso de la API de avistamientos y de la verificación de evidencias por encima del umbral del ADR 0006.
  - `make evidence FASE=3` y `CIERRE.md` con B-02 como bloqueo.
- **Requisitos:** todos los de §2
- **Verificación:** los comandos de P2-P4, con su salida pegada en el paquete
- **Resultado esperado:** todo en verde; `TRAZABILIDAD.md` sin huecos MUST de la FASE 3 salvo la parte bloqueada de REQ-FUN-022 (B-02) y la verificación de los tests instrumentados vigente para el commit de cierre.
- **Prueba negativa:** la de cada puerta. El clon limpio sin Android SDK debe pasar `make check` (Android no entra en él) y avisar de que `make android-check` no se puede ejecutar.

## 6. Espacio en disco y memoria

Tamaños de **descarga** comprobados en el manifiesto oficial `repository2-4.xml` de dl.google.com y en la página de descargas. Tamaños **instalados** estimados (**NO VERIFICADO**; T3.1 y T3.2 registran la cifra real).

| Elemento | Descarga (comprobada) | Instalado (estimado) |
|---|---|---|
| cmdline-tools 23.0 (mac x64) | 156,3 MB | ~0,2-0,3 GB |
| platform-tools 37.0.1 | 16,1 MB | ~0,05 GB |
| platforms;android-36 | 65,9 MB | ~0,1-0,2 GB |
| build-tools;36.0.0 | 79,1 MB | ~0,2-0,3 GB |
| Gradle 9.6.0 (bin) | 140,7 MB | ~0,3 GB (zip más descomprimido) |
| Caché de Gradle (AGP, Kotlin, Compose, CameraX, Room, Tink, Robolectric con su `android-all`, ktlint, detekt) | — | **~2-4 GB** (la partida más incierta) |
| Salidas de compilación del proyecto | — | ~0,3-1 GB |
| Dependencias Python nuevas (pyHanko, reportlab…) | — | ~0,1 GB |
| **Total FASE 3** | **~0,46 GB** de SDK y Gradle | **~3,5-6 GB**. Recomendado: ≥ 10 GB libres al empezar |
| *No se instala:* Android Studio | 1,5 GB (dmg) | varios GB más su caché; requisitos de RAM **NO VERIFICADOS** (página no leída entera) |
| *No se instala:* emulador más imagen de sistema | 488,7 MB más la imagen | más ≥ 2 GB de RAM para la VM |

Memoria: Gradle a 1,5 GB, el *daemon* de Kotlin a 1 GB y Docker parado durante las compilaciones. Las pruebas instrumentadas corren en el móvil, no en el Mac.

## 7. Riesgos de la fase

| ID | Riesgo | Mitigación |
|---|---|---|
| R-47 (provisional) | Gradle, AGP y Compose agotan los 8 GB de RAM o el disco (caché de Gradle en crecimiento) | Límites de memoria, sin paralelismo, Docker parado, `du` registrado; limpiar con `./gradlew clean` y la caché de Gradle si baja de 8 GB libres |
| R-48 (provisional) | El móvil del usuario es antiguo (API < 26), no tiene magnetómetro o su fabricante restringe el trabajo en segundo plano | T3.0 lo mide antes de programar; `minSdk` según el dato; rumbo manual sin magnetómetro; envío en primer plano al abrir la app |
| R-49 (provisional) | El rumbo de brújula de un móvil tiene errores grandes (perturbación magnética cerca de metal o vehículos, falta de calibración) y da una posición con aspecto preciso | Incertidumbre explícita en la `Detection` y en el PDF; aviso de calibración; error medido en T3.15 |
| R-50 (provisional) | Que el PDF o el sello de la TSA local se tomen por prueba válida | Marca en cada página, en el certificado y en la política de la TSA; TSA cualificada solo con ADR (SPEC D10) |
| R-51 (provisional) | Ventana en la que el vídeo está en claro en el almacenamiento privado de la app antes de cifrarse | Medirla; borrar justo después del hash; documentar; estudiar escribir a un descriptor cifrado (NO VERIFICADO) |
| R-52 (provisional) | Retraso de la FASE 1 o un contrato sin los campos que necesita la FASE 3 | Lista de campos llevada al STOP de la FASE 1; no se implementa FASE 3 hasta P6 de las fases anteriores (§4) |
| R-53 (provisional) | Fuentes de contexto (zonas UAS, NOTAM, ADS-B) sin licencia verificada a 0 € | Solo fixtures durante FASE 3; cualquier ingesta real se difiere hasta disponer de `dataset-intake` (FASE 4, T4.4) y verificar/archivar los términos; «fuente no disponible» visible |
| R-54 (provisional) | Un vigilante escribe en el texto libre datos que identifican o sitúan a quien maneja el dron | Aplicar sanitización y control de acceso de T1.7 antes de logs/salidas; si no pasa, rechazar o suprimir la descripción. Aviso en la UI no sustituye al control (decisión 7) |
| R-19 | Minutos de CI limitados | Compilación y tests de Android en local (`make android-check`), con la evidencia en el paquete; en CI solo licencias y guardarraíles (decisión 5) |
| R-20 | Un único Android | Limitación declarada en el cierre: la app solo se ha probado en ese modelo |

Los IDs R-47–R-54 son provisionales. No colisionan con los IDs actuales del registro global (R-01–R-33) ni con los rangos planificados para FASE 1 (R-34–R-39), FASE 2 (R-40–R-46) y FASE 4 (R-55–R-59). Se validarán otra vez su unicidad y su incorporación al registro global antes del cierre de FASE 3; este borrador no modifica dicho registro.

## 8. Decisiones y preguntas para el usuario

**P0 pendiente, sin respuesta registrada:** ¿Apruebas este plan v1 de FASE 3 para iniciar T3.0? El estado no cambiará hasta recibir una aprobación explícita.

1. **¿Qué móvil Android tienes?** Marca y modelo exactos (Ajustes → Información del teléfono), **versión de Android** y, si lo sabes, cuánto almacenamiento libre tiene. ¿Puedes activar las Opciones de desarrollador y la **depuración USB**, y tienes un cable USB de datos? ¿Me dejas consultar sus sensores con `adb` (T3.0)?
2. Aprobar la instalación por línea de comandos (§6: ~3,5-6 GB, **sin** Android Studio ni emulador) y **aceptar las licencias del Android SDK** (`sdkmanager --licenses`; las acepta el usuario, no Claude).
3. JDK: usar el **Oracle JDK 21 ya instalado** (solo para compilar, no se distribuye) o instalar **Temurin 17/21** (libre; ~0,2-0,3 GB, NO VERIFICADO).
4. Cifrado de la cola: **Keystore + Tink** (recomendado; Apache-2.0, sin base de datos cifrada completa) o **SQLCipher** (BSD; cifra toda la base).
5. CI: ¿compilar Android también en GitHub Actions (consume minutos de un repo privado, ADR 0007) o **solo en local con evidencia** (recomendado)?
6. ¿Instalar **Accessibility Scanner** (app gratuita de Google) en tu móvil para la auditoría manual de REQ-NFR-010?
7. **PENDIENTE — Datos sobre quien maneja el dron en un avistamiento:** no recogerlos en la v1 (recomendado, minimización) o añadir un campo estructurado `FCSE_ONLY` con auditoría (exigiría actualizar el alcance y contar con RBAC antes de recogerlos).
8. Firma del supervisor: **opción A** (clave en el móvil, si el *spike* funciona) u **opción B** (clave en el backend local).
9. Validación del informe con la Guardia Civil: **B-02**. Si consigues un contacto, el PDF de referencia de T3.14 es el documento que se le enseñaría.

## 9. Estimación
**4-6 semanas de trabajo efectivo** (18 tareas, T3.0-T3.17), por encima del rango de la SPEC (3-5) por el mTLS básico, la TSA local y la puesta a punto del toolchain sin Android Studio; se reestima al cerrar T3.2. Coste: 0 €. T3.4, T3.11, T3.15 y el adaptador ADS-B de T3.12 dependen del cierre de FASE 1. El adaptador de incidentes de T3.12 depende del cierre de FASE 2; según el plan actual, FASE 2 requiere previamente el cierre de FASE 1.

## 10. NO VERIFICADO en este plan
- Tamaños instalados del SDK y de la caché de Gradle (solo descargas comprobadas).
- Requisitos de sistema de Android Studio y si la Android CLI funciona en Mac Intel.
- Licencias no leídas en esta sesión: AGP, Gradle, Kotlin, protobuf-javalite, detekt y OpenSSL (se esperan Apache-2.0 o BSD); ktlint (se espera MIT).
- Que detekt 1.23.8 funcione con Kotlin 2.4; el plugin de Kotlin integrado en AGP 9; la correspondencia exacta del Compose BOM 2026.09.00.
- Opciones de mTLS de `uvicorn`; firma externa con pyHanko desde una clave del Keystore; API de comprobaciones de accesibilidad en los tests de Compose.
- Licencia y términos del WFS de zonas UAS de ENAIRE; una fuente de NOTAM a 0 €.
- Modelo, versión de Android y sensores del móvil del usuario.

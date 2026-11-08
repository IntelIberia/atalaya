# Revisión independiente (P5) — FASE -1

Fecha: 2026-11-08 · Revisor: subagente de propósito general sin el contexto de la redacción, en solo lectura · Alcance: MEGAPROMPT, entrevista, SPEC, REQUIREMENTS, plan de pruebas, riesgos y `check_spec.py`.

Resultado del revisor: sin capacidades ofensivas explícitas, sin decodificación de comunicaciones de terceros y sin persistencia de audio fuera de sesión autorizada. 20 hallazgos, todos corregidos en el commit `4039896`.

| # | Sev. | Hallazgo | Resolución |
|---|---|---|---|
| 1 | ALTA | El principio 2 (fallo visible) solo cubría el nodo caído en el mapa | Nuevo **REQ-FUN-061** (MUST): nodo caído, reloj/PPS, modelo degradado y enlace perdido → cobertura degradada en el mapa; F-01, F-02, F-03 y F-08 lo prueban |
| 2 | MEDIA | Faltaba el principio 3 (incertidumbre) como requisito general | Nuevo **REQ-FUN-062** (MUST) con test de esquema; REQ-FUN-042 lo exige |
| 3 | MEDIA | REQ-SEC-001 y G-03 usaban «término prohibido» sin listar los términos | Términos enumerados; lista blanca limitada a identificadores concretos en un fichero versionado; G-04 prueba que un identificador parecido no listado se bloquea |
| 4 | BAJA | REQ-NFR-002 bajado a SHOULD sin justificación | Vuelve a MUST con 4G emulada |
| 5 | ALTA | El analista veía `FCSE_ONLY` «salvo habilitación» | Excepción eliminada: el analista nunca ve `FCSE_ONLY` |
| 6 | MEDIA | REQ-LEG-008 no probaba la ausencia en salidas públicas ni fijaba roles | Roles fijados (escribe el analista; leen el analista, FCSE y el auditor) y test generativo sobre endpoints, exportaciones, SAPIENT y logs |
| 7 | MEDIA | Envío real a Telegram frente a «solo local» | REQ-FUN-052: canal simulado en la v1; canal real con ADR (D12) |
| 8 | MEDIA | Kaggle (nube) dentro del hito v1 frente a «solo local» | D11: ADR en la FASE 5 antes de subir nada (solo datos públicos); si no se aprueba, la v1 usa la línea base en el Mac |
| 9 | BAJA | TSA externa no funciona sin conexión | REQ-SEC-018: TSA local de prueba en la v1, sin valor probatorio y marcada así; externa con ADR (D10) |
| 10 | MEDIA | Umbrales de NFR-004/005/006 ambiguos (valor puntual o IC) | Criterio conservador con límites del IC al 95 %; «no concluyente» si solo cumple el valor puntual; Wilcoxon pareado con α = 0,05 |
| 11 | MEDIA | REQ-FUN-028 permitía cortes registrados | «0 cortes en 8 h» |
| 12 | BAJA | REQ-NFR-010 no demostraba los modos nocturno y de contraste | e2e de ambos modos y test de tamaño táctil |
| 13 | BAJA | REQ-FUN-043 sin umbral; REQ-LEG-006 sin test de consentimiento | Umbral frente a la línea base de prior uniforme y ADR; test de consentimiento añadido |
| 14 | BAJA | Ningún riesgo de categoría hardware | R-25 (nodos en campo), R-26 (Android como nodo) y R-27 (reloj sin PPS) |
| 15 | BAJA | La suma de semanas no cuadraba (32-55 frente a 34-56) | Corregida a 34-56 con el desglose; quitado el «±50 %» |
| 16 | BAJA | REQ-SEC-012 remitía a D4 en vez de D3 | Corregido |
| 17 | MEDIA/BAJA | Licencias de DroneRF y DroneAudioSet, Ceuta y artículos del RGPD sin fuente | Licencias y Ceuta marcadas NO VERIFICADO en SPEC §11; RGPD citado como Reglamento (UE) 2016/679 |
| 18 | ALTA | El filtro legal de `check_spec.py` aceptaba cualquier línea con «no» o «sin» | Sustituido por una **lista blanca de líneas revisadas** (hash de la ruta y la línea): toda mención nueva o modificada falla hasta su revisión humana |
| 19 | ALTA | Los patrones no detectaban interfiere, neutralice, transmite, TX, demodular, DroneID, persistir audio, atribución automática ni datos de pilotos | Patrones ampliados; 9 tests unitarios con esas frases. Los tests encontraron dos fallos del patrón nuevo («interfiere», «neutralice»), que se corrigieron antes del commit |
| 20 | MEDIA | No había mínimos, ni comprobación de secciones y roles, ni validación de «Ver REQ-…» ni correspondencia con el MEGAPROMPT | Añadidos: un MUST por categoría como mínimo, secciones obligatorias, siete roles, categorías de riesgo, todas las referencias REQ en todos los documentos y una tabla de correspondencia de 22 filas (7 legales, 6 principios y 9 NFR) validada |

Limitación que queda: la lista blanca depende de que una persona lea cada línea antes de añadirla. La revisión inicial de las 34 menciones la hizo Claude Code; **el usuario debe revisarla en este STOP** (`scripts/legal_allowlist.txt`).

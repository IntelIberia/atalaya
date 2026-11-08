# Registro de riesgos

Versión 0.1 · 2026-11-08 · Se revisa en cada cierre de fase.

Escala: probabilidad (P) e impacto (I) de 1 (bajo) a 5 (muy alto); severidad = P × I. Responsable: **U** = usuario, **C** = Claude Code.

| ID | Categoría | Riesgo | P | I | Sev. | Mitigación | Resp. | Estado |
|---|---|---|---|---|---|---|---|---|
| R-01 | Técnico | Alcance acústico real menor que el previsto (viento, ruido urbano, levante y poniente en Ceuta) | 4 | 5 | 20 | Campaña de campo (FASE 7) antes de fijar la geometría; fusión multisensor; afirmaciones solo con datos medidos | C/U | Abierto |
| R-02 | Datos | Sin datos de las clases militares (C6/C7) ni de C4 | 5 | 4 | 20 | Síntesis física marcada; equivalentes legales (avionetas, aeromodelos de gasolina); alianzas (Zvook, Brave1, INTA, universidades); métricas NO VERIFICADAS hasta tener datos (REQ-NFR-020) | U | Abierto |
| R-03 | Legal / datos | Licencias de datasets incompatibles con uso comercial (producto cerrado) | 4 | 4 | 16 | `dataset-intake`; aislamiento de los datos de solo investigación; test G-13 | C | Abierto |
| R-04 | Legal | Riesgo legal en RF, audio y datos de pilotos | 3 | 5 | 15 | Restricciones no negociables, hooks y reglas `deny`, DPIA, solo recepción; asesoría jurídica antes de desplegar (R-12) | C/U | Abierto |
| R-05 | Operativo | Fatiga de alarmas y pérdida de confianza de los operadores | 4 | 5 | 20 | Alertas por pista, ISA-18.2, métrica de falsas alarmas por hora, pruebas de usabilidad | C | Abierto |
| R-06 | Seguridad | Ataques a la propia red de sensores (suplantación de nodos, detecciones falsas, Remote ID falsificado, DoS) | 3 | 5 | 15 | mTLS, firmware firmado, detección de anomalías, catálogo de inyección de fallos (F-05 a F-07) | C | Abierto |
| R-07 | Negocio | Dependencia de un solo emplazamiento piloto | 3 | 3 | 9 | Segundo emplazamiento antes de comercializar; hoy ni siquiera hay uno (R-15) | U | Abierto |
| R-08 | Negocio / cumplimiento | ENS y habilitaciones que retrasan las ventas públicas | 4 | 4 | 16 | ENS desde la FASE 0 (`docs/ens/`) | C/U | Abierto |
| R-09 | Reputación / legal | Atribución errónea a un actor o país | 2 | 5 | 10 | Nunca automática; solo analista, con fuente y confianza; nunca pública (REQ-LEG-008, G-11) | C | Abierto |
| R-10 | Recursos | **Presupuesto obligatorio de 0 €**: sin hardware del kit, sin GPU de pago y sin APIs de pago | 5 | 4 | 20 | Hito v1 demostrable a 0 € (SPEC §3.1); puntos de decisión de gasto con ADR (SPEC §8) | U | Abierto |
| R-11 | Recursos | Sin drones ni registro AESA: no se puede medir el rendimiento real | 5 | 4 | 20 | Reproducción en sala claramente etiquetada; dron prestado y registro AESA para el hito v1+ | U | Abierto |
| R-12 | Legal | Sin asesoría jurídica en telecomunicaciones ni en RGPD | 5 | 4 | 20 | Todo en local en la v1; nada publicado; DPIA y ADR legales como borradores para revisión; buscar asesoría antes de desplegar o publicar | U | Abierto |
| R-13 | Negocio | Sin clientes ni contactos en FCSE, prisiones o puertos: riesgo de construir algo que el usuario real no quiere | 4 | 4 | 16 | Validar pronto el informe de avistamiento y el flujo de alerta con un usuario real (FASES 3 y 10); priorizar el contacto antes de la FASE 10 | U | Abierto |
| R-14 | Producto | Usabilidad no validada con operadores reales | 4 | 4 | 16 | Heurísticas y accesibilidad automatizada; pruebas con usuarios en cuanto haya un contacto | U | Abierto |
| R-15 | Negocio | Emplazamiento piloto sin decidir: la geometría y el fondo acústico son desconocidos | 4 | 3 | 12 | Cuatro escenarios simulados; diseño parametrizado | U | Abierto |
| R-16 | Equipo | Una sola persona: la revisión humana de cada STOP es el cuello de botella, y la ausencia de esa persona detiene el proyecto | 4 | 3 | 12 | Fases pequeñas, paquetes de evidencias legibles, CLAUDE.md y planes al día para retomar en cualquier momento | U | Abierto |
| R-17 | Técnico (IA) | La IA comete errores, inventa APIs o versiones o da por hecho lo que no está verificado | 4 | 4 | 16 | Evidencia ejecutable en cada tarea; revisión independiente por subagentes sin contexto; reglas anti-alucinación; marca NO VERIFICADO | C/U | Abierto |
| R-18 | Técnico | El Mac Intel sin GPU es lento para el stack completo, Android Studio y la inferencia | 3 | 2 | 6 | Entrenamiento en Kaggle; modelos ligeros; pruebas pesadas por la noche | C | Abierto |
| R-19 | Herramientas | Límites de GitHub en repos privados (minutos de Actions, code scanning) | 4 | 2 | 8 | CI ligera; pruebas pesadas en local con evidencia (SPEC §10, D3-D4) | C | Abierto |
| R-20 | Técnico | Un único Android: los resultados no se generalizan a otros dispositivos ni micrófonos | 4 | 3 | 12 | Documentarlo como limitación en la model card; probar en más dispositivos cuando los haya | C | Abierto |
| R-21 | Validez | La demostración con altavoz se confunde con capacidad real de detección en campo | 3 | 5 | 15 | Etiqueta obligatoria «reproducción en sala, no vuelo real» en evidencias, dashboard e informes | C | Abierto |
| R-22 | Legal | Espacio aéreo de Ceuta casi todo restringido para pruebas (según el MEGAPROMPT; NO VERIFICADO) | 4 | 3 | 12 | Grabar en zonas permitidas o con autorización (ENAIRE Drones) | U | Abierto |
| R-23 | Gobernanza | Un guardarraíl demasiado amplio bloquea el código defensivo legítimo, y la tentación es desactivarlo | 3 | 3 | 9 | Lista blanca explícita y probada (G-04); cambios en los guardarraíles solo con ADR (SPEC §10, D1) | C | Abierto |
| R-24 | Dependencias | Sin los `.proto` oficiales de SAPIENT ni acceso al harness | 3 | 3 | 9 | Pedirlos al usuario antes de la FASE 1; si no hay, la FASE 1 cierra con SAPIENT bloqueado y documentado | U | Abierto |
| R-25 | Hardware | Nodos en campo: energía (solar y batería insuficientes en invierno), temperatura (calor en cajas IP65), humedad y salinidad (Ceuta), viento sobre los micrófonos, robo y vandalismo | 4 | 4 | 16 | Prueba de banco, *burn-in* de 72 h y reinicio por corte de alimentación antes del campo (plan de pruebas §4); cortavientos; telemetría de batería y temperatura en `NodeStatus` con cobertura degradada si falla | C/U | Abierto (aplica cuando haya hardware) |
| R-26 | Hardware | Android como nodo: Android detiene los servicios en segundo plano (ahorro de batería), el teléfono se calienta y el micrófono procesa el audio (AGC, supresión de ruido) | 4 | 3 | 12 | Servicio en primer plano; test de 8 h sin cortes (REQ-FUN-028); captura con la fuente de audio sin procesar cuando el dispositivo la ofrezca; heartbeat y cobertura degradada si se detiene | C | Abierto |
| R-27 | Hardware | Sincronización de reloj sin GPS PPS (Android, Mac): la deriva impide el TDOA y degrada la fusión temporal | 5 | 3 | 15 | Los nodos sin PPS no participan en TDOA (REQ-FUN-036); deriva medida y publicada | C | Abierto |

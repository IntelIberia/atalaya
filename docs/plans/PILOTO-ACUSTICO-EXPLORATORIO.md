# Propuesta de piloto acústico exploratorio

Versión 0.2 · 2026-11-11 · Estado: **P0 exploratorio local autorizado con condiciones**.
La decisión se registra en `docs/requirements/DECISIONES-USUARIO.md`. No es P0 de FASE 4 ni
autoriza una prueba operativa.

## 1. Propósito y límite

Obtener pronto una demostración local y reproducible de clasificación **dron / no dron** con
audio pregrabado de una fuente admitida tras `dataset-intake`. El primer resultado visible será un
informe HTML local con espectrograma, probabilidad por ventana, decisión del umbral y errores del
conjunto de evaluación. Este experimento mide la viabilidad del flujo de datos y del clasificador;
no acredita alcance acústico, tasa de falsas alarmas en un emplazamiento, seguridad operacional ni
rendimiento de la plataforma completa.

La demostración de la v1 definida en `docs/SPEC.md` §3.1 es posterior: el Android del usuario
procesa sonido reproducido por un altavoz y una alerta llega al dashboard. Debe etiquetarse
«reproducción en sala, no vuelo real». Un vuelo real y un piloto en un emplazamiento requieren
otras fases, permisos y mediciones.

## 2. Puertas antes de ejecutar

Este documento **no** constituye el P0 de la FASE 4 ni adelanta su P6. El usuario pidió empezar
a probar YAMNet y se le comunicó la interpretación de un **P0 limitado** a este carril local y
aislado. Permite preparar código y comprobar una fuente candidata, y descargarla **solo después**
de verificar su licencia original y registrar procedencia, hashes y revisión inicial de privacidad.
El entrenamiento con audio real exige que el intake esté aprobado. No autoriza captura de
micrófono, uso de datos de clientes, nube, integración en Atalaya ni publicación de resultados
operativos. La secuencia ordinaria de FASE 4 conserva sus propias puertas.

Antes de leer un fichero externo, aplicar `.claude/skills/dataset-intake/SKILL.md`:

1. Volver a comprobar **en la fuente original y en la fecha de intake** que los términos cubren
   los datos y el uso previsto. Archivar texto, URL y fecha. Una investigación histórica o la
   etiqueta de un agregador no equivale a licencia verificada. Si hay duda, no ingerir.
2. Registrar autores, versión, URL, origen de cada parte, SHA-256 por fichero y una data card.
   Conservar los datos fuera de Git y versionarlos con DVC y remoto local, o implementar controles
   equivalentes dentro de la autorización aislada. La ruta `evals/frozen/v1` no se crea ni altera
   por este piloto.
3. Inspeccionar una muestra reproducible para voz u otros datos personales y resolver el
   tratamiento en la DPIA antes de usarla. No usar audio de ubicaciones de clientes, grabaciones
   propias ni material cuya procedencia por fichero no pueda determinarse.
4. Pasar una puerta de uso que rechace fuentes desconocidas, restringidas o de licencia
   incompatible. La puerta registra también las fuentes excluidas; no se incorporan a pesos ni
   métricas de producción.

**Candidato para revalidar:** el conjunto de Svanström et al. citado en el proyecto contiene
clips de dron, helicóptero y fondo, por lo que podría aportar positivos y confusores de una misma
fuente. Licencia, cobertura exacta y ausencia de datos personales necesitan evidencia nueva de
intake. El artículo describe clips de 10 s y tres aeropuertos, pero los WAV no aportan un mapa
fiable de vuelo, sesión o emplazamiento por archivo. No se inventarán esos grupos. Una partición
por clip solo podrá emplearse para probar el flujo, marcada **exploratoria, con contaminación entre
particiones no descartada**; no produce una estimación de generalización. Una segunda fuente de
campo solo servirá como evaluación externa tras su propio intake; no se mezclará al azar con la
primera.

## 3. Experimento mínimo en el Mac

- **Entorno:** CPU del Mac Intel, sin GPU de pago, servicios cloud ni subida de datos. Comprobar
  licencia, versión y disponibilidad de rueda para cada dependencia nueva antes de fijarla.
- **Etiquetas:** binario dron / no dron; helicópteros, aeronaves y ruido de fondo se mantienen como
  confusores identificables en el informe. Etiquetas ambiguas se excluyen y se cuentan.
- **Ventanas:** parámetros de muestreo, duración, solape y normalización fijados por configuración
  y guardados junto al modelo. Ningún fragmento de una grabación aparece en dos particiones.
- **Separación:** si la fuente proporciona IDs fiables, agrupar por grabación original y vuelo o
  sesión; si hay suficientes sitios identificados, reservar uno entero para prueba. Detectar
  duplicados exactos y casi duplicados antes de congelar particiones. Con IDs provisionales por
  clip, el flujo permite únicamente una prueba técnica explícita, sin métrica de generalización;
  el informe debe mostrar este límite junto a cada cifra.
- **Modelos:** comparar una referencia simple basada en rasgos espectrales con log-mel más
  clasificador ligero entrenado en CPU. YAMNet con embeddings congelados es opcional, condicionado
  a licencias de pesos/dependencias, ruedas compatibles y tiempo de inferencia. No ajustar el
  umbral ni hiperparámetros usando el conjunto de prueba.
- **Métricas:** matriz de confusión, precision, recall y PR-AUC por grupo y agregadas. Calcular
  falsas alarmas por hora solo sobre duración negativa continua conocida; si no hay suficiente
  duración, marcar la cifra **NO VERIFICADA**. Informar número de vuelos, sitios, horas y clases,
  además de intervalos de incertidumbre cuando los grupos permitan estimarlos.
- **Informe visible:** HTML local generado desde predicciones de prueba, con espectrograma y
  curva de probabilidad por ventana, umbral y casos erróneos. No incrustar audio, identificadores
  personales ni rutas absolutas de los datos. El informe muestra las limitaciones junto a cada
  métrica y no publica un servicio de red.

## 4. Verificaciones y condiciones de parada

| Comprobación | Condición |
|---|---|
| Licencia e intake | Evidencia de fuente original, data card y hashes completos; cualquier duda detiene la ingesta |
| Privacidad | Sin voz identificable ni audio de terceros sin base de uso; nada de datos sensibles en logs o informe |
| Integridad | Manifiesto de datos y entorno reproducible; alterar un byte rompe la verificación |
| Fugas | Duplicado o ventanas del mismo vuelo en train y test provocan fallo, nunca corrección silenciosa |
| Métricas | Predicciones sobre grupos retenidos y umbral fijado en validación; ninguna cifra operativa sin tiempo negativo suficiente |
| Coste y aislamiento | 0 €; todo local; audio y modelos fuera de Git; ningún micrófono activo en esta etapa |

El piloto se detiene si no hay una fuente admisible, si el tamaño impide conservar margen de disco,
si las etiquetas no permiten separar positivos y negativos por grupo, si aparece voz sin una base
de tratamiento resuelta o si la prueba depende de una capacidad aún no construida. Un resultado
negativo también es entregable: informe de causa y datos faltantes, sin modificar umbrales después
de ver el conjunto de prueba.

## 5. Entregables y decisión pendiente

Tras superar sus puertas, el paquete exploratorio incluiría: manifiesto y data card, script de
preparación y split reproducible, configuración/modelo con hash, predicciones retenidas, informe
HTML local y model card con límites. No sustituye `evals/frozen/v1`, la FASE 5, la prueba Android ni
la revisión P6 de ninguna fase. Estimación preliminar: **2–4 jornadas de trabajo efectivo** desde
la autorización y el intake admisible; la verificación de la fuente puede ampliar ese plazo.

**P0 limitado registrado:** se inicia este carril exploratorio aislado con las puertas anteriores.
No se levanta ninguna puerta de FASE 1–4. La elección y el uso de cada fuente externa siguen
condicionados al intake; sin metadatos de agrupación fiables, los resultados se etiquetan como
prueba técnica por clip y no como validación de detección en campo.

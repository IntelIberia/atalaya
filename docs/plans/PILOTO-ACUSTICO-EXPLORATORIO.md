# Propuesta de piloto acústico exploratorio

Versión 0.4 · 2026-11-11 · Estado: **P0 exploratorio aislado autorizado con condiciones**.
La decisión se registra en `docs/requirements/DECISIONES-USUARIO.md`. No es P0 de FASE 4 ni
autoriza una prueba operativa.

## 1. Propósito y límite

Obtener pronto una demostración reproducible de clasificación **dron / no dron** con
audio pregrabado de una fuente admitida tras `dataset-intake`. El primer resultado visible será un
cuaderno de Colab con espectrograma, puntuación por ventana, decisión del umbral y errores del
conjunto de evaluación. Este experimento mide la viabilidad del flujo de datos y del clasificador;
no acredita alcance acústico, tasa de falsas alarmas en un emplazamiento, seguridad operacional ni
rendimiento de la plataforma completa.

La demostración de la v1 definida en `docs/SPEC.md` §3.1 es posterior: el Android del usuario
procesa sonido reproducido por un altavoz y una alerta llega al dashboard. Debe etiquetarse
«reproducción en sala, no vuelo real». Un vuelo real y un piloto en un emplazamiento requieren
otras fases, permisos y mediciones.

## 2. Puertas antes de ejecutar

Este documento **no** constituye el P0 de la FASE 4 ni adelanta su P6. El usuario pidió empezar
a probar YAMNet y se le comunicó la interpretación de un **P0 limitado** a este carril aislado y
aislado. Permite preparar código y comprobar una fuente candidata. La secuencia obligatoria es:
preflight de licencia original, procedencia e identificadores upstream del contenido; descarga
aislada en ruta ignorada por Git o en el almacenamiento temporal de Colab; SHA-256 por archivo,
inspección de datos personales, DVC local y data card;
aprobación explícita del intake; y solo entonces entrenamiento con audio real. La descarga se
detiene si falla el preflight y el entrenamiento si falla cualquier paso posterior. No autoriza captura de
micrófono, uso de datos de clientes, acceso de Colab al repositorio privado, montaje de Drive,
integración en Atalaya ni publicación de resultados operativos. La instrucción posterior del
usuario «continua en el google collab» autoriza subir el cuaderno autónomo y ejecutar allí
únicamente datos públicos cuya licencia original se haya verificado. La secuencia ordinaria de
FASE 4 conserva sus propias puertas.

Antes de leer un fichero externo, aplicar `.claude/skills/dataset-intake/SKILL.md`:

1. Volver a comprobar **en la fuente original y en la fecha de intake** que los términos cubren
   los datos y el uso previsto. Archivar texto, URL y fecha. Una investigación histórica o la
   etiqueta de un agregador no equivale a licencia verificada. Si hay duda, no ingerir.
2. Registrar autores, versión, URL, origen de cada parte, SHA-256 por fichero y una data card.
   Conservar los datos fuera de Git y versionarlos con DVC y remoto local, o implementar controles
   equivalentes dentro de la autorización aislada. La ruta `evals/frozen/v1` no se crea ni altera
   por este piloto.
3. Inspeccionar una muestra reproducible para voz u otros datos personales y resolver el
   tratamiento en la DPIA antes de entrenar. El cuaderno ofrece reproducción y una señal
   auxiliar de YAMNet; la puerta de entrenamiento permanece cerrada hasta revisión humana.
   No usar audio de ubicaciones de clientes, grabaciones propias ni material cuya procedencia
   por fichero no pueda determinarse.
4. Pasar una puerta de uso que rechace fuentes desconocidas, restringidas o de licencia
   incompatible. La puerta registra también las fuentes excluidas; no se incorporan a pesos ni
   métricas de producción.

**Fuente inicial en intake:** el conjunto de Svanström et al. citado en el proyecto contiene
clips de dron, helicóptero y fondo, por lo que podría aportar positivos y confusores de una misma
fuente. El repositorio declara CC0; la tesis de sus autores identifica vídeos visibles de terceros,
pero no documenta si alguno de los WAV procede de ellos. La cadena de derechos por WAV y la ausencia
de datos personales siguen pendientes. La descarga exploratoria de 90 WAV se verificó por hash y
se detuvo la ingesta posterior. El artículo describe clips de 10 s y tres aeropuertos, pero los WAV no aportan un mapa
fiable de vuelo, sesión o emplazamiento por archivo. No se inventarán esos grupos. Una partición
por clip solo podrá emplearse para probar el flujo, marcada **exploratoria, con contaminación entre
particiones no descartada**; no produce una estimación de generalización. Una segunda fuente de
campo solo servirá como evaluación externa tras su propio intake; no se mezclará al azar con la
primera.

**Fuente para dirección de llegada:** el registro original [Fraunhofer IDMT en
Zenodo](https://zenodo.org/records/17525811) declara CC BY 4.0 y ofrece un ZIP de 1,515,112,211
bytes con audio de una matriz de ocho micrófonos y referencias de azimut. Es una línea de
evaluación posterior: se deben validar geometría, sincronización, estructura, hashes y atribución
antes del experimento multicanal. Una matriz única permite estimar dirección; para triangular
posición hacen falta observaciones y geometría adicionales. No se incluye el ZIP en el cuaderno
rápido de clasificación.

**Fuente bloqueada:** la [ficha original de DADS](https://huggingface.co/datasets/geronimobasso/drone-audio-detection-samples)
marca MIT en sus metadatos, pero incluye [Al-Emadi](https://github.com/saraalemadi/DroneAudioDataset/blob/master/LICENSE.md),
que prohíbe usos de seguridad y defensa, y UrbanSound8K, no comercial. Sin procedencia y derechos
compatibles por archivo, DADS queda excluido de descarga, entrenamiento y modelos derivados.
Las grabaciones con micrófono a bordo
también requieren separar el ruido propio del dron del caso de detección desde el perímetro.

## 3. Experimento mínimo en Colab

- **Entorno:** Colab en CPU, sin GPU de pago, Drive montado, conexión al GitHub privado ni subida
  de audio no público. El cuaderno puede alojarse en el Drive personal del usuario; el runtime
  solo recibe el cuaderno autónomo y audio público verificado. Comprobar versiones de dependencias
  en el runtime antes de ejecutar.
- **Etiquetas:** binario dron / no dron; helicópteros, aeronaves y ruido de fondo se mantienen como
  confusores identificables en el informe. Etiquetas ambiguas se excluyen y se cuentan.
- **Ventanas:** parámetros de muestreo, duración, solape y normalización fijados por configuración
  y guardados junto al modelo. Ningún fragmento de una grabación aparece en dos particiones.
- **Separación:** si la fuente proporciona IDs fiables, agrupar por grabación original y vuelo o
  sesión; si hay suficientes sitios identificados, reservar uno entero para prueba. Detectar
  duplicados exactos y casi duplicados antes de congelar particiones. Con IDs provisionales por
  clip, el flujo permite únicamente una prueba técnica explícita, sin métrica de generalización;
  el informe debe mostrar este límite junto a cada cifra.
- **Modelos:** empezar con YAMNet oficial y una regresión logística ligera sobre embeddings
  congelados. Comparar después una referencia de rasgos espectrales sobre el mismo reparto.
  Comprobar licencias de pesos/dependencias y tiempo de inferencia. No ajustar el umbral ni
  hiperparámetros usando el conjunto de prueba.
- **Métricas:** matriz de confusión, precision, recall y PR-AUC por grupo y agregadas. Calcular
  falsas alarmas por hora solo sobre duración negativa continua conocida; si no hay suficiente
  duración, marcar la cifra **NO VERIFICADA**. Informar número de vuelos, sitios, horas y clases,
  además de intervalos de incertidumbre cuando los grupos permitan estimarlos.
- **Informe visible:** gráficos en el cuaderno generados desde predicciones de prueba, con espectrograma y
  curva de probabilidad por ventana, umbral y casos erróneos. No incrustar audio, identificadores
  personales ni rutas absolutas de los datos. Los gráficos muestran las limitaciones junto a cada
  métrica y no publican un servicio de red.

## 4. Verificaciones y condiciones de parada

| Comprobación | Condición |
|---|---|
| Licencia e intake | Evidencia de fuente original, data card y hashes completos; cualquier duda detiene la ingesta |
| Privacidad | Sin voz identificable ni audio de terceros sin base de uso; nada de datos sensibles en logs o informe |
| Integridad | Manifiesto de datos y entorno reproducible; alterar un byte rompe la verificación |
| Fugas | Duplicado o ventanas del mismo vuelo en train y test provocan fallo, nunca corrección silenciosa |
| Métricas | Predicciones sobre grupos retenidos y umbral fijado en validación; ninguna cifra operativa sin tiempo negativo suficiente |
| Coste y aislamiento | Runtime gratuito en CPU; cuaderno autónomo; audio y modelos fuera de Git; ningún micrófono activo en esta etapa |

El piloto se detiene si no hay una fuente admisible, si el tamaño impide conservar margen de disco,
si falta alguna clase, si aparece voz sin una base de tratamiento resuelta o si la prueba depende
de una capacidad aún no construida. Sin grupos de vuelo/sesión/sitio fiables se detiene la
**evaluación de generalización** y cualquier métrica operativa; tras aprobar el intake puede
ejecutarse una prueba técnica por clip expresamente rotulada, sin interpretar sus cifras como
rendimiento independiente. Un resultado negativo también es entregable: informe de causa y datos
faltantes, sin modificar umbrales después de ver el conjunto de prueba.

## 5. Entregables y decisión pendiente

Tras superar sus puertas, el paquete exploratorio incluiría: manifiesto y data card, script de
preparación y split reproducible, configuración/modelo con hash, predicciones retenidas, gráficos
en Colab y model card con límites. No sustituye `evals/frozen/v1`, la FASE 5, la prueba Android ni
la revisión P6 de ninguna fase. Estimación preliminar: **2–4 jornadas de trabajo efectivo** desde
la autorización y el intake admisible; la verificación de la fuente puede ampliar ese plazo.

**P0 limitado registrado:** se inicia este carril exploratorio aislado con las puertas anteriores.
No se levanta ninguna puerta de FASE 1–4. La elección y el uso de cada fuente externa siguen
condicionados al intake; sin metadatos de agrupación fiables, los resultados se etiquetan como
prueba técnica por clip y no como validación de detección en campo.

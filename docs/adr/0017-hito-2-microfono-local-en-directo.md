# 0017 — Hito 2: micrófono del Mac en directo, solo en memoria, para la demo del piloto acústico

- Estado: aceptado por el usuario (2026-11-16, «Si, yo doy el visto bueno a todo»); revisiones `legal-guardrail-reviewer` y `privacy-reviewer` pendientes antes de H2.7 (captura)
- Fecha: 2026-11-16
- Decisores: usuario (aprobado 2026-11-16); Claude Code (redacción)

## Contexto
El usuario quiere una demo local en directo (plan `docs/plans/HITO-2.md`): el Mac escucha con su
micrófono mientras se reproducen por un altavoz vídeos con sonido de drones, y una página en
`localhost` muestra la alerta. Decisiones ya tomadas por el usuario: 0 €, solo local, sin drones
reales, el sonido solo en memoria (inferencia y descarte inmediato), alerta en página local y
aislado del producto, como el piloto (`pilots/`).

Hasta ahora el piloto prohibía expresamente el micrófono (`docs/plans/PILOTO-ACUSTICO-EXPLORATORIO.md`
§2 y ADR 0016). Abrirlo en el Mac es un cambio de alcance con efecto en privacidad, y añade
dependencias estructurales al piloto: captura de sonido, inferencia ONNX en CPU y la conversión de
YAMNet a ONNX en Colab. Requisitos afectados: REQ-LEG-005, REQ-LEG-006, REQ-PRIV-002, REQ-PRIV-003,
REQ-PRIV-006, REQ-PRIV-010, REQ-NFR-015, REQ-NFR-016, REQ-LEG-009, REQ-LEG-016 y, como antecedente
del demostrador v1, REQ-FUN-057.

Hecho técnico que condiciona el diseño (evidencia de la iteración 5, rama `piloto/iteracion-5`,
cifras transcritas a mano): YAMNet + regresión logística separa bien dentro de las fuentes vistas,
pero en leave-one-source-out el recall en ITU ARIS es ≈ 0 y las falsas alarmas en FSD50K llegan al
52 %. Un micrófono de portátil captando un altavoz es otra fuente nueva: sin normalización y aumento
de canal, lo esperable es que la demo falle por el mismo atajo de dominio.

## Opciones consideradas
1. **Captura en Python con `sounddevice` (PortAudio) + YAMNet en ONNX con `onnxruntime`, en el Mac.**
   Pros: proceso único, control total de la memoria y de los ficheros abiertos, comprobable con tests
   (auditoría de `open`), coherente con MEGAPROMPT `<computo>` («inferencia ONNX en CPU» en el Mac).
   Contras: dos dependencias nuevas con binarios nativos; la rueda x86_64 de macOS de `onnxruntime`
   para la versión elegida está **NO VERIFICADA** (podría obligar a fijar una versión antigua).
2. **Captura en Python + YAMNet con TensorFlow 2.16.2** (ya fijado como extra `yamnet` del piloto).
   Pros: sin conversión; misma implementación que Colab. Contras: instalación de cientos de MB en un
   disco con ~9,8 GB libres y 8 GB de RAM; TensorFlow dejó de publicar ruedas para Mac Intel después
   de 2.16 (NO VERIFICADO en la fecha de este ADR). Queda como alternativa de respaldo.
3. **Captura en el navegador (`getUserMedia`) e inferencia en JavaScript.** Pros: sin dependencias de
   Python para el sonido. Contras: no se puede auditar con los mismos tests qué escribe el proceso;
   duplica la normalización en otro lenguaje; una página con micrófono es más fácil de exponer.
4. **No usar micrófono: inyectar ficheros con licencia en el pipeline.** Pros: sin riesgo de
   privacidad. Contras: no es la demo que pide el usuario y no mide el canal altavoz → micrófono.

## Decisión
Propuesta: opción 1, con la opción 2 como respaldo si T0.1 del plan demuestra que no hay rueda de
`onnxruntime` utilizable en el Mac Intel. Condiciones obligatorias:

- **Alcance:** solo `pilots/acoustic/` (subpaquete `live`, extra opcional `live`), nunca `src/`,
  `edge/` ni el producto. Nada de lo captado sale del proceso ni se envía a Colab.
- **Solo memoria:** búfer circular preasignado; ninguna muestra ni embedding llega a un fichero, a
  un log, a la página ni a la red. Garantía comprobable: análisis estático de importaciones y
  llamadas prohibidas, gancho de auditoría de `open` durante una ejecución completa con fuente
  simulada, `RLIMIT_CORE = 0` y borrado del búfer al parar (tareas H2.7 y H2.8 del plan).
- **Puerta de voz:** las ventanas con voz según YAMNet (umbral 0,30, el mismo del piloto) se
  descartan antes del clasificador y no generan puntuación visible.
- **Página local:** servidor de la biblioteca estándar enlazado solo a `127.0.0.1`, sin recursos
  externos, con CSP y comprobación de `Host`.
- **Reproducción de vídeos:** el sonido llega solo por el aire, desde el altavoz. **No** se
  descarga ni se captura digitalmente audio de YouTube ni de otra plataforma (ToS y derechos de
  autor); herramientas de descarga como `yt-dlp` quedan fuera. De cada vídeo se anotan solo título
  y URL como metadatos del protocolo. Ese material no entra en ningún entrenamiento.
- **Dependencias** (versiones exactas tras T0.1, con licencia leída en la fuente y registrada en el
  plan): `sounddevice` (MIT según PyPI, NO VERIFICADO), su biblioteca PortAudio (licencia tipo MIT,
  NO VERIFICADO), `onnxruntime` (MIT, NO VERIFICADO) en el Mac; `tf2onnx` (Apache-2.0, NO
  VERIFICADO) y `onnx` solo en Colab para convertir YAMNet (Apache-2.0 según TensorFlow Models, NO
  VERIFICADO). Ninguna con copyleft fuerte (REQ-LEG-016). Coste 0 €.

## Consecuencias
- Positivas: primera prueba del canal real altavoz → micrófono sin guardar nada; reutiliza el código
  probado del piloto; el modelo local es un artefacto pequeño (JSON con pesos y hashes) cargado tras
  verificar su SHA-256.
- Negativas: el micrófono abierto en una vivienda capta voces de terceros aunque se descarten; la
  memoria del proceso puede ir a la swap del sistema (macOS la cifra por defecto, NO VERIFICADO en
  este Mac): riesgo residual documentado, no eliminado.
- Riesgos: que la demo «funcione» por memorizar los vídeos o por el volumen y se presente como
  rendimiento real. Mitigación: etiqueta fija «reproducción en sala, no vuelo real», línea base
  (iteración 5) en el mismo protocolo, métricas con IC 95 % y lo no medible marcado NO VERIFICADO.
- Verificación: tests de H2.7–H2.12 del plan en verde (incluidas sus pruebas negativas),
  `make check` en verde, revisión `privacy-reviewer` y `legal-guardrail-reviewer` sin hallazgos
  abiertos y registro de la aprobación en `docs/requirements/DECISIONES-USUARIO.md`.

## Anexo T0.1 — Dependencias del Mac verificadas (2026-11-16)
Leído en los metadatos de las ruedas instaladas (`*.dist-info/METADATA` y ficheros de licencia) y en
el índice de PyPI. Instalación real con `uv sync --extra live --frozen` en el Mac Intel (macOS 15.8.3,
x86_64, Python 3.12).

| Paquete | Versión | Licencia | Motivo |
|---|---|---|---|
| `onnxruntime` | 1.23.2 | MIT | Inferencia ONNX en CPU; última versión con rueda `cp312-macosx_13_0_x86_64` (1.24.x en adelante no la publica) |
| `sounddevice` | 0.5.6 | MIT | Captura de entrada (solo `InputStream`) |
| PortAudio (dentro de `sounddevice`) | V19.7.0-devel | MIT (README de `portaudio-binaries`) | Biblioteca nativa de sonido; las DLL de Windows con ASIO incluidas en la rueda no se cargan en macOS |
| `cffi` | 2.1.1 | MIT-0 | Dependencia de `sounddevice` |
| `pycparser` | 3.12 | BSD-3-Clause | Dependencia de `cffi` |
| `coloredlogs` / `humanfriendly` | 15.0.1 / 10.0 | MIT | Dependencias de `onnxruntime` |
| `flatbuffers` | 25.12.19 | Apache-2.0 | Dependencia de `onnxruntime` |
| `protobuf` | 4.25.9 | BSD-3-Clause | Dependencia de `onnxruntime` |
| `sympy` / `mpmath` | 1.14.0 / 1.3.0 | BSD | Dependencias de `onnxruntime` |

Ninguna con copyleft (REQ-LEG-016). Incremento medido del entorno: 128 MB (257 412 kB → 388 120 kB
con `du -sk .venv`), dentro del presupuesto de 300 MB. El extra `live` no arrastra TensorFlow.
`onnxruntime` figura también en el grupo `dev` para que los tests del cargador (H2.6) ejecuten un
ONNX diminuto real; `tf2onnx` y `onnx` siguen siendo solo de Colab (sus licencias, NO VERIFICADO).

---
description: "Da de alta un dataset o fuente de datos de terceros con licencia verificada, hash, procedencia, data card y análisis de fugas. Obligatoria antes de usar cualquier dato externo."
---
# Intake del dataset: $ARGUMENTS

1. **Licencia:** localiza la licencia en la fuente original (no en agregadores) y archiva su texto y
   URL con fecha en `ml/datasets/<id>/LICENSE-fuente.txt`. Clasifica: comercial OK / solo investigación /
   desconocida. Desconocida o no comercial ⇒ `production_allowed: false` (REQ-LEG-009).
2. **Procedencia:** URL, versión, fecha de descarga, autores, artículo; origen de cada parte si es un
   agregado (p. ej. DADS). Audio OSINT de conflictos ⇒ `osint_conflict: true`, nunca producción.
3. **Integridad:** SHA-256 por fichero en un manifiesto; versión con DVC. Nunca en git.
4. **Datos personales:** ¿hay voz, personas, matrículas? Si sí: evaluar en la DPIA antes de usar.
5. **Fugas:** duplicados exactos y casi duplicados (huella acústica) entre particiones; mismo vuelo,
   sesión o emplazamiento en varias particiones ⇒ reparticionar por sesión/emplazamiento.
6. **Distribución** de clases (C1-C9) y revisión manual de una muestra aleatoria con semilla registrada.
7. **Data card** en `docs/data-cards/<id>.md` con todo lo anterior y las limitaciones.
8. Nada de esto se marca como hecho sin la salida real de los comandos.

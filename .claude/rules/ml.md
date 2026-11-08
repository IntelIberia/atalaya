---
paths:
  - "ml/**"
  - "evals/**"
---
# Regla de ML y datos

- **No toques `evals/frozen/`**: es inmutable y se verifica por hash antes de cada evaluación.
- Todo dataset entra por la skill `/dataset-intake` (licencia, hash, data card, procedencia, fugas).
  Lo no comercial o sin licencia verificada nunca entra en particiones de producción (REQ-LEG-009).
- Divisiones por **sesión y emplazamiento**, nunca por clip.
- Métricas: precisión, recall, F1, falsas alarmas por hora, DET y calibración, con IC al 95 % y
  recalculadas por un segundo script independiente. Siempre frente a la línea base anterior.
- Entrenamiento: script reproducible (semilla, versión DVC, contenedor, MLflow). Nunca notebooks sueltos.
  Nada de entrenar modelos grandes en el Mac Intel. A la nube solo datos públicos (ADR previo).
- La síntesis física (C6/C7) se marca `synthetic=true` y nunca se presenta como rendimiento real.

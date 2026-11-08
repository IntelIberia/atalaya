---
paths:
  - "edge/**"
---
# Regla de borde (nodos)

- **El audio nunca toca disco.** Búfer circular solo en memoria; inferencia por ventanas; el audio se
  descarta tras inferir (REQ-LEG-005, REQ-PRIV-002). Nada de `open(..., "wb")`, `soundfile.write`,
  `wave.open(..., "w")` ni ficheros temporales con audio.
- Del nodo solo salen detecciones, puntuaciones, marcas de tiempo, estado y características agregadas
  que **no permiten reconstruir** el audio (REQ-PRIV-010).
- La grabación para entrenamiento solo existe en el modo «sesión autorizada» (REQ-LEG-006).
- Cada nodo publica heartbeat cada 30 s y su estado (reloj, PPS, modelo) para que la cobertura degradada
  sea visible (REQ-FUN-061).
- Test obligatorio: sistema de ficheros de solo lectura + espía de `open`/`write`.

---
paths:
  - "edge/rf-presence/**"
  - "edge/adsb/**"
  - "edge/esp32-remoteid/**"
---
# Regla de radiofrecuencia: SOLO RECEPCIÓN

- Ningún camino de transmisión: ni `tx`, ni sinks de GNU Radio, ni `writeStream`, ni inyección de
  tramas Wi-Fi, ni anuncios BLE en el ESP32 (REQ-LEG-002). El guardarraíl lo bloquea.
- RF pasiva: solo energía, espectrogramas y características de presencia, **sin demodular** (REQ-LEG-003).
- Remote ID: solo mensajes estándar (ASTM F3411 / EN 4709-002) con OpenDroneID. Los campos de piloto
  y operador se marcan `FCSE_ONLY` **en el propio nodo**.
- Las pruebas de Remote ID usan tramas grabadas o vectores de referencia: nunca se emite Remote ID.

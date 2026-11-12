# 0012 — Semántica de equivalencia del replay en la FASE 1

- Estado: aceptado
- Fecha: 2026-11-10
- Decisores: usuario (aprobación P0), Codex (verificación e implementación)

## Contexto
El motor de seguimiento real se implementa en la FASE 9. En la FASE 1 se necesita comprobar que la
semilla produce una secuencia reproducible y que la salida MQTT equivale a reproducir el archivo.

## Opciones consideradas
1. Exigir equivalencia de salidas del tracker aún no implementado: no verificable en esta fase.
2. Definir la equivalencia inicial sobre eventos serializados y pistas de verdad terreno, y comprobar
   el tracker real cuando exista.

## Decisión
En FASE 1, mismo escenario y semilla deben producir la misma secuencia ordenada de eventos del
simulador y de verdad terreno. La comparación de resultados del tracker se realizará en FASE 9 y no
se declara satisfecha aquí.

## Consecuencias
- Positivas: determinismo y replay se prueban desde el primer contrato.
- Negativas: esta fase no prueba todavía la equivalencia del tracker.
- Verificación: dos procesos independientes, hashes iguales y comparación elemento a elemento de
  la secuencia en vivo frente al replay MQTT.

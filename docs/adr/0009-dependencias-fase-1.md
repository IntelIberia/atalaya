# 0009 — Dependencias y generación de contratos de la FASE 1

- Estado: aceptado
- Fecha: 2026-11-10
- Decisores: usuario (aprobación P0), Codex (verificación e implementación)

## Contexto
La FASE 1 necesita Protobuf, generación de bindings, validación de escenarios, compresión de replay y
MQTT. El equipo de desarrollo es un Mac Intel con Python 3.12 y presupuesto de 0 €. La compatibilidad
de wheels, licencia y mantenimiento debe comprobarse antes de fijar cada versión.

## Opciones consideradas
1. Escribir bindings a mano: duplica el contrato y permite deriva.
2. Generar desde `.proto` con versiones fijadas y comprobar que la salida no deriva: reproducible y
   verificable.
3. Incorporar dependencias sin comprobar wheels/licencias: acelera el inicio, pero puede introducir
   costes o bloquear el entorno.

## Decisión
Se aprueban las familias `protobuf`, `grpcio-tools`, `types-protobuf`, `zstandard`, `paho-mqtt`,
`jsonschema` y `types-jsonschema`, sujetas a comprobación de versión vigente, licencia, mantenimiento
y wheel para macOS x86_64 antes de incorporarlas. `grpcio-tools` aporta `protoc`; los bindings
generados se versionan, con una tarea que vuelve a generarlos y verifica que no hay diff. No se cambia
la plataforma de ejecución ni el presupuesto de 0 €.

## Consecuencias
- Positivas: contrato único, bindings reproducibles y compatibilidad local comprobable.
- Negativas: actualizaciones de `protoc` pueden cambiar la salida; la versión del compilador debe
  quedar anotada y actualizarse conscientemente.
- Verificación: T1.1 fija versiones con `uv.lock`, `make doctor` informa `protoc` y el test de deriva
  exige una generación limpia.

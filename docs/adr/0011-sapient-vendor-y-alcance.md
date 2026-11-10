# 0011 — SAPIENT: fuente, verificación y alcance del gateway

- Estado: aceptado
- Fecha: 2026-11-10
- Decisores: usuario (aprobación P0), Codex (verificación e implementación)

## Contexto
La interoperabilidad requiere los contratos publicados de BSI Flex 335 v2.0. El repo Dstl publica
los `.proto` con Apache-2.0. El harness de conformidad oficial no puede ejecutarse en el Mac Intel
disponible. Los archivos incluyen tipos que podrían representar tareas a efectores.

## Opciones consideradas
1. Escribir tipos SAPIENT a mano o modificar los originales: crea divergencia con la fuente oficial.
2. Copiar los `.proto` oficiales sin cambios, fijar el commit y hashes y generar bindings.
3. Declarar conformidad por pruebas unitarias locales aunque el harness no se haya ejecutado.

## Decisión
Se adopta la opción 2 desde `dstl/SAPIENT-Proto-Files`, conservando licencia y avisos. Si un tipo
importado necesita generar bindings de `task.proto`, estos pueden generarse, pero el `sapient-gateway`
no construye, ejecuta ni reenvía tareas dirigidas a efectores. Solo se implementan funciones de nodo
de sensor y de fusión, con redacción previa de campos no públicos.

El harness permanece bloqueado como B-07b y NO VERIFICADO hasta ejecutarse en Windows con la versión
requerida de PostgreSQL. Esquema, round-trip y mapeo locales se informan como pruebas parciales y no
cierran REQ-FUN-054.

## Consecuencias
- Positivas: la fuente y la licencia son auditables; no se atribuye conformidad sin la prueba oficial.
- Negativas: REQ-FUN-054 sigue bloqueado hasta disponer de Windows y ejecutar el harness.
- Verificación: hash por fichero, commit de origen registrado, licencia conservada, test que bloquea
  tareas a efectores y trazabilidad en estado B mientras falte el harness.

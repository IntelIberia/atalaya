# 0014 — Bloqueo de guardarraíl en el esquema SAPIENT oficial

- Estado: **propuesto; revisión técnica independiente completada; STOP T1.8 pendiente de revisión jurídica y decisión del usuario**
- Fecha: 2026-11-10
- Decisiones pendientes: revisión jurídica competente y aprobación expresa del usuario

## Contexto

El plan de FASE 1 y el ADR 0011 prevén copiar sin modificaciones los contratos BSI Flex 335 v2.0
publicados por Dstl, fijar su commit y sus hashes, y generar los bindings. La copia fue detenida
antes de entrar en el repositorio: el guardarraíl `offensive-term` devuelve exit 2 para dos líneas
de `registration.proto`. El [expediente de T1.8](../evidence/FASE-1/T1.8-STOP-guardarrail.md)
contiene referencias a las líneas originales, sus hashes, el resultado del control y enlaces al
commit fijado. Los literales y la salida completa permanecen solo en el scratchpad temporal.

El esquema externo enumera tipos de nodo y describe categorías de capacidad para interoperar con
otros participantes de SAPIENT. Esos tipos forman parte del vocabulario del estándar, pero Atalaya
solo puede actuar como nodo de sensor o de fusión y no debe construir, ejecutar ni reenviar tareas
dirigidas a efectores (ADR 0011; REQ-LEG-001). El archivo está importado por el mensaje raíz de
SAPIENT; omitirlo impediría generar ese mensaje sin alterar el esquema oficial.

ADR 0005 permite identificadores completos en su lista blanca únicamente cuando son defensivos,
con justificación y revisión. Las coincidencias actuales describen categorías ajenas a la función
de Atalaya; no justifican ampliar la lista blanca global. La regla legal permanente exige parar y
proponer un ADR cuando un guardarraíl bloquea una fuente considerada legítima.

El `LICENCE.txt` original es un aviso con enlace a Apache-2.0, no el texto íntegro de esa licencia.
Una eventual distribución de los contratos o bindings deberá entregar también una copia completa de
Apache-2.0 y conservar los avisos aplicables, conforme a la
[sección 4 de la licencia](https://www.apache.org/licenses/LICENSE-2.0). Esta obligación se revisará
antes de distribuir; no se añade ningún archivo de terceros mientras T1.8 siga bloqueada.

## Opciones consideradas

1. **Mantener T1.8 bloqueada.** Conserva el límite vigente mientras se revisan el origen, la
   licencia, el alcance de uso y la política de guardarraíles. Retrasa la interoperabilidad.
2. **Evaluar una excepción futura limitada a fuente externa inmutable.** Solo tras aprobación
   explícita y revisión legal, con cambio expreso de ADR 0005 y REQ-SEC-001 y revisión de la
   compatibilidad con REQ-LEG-001: ruta vendorizada exacta, commit fijado, SHA-256 completo del
   archivo, únicamente las dos coincidencias documentadas, sin aceptar cambios de bytes. El
   guardarraíl seguiría inspeccionando todo el resto del árbol. Los bindings generados requerirían
   una revisión separada de sus coincidencias y procedencia antes de considerar cualquier alcance
   adicional.
3. **Reducir el subconjunto de esquemas integrado.** Evitaría incorporar partes no usadas, pero el
   mensaje raíz importa `registration.proto`; esta opción no cumple T1.8 ni ADR 0011 sin un cambio de
   plan aprobado. No se modifica la fuente para hacerla compilar.
4. **Editar el archivo oficial o añadir términos generales a la lista blanca.** Se descarta como
   propuesta: rompería la identidad byte a byte o relajaría el bloqueo en código propio.

## Decisión

**No se aprueba ninguna excepción en este ADR.** T1.8 queda bloqueada. No se han copiado los
`.proto`, generado bindings, cambiado el guardarraíl ni añadido entradas a sus listas blancas.
La revisión técnica independiente confirmó el origen, hashes y bloqueo; no constituye aprobación
jurídica. El usuario, tras la revisión jurídica, debe decidir si la opción 2 es admisible. Una aprobación
futura requeriría primero resolver los cambios de política y el requisito legal indicados, y
delimitar por separado el archivo oficial y cualquier salida generada, con pruebas negativas que
demuestren que un cambio de hash o una coincidencia nueva vuelven a bloquear.

## Consecuencias

- No se declara conformidad SAPIENT ni se marca REQ-FUN-054 como cumplido; B-07b sigue abierto.
- T1.8b y cualquier gateway dependiente de esos bindings esperan la resolución del STOP.
- ADR 0005, REQ-LEG-001 y REQ-SEC-001 permanecen intactos y activos.
- El expediente permite revisar una propuesta concreta sin asumir aprobación legal ni del usuario.

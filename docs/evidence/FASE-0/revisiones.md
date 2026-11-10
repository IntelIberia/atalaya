# Revisiones independientes del relevo

Revisores sin contexto de implementación, solo lectura, siguiendo phase-close y los agentes del repositorio. Sesión 2026-11-09 a 2026-11-10.

| Revisor | Hallazgo | Resolución y comprobación |
|---|---|---|
| Independiente | Consumidor acepta mutación parcial con hashes válidos | valid_report compartido por productor y consumidor. Auditor confirma corrección |
| Independiente | Faltaban cierre y evidencias actuales | Paquete de relevo y CIERRE provisional. La fase permanece abierta |
| Independiente | Planes 1–4 desactualizados, colisiones ADR/riesgos | Registrado en RELEVO. Borradores conservados en sus ramas |
| Auditor de tests | Tests estáticos podían dar por verificado el stack | Generación de evidencias exige ambos JUnit. Smoke real 12/12. Pendiente vincular automáticamente la frescura del JUnit a fuentes y configuración |
| Auditor de tests | Superviviente _decode_5 falsamente equivalente | Test con bytes añadido. Auditor verifica que el mutante se elimina |
| Seguridad y legal | Sensibilidad de campo vecino autoriza JSON compacto público | Parser JSON estructural. Pruebas por clave y descriptor. Revisión de privacidad confirma reproducciones resueltas |
| Privacidad | Primera revisión interrumpida por límite de uso | Segundo intento completado, con informe y validación posterior |
| Privacidad | Parser JSON inicial omitía nombres de campo en valores | Descriptor público bloqueado y privado permitido. Validación independiente posterior OK |
| Privacidad | Teléfonos terminados en ceros omitidos | Excepción restringida a contexto de frecuencia. Reproducción independiente OK |
| Privacidad | Subcadena noreply en correo personal permitida | Excepción anclada al buzón técnico. Reproducción independiente OK |
| Legal | Dos entradas legales delegadas | Conservan política restrictiva. Registro explícito sin fingir aprobación P6 |

La revisión final del conjunto y el análisis individual de los 58 supervivientes permanecen pendientes. Los informes de los revisores corresponden a inspecciones y reproducciones puntuales. Las ejecuciones de make check, smoke y mutación las realizó el agente principal y constan en el paquete.

## Continuación del 10 de noviembre

El cierre exige ahora identidad de la prueba de integración, resultado verde y SHA-256 vigente del smoke, la prueba, conftest, pyproject y configuración Compose. Las pruebas negativas cubren informe vacío, fallido, omitido y obsoleto. El auditor independiente confirmó la corrección con 18 pruebas puntuales. La CI limpia mantiene el recorrido ligero. Un informe obsoleto presente localmente exige ejecutar nuevamente make smoke.

Se ampliaron las pruebas de mutación para límites binarios, diagnóstico JSON, campos vecinos, comentarios YAML y escapes de shell. La clasificación individual actual se registra en revision-supervivientes.md. La aprobación P6 sigue reservada al propietario.

El auditor contrastó los 41 supervivientes por AST y reprodujo un hueco de comodines combinados. Se añadió su regresión y se eliminó el mutante. Los 40 restantes quedan justificados con la corrección de la explicación sobre force_text. No se encontraron otros huecos confirmados.

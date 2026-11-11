# Reubicación de informes de mutación de FASE 1

El 2026-11-11 se detectó que T1.1 y T1.4–T1.6 habían escrito sus informes de mutación en
`docs/evidence/FASE-0/mutacion.json`, aunque FASE 0 estaba cerrada y aprobada. Se restauraron
los seis ficheros del paquete FASE 0 que diferían de la etiqueta `fase-0-cerrada`. Su manifiesto
vuelve a verificar los 45 ficheros del cierre.

Para conservar la procedencia de los resultados posteriores, se extrajeron los bytes exactos de
cada commit de tarea y se archivaron aquí:

| Tarea | Commit fuente | Archivo archivado | SHA-256 |
|---|---|---|---|
| T1.1 | `5a5313e` | `mutacion-T1.1-historica.json` | `8e57b96228d0902effa019407a5cfebb650d35465f50f51f23da746c32af610f` |
| T1.4 | `ca5634b` | `mutacion-T1.4-historica.json` | `bd0caf574fddcf746bcf27e95964db811c101fb2f248ad0a2a4d07fb23d56290` |
| T1.5 | `bd65487` | `mutacion-T1.5-historica.json` | `9ed8b0a47934d1e928fa6d2e6570182a6ff76e214b131279638b57a9344f1256` |
| T1.6 | `069a4c7` | `mutacion-T1.6-historica.json` | `e261f55ba1fa507c997222bb735b3770599f8d45c7fff18bda65d59db76f0496` |

Cada informe mide **solo** `scripts/guardrails.py`: 573 mutantes detectados de 622 (92,12 %).
Estos informes son históricos y sus hashes de inputs corresponden al código y los tests de su
respectivo commit. No acreditan la mutación de `validate.py`, `redact.py` ni de la proyección de
logs. El informe vigente de FASE 1 está en `mutacion.json` y mide los cuatro módulos críticos
actuales; SHA-256 del informe: `8af6a30d86fa28e2661a8927f9c94b22792974ec33c31588270214cdb6305287`;
`inputs_sha256`: `ec68558f5e93407e4908671b4bbbd8dc2c86ccb52fc4103a45b0da83a855ecef`.
El test de actualidad y `make mutation` seleccionan la fase activa; la regresión de FASE 0
comprueba el manifiesto del paquete aprobado sin reescribirlo.

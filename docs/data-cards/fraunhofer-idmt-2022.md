# Data card: Fraunhofer IDMT, audio real multicanal de 2022

**Estado (2026-11-11): candidato para dirección de llegada; no descargado ni
aprobado para entrenamiento, evaluación o producción.**

La [fuente original en Zenodo](https://zenodo.org/records/17525811) / [API del
registro](https://zenodo.org/api/records/17525811) identifica a Ximei Yang y
Joerg Bitzer, publicación de 2025-11-04 y licencia **CC BY 4.0**. La licencia
permite usos comerciales con atribución y cumplimiento de sus condiciones; el
intake de privacidad, estructura y atribución aún no está hecho. El único archivo
publicado, `MicArrayData30s.zip`, tiene **1.515.112.211 bytes** y MD5 declarado
`fd8cfda2d852e351b2d33e1ae9a5aba4`. No se ha verificado localmente su hash.

Según la descripción del registro, la captura se hizo en Berne (Alemania) en
agosto de 2022 con una matriz cúbica de **ocho micrófonos**, lado **15 cm**,
ejes `x` norte y `z` arriba. Selecciona ocho vuelos fiables, unos 106 minutos
en total, cortados en fragmentos de 30 s, con coordenadas y azimut de referencia
en `DOATruePos.csv`. El [repositorio asociado de los autores](https://github.com/SOUNDS-RESEARCH/DroneSynthesis2DOA)
describe la copia de Zenodo como **preprocesada** y la evaluación como solo
azimut. Por eso la existencia de canales crudos, la sincronización real y la
geometría por fichero deben comprobarse dentro del ZIP antes de ejecutar DOA.

**Puerta de uso:** descarga aislada solo tras planificar espacio y verificar
licencia/atribución; comparar el MD5 publicado y calcular SHA-256 por fichero;
inspeccionar estructura, canales, tiempos, coordenadas, privacidad y sesiones;
registrar DVC y muestra con semilla. Mantener `intake_approved=false`,
`training_allowed=false`, `production_allowed=false`. No incluir este ZIP en el
cuaderno rápido de clasificación YAMNet. Una sola matriz puede estimar dirección;
no proporciona por sí sola triangulación de posición.

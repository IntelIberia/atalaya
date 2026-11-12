# 0016 — Google Colab como entorno del piloto acústico exploratorio

- Estado: aceptado
- Fecha: 2026-11-11
- Decisores: usuario (DECISIONES-USUARIO.md, 2026-11-11: «continua en el google collab» y autorización explícita de las puertas de la prueba técnica); Claude Code

## Contexto
ADR 0004 fija presupuesto 0 € y ejecución **solo local**; cualquier uso de la nube exige un ADR. El
piloto acústico exploratorio (`docs/plans/PILOTO-ACUSTICO-EXPLORATORIO.md`) necesita TensorFlow y
YAMNet, que no son prácticos en el Mac Intel de 8 GB, y el usuario pidió continuar en Colab. Este
ADR regulariza el uso que ya se hizo los días 2026-11-11 (hallazgo de la auditoría del relevo).
Requisitos afectados: REQ-NFR-015, REQ-NFR-016, REQ-PRIV-009, REQ-LEG-009.

## Opciones consideradas
1. **Solo local**: coherente con ADR 0004, pero TensorFlow/YAMNet en el Mac Intel es lento y frágil.
2. **Colab gratuito (CPU), cuaderno autónomo, solo datos públicos con licencia verificada**.
3. **GPU de pago** (Colab Pro, RunPod): contradice el presupuesto de 0 €.

## Decisión
Opción 2, con estas condiciones obligatorias:
- Runtime gratuito en CPU; sin Drive montado en el runtime, sin acceso al GitHub privado, sin
  credenciales, sin micrófono.
- Solo se ejecuta el cuaderno generado por `pilots/acoustic/build_colab.py` (código probado e
  incrustado tal cual) y solo con datos públicos cuya licencia original se haya verificado.
  **Nunca** audio de clientes, de emplazamientos ni grabaciones propias (REQ-PRIV-009).
- El cuaderno puede guardarse en el Drive personal del usuario; el audio vive solo en el
  almacenamiento temporal del runtime.
- Las cifras obtenidas son **prueba técnica**: no son métricas de producto ni entran en `evals/frozen`.

## Consecuencias
- Positivas: iteración rápida y gratuita sobre YAMNet; el usuario puede ver los resultados.
- Negativas: dependencia de un servicio externo cuyas condiciones y versiones cambian
  (TensorFlow 2.21 en Colab frente a 2.16 fijado en local); resultados no reproducibles bit a bit.
- Verificación: el test `test_notebook_gates_open_only_for_documented_technical_test` exige la
  decisión documentada junto a cada puerta; las evidencias de cada ejecución se guardan en
  `docs/evidence/piloto-acustico/`. **Pendiente:** generar las métricas por script desde un
  fichero de predicciones exportado del cuaderno, con hash, en vez de copiarlas de la salida.
- Actualización 2026-11-12 (iteración 4): el cuaderno exporta `predicciones.csv` (determinista, con
  SHA-256 impreso y guardado en `modelo_piloto.json`) y `pilots/acoustic/recompute_metrics.py`
  recalcula las métricas de forma independiente verificando ese hash. El pendiente se cierra cuando
  una ejecución real archive el CSV y su recálculo en `docs/evidence/piloto-acustico/`.
- Actualización 2026-11-12 (iteración 5): sin dependencias nuevas; los puntos de control del
  cuaderno viven solo en `/content` del runtime (nunca Drive): sobreviven a un reinicio del kernel,
  no al reciclado de la máquina. `predicciones.csv` amplía columnas (tipo de negativo, puntuaciones
  cruda/Platt/isotónica) y `modelo_piloto.json` lleva hash propio que `recompute_metrics.py --record`
  verifica. Las falsas alarmas por hora del cuaderno son una estimación NO VERIFICADA.

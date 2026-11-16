# 0018 — Criterio de avance del hito 2: LOSO por fuente e independiente de la prevalencia (sustituye a D-6)

- Estado: aceptado por el usuario (2026-11-16, «Aprobar ADR 0018 (Recommended)»); sustituye a la decisión D-6
- Fecha: 2026-11-16
- Decisores: usuario (aprobado 2026-11-16); Claude Code (redacción, a petición del coordinador del hito 2)

## Contexto
El plan del hito 2 (`docs/plans/HITO-2.md`, H2.5) fija como criterio de avance de la iteración 6 la
decisión D-6 (aprobada el 2026-11-16, `docs/requirements/DECISIONES-USUARIO.md`): PR-AUC LOSO en
ITU ARIS ≥ 0,85, recall LOSO en ARIS ≥ 0,50 y FPR LOSO en FSD50K ≤ 0,10. El usuario exige que la
demo «dé la talla» y que el criterio no se rebaje sin ADR. Este ADR **no lo rebaja**: corrige un
error de métrica que hace que la primera condición no mida lo que pretende.

Hechos (recalculados por script desde el `predicciones.csv` exacto de la iteración 5, SHA-256
`8ec5d2281682dd02cb11c3a0d9a74feb59df508325afdaa99a715d39a7c67407`; copia fuera de Git; cálculo con
`sklearn.metrics.roc_auc_score` y `average_precision_score` sobre las filas `esquema = loso`):

| Modelo (iteración 5) | Fuente no vista | Prevalencia de dron | ROC-AUC | PR-AUC | Recall con el umbral |
|---|---|---|---|---|---|
| YAMNet media | ITU ARIS | 0,830 | 0,291 | 0,740 | 0,002 |
| YAMNet media | Svanström | 0,350 | 0,908 | 0,789 | 0,000 |
| YAMNet ventanas + aumento · atención | ITU ARIS | 0,830 | 0,387 | 0,793 | 0,008 |
| MFCC + sonoridad | ITU ARIS | 0,830 | 0,226 | 0,737 | 0,168 |

1. **El PR-AUC depende de la prevalencia.** En ARIS el 83 % de los clips son dron (4 485 de 5 405
   tras la puerta de voz): un clasificador aleatorio ya obtiene PR-AUC ≈ 0,83. Con ROC-AUC 0,29–0,39
   —**peor que el azar**— la iteración 5 obtuvo PR-AUC 0,74–0,79. «PR-AUC ≥ 0,85» en ARIS se puede
   cumplir con un ordenamiento casi aleatorio: no es exigente.
2. **Mide una sola fuente.** El criterio solo mira ARIS y FSD50K; no dice nada de Svanström ni de
   ESC-10, ni de las fuentes de dron que entren por intake (Salford, DroneAudioSet, Yi-KAIST).
3. **En LOSO sin ARIS solo quedaban 28 positivos** (Svanström) en entrenamiento: el pliegue no
   puede medir generalización entre fuentes de dron; hacen falta ≥ 2 fuentes de dron entrenando.
4. **El orden transfiere y el umbral no** (LOSO sin Svanström: ROC-AUC 0,908 con recall 0): por eso
   el criterio debe exigir a la vez ordenamiento (ROC-AUC) y decisión con umbral fijado sin ver la
   fuente.

Requisitos afectados: ninguno de `REQUIREMENTS.md` cambia (el criterio es del hito, no del
producto). Relacionados: REQ-FUN-027 (inferencia por ventanas), REQ-LEG-009 (datos con licencia
verificada), REQ-FUN-057 (antecedente del demostrador).

## Opciones consideradas
1. **Mantener D-6 tal cual.** Pros: ya aprobado. Contras: su primera condición se cumple casi por
   azar en ARIS (prevalencia 0,83), deja fuera fuentes y permite declarar «da la talla» a un
   modelo que no ordena mejor que el azar en la fuente no vista.
2. **D-6 con el PR-AUC normalizado por la prevalencia** (p. ej. PR-AUC − prevalencia, o AUC-PR
   «ganancia»). Pros: cambio mínimo. Contras: sigue mirando solo ARIS; los umbrales normalizados
   son poco intuitivos y no hay referencia publicada para elegirlos (NO VERIFICADO).
3. **Criterio LOSO por fuente, independiente de la prevalencia (elegida).** ROC-AUC (invariante a la
   prevalencia), recall y FPR por fuente retenida con el umbral fijado sin verla, y exigencia de
   ≥ 2 fuentes de dron en entrenamiento. Pros: más exigente, cubre todas las fuentes y se recalcula
   por script independiente. Contras: requiere más fuentes de dron (intake de Salford,
   DroneAudioSet o Yi-KAIST); con una sola fuente de dron extra, el pliegue que la retiene queda con
   pocos positivos.

## Decisión
Se propone sustituir D-6 por el **criterio C-LOSO**, que se aplica al modelo principal
**preinscrito** de la iteración 6 (fijado en el código antes de ejecutar; ninguna otra variante
puede «elegirse» después mirando los resultados LOSO):

Para cada pliegue leave-one-source-out (la fuente retenida nunca se ve en entrenamiento, ni en
calibración, ni para elegir el umbral):

- **(a) Fuentes con dron retenidas** (ARIS, Svanström y cualquier fuente de dron admitida): el
  pliegue solo cuenta si el entrenamiento tiene **≥ 2 fuentes de dron distintas** (las mezclas
  sintéticas no cuentan como fuente); si no, el pliegue es **NO EVALUABLE** y el criterio **no se
  cumple**. Si cuenta: **ROC-AUC ≥ 0,85** y **recall ≥ 0,50** con el umbral elegido en validación
  sin esa fuente. Una fuente retenida **solo de dron** (sin negativos propios: Salford,
  DroneAudioSet, Yi-KAIST) no tiene ROC-AUC definido y se juzga por el recall.
- **(b) FPR ≤ 0,10** sobre los negativos de **cada** fuente retenida (ESC-10, FSD50K y los fondos de
  ARIS y de Svanström), con el mismo umbral.
- Todas las cifras con IC 95 % por grupos (remuestreo de grupos completos); el criterio se juzga
  sobre la estimación puntual y el IC se publica junto a ella.
- Las cifras de D-6 (PR-AUC LOSO ARIS, recall ARIS, FPR FSD50K) se siguen publicando para trazabilidad.
- La **calibración de sitio** (D-7: pocos clips negativos de la fuente retenida para centrar los
  rasgos y ajustar el umbral, apartados del test) se informa como **variante aparte**; nunca
  sustituye a C-LOSO ni cuenta para cumplirlo.
- Si C-LOSO no se cumple, la demo puede seguir rotulada «modelo que no generaliza» y **se itera**
  (decisión del usuario del 2026-11-16), igual que con D-6.

## Consecuencias
- Positivas: el criterio deja de cumplirse por azar en fuentes con prevalencia alta; obliga a
  generalizar entre fuentes de dron, que es lo que necesita el micrófono del Mac (otra fuente
  nueva); se comprueba con `pilots/acoustic/recompute_metrics.py --criterio c-loso`, que no importa
  `acoustic_pilot` ni numpy.
- Negativas: con las cuatro fuentes actuales (una sola fuente de dron además de ARIS) C-LOSO es
  **NO EVALUABLE** en el pliegue sin ARIS y en el pliegue sin Svanström: el cumplimiento depende de
  que el usuario apruebe el uso en la prueba técnica de al menos una fuente de dron más
  (Salford DroneNoise, DroneAudioSet solo-dron o Yi-KAIST; manifiestos en `ml/datasets/`, todos con
  `intake_approved=false`). El cuaderno de la iteración 6 trae esas fuentes **desactivadas** hasta
  esa decisión.
- Riesgos: con pocos grupos por fuente (p. ej. Svanström, grupos provisionales) el IC es ancho;
  ROC-AUC alto con umbral mal trasladado sigue dando recall bajo (por eso se exigen ambos).
- Verificación: el cuaderno de la iteración 6 imprime la tabla C-LOSO y D-6; el recálculo
  independiente debe coincidir en cada cifra; los tests `tests/test_notebook_iter6.py` y
  `tests/test_recompute_metrics_iter6.py` comprueban que el criterio implementado es este.
- Plan: `docs/plans/HITO-2.md` (H2.5) enlaza este ADR; mientras siga «propuesto», D-6 se informa
  también y ninguna de las dos se declara cumplida sin el recálculo independiente.

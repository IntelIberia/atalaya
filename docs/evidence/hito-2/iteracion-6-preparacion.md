# Iteración 6 — preparada el 2026-11-16 (cuaderno sin ejecutar en Colab)

Prueba técnica aislada (ADR 0016, ADR 0017, plan `docs/plans/HITO-2.md` H2.1–H2.5). **Resultados en
Colab: NO VERIFICADOS** hasta ejecutar el cuaderno; nada entra en el producto.

## Cuaderno
- `pilots/acoustic/Atalaya_YAMNet_Colab_iter6.ipynb`, generado por
  `uv run --frozen python build_colab.py --iter6` (celdas en `pilots/acoustic/colab_iter6.py`;
  módulos de `acoustic_pilot/` incrustados literalmente, salvo sus importaciones relativas).
  El SHA-256 del fichero y el hash del código incrustado se registran en `registro-tareas.md` (H2.5)
  y los comprueba `tests/test_notebook_iter6.py` (regeneración byte a byte).
- Modelo principal **preinscrito**: `iter6 · completo (canal + cruzadas + armónico + INLP + DRO)`.
  Variantes de ablación: normalización sola; + canal y cruzadas; + armónico; + INLP. Línea base:
  `iter5 · YAMNet media`, reentrenada en la misma ejecución con su receta.
- Métrica principal: LOSO. Criterio C-LOSO (ADR 0018, **propuesto**) y D-6 como referencia.
- Línea base exacta de la iteración 5 recalculada por script: `linea-base-iter5-c-loso.txt`
  (C-LOSO **NO CUMPLE** y pliegues de ARIS y Svanström **NO EVALUABLES**: una sola fuente de dron
  entrenando; ROC-AUC LOSO ARIS 0,23–0,39).

## Ensayo en seco local (sin TensorFlow ni audio real)
Script fuera del repositorio (`scratchpad/dev/dryrun.py` de la sesión): YAMNet sustituido por
rasgos espectrales deterministas, 107 WAV sintéticos de 5 fuentes (3 con dron), ejecución de todas
las celdas desde los rasgos hasta el final. Para pandas se usó un entorno efímero
(`uv run --frozen --with pandas==2.2.3`), **sin** cambiar `pyproject.toml` ni `uv.lock`.
- Sin errores en LOSO (6 variantes), sgkf5, variante de sitio, resumen y criterio, modelo final,
  exportación y autocomprobación de «Prueba tu audio» (dron → DRON DETECTADO, fondo → NO DETECTADO).
- ONNX: sin `onnxruntime` local, el cuaderno **no** exporta `modelo_hito2.json` ni `yamnet.onnx`
  (fallo cerrado comprobado). Con conversor y sesión sustitutos, exporta el artefacto (30,7 kB,
  ≤ 200 kB), `check_golden` lo reproduce y `SHA256SUMS` verifica todos los ficheros.
- `recompute_metrics.py --record registro_iter6.json --artifact modelo_hito2.json --criterio c-loso`
  coincide con el cuaderno en estado, ROC-AUC, recall y FPR de cada fuente y en D-6.
- Errores encontrados y corregidos antes del commit: índice con tupla en la línea base
  (`y[train]`) y regla C-LOSO para fuentes solo de dron (ROC-AUC no definido: se juzgan por recall).
- **No** es un resultado del modelo: las cifras del ensayo no significan nada.

## NO VERIFICADO (se verifica al ejecutar en Colab)
- Versiones de Colab: `tf2onnx` 1.16.1 (sin dependencias), `onnx` 1.17.0, `onnxruntime` 1.20.1
  con el TensorFlow de Colab; conversión de YAMNet (con su STFT) a ONNX opset 17 y paridad ≤ 1e-4.
- Tiempo total (estimado 1,5–3 h en CPU gratuita) y memoria.
- Fuentes de dron extra (Salford, DroneAudioSet, Yi-KAIST): código listo pero **desactivado**
  (`EXTRA_AUTHORIZATION` en `build_colab.py`); hosts de la CDN de Hugging Face, esquema de los
  parquet de DroneAudioSet y nombres de los miembros del TAR de Yi-KAIST sin comprobar.
- Si el modelo cumple C-LOSO: depende de los datos; con las cuatro fuentes actuales los pliegues
  de ARIS y Svanström serán NO EVALUABLES (hace falta al menos una fuente de dron más).

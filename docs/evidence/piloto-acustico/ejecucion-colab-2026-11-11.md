# Ejecución en Colab del piloto YAMNet — 2026-11-11 23:38

- Cuaderno: `pilots/acoustic/Atalaya_YAMNet_Colab.ipynb` (commit 365bf29, SHA-256 3fc5b20c15672580…), subido a Colab (CPU gratuita, sin Drive) y ejecutado con «Ejecutar todas».
- Puertas abiertas por autorización explícita del usuario (DECISIONES-USUARIO.md, 2026-11-11), solo prueba técnica.
- Entorno: TensorFlow 2.21.0 de Colab; tensorflow-hub 0.16.1; YAMNet `https://tfhub.dev/google/yamnet/1`.

## Resultados (copiados de las salidas del cuaderno)
- Licencia CC0 original verificada por SHA-256; 24 WAV descargados y verificados (42,3 MB).
- Revisión de voz automática (máx. puntuación YAMNet de Speech/Conversation/Narration/Child speech):
  BACKGROUND_006 **0,748** (evento principal «Scrape»), BACKGROUND_015 0,408, BACKGROUND_020 0,301,
  DRONE_022 0,280, BACKGROUND_022 0,268; el resto < 0,17. → **Posible voz en BACKGROUND_006** (pendiente de escucha humana).
- Partición por grupos: train/val/test = 14/5/5 clips, grupos 14/5/5 (provisionales, uno por clip).
- Umbral elegido en validación: 0,7976.
- Test: tn=4, fp=0, fn=0, tp=1 → precision 1,000, recall 1,000, PR-AUC 1,000; IC 95 % por grupo
  NO DISPONIBLE (5 grupos < 10). Falsas alarmas por hora: NO VERIFICADA (10 s < 24 h).

## Lectura
Prueba técnica: demuestra que el flujo descarga→verificación→YAMNet→partición por grupos→umbral en
validación→métricas funciona en Colab. **No** mide precisión: un solo positivo en test. Contaminación
entre particiones no descartada. Nada de esto entra en el producto.

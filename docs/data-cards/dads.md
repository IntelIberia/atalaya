# Data card: DADS, Drone Audio Detection Samples

**Estado (2026-11-11): BLOQUEADO para Atalaya. No descargado, entrenado ni
incorporado a pesos o métricas.**

La [ficha del agregador en Hugging Face](https://huggingface.co/datasets/geronimobasso/drone-audio-detection-samples)
marca `mit` en metadatos y enumera 180.320 ejemplos (163.591 dron, 16.729 no
dron), 6,81 GB, WAV mono PCM16 a 16 kHz. Sin embargo, su propia sección
*Licensing* exige verificar las licencias de las fuentes originales para uso
comercial y no comercial. No ofrece aquí una atribución verificable por muestra
ni IDs de vuelo/sesión que garanticen particiones independientes.

La fuente positiva [DroneAudioDataset de Sara Al-Emadi](https://github.com/saraalemadi/DroneAudioDataset/blob/master/LICENSE.md)
tiene una licencia de investigación académica que **prohíbe expresamente usos
militares, de defensa, inteligencia y seguridad**, incluso no comerciales, y
exige permiso separado para uso comercial. La fuente negativa
[UrbanSound8K](https://urbansounddataset.weebly.com/) declara **CC BY-NC 3.0**
y limita el uso a fines no comerciales. La ficha DADS enumera además el
*SPCup19 Egonoise Dataset*, grabado con micrófono a bordo; esas señales de ruido
propio no representan necesariamente la detección desde un sensor de perímetro.

La etiqueta MIT del agregado no sustituye los derechos de los originales ni
elimina estas restricciones. La segregación hipotética de fuentes tampoco basta
sin trazabilidad de cada muestra. Para levantar el bloqueo harían falta derechos
compatibles por origen y por archivo, separación verificable de material
restringido, revisión de privacidad y un intake nuevo con hashes, DVC, sesgos
y particiones por grabación. Hasta entonces `intake_approved=false`,
`training_allowed=false`, `production_allowed=false`.

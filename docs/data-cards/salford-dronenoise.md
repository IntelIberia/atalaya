# Data card: DroneNoise Database (Universidad de Salford)

**Estado (2026-11-11): preflight de licencia e inventario; sin audio en el Mac.**
`intake_approved=false`, `training_allowed=false`, `production_allowed=false`,
`generalization_eval_allowed=false` en [`manifest.json`](../../ml/datasets/salford-dronenoise/manifest.json).

## Fuente y licencia

- Autores: Carlos Ramos Romero, Antonio J. Torija Martínez, Nathan Green, César Asensio.
  Proyecto DroneNoise (EPSRC).
- Registro original: [Figshare institucional de Salford](https://salford.figshare.com/articles/dataset/DroneNoise_Database/22133411),
  DOI [10.17866/rd.salford.22133411.v3](https://doi.org/10.17866/rd.salford.22133411.v3), versión 3.
- Licencia **CC BY 4.0**, verificada hoy en la API del registro (`license.name = "CC BY 4.0"`).
  Uso comercial permitido, sin restricción de campo; exige atribución con la cita del registro.
  Texto legal y SHA-256 en [`LICENSE-fuente.txt`](../../ml/datasets/salford-dronenoise/LICENSE-fuente.txt).
- El registro USIR enlazado devolvió HTTP 403 a la consulta automática: **NO VERIFICADO**.

## Origen e inventario

Campaña en campo en Edzell (Escocia) el 17-08-2022, solo sobrevuelos y estacionarios.

| Parte | Ficheros | Notas |
|---|---|---|
| WAV de vuelo `Ed_*` | 165 | 20 eventos × 9 micrófonos (M1–M9), con anomalías abajo |
| Calibración `Calib_Scotland_ch1..9` | 9 | Tono de calibración; excluidos de entrenamiento |
| `DNM_SQM_FLYO_AESCT.xlsx` | 1 | Métricas psicoacústicas por evento (68.631 bytes) |
| **Total** | **175** | **742.123.543 bytes** |

Hash publicado: MD5 por fichero (Figshare); el SHA-256 lo calcula `fetch.py` en Colab.
La hoja XLSX se descargó al Mac para leer la estructura (SHA-256 en el manifiesto).

Anomalías: `Ed_3p_10_H00_N_C_nw_ev1_M5.wav` aparece dos veces con el mismo MD5 (duplicado
exacto, marcado `training_excluded`); los eventos estacionarios `ev2` y `ev3` de `3p` solo tienen
M5. La hoja tiene pesos que no cuadran con el modelo en algunas filas y direcciones `uw` frente a
`dw` en los nombres: **NO VERIFICADO** qué es correcto.

## Grupos disponibles

El nombre codifica modelo (`3p`, `Fp`, `M3`, `Yn`), altura 10 m, operación (F15 = sobrevuelo a
15 m/s, H00 = estacionario), carga útil, sentido y evento (`ev1`…`ev5`). Por los pesos de la hoja
(249 g, 795 g, 6,3 kg y 1,98 kg con 6 rotores) podrían ser DJI Mini 3 Pro, DJI FPV, DJI Matrice 300
y un hexacóptero Yuneec: **inferencia NO VERIFICADA**. `group_id` = evento (los 9 micrófonos
graban simultáneamente y nunca deben separarse). Para generalización, retener un modelo entero.
**Un solo sitio y un solo día**: no hay retención por emplazamiento posible.

## Datos personales

Grabación en campo abierto: puede haber voces de operadores o personal (**NO VERIFICADO**).
Escucha de una muestra con semilla y revisión DPIA pendientes.

## Limitaciones

- Solo positivos de dron (más calibración); sin tramos de fondo sin dron identificados.
- Cuatro modelos, una altura (10 m), un viento y un día: poca variedad de condiciones.
- Útil para firmas reales de sobrevuelo en tierra, el caso más cercano a Atalaya de los cuatro.

## Puerta de uso

Descarga solo en Colab (`python fetch.py`). Antes de entrenar: SHA-256 traídos al manifiesto,
escucha y privacidad, partición por evento/modelo y aprobación explícita del intake.

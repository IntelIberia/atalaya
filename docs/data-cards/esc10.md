# Data card: ESC-10 (subconjunto CC BY de ESC-50), confusores

**Estado (2026-11-11): preflight de licencia e inventario; sin audio en el Mac.**
`intake_approved=false`, `training_allowed=false`, `production_allowed=false`,
`generalization_eval_allowed=false` en [`manifest.json`](../../ml/datasets/esc10/manifest.json).

## Fuente y licencia

- Autor: Karol J. Piczak, *ESC: Dataset for Environmental Sound Classification*, ACM MM 2015.
- Repositorio original: [karolpiczak/ESC-50](https://github.com/karolpiczak/ESC-50), commit fijado
  `33c8ce9eb2cf0b1c2f8bcf322eb349b6be34dbb6` (HEAD de `master` hoy).
- Verificado hoy en el `LICENSE` del commit: ESC-50 completo es **CC BY-NC 3.0** (no se descarga
  ni se usa); **ESC-10 es CC BY 3.0 Unported**. Cada clip procede de Freesound y el LICENSE da su
  autor y licencia original: en ESC-10 hay 233 CC0, 165 CC-BY y **2 CC Sampling+**. Texto de
  cabecera, las 400 atribuciones y SHA-256 en [`LICENSE-fuente.txt`](../../ml/datasets/esc10/LICENSE-fuente.txt).

## Inventario

| Categoría | Clips | Admitidos | Motivo de exclusión |
|---|---|---|---|
| dog, chainsaw, clock_tick, crackling_fire, helicopter, rain, sea_waves | 40 c/u | 40 c/u | — |
| rooster | 40 | 38 | 2 con licencia original CC Sampling+ (dudosa para uso comercial) |
| sneezing, crying_baby | 40 c/u | 0 | Sonidos de personas (datos personales) |
| **Total** | **400 (176.417.600 B)** | **318 (140.251.992 B)** | |

WAV de 5 s, 44,1 kHz. Hash publicado: Git blob SHA-1 por fichero en el commit fijado; el SHA-256 lo
calcula `fetch.py`. `fetch.py` rechaza cualquier fichero no marcado `esc10=True`.

## Grupos disponibles

`fold` (1–5) del autor, que mantiene juntos los fragmentos del mismo audio de Freesound, y
`freesound_src_file` (304 originales) como `group_id`. No hay sitio ni sesión.

## Datos personales

Grabaciones de terceros de Freesound: perros, gallos o ambientes urbanos pueden llevar voces de
fondo (**NO VERIFICADO**). Escucha de muestra pendiente.

## Limitaciones

- Solo negativos/confusores (helicóptero, motosierra, lluvia, viento de olas…); 5 s por clip.
- Según el README del autor, algunos originales vienen procesados (p. ej. limitados en banda) de
  forma dependiente de la clase: riesgo de atajo.
- Atribución obligatoria por clip en el paquete del producto.

## Puerta de uso

Descarga en Colab (`python fetch.py`, ~140 MB). Antes de entrenar: inventario SHA-256, escucha y
aprobación explícita del intake.

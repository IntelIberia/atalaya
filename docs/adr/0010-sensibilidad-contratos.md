# 0010 — Sensibilidad y validación de contratos

- Estado: aceptado
- Fecha: 2026-11-10
- Decisores: usuario (aprobación P0), Codex (verificación e implementación)

## Contexto
Los contratos Protobuf transportan detecciones y metadatos con niveles distintos de sensibilidad.
Cada campo debe declarar `PUBLIC`, `OPERATOR` o `FCSE_ONLY`; la política de redacción debe considerar
la ruta anidada y aplicar el nivel más restrictivo. El guardarraíl existente busca el literal
`FCSE_ONLY` en campos llamados `pilot_*` u `operator_*`.

## Opciones consideradas
1. Prefijar todos los valores según Buf: requiere cambiar el guardarraíl para reconocer el nuevo
   literal restringido.
2. Usar los valores de dominio aprobados y limitar la excepción Buf a un único archivo de opciones.
3. Eliminar la comprobación del guardarraíl: no aceptable.

## Decisión
Se usan valores `PUBLIC`, `OPERATOR`, `FCSE_ONLY` y `SENSITIVITY_UNSPECIFIED`. Buf puede exceptuar
`ENUM_VALUE_PREFIX` únicamente en `proto/atalaya/v1/options.proto`. No se debilita el guardarraíl.
La sensibilidad efectiva de un campo anidado es el máximo nivel de restricción de su ruta. La
redacción debe ocurrir antes de serializar, publicar o escribir logs, y se valida recorriendo los
descriptores generados.

## Consecuencias
- Positivas: el nombre del nivel legal permanece reconocible para el guardarraíl y la tabla de
  sensibilidad es verificable desde los descriptores.
- Negativas: la excepción localizada de Buf exige una prueba que impida ampliarla a otros ficheros.
- Verificación: meta-test de campos declarados, tabla generada, redaction tests con centinelas y
  escaneo del diff completo.

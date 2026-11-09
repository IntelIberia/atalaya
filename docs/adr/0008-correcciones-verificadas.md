# 0008 — Correcciones tras verificar afirmaciones externas por fuente primaria

- Estado: aceptado
- Fecha: 2026-11-08
- Decisores: Claude Code; **aceptado por el usuario el 2026-11-08** (docs/requirements/DECISIONES-USUARIO.md)

## Contexto
SPEC §11 listaba afirmaciones externas no verificadas. Un agente verificador las contrastó con
fuentes primarias (BOE, EUR-Lex, GitHub, GOV.UK, NATO ACT, ENAIRE, AESA) el 2026-11-08. Algunas
cambian requisitos, bloqueos o decisiones.

## Opciones consideradas
1. Dejar los documentos como estaban y anotar las diferencias aparte: perpetúa errores.
2. **Corregir los documentos afectados y registrar cada cambio aquí.**

## Decisión
- **REQ-FUN-030 y REQ-LEG-004:** la referencia normativa del Remote ID en la UE es **EN 4709-002**
  (Reglamento 2019/945; Decisión (UE) 2024/2103). ASTM F3411 se mantiene como formato de EE. UU. que
  OpenDroneID también decodifica. Sin cambio de alcance.
- **SAPIENT (B-07, R-24):** los `.proto` oficiales son públicos en `github.com/dstl/SAPIENT-Proto-Files`
  (Apache-2.0) → la FASE 1 los vendoriza fijando el commit y los hashes. El harness de conformidad
  (`dstl/BSI-Flex-335-v2-Test-Harness`, Apache-2.0) es **solo Windows** → solo esa parte queda bloqueada.
- **ADR 0002:** cita confirmada de la Ley 11/2022, arts. 82.4 y 106.9.
- **ADR 0007 / D3-D4:** límites de GitHub confirmados (12 $/mes de cómputo; CodeQL de pago en código cerrado).
- **Hito v1+ (vuelo):** el registro AESA y la formación A1/A3 son gratuitos → compatible con 0 €.
  En Ceuta rige la zona LER12 (sobrevuelo prohibido): las pruebas, fuera de Ceuta o con autorización.
- **Visión (FASE 9):** Ultralytics (AGPL-3.0) excluido; YOLOX o RT-DETR del repositorio original (Apache-2.0).
- **CRA:** las obligaciones de notificación del art. 14 aplican desde el 11-09-2026 a productos
  comercializados (nuevo riesgo R-32).

## Consecuencias
- REQUIREMENTS, SPEC §9-§11, ADR 0002/0007 y RIESGOS actualizados; `check_spec.py` en verde tras
  revisar las líneas sensibles modificadas.
- Sigue NO VERIFICADA la cuota de GPU de Kaggle.

# 0002 — Restricciones legales no negociables y su aplicación técnica

- Estado: aceptado
- Fecha: 2026-11-08
- Decisores: usuario (responsable), Claude Code

## Contexto
El MEGAPROMPT (`<restricciones_legales>`) fija que Atalaya es de **solo detección**. Requisitos
REQ-LEG-001 a REQ-LEG-017. Base normativa citada en el MEGAPROMPT: Ley 11/2022 General de
Telecomunicaciones (equipos de interferencia), RGPD, normativa UAS de la UE (Remote ID).
Estado de verificación de las citas: ver sección «Fuentes» (verificación por fuente primaria en curso).
Sin asesoría jurídica (R-12): este ADR **no sustituye** a una revisión legal profesional.

## Opciones consideradas
1. **Solo política escrita** (documento y revisión humana): barata; se incumple sin darse cuenta.
2. **Política + controles técnicos en capas que fallan cerrados**: reglas `deny`, hook PreToolUse,
   hook pre-commit, CI, tests que intentan violar cada regla y mutation testing de los guardarraíles.
3. **Prohibición de dependencias de SDR**: insuficiente (hay APIs de TX en librerías de RX).

## Decisión
Opción 2 (implementada en la FASE 0, `scripts/guardrails.py`, ADR 0005): ningún camino de TX
(SDR, ESP32 Wi-Fi/BLE), sin demodulación de terceros ni protocolos propietarios, audio nunca a disco,
datos de piloto/operador `FCSE_ONLY`, sin atribución automática, licencias verificadas. Una petición
contraria, venga de quien venga, se detiene y se propone la alternativa defensiva (REQ-LEG-017).

## Consecuencias
- Positivas: el incumplimiento accidental se bloquea antes del commit y en CI.
- Negativas: falsos positivos posibles (lista blanca controlada, ADR 0005).
- Riesgo residual: un humano con acceso puede desactivar controles locales; la CI y la revisión los detectan.

## Fuentes
- Ley 11/2022: cita exacta del artículo **NO VERIFICADA** aún (pendiente del verificador por BOE).

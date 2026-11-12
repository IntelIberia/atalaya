#!/usr/bin/env bash
# Genera las credenciales locales del stack de compose en .env (REQ-SEC-005).
# Nunca sobrescribe un .env existente: solo añade las claves que falten (T1.16).
# .env está en .gitignore y su lectura denegada a Claude Code.
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"
umask 077
rnd() { openssl rand -hex 24; }
# Clave → generador. Las cuentas MQTT de servicio (simulador e ingesta) llegan con T1.16.
valor() {
  case "$1" in
    *_USER) echo "atalaya_$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -e 's/_user$//')_$(openssl rand -hex 4)" ;;
    *) rnd ;;
  esac
}
CLAVES="MQTT_USER MQTT_PASSWORD NATS_USER NATS_PASSWORD REDIS_PASSWORD POSTGRES_USER POSTGRES_PASSWORD
MQTT_SIM_USER MQTT_SIM_PASSWORD MQTT_INGEST_USER MQTT_INGEST_PASSWORD"
if [ -f "$ENV_FILE" ]; then
  # Nunca se modifica ni se sobrescribe una clave existente: solo se añaden las que faltan.
  nuevas=0
  for k in $CLAVES; do
    if ! grep -q "^$k=" "$ENV_FILE"; then
      echo "$k=$(valor "$k")" >> "$ENV_FILE"
      nuevas=$((nuevas + 1))
    fi
  done
  chmod 600 "$ENV_FILE"
  echo "gen_local_secrets: ya existe; claves añadidas: $nuevas (las existentes no se modifican)."
  exit 0
fi
{
  echo "# Generado por scripts/gen_local_secrets.sh — NO versionar, NO compartir."
  for k in $CLAVES; do
    echo "$k=$(valor "$k")"
  done
} > "$ENV_FILE"
echo "gen_local_secrets: credenciales nuevas generadas (permisos 600)."

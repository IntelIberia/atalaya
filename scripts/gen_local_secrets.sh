#!/usr/bin/env bash
# Genera las credenciales locales del stack de compose en .env (REQ-SEC-005).
# Nunca sobrescribe un .env existente. .env está en .gitignore y su lectura denegada a Claude Code.
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"
if [ -f "$ENV_FILE" ]; then
  echo "gen_local_secrets: ya existe; no se modifica."
  exit 0
fi
umask 077
rnd() { openssl rand -hex 24; }
{
  echo "# Generado por scripts/gen_local_secrets.sh — NO versionar, NO compartir."
  echo "MQTT_USER=atalaya_$(openssl rand -hex 4)"
  echo "MQTT_PASSWORD=$(rnd)"
  echo "NATS_USER=atalaya_$(openssl rand -hex 4)"
  echo "NATS_PASSWORD=$(rnd)"
  echo "REDIS_PASSWORD=$(rnd)"
  echo "POSTGRES_USER=atalaya_$(openssl rand -hex 4)"
  echo "POSTGRES_PASSWORD=$(rnd)"
} > "$ENV_FILE"
echo "gen_local_secrets: credenciales nuevas generadas (permisos 600)."

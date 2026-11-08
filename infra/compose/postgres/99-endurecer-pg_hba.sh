#!/usr/bin/env bash
# Sin «trust» (REQ-SEC-005): la imagen timescaledb-ha ignora POSTGRES_INITDB_ARGS y deja
# trust en local y loopback. Se ejecuta al final de la inicialización (tras crear extensiones).
set -eu
HBA="${PGDATA:-/home/postgres/pgdata/data}/pg_hba.conf"
sed -i -E 's/[[:space:]]trust[[:space:]]*$/ scram-sha-256/' "$HBA"
if grep -qE '[[:space:]]trust[[:space:]]*$' "$HBA"; then
  echo "endurecer-pg_hba: quedan reglas trust" >&2
  exit 1
fi
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -c "select pg_reload_conf();" > /dev/null
echo "endurecer-pg_hba: OK (sin trust)"

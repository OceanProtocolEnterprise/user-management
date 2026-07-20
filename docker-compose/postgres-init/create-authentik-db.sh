#!/bin/bash
# Runs automatically on FIRST initialization of the postgres data volume.
# Creates a dedicated role + database for authentik alongside the walt.id DB.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE ${AUTHENTIK_PG_USER} LOGIN PASSWORD '${AUTHENTIK_PG_PASS}';
    CREATE DATABASE ${AUTHENTIK_PG_DB} OWNER ${AUTHENTIK_PG_USER};
EOSQL

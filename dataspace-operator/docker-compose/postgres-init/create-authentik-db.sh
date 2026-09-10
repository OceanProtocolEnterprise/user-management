#!/bin/bash
# Runs automatically on FIRST initialization of the postgres data volume.
# Creates a dedicated role + database for walt.id and authentik alongside the walt.id DB.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE ${DB_USERNAME} LOGIN PASSWORD '${DB_PASSWORD}';
    CREATE DATABASE ${DB_NAME} OWNER ${DB_USERNAME};
    CREATE ROLE ${AUTHENTIK_POSTGRESQL__USER} LOGIN PASSWORD '${AUTHENTIK_POSTGRESQL__PASSWORD}';
    CREATE DATABASE ${AUTHENTIK_POSTGRESQL__NAME} OWNER ${AUTHENTIK_POSTGRESQL__USER};
EOSQL
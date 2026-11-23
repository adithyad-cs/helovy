#!/bin/bash
# HIVE DOCS (PS5) — local-only database bootstrap (docs/05 §7.2, docs/06 §11).
#
# Runs once, when the `pgdata` volume is first initialised by the postgres image.
# Creates:
#   - role ps5_migrator: owner of both databases (and so of their `public` schema); used for DDL
#   - role ps5_app:      restricted runtime role; CONNECT and schema USAGE only here.
#                        Table privileges are granted explicitly by each migration (06 §11).
#   - databases ps5 (development/demonstration) and ps5_test (automated tests).
#
# Passwords come from the compose environment and are passed to psql as variables,
# so they are quoted by psql and never appear in this file or in the logs.
set -euo pipefail

: "${PS5_MIGRATOR_PASSWORD:?PS5_MIGRATOR_PASSWORD must be set}"
: "${PS5_APP_PASSWORD:?PS5_APP_PASSWORD must be set}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  --set=migrator_password="$PS5_MIGRATOR_PASSWORD" \
  --set=app_password="$PS5_APP_PASSWORD" <<'EOSQL'
CREATE ROLE ps5_migrator LOGIN PASSWORD :'migrator_password';
CREATE ROLE ps5_app LOGIN PASSWORD :'app_password';

CREATE DATABASE ps5 OWNER ps5_migrator;
CREATE DATABASE ps5_test OWNER ps5_migrator;

REVOKE ALL ON DATABASE ps5 FROM PUBLIC;
REVOKE ALL ON DATABASE ps5_test FROM PUBLIC;
GRANT CONNECT ON DATABASE ps5 TO ps5_app;
GRANT CONNECT ON DATABASE ps5_test TO ps5_app;
EOSQL

for database in ps5 ps5_test; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$database" <<'EOSQL'
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO ps5_app;
EOSQL
done

echo "ps5 init: roles ps5_migrator and ps5_app, databases ps5 and ps5_test created"

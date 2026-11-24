#!/usr/bin/env bash
# One-time setup of a local PostgreSQL server in the GitHub Codespace (used by notebook 05.2).
# Usage (from the repository root):  bash src/setup_postgres_codespace.sh
# After each restart of the Codespace only this is needed:  sudo service postgresql start
# The password below is for local development only. Nothing in this database is secret.
set -e

sudo apt-get update -qq
sudo apt-get install -y -qq postgresql
sudo service postgresql start

# Create the user and the database only if they do not exist yet (safe to run twice)
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname = 'sci'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE USER sci WITH PASSWORD 'sci_alpi'"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'sci_alpi'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE DATABASE sci_alpi OWNER sci ENCODING 'UTF8' TEMPLATE template0"

echo "PostgreSQL is ready: database sci_alpi, user sci, host localhost, port 5432."
echo "Now open notebooks/05.2_postgresql_database.ipynb and choose Run All."

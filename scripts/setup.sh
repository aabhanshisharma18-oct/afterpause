#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
if [[ ! -f .env ]]; then
  secret="$(.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))')"
  (umask 077; printf 'APP_ENV=development\nSECRET_KEY=%s\n' "$secret" > .env)
  echo 'Created .env for the local SQLite quick start. See README for the MySQL setup.'
fi
.venv/bin/flask --app app db upgrade

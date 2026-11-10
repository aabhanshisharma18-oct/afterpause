#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export APP_ENV=demo
.venv/bin/flask --app app db upgrade
.venv/bin/flask --app app seed-demo
echo 'Run APP_ENV=demo bash scripts/dev.sh to explore the demo.'

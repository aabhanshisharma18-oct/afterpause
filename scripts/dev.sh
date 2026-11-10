#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/flask --app app run --host=127.0.0.1 --port="${PORT:-8000}"

#!/bin/sh
set -eu
: "${SECRET_KEY:?Set a persistent random SECRET_KEY of at least 32 characters}"
: "${DATABASE_URL:?Set a mysql+pymysql DATABASE_URL}"
: "${RATELIMIT_STORAGE_URI:?Set a shared Redis URL}"
: "${UPLOAD_DIR:?Set UPLOAD_DIR on a persistent volume}"
export APP_ENV=production
mkdir -p "$UPLOAD_DIR"
test -w "$UPLOAD_DIR" || { echo "UPLOAD_DIR is not writable" >&2; exit 1; }
# One application instance only. With multiple replicas, run migrations once
# as a separate release job and set RUN_MIGRATIONS=0 on all replicas.
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    python -m flask --app app db upgrade
fi
exec gunicorn --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --timeout 60 --access-logfile - --error-logfile - 'app:create_app()'

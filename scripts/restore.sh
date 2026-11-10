#!/usr/bin/env bash
set -euo pipefail
if [[ $# != 4 || ! $1 =~ ^[a-zA-Z0-9_]+_restore$ || $4 != --confirm-restore ]]; then
  echo 'Usage: restore.sh EMPTY_DATABASE_ending_in_restore EMPTY_UPLOAD_DIRECTORY TRUSTED_BACKUP.tar.gz --confirm-restore' >&2
  exit 2
fi
: "${MYSQL_OPTION_FILE:?Set MYSQL_OPTION_FILE to a private MySQL client option file}"
database="$1"
uploads="$2"
archive="$3"
rows="$(mysql --defaults-extra-file="$MYSQL_OPTION_FILE" --batch --skip-column-names "$database" -e 'SHOW TABLES')"
[[ -z "$rows" ]] || { echo 'Restore requires an empty database.' >&2; exit 2; }
mkdir -p "$uploads"
[[ -z "$(ls -A "$uploads")" ]] || { echo 'Restore requires an empty upload directory.' >&2; exit 2; }
staging="$(mktemp -d)"
trap 'rm -rf -- "$staging"' EXIT
umask 077
tar -xzf "$archive" -C "$staging" museum.sql uploads
mysql --defaults-extra-file="$MYSQL_OPTION_FILE" "$database" < "$staging/museum.sql"
cp -R "$staging/uploads"/. "$uploads/"
echo "Database and media restored to $database."

#!/usr/bin/env bash
set -euo pipefail
if [[ $# != 3 || ! $1 =~ ^[a-zA-Z0-9_]+$ ]]; then
  echo 'Usage: backup.sh DATABASE UPLOAD_DIRECTORY DESTINATION.tar.gz' >&2
  exit 2
fi
: "${MYSQL_OPTION_FILE:?Set MYSQL_OPTION_FILE to a private MySQL client option file}"
database="$1"
uploads="$2"
archive="$3"
[[ ! -e "$archive" ]] || { echo 'Choose a new backup destination.' >&2; exit 2; }
[[ -d "$uploads" ]] || { echo 'The upload directory does not exist.' >&2; exit 2; }
staging="$(mktemp -d)"
trap 'rm -rf -- "$staging"' EXIT
umask 077
mysqldump --defaults-extra-file="$MYSQL_OPTION_FILE" --single-transaction --no-tablespaces --set-gtid-purged=OFF "$database" > "$staging/museum.sql"
mkdir "$staging/uploads"
cp -R "$uploads"/. "$staging/uploads/"
tar -czf "$archive" -C "$staging" museum.sql uploads
echo "Backup created: $archive"

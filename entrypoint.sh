#!/bin/sh
set -e

# Wait for the database to accept connections before doing anything that
# touches it. DB_HOST/DB_PORT come from the environment (.env).
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-3306}"

echo "Waiting for database at ${DB_HOST}:${DB_PORT} ..."
while ! nc -z "$DB_HOST" "$DB_PORT"; do
    sleep 1
done
echo "Database is up."

# Apply migrations and collect static files. Both are idempotent and safe to
# run on every container start.
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Hand off to the container's main command (Daphne in prod, runserver in dev).
exec "$@"

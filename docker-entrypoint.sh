#!/bin/sh
set -e

if [ "${RUN_STARTUP_MIGRATIONS:-true}" = "true" ]; then
    echo "Aplicando migraciones..."
    python manage.py migrate --noinput

    echo "Recolectando archivos estáticos..."
    python manage.py collectstatic --noinput
fi

exec "$@"

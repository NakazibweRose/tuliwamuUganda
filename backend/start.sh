#!/usr/bin/env bash
# Container start: migrate, seed fictional demo data once (if enabled), run the web server.
set -o errexit
python manage.py migrate --noinput
if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then python manage.py seed_demo --if-empty && python manage.py upgrade_demo; fi
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --timeout 60

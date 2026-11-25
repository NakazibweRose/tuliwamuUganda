#!/usr/bin/env bash
# Container start: migrate, seed fictional demo data once (if enabled), run the web server.
set -o errexit
python manage.py migrate --noinput
if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  python manage.py seed_demo --if-empty
  # Changing DEMO_RESET_ID on the host wipes all demo activity once and starts clean (accounts kept).
  if [ -n "${DEMO_RESET_ID:-}" ]; then python manage.py seed_demo --reset-id "$DEMO_RESET_ID"; fi
  # Changing CLEAR_ACTIVITY_ID wipes cases, reports, documents and messages once, keeping all accounts.
  if [ -n "${CLEAR_ACTIVITY_ID:-}" ]; then python manage.py clear_activity --once-id "$CLEAR_ACTIVITY_ID"; fi
  python manage.py upgrade_demo
fi
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --timeout 60

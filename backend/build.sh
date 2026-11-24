#!/usr/bin/env bash
# Render build step: install, collect static files, migrate. Seed demo data only when asked.
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then python manage.py seed_demo; fi

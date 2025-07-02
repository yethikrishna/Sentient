#!/bin/sh
set -e

# Optional: load .env for local/dev environments. Do not load for 'stag' or 'prod'.
if [ -f /app/.env ] && { [ "$ENVIRONMENT" = "dev" ] || [ -z "$ENVIRONMENT" ]; }; then
  echo "Loading environment variables from /app/.env"
  set -a
  . /app/.env
  set +a
fi

echo "Container starting... Launching supervisord."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
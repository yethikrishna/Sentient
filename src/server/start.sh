#!/bin/sh
set -e

# Optional: load .env only if not running on Railway
if [ -f /app/.env ] && [ -z "$RAILWAY_ENVIRONMENT" ]; then
  echo "Loading environment variables from /app/.env"
  set -a
  . /app/.env
  set +a
fi

echo "Container starting... Launching supervisord."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
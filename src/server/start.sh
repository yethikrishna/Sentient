#!/bin/sh
set -e

if [ -f /app/.env ]; then
  dos2unix /app/.env
  echo "Loading environment variables from /app/.env"
  set -a
  . /app/.env
  set +a
fi

echo "Container starting... Launching supervisord."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
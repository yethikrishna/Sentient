#!/bin/sh
set -e

# Conditionally load environment variables from /app/.env
# This is for production/staging deployments, not for self-hosting.
if [ "$ENVIRONMENT" != "SELFHOST" ]; then
  if [ -f /app/.env ]; then
    dos2unix /app/.env
    echo "Loading environment variables from /app/.env for $ENVIRONMENT mode."
    while IFS= read -r line || [ -n "$line" ]; do
      case "$line" in
        ''|\#*) continue ;;
      esac
      export "$line"
    done < /app/.env
  fi
fi

echo "Container starting... Launching supervisord."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
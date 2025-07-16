#!/bin/sh
set -e

# This script runs inside the Docker container to start supervisord.
# For self-hosting, environment variables are injected directly by Docker Compose.
# For other environments (dev-cloud, stag), it sources /app/.env.

# Docker Compose for self-hosting sets ENVIRONMENT=selfhost.
# In this case, we MUST NOT source a local .env file, as it would
# overwrite the correct self-host configuration.
if [ "$ENVIRONMENT" = "selfhost" ]; then
    echo "start.sh: Self-host mode detected. Bypassing .env file sourcing."
else
    # This block is for non-selfhost deployments like dev-cloud/stag
    ENV_FILE="/app/.env"
    TEMP_ENV_FILE="/tmp/filtered.env"

    if [ -f "$ENV_FILE" ]; then
        echo "start.sh: Found $ENV_FILE, sourcing variables for supervisord..."
        dos2unix "$ENV_FILE" >/dev/null 2>&1 || true
        grep -v -e '^\s*#' -e '^\s*$' "$ENV_FILE" > "$TEMP_ENV_FILE"
        set -a
        . "$TEMP_ENV_FILE"
        set +a
        rm "$TEMP_ENV_FILE"
    else
        echo "start.sh: WARNING - $ENV_FILE not found. Relying on container's environment."
    fi
fi

echo "start.sh: Launching supervisord for ENVIRONMENT='${ENVIRONMENT:-unknown}'..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf

#!/bin/sh
set -e

# This script runs inside the Docker container to load environment variables
# from a file before starting supervisord. This ensures all supervisord-managed
# processes inherit the same environment.

ENV_FILE="/app/.env"
TEMP_ENV_FILE="/tmp/filtered.env"

if [ -f "$ENV_FILE" ]; then
    echo "start.sh: Found $ENV_FILE, sourcing variables for supervisord..."
    # Ensure Unix line endings for compatibility.
    dos2unix "$ENV_FILE" >/dev/null 2>&1 || true
    
    # Filter out comments and empty lines, and write to a temporary file
    grep -v -e '^\s*#' -e '^\s*$' "$ENV_FILE" > "$TEMP_ENV_FILE"

    # Set the 'allexport' option to export all subsequent variable definitions.
    # Then, source the temporary file.
    set -a
    . "$TEMP_ENV_FILE"
    set +a

    # Clean up the temporary file
    rm "$TEMP_ENV_FILE"
else
    echo "start.sh: WARNING - $ENV_FILE not found. Relying on container's environment."
fi

echo "start.sh: Launching supervisord for ENVIRONMENT='${ENVIRONMENT:-unknown}'..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
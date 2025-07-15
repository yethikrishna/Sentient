#!/bin/bash
#
# ==============================================================================
# start_all_services.sh
# ==============================================================================
#
# SYNOPSIS:
#   Starts all backend services, workers, and the frontend client for the
#   Sentient project on a Linux environment.
#
# DESCRIPTION:
#   This script automates the startup of all necessary services for local
#   development. It launches each service in its own dedicated terminal window
#   with a clear title.
#
# NOTES:
#   - Run this script from the project's root directory.
#   - You might need to install 'gnome-terminal' or change the TERMINAL_CMD
#     variable below to your preferred terminal emulator (e.g., konsole, xterm).
#   - Ensure services like MongoDB and Redis are installed and enabled on your system.
#   - This script may require 'sudo' for starting system services.
#
# ==============================================================================

# --- Configuration ---
# Select your preferred terminal emulator to launch services.
# If you encounter "symbol lookup error" with gnome-terminal (a common issue with Snap),
# try changing this to a different terminal you have installed.
#
# Examples:
# TERMINAL_CMD="xterm -e"
# TERMINAL_CMD="konsole -e"
# TERMINAL_CMD="gnome-terminal --"
TERMINAL_CMD="xterm -e"

# --- Script Body ---
# Exit immediately if a command exits with a non-zero status.
set -e

# --- Helper Functions ---
function check_command() {
    if ! command -v $1 &> /dev/null
    then
        echo "Error: Command '$1' could not be found. Please install it to continue."
        exit 1
    fi
}

function start_in_new_terminal() {
    local title="$1"
    local command="$2"
    # Use printf for better formatting and to avoid issues with echo's -e flag
    printf "🚀 Launching %s...\n" "$title"
    # The `exec bash` at the end keeps the new terminal open after the command finishes or fails.
    $TERMINAL_CMD /bin/bash -c "echo -ne '\033]0;${title}\a'; ${command}; exec bash" &
    sleep 0.5 # Give the desktop environment time to launch the new terminal
}

# --- Pre-run Checks ---
echo "--- Performing Pre-run Checks ---"
check_command systemctl
check_command redis-cli
check_command npm
check_command $(echo "$TERMINAL_CMD" | cut -d' ' -f1) # Check for the chosen terminal

# --- Path and Environment Setup ---
echo "--- Setting up Environment ---"
PROJECT_ROOT=$(pwd)
SRC_PATH="$PROJECT_ROOT/src"
SERVER_PATH="$SRC_PATH/server"
CLIENT_PATH="$SRC_PATH/client"
MCP_HUB_PATH="$SERVER_PATH/mcp_hub"
VENV_ACTIVATE_PATH="$SERVER_PATH/venv/bin/activate"
ENV_FILE="$SERVER_PATH/.env"

if [ ! -d "$SRC_PATH" ] || [ ! -d "$SERVER_PATH" ] || [ ! -d "$CLIENT_PATH" ]; then
    echo "Error: Critical directories (src, src/server, src/client) not found."
    echo "Please ensure you are running this script from the project's root directory."
    exit 1
fi

if [ ! -f "$VENV_ACTIVATE_PATH" ]; then
    echo "Error: Python virtual environment not found at '$VENV_ACTIVATE_PATH'."
    echo "Please create it first inside 'src/server' (e.g., python -m venv venv)."
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at '$ENV_FILE'. Please copy from .env.template."
    exit 1
fi

# Extract Redis password from .env file
REDIS_PASSWORD=$(grep -E "^\s*REDIS_PASSWORD\s*=" "$ENV_FILE" | cut -d '=' -f 2- | tr -d '"\r' | sed 's/^ *//;s/ *$//')
if [ -z "$REDIS_PASSWORD" ]; then
    echo "Error: Could not find REDIS_PASSWORD in '$ENV_FILE'."
    exit 1
fi
echo "✅ Redis password loaded from .env file."

# --- 1. Start Databases & Core Infrastructure ---
echo -e "\n--- 1. Starting Databases & Core Infrastructure ---"

# Start MongoDB Service
echo "🚀 Starting MongoDB Service (may require sudo)..."
sudo systemctl start mongod || echo "MongoDB service was already running or failed to start. Check with: sudo systemctl status mongod"
sleep 1

# Start Redis Server
echo "🚀 Starting Redis Server (may require sudo)..."
if ! pgrep -x "redis-server" > /dev/null; then
    sudo systemctl start redis-server || (echo "Failed to start Redis via systemctl. Check service status." && exit 1)
    echo "Redis service started."
else
    echo "Redis service is already running."
fi
sleep 1

# --- 2. Resetting Queues & State ---
echo -e "\n--- 2. Resetting Queues & State ---"
echo "🚀 Flushing Redis database (Celery Queue)..."
redis-cli -a "$REDIS_PASSWORD" FLUSHALL
echo "✅ Redis flushed."

# --- 3. Start MCP Servers ---
echo -e "\n--- 3. Starting All MCP Servers ---"

if [ ! -d "$MCP_HUB_PATH" ]; then
    echo "Error: MCP Hub directory not found at '$MCP_HUB_PATH'."
    exit 1
fi

MCP_SERVERS=$(find "$MCP_HUB_PATH" -mindepth 1 -maxdepth 1 -type d -exec basename {} \;)
echo "Found the following MCP servers to start:"
echo "$MCP_SERVERS" | sed 's/^/ - /'
echo ""

for server_name in $MCP_SERVERS; do
    window_title="MCP - ${server_name^^}" # Uppercase title
    python_module="mcp_hub.$server_name.main"
    command_to_run="source '$VENV_ACTIVATE_PATH' && cd '$SERVER_PATH' && python -m '$python_module'"
    start_in_new_terminal "$window_title" "$command_to_run"
done

# --- 4. Start Backend Workers ---
echo -e "\n--- 4. Starting Backend Workers ---"

worker_command="source '$VENV_ACTIVATE_PATH' && cd '$SERVER_PATH' && celery -A workers.celery_app worker --loglevel=info --pool=solo"
start_in_new_terminal "WORKER - Celery Worker" "$worker_command"

beat_command="source '$VENV_ACTIVATE_PATH' && cd '$SERVER_PATH' && celery -A workers.celery_app beat --loglevel=info"
start_in_new_terminal "WORKER - Celery Beat" "$beat_command"

# --- 5. Start Main API Server and Frontend Client ---
echo -e "\n--- 5. Starting Main API and Client ---"

main_api_command="source '$VENV_ACTIVATE_PATH' && cd '$SERVER_PATH' && python -m main.app"
start_in_new_terminal "API - Main Server" "$main_api_command"

client_command="cd '$CLIENT_PATH' && npm run dev"
start_in_new_terminal "CLIENT - Next.js" "$client_command"

echo -e "\n✅ All services have been launched successfully in new terminals."
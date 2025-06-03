# polling_service/core/config.py
import os
from dotenv import load_dotenv
from datetime import timedelta

# Load .env from the root of polling_service, one level up from core
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=dotenv_path)

# Polling intervals and thresholds
POLLING_INTERVALS = {
    "ACTIVE_USER_SECONDS": int(os.getenv("POLL_ACTIVE_USER_SECONDS", 60)),
    "RECENTLY_ACTIVE_SECONDS": int(os.getenv("POLL_RECENTLY_ACTIVE_SECONDS", 5 * 60)),
    "PEAK_HOURS_SECONDS": int(os.getenv("POLL_PEAK_HOURS_SECONDS", 15 * 60)),
    "OFF_PEAK_SECONDS": int(os.getenv("POLL_OFF_PEAK_SECONDS", 60 * 60)),
    "INACTIVE_SECONDS": int(os.getenv("POLL_INACTIVE_SECONDS", 2 * 60 * 60)),
    "MIN_POLL_SECONDS": int(os.getenv("POLL_MIN_SECONDS", 30)),
    "MAX_POLL_SECONDS": int(os.getenv("POLL_MAX_SECONDS", 4 * 60 * 60)),
    "FAILURE_BACKOFF_FACTOR": int(os.getenv("POLL_FAILURE_BACKOFF_FACTOR", 2)),
    "MAX_FAILURE_BACKOFF_SECONDS": int(os.getenv("POLL_MAX_FAILURE_BACKOFF_SECONDS", 6 * 60 * 60)),
    "SCHEDULER_TICK_SECONDS": int(os.getenv("POLL_SCHEDULER_TICK_SECONDS", 15)),
}

ACTIVE_THRESHOLD_MINUTES = int(os.getenv("POLL_ACTIVE_THRESHOLD_MINUTES", 10))
RECENTLY_ACTIVE_THRESHOLD_HOURS = int(os.getenv("POLL_RECENTLY_ACTIVE_THRESHOLD_HOURS", 1))
PEAK_HOURS_START = int(os.getenv("POLL_PEAK_HOURS_START", 8))
PEAK_HOURS_END = int(os.getenv("POLL_PEAK_HOURS_END", 22))

SUPPORTED_SERVICES = os.getenv("POLL_SUPPORTED_SERVICES", "gmail").split(',')

# LLM Configs (needed by polling_engine runnables)
BASE_MODEL_URL = os.getenv("BASE_MODEL_URL")
BASE_MODEL_REPO_ID = os.getenv("BASE_MODEL_REPO_ID")
OPENAI_API_URL = os.getenv("OPENAI_API_URL")
CLAUDE_API_URL = os.getenv("CLAUDE_API_URL")
GEMINI_API_URL = os.getenv("GEMINI_API_URL")
OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL") # If used

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Google API (for engines like GmailPollingEngine)
GOOGLE_CLIENT_SECRET_JSON_PATH = os.getenv("GOOGLE_CLIENT_SECRET_JSON_PATH")
GOOGLE_TOKEN_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "google_tokens") # Store user tokens here
os.makedirs(GOOGLE_TOKEN_STORAGE_DIR, exist_ok=True)

# This will be populated in main_server.py after engine classes are defined.
# It maps service names (string) to engine classes (Type[BasePollingEngine]).
SERVICE_ENGINE_MAP = {}
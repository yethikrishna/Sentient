import os
from dotenv import load_dotenv
from datetime import timedelta

# Load .env from the root, which is two levels up from 'utils'
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=dotenv_path)

# Polling intervals and thresholds (simplified for Gmail)
POLLING_INTERVALS = {
    "ACTIVE_USER_SECONDS": int(os.getenv("POLL_GMAIL_ACTIVE_USER_SECONDS", 5 * 60)), # e.g., 5 minutes
    "RECENTLY_ACTIVE_SECONDS": int(os.getenv("POLL_GMAIL_RECENTLY_ACTIVE_SECONDS", 15 * 60)), # e.g., 15 minutes
    "PEAK_HOURS_SECONDS": int(os.getenv("POLL_GMAIL_PEAK_HOURS_SECONDS", 30 * 60)), # e.g., 30 minutes
    "OFF_PEAK_SECONDS": int(os.getenv("POLL_GMAIL_OFF_PEAK_SECONDS", 60 * 60)), # e.g., 1 hour
    "INACTIVE_SECONDS": int(os.getenv("POLL_GMAIL_INACTIVE_SECONDS", 2 * 60 * 60)), # e.g., 2 hours
    "MIN_POLL_SECONDS": int(os.getenv("POLL_GMAIL_MIN_SECONDS", 60)), # e.g., 1 minute
    "MAX_POLL_SECONDS": int(os.getenv("POLL_GMAIL_MAX_SECONDS", 4 * 60 * 60)), # e.g., 4 hours
    "FAILURE_BACKOFF_FACTOR": int(os.getenv("POLL_GMAIL_FAILURE_BACKOFF_FACTOR", 2)),
    "MAX_FAILURE_BACKOFF_SECONDS": int(os.getenv("POLL_GMAIL_MAX_FAILURE_BACKOFF_SECONDS", 6 * 60 * 60)),
    "SCHEDULER_TICK_SECONDS": int(os.getenv("POLL_SCHEDULER_TICK_SECONDS", 30)), # How often scheduler checks due tasks
}

ACTIVE_THRESHOLD_MINUTES = int(os.getenv("POLL_ACTIVE_THRESHOLD_MINUTES", 30)) # User active in last 30 mins
RECENTLY_ACTIVE_THRESHOLD_HOURS = int(os.getenv("POLL_RECENTLY_ACTIVE_THRESHOLD_HOURS", 3)) # User active in last 3 hours
PEAK_HOURS_START = int(os.getenv("POLL_PEAK_HOURS_START", 8)) # 8 AM
PEAK_HOURS_END = int(os.getenv("POLL_PEAK_HOURS_END", 22)) # 10 PM

SUPPORTED_SERVICES = ["gmail"] # Only Gmail is supported now

# LLM Configs - Only if a simple local LLM is used for the dummy chat/voice response.
# Otherwise, these can be removed if responses are hardcoded.
BASE_MODEL_URL = os.getenv("BASE_MODEL_URL") # e.g., http://localhost:11434 for Ollama
BASE_MODEL_REPO_ID = os.getenv("BASE_MODEL_REPO_ID") # e.g., llama3.2:3b

# Google API (Essential for Gmail PollingEngine)
# Path to client_secret.json (downloaded from Google Cloud Console)
GOOGLE_CLIENT_SECRET_JSON_PATH = os.getenv("GOOGLE_CLIENT_SECRET_JSON_PATH")
# Directory to store user-specific Google API tokens
GOOGLE_TOKEN_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "google_tokens")
os.makedirs(GOOGLE_TOKEN_STORAGE_DIR, exist_ok=True)

# Kafka Configuration (Essential for Gmail polling results)
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(',')
GMAIL_POLL_KAFKA_TOPIC = os.getenv("GMAIL_POLL_KAFKA_TOPIC", "gmail_polling_results")

# This will be populated in dependencies.py or main_server.py after engine classes are defined.
# Maps service names (string) to engine classes (Type[BasePollingEngine]).
SERVICE_ENGINE_MAP = {}

# TTS Provider for dummy voice response (optional)
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "ORPHEUS").upper() # e.g., ORPHEUS for local basic TTS
# No need for ElevenLabs or GCP TTS keys if only Orpheus is used for dummy sound

print(f"[Config] Loaded: MONGO_URI={os.getenv('MONGO_URI')}, MONGO_DB_NAME={os.getenv('MONGO_DB_NAME')}")
print(f"[Config] Loaded: KAFKA_BOOTSTRAP_SERVERS={KAFKA_BOOTSTRAP_SERVERS}, GMAIL_POLL_KAFKA_TOPIC={GMAIL_POLL_KAFKA_TOPIC}")
print(f"[Config] Loaded: GOOGLE_TOKEN_STORAGE_DIR={GOOGLE_TOKEN_STORAGE_DIR}")
# src/server/workers/pollers/gmail/config.py
import os
from dotenv import load_dotenv
import datetime

dotenv_path = "server/.env"
print(f"[{datetime.datetime.now()}] [GmailPoller_Config] Loading .env from: {dotenv_path}")
load_dotenv(dotenv_path=dotenv_path)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentient_agent_db")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(',')
GMAIL_POLL_KAFKA_TOPIC = os.getenv("GMAIL_POLL_KAFKA_TOPIC", "gmail_polling_results")

# AES Encryption Keys (for decrypting Google tokens stored by main server)
AES_SECRET_KEY_HEX = os.getenv("AES_SECRET_KEY")
AES_IV_HEX = os.getenv("AES_IV")
AES_SECRET_KEY = bytes.fromhex(AES_SECRET_KEY_HEX) if AES_SECRET_KEY_HEX and len(AES_SECRET_KEY_HEX) == 64 else None
AES_IV = bytes.fromhex(AES_IV_HEX) if AES_IV_HEX and len(AES_IV_HEX) == 32 else None

if not AES_SECRET_KEY or not AES_IV:
    print(f"[{datetime.datetime.now()}] [GmailPoller_Config_WARNING] AES keys for token decryption are missing or invalid.")

# Google API Config (Poller specific, if it handles its own auth entirely)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID_POLLER")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET_POLLER")
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID_POLLER")
# Token storage path (poller might need read access if main server stores them, or store its own)
_POLLER_DIR_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")) # gmail -> pollers -> workers -> server -> src
GOOGLE_TOKEN_STORAGE_DIR_POLLER = os.path.join(_POLLER_DIR_ROOT, "google_tokens") # Shared with main server


# Polling intervals (can be fine-tuned for the poller specifically)
POLLING_INTERVALS_WORKER = {
    "ACTIVE_USER_SECONDS": int(os.getenv("WORKER_POLL_ACTIVE_SECONDS", 5 * 60)),
    "RECENTLY_ACTIVE_SECONDS": int(os.getenv("WORKER_POLL_RECENT_SECONDS", 15 * 60)),
    "PEAK_HOURS_SECONDS": int(os.getenv("WORKER_POLL_PEAK_SECONDS", 30 * 60)),
    "OFF_PEAK_SECONDS": int(os.getenv("WORKER_POLL_OFFPEAK_SECONDS", 60 * 60)),
    "INACTIVE_SECONDS": int(os.getenv("WORKER_POLL_INACTIVE_SECONDS", 2 * 60 * 60)),
    "MIN_POLL_SECONDS": int(os.getenv("WORKER_POLL_MIN_SECONDS", 60)),
    "MAX_POLL_SECONDS": int(os.getenv("WORKER_POLL_MAX_SECONDS", 4 * 60 * 60)),
    "FAILURE_BACKOFF_FACTOR": int(os.getenv("WORKER_POLL_BACKOFF_FACTOR", 2)),
    "MAX_CONSECUTIVE_FAILURES": int(os.getenv("WORKER_POLL_MAX_FAILURES", 5)),
    "MAX_FAILURE_BACKOFF_SECONDS": int(os.getenv("WORKER_POLL_MAX_BACKOFF_SECONDS", 6 * 60 * 60)),
    "SCHEDULER_TICK_SECONDS": int(os.getenv("WORKER_SCHEDULER_TICK_SECONDS", 30)), # How often this worker script checks DB
}
ACTIVE_THRESHOLD_MINUTES_WORKER = int(os.getenv("WORKER_ACTIVE_THRESHOLD_MINUTES", 30))
RECENTLY_ACTIVE_THRESHOLD_HOURS_WORKER = int(os.getenv("WORKER_RECENT_THRESHOLD_HOURS", 3))
PEAK_HOURS_START_WORKER = int(os.getenv("WORKER_PEAK_HOURS_START", 8))
PEAK_HOURS_END_WORKER = int(os.getenv("WORKER_PEAK_HOURS_END", 22))

print(f"[{datetime.datetime.now()}] [GmailPoller_Config] Config loaded. Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
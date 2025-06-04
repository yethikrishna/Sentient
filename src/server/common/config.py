import os
from dotenv import load_dotenv
from datetime import timedelta
import datetime # For logging

# Correctly determine the .env path relative to this config.py file
# Assuming config.py is in src/server/common_lib/utils/
# .env is in src/server/
current_file_dir = os.path.dirname(os.path.abspath(__file__))
env_path_parts = [current_file_dir, "..", "..", "..", ".env"] # utils -> common_lib -> server -> src -> .env
# Correct path is current_file_dir -> common_lib -> server -> .env
# So, three levels up from 'utils' to 'server' directory where .env is.
dotenv_path = os.path.abspath(os.path.join(current_file_dir, "..", "..", ".env"))

print(f"[{datetime.datetime.now()}] [ConfigLoader] Attempting to load .env from: {dotenv_path}")
load_dotenv(dotenv_path=dotenv_path)

# Auth0 Configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE") 
AUTH0_MANAGEMENT_CLIENT_ID = os.getenv("AUTH0_MANAGEMENT_CLIENT_ID")
AUTH0_MANAGEMENT_CLIENT_SECRET = os.getenv("AUTH0_MANAGEMENT_CLIENT_SECRET")
ALGORITHMS = ["RS256"]

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentient_db")

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(',')
GMAIL_POLL_KAFKA_TOPIC = os.getenv("GMAIL_POLL_KAFKA_TOPIC", "gmail_polling_results")
KAFKA_CONSUMER_GROUP_ID_CONTEXT_OPS = os.getenv("KAFKA_CONTEXT_OPERATIONS_GROUP_ID", "context_operations_group")

# AES Encryption Keys
AES_SECRET_KEY_HEX = os.getenv("AES_SECRET_KEY")
AES_IV_HEX = os.getenv("AES_IV")

AES_SECRET_KEY = None
AES_IV = None

if AES_SECRET_KEY_HEX and len(AES_SECRET_KEY_HEX) == 64: # 32 bytes = 64 hex chars
    AES_SECRET_KEY = bytes.fromhex(AES_SECRET_KEY_HEX)
else:
    print(f"[{datetime.datetime.now()}] [CONFIG_WARNING] AES_SECRET_KEY is missing or invalid. Encryption/Decryption will fail.")
    # raise ValueError("AES_SECRET_KEY must be a 64-character hex string (32 bytes).")

if AES_IV_HEX and len(AES_IV_HEX) == 32: # 16 bytes = 32 hex chars
    AES_IV = bytes.fromhex(AES_IV_HEX)
else:
    print(f"[{datetime.datetime.now()}] [CONFIG_WARNING] AES_IV is missing or invalid. Encryption/Decryption will fail.")
    # raise ValueError("AES_IV must be a 32-character hex string (16 bytes).")

# Polling intervals
POLLING_INTERVALS = {
    "ACTIVE_USER_SECONDS": int(os.getenv("POLL_GMAIL_ACTIVE_USER_SECONDS", 5 * 60)),
    "RECENTLY_ACTIVE_SECONDS": int(os.getenv("POLL_GMAIL_RECENTLY_ACTIVE_SECONDS", 15 * 60)),
    "PEAK_HOURS_SECONDS": int(os.getenv("POLL_GMAIL_PEAK_HOURS_SECONDS", 30 * 60)),
    "OFF_PEAK_SECONDS": int(os.getenv("POLL_GMAIL_OFF_PEAK_SECONDS", 60 * 60)),
    "INACTIVE_SECONDS": int(os.getenv("POLL_GMAIL_INACTIVE_SECONDS", 2 * 60 * 60)),
    "MIN_POLL_SECONDS": int(os.getenv("POLL_GMAIL_MIN_SECONDS", 60)),
    "MAX_POLL_SECONDS": int(os.getenv("POLL_GMAIL_MAX_SECONDS", 4 * 60 * 60)),
    "FAILURE_BACKOFF_FACTOR": int(os.getenv("POLL_GMAIL_FAILURE_BACKOFF_FACTOR", 2)),
    "MAX_CONSECUTIVE_FAILURES": int(os.getenv("POLL_MAX_CONSECUTIVE_FAILURES", 5)),
    "MAX_FAILURE_BACKOFF_SECONDS": int(os.getenv("POLL_GMAIL_MAX_FAILURE_BACKOFF_SECONDS", 6 * 60 * 60)),
    "SCHEDULER_TICK_SECONDS": int(os.getenv("POLL_SCHEDULER_TICK_SECONDS", 30)),
}

ACTIVE_THRESHOLD_MINUTES = int(os.getenv("POLL_ACTIVE_THRESHOLD_MINUTES", 30))
RECENTLY_ACTIVE_THRESHOLD_HOURS = int(os.getenv("POLL_RECENTLY_ACTIVE_THRESHOLD_HOURS", 3))
PEAK_HOURS_START = int(os.getenv("POLL_PEAK_HOURS_START", 8)) # Local time of the server
PEAK_HOURS_END = int(os.getenv("POLL_PEAK_HOURS_END", 22)) # Local time of the server

SUPPORTED_POLLING_SERVICES = ["gmail"] # Only Gmail for now

# Google API Config
_SRC_DIR_ROOT = os.path.abspath(os.path.join(current_file_dir, "..", "..", "..")) # utils -> common_lib -> server -> src
GOOGLE_TOKEN_STORAGE_DIR = os.path.join(_SRC_DIR_ROOT, "google_tokens") # Path relative to src directory
os.makedirs(GOOGLE_TOKEN_STORAGE_DIR, exist_ok=True)

# Server URLs for inter-service communication
MAIN_SERVER_URL = f"http://localhost:{os.getenv('MAIN_SERVER_PORT', '5000')}"
CHAT_SERVER_URL = os.getenv("CHAT_SERVER_URL", "http://localhost:5001")
VOICE_SERVER_URL = os.getenv("VOICE_SERVER_URL", "http://localhost:5002")
POLLING_SERVER_URL = os.getenv("POLLING_SERVER_URL", "http://localhost:5003")
CONTEXT_OPERATIONS_SERVER_URL = os.getenv("CONTEXT_OPERATIONS_SERVER_URL", "http://localhost:5004")


# Log basic config values for verification
print(f"[{datetime.datetime.now()}] [CONFIG_LOADED] AUTH0_DOMAIN: {'SET' if AUTH0_DOMAIN else 'NOT SET'}")
print(f"[{datetime.datetime.now()}] [CONFIG_LOADED] AUTH0_AUDIENCE: {'SET' if AUTH0_AUDIENCE else 'NOT SET'}")
print(f"[{datetime.datetime.now()}] [CONFIG_LOADED] MONGO_URI: {MONGO_URI}")
print(f"[{datetime.datetime.now()}] [CONFIG_LOADED] KAFKA_BOOTSTRAP_SERVERS: {KAFKA_BOOTSTRAP_SERVERS}")
print(f"[{datetime.datetime.now()}] [CONFIG_LOADED] GOOGLE_TOKEN_STORAGE_DIR: {GOOGLE_TOKEN_STORAGE_DIR}")
print(f"[{datetime.datetime.now()}] [CONFIG_LOADED] MAIN_SERVER_URL: {MAIN_SERVER_URL}")
print(f"[{datetime.datetime.now()}] [CONFIG_LOADED] CHAT_SERVER_URL: {CHAT_SERVER_URL}")
print(f"[{datetime.datetime.now()}] [CONFIG_LOADED] VOICE_SERVER_URL: {VOICE_SERVER_URL}")
print(f"[{datetime.datetime.now()}] [CONFIG_LOADED] POLLING_SERVER_URL: {POLLING_SERVER_URL}")
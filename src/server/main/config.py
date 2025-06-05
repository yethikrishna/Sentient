# src/server/main/config.py
import os
from dotenv import load_dotenv
import datetime

# Load .env from the current 'main' directory
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
print(f"[{datetime.datetime.now()}] [MainServer_Config] Loading .env from: {dotenv_path}")
load_dotenv(dotenv_path=dotenv_path)

APP_SERVER_PORT = int(os.getenv("APP_SERVER_PORT", "5000"))
IS_DEV_ENVIRONMENT = os.getenv("IS_DEV_ENVIRONMENT", "false").lower() in ("true", "1", "t", "y")

# Auth0 Configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
ALGORITHMS = ["RS256"]
# For Management API (e.g., for setting referrer status)
AUTH0_MANAGEMENT_CLIENT_ID = os.getenv("AUTH0_MANAGEMENT_CLIENT_ID")
AUTH0_MANAGEMENT_CLIENT_SECRET = os.getenv("AUTH0_MANAGEMENT_CLIENT_SECRET")


# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentient_db")

# AES Encryption Keys
AES_SECRET_KEY_HEX = os.getenv("AES_SECRET_KEY")
AES_IV_HEX = os.getenv("AES_IV")

AES_SECRET_KEY = None
AES_IV = None

if AES_SECRET_KEY_HEX:
    if len(AES_SECRET_KEY_HEX) == 64: # 32 bytes = 64 hex chars
        AES_SECRET_KEY = bytes.fromhex(AES_SECRET_KEY_HEX)
    else:
        print(f"[{datetime.datetime.now()}] [MainServer_Config_WARNING] AES_SECRET_KEY is invalid (must be 64 hex chars). Encryption/Decryption will fail.")
else:
    print(f"[{datetime.datetime.now()}] [MainServer_Config_WARNING] AES_SECRET_KEY is missing. Encryption/Decryption will fail.")

if AES_IV_HEX:
    if len(AES_IV_HEX) == 32: # 16 bytes = 32 hex chars
        AES_IV = bytes.fromhex(AES_IV_HEX)
    else:
        print(f"[{datetime.datetime.now()}] [MainServer_Config_WARNING] AES_IV is invalid (must be 32 hex chars). Encryption/Decryption will fail.")
else:
    print(f"[{datetime.datetime.now()}] [MainServer_Config_WARNING] AES_IV is missing. Encryption/Decryption will fail.")


# Google API Config (mainly for token storage path if server handles auth code exchange)
_SERVER_DIR_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) # main -> server
GOOGLE_TOKEN_STORAGE_DIR = os.path.join(_SERVER_DIR_ROOT, "google_tokens")
os.makedirs(GOOGLE_TOKEN_STORAGE_DIR, exist_ok=True)


# Polling related constants (used by main server for toggling)
POLLING_INTERVALS = {
    "ACTIVE_USER_SECONDS": int(os.getenv("POLL_GMAIL_ACTIVE_USER_SECONDS", 5 * 60)),
}
SUPPORTED_POLLING_SERVICES = ["gmail"] # Only Gmail for now

# Data sources structure for initializing if not present in user's profile
# (The actual GmailPollingEngine class is in the poller worker, not directly used by main server)
DATA_SOURCES_CONFIG = {
    "gmail": {
        "display_name": "Gmail",
        "description": "Polls your Gmail inbox for new emails.",
        "enabled_by_default": False,
        "configurable": True, # Example: can user configure sub-settings for this source?
        # No engine_class here as main server doesn't run the engine
    }
}

# Voice Service Configs (Placeholders, actual TTS providers not fully integrated for dummy)
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "DUMMY") # Default to dummy
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ORPHEUS_MODEL_PATH = os.getenv("ORPHEUS_MODEL_PATH")

print(f"[{datetime.datetime.now()}] [MainServer_Config] Configuration loaded. AUTH0_DOMAIN: {'SET' if AUTH0_DOMAIN else 'NOT SET'}")
# src/server/main/config.py
# src/server/main/config.py
import os
from dotenv import load_dotenv
import datetime

# Load .env from the current 'main' directory
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env") # Corrected path to be server/.env
print(f"[{datetime.datetime.now()}] [MainServer_Config] Loading .env from: {dotenv_path}")
load_dotenv(dotenv_path=dotenv_path)

APP_SERVER_PORT = int(os.getenv("APP_SERVER_PORT", "5000"))
IS_DEV_ENVIRONMENT = os.getenv("IS_DEV_ENVIRONMENT", "false").lower() in ("true", "1", "t", "y")

# Auth0 Configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE") # This is your custom API audience from Auth0
ALGORITHMS = ["RS256"]
# For Management API (e.g., for setting referrer status)
AUTH0_MANAGEMENT_CLIENT_ID = os.getenv("AUTH0_MANAGEMENT_CLIENT_ID")
AUTH0_MANAGEMENT_CLIENT_SECRET = os.getenv("AUTH0_MANAGEMENT_CLIENT_SECRET")


# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentient_db") # Changed default to sentient_db

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
GOOGLE_TOKEN_STORAGE_DIR = os.path.join(_SERVER_DIR_ROOT, "google_tokens") # This path might be less relevant if client passes tokens
os.makedirs(GOOGLE_TOKEN_STORAGE_DIR, exist_ok=True)


# Polling related constants (used by main server for toggling)
POLLING_INTERVALS = {
    "ACTIVE_USER_SECONDS": int(os.getenv("POLL_GMAIL_ACTIVE_USER_SECONDS", 5 * 60)),
}
SUPPORTED_POLLING_SERVICES = ["gmail"] 

# Data sources structure for initializing if not present in user's profile
DATA_SOURCES_CONFIG = {
    "gmail": {
        "display_name": "Gmail",
        "description": "Polls your Gmail inbox for new emails.",
        "enabled_by_default": False,
        "configurable": True, 
    }
}

# Voice Service Configs 
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "ORPHEUS" if IS_DEV_ENVIRONMENT else "ELEVENLABS") # Default based on IS_DEV
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
# For Orpheus (Dev)
ORPHEUS_MODEL_PATH = os.getenv("ORPHEUS_MODEL_PATH", os.path.join(os.path.dirname(__file__), "..", "legacy", "voice", "models", "orpheus-3b-0.1-ft-q4_k_m.gguf"))
ORPHEUS_N_GPU_LAYERS = int(os.getenv("ORPHEUS_N_GPU_LAYERS", 30))

# LLM Configuration (Simplified for now)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434") # For dev
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "llama3.2:3b") # For dev
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") # For prod
OPENROUTER_MODEL_NAME = os.getenv("OPENROUTER_MODEL_NAME", "meta-llama/llama-3.1-8b-instruct") # For prod

print(f"[{datetime.datetime.now()}] [MainServer_Config] Configuration loaded. AUTH0_DOMAIN: {'SET' if AUTH0_DOMAIN else 'NOT SET'}")
print(f"[{datetime.datetime.now()}] [MainServer_Config] IS_DEV_ENVIRONMENT: {IS_DEV_ENVIRONMENT}")
print(f"[{datetime.datetime.now()}] [MainServer_Config] TTS_PROVIDER: {TTS_PROVIDER}")
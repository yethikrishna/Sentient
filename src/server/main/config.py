# src/server/main/config.py
import os
from dotenv import load_dotenv
import datetime

# Load .env from the current 'main' directory's parent, which is 'server'
dotenv_path = "server/.env"
print(f"[{datetime.datetime.now()}] [MainServer_Config] Loading .env from: {dotenv_path}")
load_dotenv(dotenv_path=dotenv_path)

APP_SERVER_PORT = int(os.getenv("APP_SERVER_PORT", "5000"))

# Auth0 Configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE") 
ALGORITHMS = ["RS256"]
# For Management API
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


# Polling related constants
POLLING_INTERVALS = {
    "ACTIVE_USER_SECONDS": int(os.getenv("POLL_GMAIL_ACTIVE_USER_SECONDS", 5 * 60)),
}
SUPPORTED_POLLING_SERVICES = ["gmail"] 

DATA_SOURCES_CONFIG = {
    "gmail": {
        "display_name": "Gmail",
        "description": "Polls your Gmail inbox for new emails.",
        "enabled_by_default": False,
        "configurable": True, 
    }
}

# --- Service Provider Configuration ---
# These variables allow for flexible switching between different service providers.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "OLLAMA")  # Options: "OLLAMA", "OPENROUTER"
STT_PROVIDER = os.getenv("STT_PROVIDER", "FASTER_WHISPER") # Options: "FASTER_WHISPER", "ELEVENLABS"
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "ORPHEUS") # Options: "ORPHEUS", "ELEVENLABS", "GCP"

# --- Service-Specific API Keys and Paths ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY") # Used for both STT and TTS from ElevenLabs

# For Orpheus (Dev TTS)
ORPHEUS_MODEL_PATH = os.getenv("ORPHEUS_MODEL_PATH", os.path.join(os.path.dirname(__file__), "..", "legacy", "voice", "models", "orpheus-3b-0.1-ft-q4_k_m.gguf"))
ORPHEUS_N_GPU_LAYERS = int(os.getenv("ORPHEUS_N_GPU_LAYERS", 30))

# FasterWhisper STT (Dev STT) - Configs are usually passed at instantiation
FASTER_WHISPER_MODEL_SIZE = os.getenv("FASTER_WHISPER_MODEL_SIZE", "base")
FASTER_WHISPER_DEVICE = os.getenv("FASTER_WHISPER_DEVICE", "cpu")
FASTER_WHISPER_COMPUTE_TYPE = os.getenv("FASTER_WHISPER_COMPUTE_TYPE", "int8")


# LLM Endpoint Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434") 
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "qwen3:4b") 
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") 
OPENROUTER_MODEL_NAME = os.getenv("OPENROUTER_MODEL_NAME", "qwen/qwen3-8b:free") 
# MCP Server URLs
MEMORY_MCP_SERVER_URL = os.getenv("MEMORY_MCP_SERVER_URL", "http://localhost:8001/sse")

MONGO_URI= os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME= os.getenv("MONGO_DB_NAME", "sentient_db")
NEO4J_URI= os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER= os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD= os.getenv("NEO4J_PASSWORD", "password")

print(f"[{datetime.datetime.now()}] [MainServer_Config] Configuration loaded. AUTH0_DOMAIN: {'SET' if AUTH0_DOMAIN else 'NOT SET'}")
print(f"[{datetime.datetime.now()}] [MainServer_Config] LLM Provider: {LLM_PROVIDER}")
print(f"[{datetime.datetime.now()}] [MainServer_Config] STT Provider: {STT_PROVIDER}")
print(f"[{datetime.datetime.now()}] [MainServer_Config] TTS Provider: {TTS_PROVIDER}")
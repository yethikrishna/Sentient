# src/server/workers/extractor/config.py
import os

import logging
from dotenv import load_dotenv

# Conditionally load .env for local development
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "OLLAMA")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "qwen3:4b")
NOVITA_API_KEY = os.getenv("NOVITA_API_KEY")
NOVITA_MODEL_NAME = os.getenv("NOVITA_MODEL_NAME", "qwen/qwen3-4b-fp8")

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentient_agent_db")

logging.info(f"Extractor Worker configured. LLM Provider: {LLM_PROVIDER}")
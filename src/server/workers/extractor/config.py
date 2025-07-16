# src/server/workers/extractor/config.py
import os

import logging
from dotenv import load_dotenv

# Load .env file for 'dev-local' environment.
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
# OpenAI API Standard Configuration
OPENAI_API_BASE_URL = os.getenv("OPENAI_API_BASE_URL", "http://localhost:11434")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "qwen2:1.5b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "ollama")
# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentient_agent_db")

logging.info(f"Extractor Worker configured. LLM Endpoint: {OPENAI_API_BASE_URL}")

# src/server/workers/extractor/config.py
import os
from dotenv import load_dotenv
import logging

# Load .env file from the current directory
dotenv_path = "server/.env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    logging.info(f"Loaded .env config from {dotenv_path}")
else:
    # Fallback to loading from the main server .env if the local one doesn't exist
    # This helps in environments where all configs are centralized
    server_dotenv_path = "server/.env"
    if os.path.exists(server_dotenv_path):
        load_dotenv(dotenv_path=server_dotenv_path)
        logging.info(f"Loaded .env config from {server_dotenv_path}")

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "OLLAMA")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "qwen3:4b")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL_NAME = os.getenv("OPENROUTER_MODEL_NAME", "qwen/qwen-7b-chat")

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(',')
CONTEXT_EVENTS_TOPIC = os.getenv("CONTEXT_EVENTS_TOPIC", "gmail_polling_results")
MEMORY_OPERATIONS_TOPIC = os.getenv("MEMORY_OPERATIONS_TOPIC", "memory_operations")
ACTION_ITEMS_TOPIC = os.getenv("ACTION_ITEMS_TOPIC", "action_items")
KAFKA_CONSUMER_GROUP_ID = os.getenv("KAFKA_CONSUMER_GROUP_ID", "extractor_worker_group")

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentient_agent_db")

logging.info(f"Extractor Worker configured. LLM Provider: {LLM_PROVIDER}, Input Topic: {CONTEXT_EVENTS_TOPIC}")
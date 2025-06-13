import os
from dotenv import load_dotenv
import logging

# Load .env file from the current directory or fallback to main server .env
dotenv_path = "server/.env"
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    logging.info(f"Loaded planner worker .env config from {dotenv_path}")
else:
    server_dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(server_dotenv_path):
        load_dotenv(dotenv_path=server_dotenv_path)
        logging.info(f"Loaded planner worker .env config from main server path: {server_dotenv_path}")

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "OLLAMA")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "qwen3:4b")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL_NAME = os.getenv("OPENROUTER_MODEL_NAME", "qwen/qwen-7b-chat")

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(',')
ACTION_ITEMS_TOPIC = os.getenv("ACTION_ITEMS_TOPIC", "action_items")
KAFKA_CONSUMER_GROUP_ID = os.getenv("KAFKA_CONSUMER_GROUP_ID", "planner_worker_group")

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentient_db")

# Main Server's INTEGRATIONS_CONFIG
# This needs to be imported carefully, assuming a shared structure or environment
try:
    from server.main.config import INTEGRATIONS_CONFIG
except (ImportError, ModuleNotFoundError):
    logging.warning("Could not import INTEGRATIONS_CONFIG from main server. Tool availability check will be limited.")
    INTEGRATIONS_CONFIG = {}


logging.info(f"Planner Worker configured. Input Topic: {ACTION_ITEMS_TOPIC}")
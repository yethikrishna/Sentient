# src/server/workers/memory/config.py
import os
from dotenv import load_dotenv
import logging

# Load .env file from the current directory or fallback to main server .env
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    logging.info(f"Loaded memory worker .env config from {dotenv_path}")

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "OLLAMA")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "qwen3:4b")
NOVITA_API_KEY = os.getenv("NOVITA_API_KEY")
NOVITA_MODEL_NAME = os.getenv("NOVITA_MODEL_NAME", "qwen/qwen3-4b-fp8")

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(',')
MEMORY_OPERATIONS_TOPIC = os.getenv("MEMORY_OPERATIONS_TOPIC", "memory_operations")
KAFKA_CONSUMER_GROUP_ID = os.getenv("KAFKA_CONSUMER_GROUP_ID", "memory_worker_group")

# Memory MCP Server URL
MEMORY_MCP_SERVER_URL = os.getenv("MEMORY_MCP_SERVER_URL", "http://localhost:8001/sse")

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentient_db")

logging.info(f"Memory Worker configured. Input Topic: {MEMORY_OPERATIONS_TOPIC}, MCP Target: {MEMORY_MCP_SERVER_URL}")
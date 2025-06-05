# src/server/queues/context_operations/config.py
import os
from dotenv import load_dotenv
import datetime

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
print(f"[{datetime.datetime.now()}] [ContextQueue_Config] Loading .env from: {dotenv_path}")
load_dotenv(dotenv_path=dotenv_path)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentient_db")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(',')
KAFKA_CONSUMER_GROUP_ID = os.getenv("KAFKA_CONSUMER_GROUP_ID", "context_operations_group")
KAFKA_CONSUME_TOPIC = os.getenv("KAFKA_CONSUME_TOPIC", "gmail_polling_results") # Topic to consume from

print(f"[{datetime.datetime.now()}] [ContextQueue_Config] Config loaded. Kafka topic: {KAFKA_CONSUME_TOPIC}")
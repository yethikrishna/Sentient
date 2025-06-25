import asyncio
import logging
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError
import os
from dotenv import load_dotenv

# --- Configuration ---
# Load .env file from the main server directory to get Kafka settings
try:
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        print(f"Loaded Kafka config from: {dotenv_path}")
except Exception as e:
    print(f"Warning: Could not load .env file. Using default values. Error: {e}")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(',')

# Define topics with their desired partition count and replication factor
# Replication factor should be 1 for local dev, 3 for production clusters
CONTEXT_EVENTS_TOPIC_STR = os.getenv("CONTEXT_EVENTS_TOPIC", "dev_gmail_polling_results,dev_gcalendar_polling_results,dev_journal_block_events")
CONTEXT_EVENTS_TOPICS = [topic.strip() for topic in CONTEXT_EVENTS_TOPIC_STR.split(',')]

MEMORY_OPERATIONS_TOPIC = os.getenv("MEMORY_OPERATIONS_TOPIC", "dev_memory_operations")
ACTION_ITEMS_TOPIC = os.getenv("ACTION_ITEMS_TOPIC", "dev_action_items")

TOPICS_TO_CREATE = [
    NewTopic(name=topic_name, num_partitions=4, replication_factor=1) for topic_name in CONTEXT_EVENTS_TOPICS
]
TOPICS_TO_CREATE.append(NewTopic(name=MEMORY_OPERATIONS_TOPIC, num_partitions=2, replication_factor=1))
TOPICS_TO_CREATE.append(NewTopic(name=ACTION_ITEMS_TOPIC, num_partitions=2, replication_factor=1))


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def create_kafka_topics():
    """
    Connects to Kafka and creates predefined topics if they don't already exist.
    """
    admin_client = AIOKafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await admin_client.start()
    logging.info(f"Connected to Kafka as Admin at {KAFKA_BOOTSTRAP_SERVERS}.")

    existing_topics = await admin_client.list_topics()
    logging.info(f"Existing topics: {existing_topics}")

    topics_to_actually_create = []
    for topic in TOPICS_TO_CREATE:
        if topic.name not in existing_topics:
            topics_to_actually_create.append(topic)
        else:
            logging.warning(f"Topic '{topic.name}' already exists. Skipping creation.")
    
    if not topics_to_actually_create:
        logging.info("All required topics already exist. No action needed.")
        await admin_client.close()
        return

    try:
        logging.info(f"Attempting to create {len(topics_to_actually_create)} topics...")
        await admin_client.create_topics(new_topics=topics_to_actually_create, validate_only=False)
        for topic in topics_to_actually_create:
            logging.info(f"Successfully requested creation of topic: '{topic.name}'")

    except TopicAlreadyExistsError:
        # This case is now handled by the pre-check, but kept for safety
        logging.warning("One or more topics already exist. No action taken for existing topics.")
    except Exception as e:
        logging.error(f"An error occurred during topic creation: {e}", exc_info=True)
    finally:
        await admin_client.close()
        logging.info("Admin client connection closed.")

if __name__ == "__main__":
    asyncio.run(create_kafka_topics())
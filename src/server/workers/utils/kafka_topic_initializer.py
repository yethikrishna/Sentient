import asyncio
import logging
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError

# --- Configuration ---
KAFKA_BOOTSTRAP_SERVERS = ["localhost:9092"]
# Define topics with their desired partition count and replication factor
# Replication factor should be 1 for local dev, 3 for production clusters
TOPICS_TO_CREATE = [
    NewTopic(name="gmail_polling_results", num_partitions=4, replication_factor=1),
    NewTopic(name="gcalendar_polling_results", num_partitions=4, replication_factor=1),
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def create_kafka_topics():
    """
    Connects to Kafka and creates predefined topics if they don't already exist.
    """
    admin_client = AIOKafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await admin_client.start()
    logging.info("Connected to Kafka as Admin.")

    try:
        logging.info(f"Attempting to create {len(TOPICS_TO_CREATE)} topics...")
        await admin_client.create_topics(new_topics=TOPICS_TO_CREATE, validate_only=False)
        for topic in TOPICS_TO_CREATE:
            logging.info(f"Successfully requested creation of topic: '{topic.name}'")

    except TopicAlreadyExistsError:
        logging.warning("One or more topics already exist. No action taken for existing topics.")
    except Exception as e:
        logging.error(f"An error occurred during topic creation: {e}")
    finally:
        await admin_client.close()
        logging.info("Admin client connection closed.")

if __name__ == "__main__":
    asyncio.run(create_kafka_topics())
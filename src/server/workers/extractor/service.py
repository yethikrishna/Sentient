import asyncio
import logging

from .kafka_clients import KafkaManager
from .llm import get_extractor_agent
from .db import ExtractorMongoManager # Keep for logging processed events
from ..tasks import process_action_item
from . import config

logger = logging.getLogger(__name__)

class ExtractorService:
    def __init__(self):
        self.kafka_manager = KafkaManager()
        self.db_manager = ExtractorMongoManager()
        self.extractor_agent = get_extractor_agent()

    async def process_message(self, message_data: dict):
        user_id = message_data.get("user_id")
        event_id = message_data.get("event_id")
        email_content = message_data.get("email_content")

        if not all([user_id, event_id, email_content]):
            logger.error(f"Missing data in message: {message_data}")
            return

        logger.info(f"Processing event {event_id} for user {user_id}")

        try:
            # Assuming extractor_agent returns a dict with 'action_items' and 'memory_items'
            extraction_result = await self.extractor_agent.extract(email_content)
            action_items = extraction_result.get("action_items", [])
            memory_items = extraction_result.get("memory_items", [])

            # Log the processed event
            await self.db_manager.log_processed_event(event_id, user_id, email_content, action_items, memory_items)

            async with self.kafka_manager.get_producer() as producer:
                if not producer:
                    logger.error("Could not get Kafka producer. Halting message processing.")
                    return
                
                if action_items:
                    process_action_item.delay(user_id, action_items, event_id, email_content)

        except Exception as e:
            logger.exception(f"Error processing message for event {event_id}: {e}")

    async def start_consumer(self):
        consumer = self.kafka_manager.get_consumer(config.EMAIL_EVENTS_TOPIC)
        if not consumer:
            logger.error("Could not get Kafka consumer. Exiting.")
            return

        logger.info(f"Starting Kafka consumer for topic: {config.EMAIL_EVENTS_TOPIC}")
        try:
            async for msg in consumer:
                message_data = msg.value
                await self.process_message(message_data)
        except asyncio.CancelledError:
            logger.info("Consumer task cancelled.")
        except Exception as e:
            logger.exception(f"Error in Kafka consumer loop: {e}")
        finally:
            await consumer.stop()
            logger.info("Kafka consumer stopped.")

async def main():
    service = ExtractorService()
    await service.start_consumer()

if __name__ == "__main__":
    # This part would typically be handled by a larger application framework
    # For standalone testing, you might run:
    # asyncio.run(main())
    pass
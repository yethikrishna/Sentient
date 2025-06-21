import asyncio
import logging
import json
import re
import traceback

from .kafka_clients import KafkaManager
from .llm import get_extractor_agent
from .db import ExtractorMongoManager
from ..tasks import process_action_item
from . import config

logger = logging.getLogger(__name__)

class ExtractorService:
    def __init__(self, db_manager: ExtractorMongoManager):
        self.db_manager = db_manager
        self.agent = get_extractor_agent()
        logger.info("ExtractorService initialized.")

    async def process_message(self, msg):
        """Processes a single context event from Kafka."""
        try:
            logger.info(f"Received message from Kafka at offset {msg.offset}. Processing...")
            event_batch = msg.value
            if not isinstance(event_batch, list):
                logger.warning(f"Received non-list payload. Skipping. Payload: {event_batch}")
                return

            for event_data in event_batch:
                user_id = event_data.get("user_id")
                event_id = event_data.get("event_id")

                if not all([user_id, event_id]) or await self.db_manager.is_event_processed(user_id, event_id):
                    logger.info(f"Skipping event {event_id} (missing data or already processed).")
                    continue

                email_content = event_data.get("data", {})
                subject = email_content.get("subject", "")
                body = email_content.get("body", "")

                if not body and not subject:
                    continue

                logger.info(f"Processing event {event_id} for user {user_id}")

                llm_input_content = f"Subject: {subject}\n\nBody:\n{body}"
                messages = [{'role': 'user', 'content': llm_input_content}]

                loop = asyncio.get_running_loop()
                def run_agent_sync():
                    response_str = ""
                    for chunk in self.agent.run(messages=messages):
                        if isinstance(chunk, list) and chunk:
                            last_message = chunk[-1]
                            if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                                content = last_message["content"]
                                match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
                                response_str = match.group(1) if match else content
                    return response_str

                llm_response_str = await loop.run_in_executor(None, run_agent_sync)
                if not llm_response_str:
                    logger.error(f"LLM returned no response for event {event_id}.")
                    continue

                try:
                    extracted_data = json.loads(llm_response_str)
                    memory_items = extracted_data.get("memory_items", [])
                    action_items = extracted_data.get("action_items", [])
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode LLM JSON for event {event_id}.")
                    continue

                # --- Send to Kafka Topics ---
                producer = await KafkaManager.get_producer()
                if not producer:
                    logger.error("Could not get Kafka producer. Halting message processing.")
                    return
                
                for fact in memory_items:
                    if isinstance(fact, str) and fact.strip():
                        memory_payload = {"user_id": user_id, "fact": fact}
                        await producer.send_and_wait(config.MEMORY_OPERATIONS_TOPIC, memory_payload)
                        logger.info(f"Sent memory item to Kafka for user {user_id}: '{fact[:50]}...'")

                if action_items:
                    process_action_item.delay(user_id, action_items, event_id, email_content)
                    logger.info(f"Sent {len(action_items)} action items to Planner for user {user_id}.")

                await self.db_manager.log_extraction_result(event_id, user_id, len(memory_items), len(action_items))

        except Exception as e:
            logger.error(f"Error processing message at offset {msg.offset}: {e}", exc_info=True)

    async def run(self, shutdown_event: asyncio.Event):
        logger.info("Extractor service running. Waiting for messages...")
        consumer = await KafkaManager.get_consumer()
        
        while not shutdown_event.is_set():
            try:
                result = await asyncio.wait_for(consumer.getmany(timeout_ms=1000), timeout=1.5)
                for tp, messages in result.items():
                    for msg in messages:
                        await self.process_message(msg)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"An error occurred in consumer loop: {e}", exc_info=True)
                await asyncio.sleep(5)
        
        logger.info("Shutdown signal received, exiting consumer loop.")
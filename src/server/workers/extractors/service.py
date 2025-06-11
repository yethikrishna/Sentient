# src/server/workers/extractor/service.py
import asyncio
import logging
import json
import traceback

from .kafka_clients import KafkaManager
from .llm import get_extractor_agent
from .db import ExtractorMongoManager

logger = logging.getLogger(__name__)

class ExtractorService:
    def __init__(self, db_manager: ExtractorMongoManager):
        self.db_manager = db_manager
        self.agent = get_extractor_agent()
        logger.info("ExtractorService initialized.")

    async def process_message(self, msg):
        """Processes a single context event from Kafka."""
        try:
            event_batch = msg.value
            if not isinstance(event_batch, list):
                logger.warning(f"Received non-list payload at offset {msg.offset}. Skipping.")
                return

            logger.info(f"Processing batch of {len(event_batch)} events from Kafka.")

            for event_data in event_batch:
                if not isinstance(event_data, dict):
                    logger.warning(f"Skipping non-dict item in event batch: {event_data}")
                    continue

                user_id = event_data.get("user_id")
                event_id = event_data.get("event_id")

                if not all([user_id, event_id]):
                    logger.warning(f"Skipping message in batch due to missing user_id or event_id.")
                    continue

                email_content = event_data.get("data", {})
                subject = email_content.get("subject", "")
                body = email_content.get("body", "")

                if not body and not subject:
                    logger.info(f"Skipping event {event_id} for user {user_id} as it has no content.")
                    continue

                logger.info(f"Processing event {event_id} for user {user_id}...")

                # Prepare content for the LLM
                llm_input_content = f"Subject: {subject}\n\nBody:\n{body}"
                messages = [{'role': 'user', 'content': llm_input_content}]

                # Run the Qwen agent to get the structured JSON output
                llm_response_str = ""
                for chunk in self.agent.run(messages=messages):
                    # The response for a non-streaming JSON output agent is typically the last message
                    if isinstance(chunk, list) and chunk:
                        last_message = chunk[-1]
                        if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                            llm_response_str = last_message["content"]

                if not llm_response_str:
                    logger.error(f"LLM did not return a response for event {event_id}.")
                    continue

                # Parse the JSON response
                try:
                    extracted_data = json.loads(llm_response_str)
                    memory_items = extracted_data.get("memory_items", [])
                    action_items = extracted_data.get("action_items", [])
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode JSON from LLM for event {event_id}. Response: {llm_response_str}")
                    continue

                # Pass the original context along with the action items for continuity
                original_context = event_data.get("data", {})

                # Produce to output queues
                if memory_items and isinstance(memory_items, list):
                    await KafkaManager.produce_memories(user_id, memory_items, event_id)

                if action_items and isinstance(action_items, list):
                    await KafkaManager.produce_actions(user_id, action_items, event_id, original_context)

                # Log the processing result
                await self.db_manager.log_extraction_result(
                    original_event_id=event_id,
                    user_id=user_id,
                    memory_count=len(memory_items),
                    action_count=len(action_items)
                )

        except Exception as e:
            logger.error(f"Error processing message at offset {msg.offset}: {e}")
            traceback.print_exc()

    async def run(self, shutdown_event: asyncio.Event):
        """The main loop for the service."""
        logger.info("Extractor service running. Waiting for messages...")
        consumer = await KafkaManager.get_consumer()
        
        while not shutdown_event.is_set():
            try:
                # The getmany call waits for messages and is cancel-friendly
                result = await asyncio.wait_for(consumer.getmany(timeout_ms=1000), timeout=1.5)
                for tp, messages in result.items():
                    for msg in messages:
                        await self.process_message(msg)
            except asyncio.TimeoutError:
                # This is normal, just means no messages in the last second
                continue
            except Exception as e:
                logger.error(f"An error occurred in the consumer loop: {e}")
                # Wait a bit before retrying to prevent rapid-fire errors
                await asyncio.sleep(5)
        
        logger.info("Shutdown signal received, exiting consumer loop.")
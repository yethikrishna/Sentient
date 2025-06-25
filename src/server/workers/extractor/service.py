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
                # Handle single event object as well for flexibility
                if isinstance(event_batch, dict):
                    event_batch = [event_batch]
                else:
                    logger.warning(f"Received non-list/dict payload. Skipping. Payload: {event_batch}")
                    return

            for event_data in event_batch:
                user_id = event_data.get("user_id")
                event_id = event_data.get("event_id")
                service_name = event_data.get("service_name")
                
                if not all([user_id, event_id, service_name]) or await self.db_manager.is_event_processed(user_id, event_id):
                    logger.info(f"Skipping event {event_id} (missing data or already processed).")
                    continue

                # Prepare LLM input based on the event source
                llm_input_content = ""
                if service_name == "journal_block":
                    llm_input_content = f"Source: Journal Entry\n\nContent:\n{event_data.get('data', {}).get('content', '')}"
                elif service_name == "gmail":
                    subject = event_data.get("data", {}).get("subject", "")
                    body = event_data.get("data", {}).get("body", "")
                    llm_input_content = f"Source: Email\nSubject: {subject}\n\nBody:\n{body}"
                elif service_name == "gcalendar":
                    summary = event_data.get("data", {}).get("summary", "")
                    description = event_data.get("data", {}).get("description", "")
                    llm_input_content = f"Source: Calendar Event\nSummary: {summary}\n\nDescription:\n{description}"
                
                if not llm_input_content.strip():
                    logger.warning(f"Skipping event {event_id} due to empty content.")
                    continue

                logger.info(f"Processing event {event_id} ({service_name}) for user {user_id}")

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
                    logger.error(f"Failed to decode LLM JSON for event {event_id}: {llm_response_str}")
                    continue

                # --- Send to Kafka Topics ---
                for fact in memory_items:
                    if isinstance(fact, str) and fact.strip():
                        # The memory worker will handle storing this
                        process_memory_item.delay(user_id, fact)
                        logger.info(f"Dispatched memory item to Celery for user {user_id}: '{fact[:50]}...'")

                if action_items:
                    process_action_item.delay(user_id, action_items, event_id, event_data)
                    logger.info(f"Dispatched {len(action_items)} action items to Planner for user {user_id}.")

                await self.db_manager.log_extraction_result(event_id, user_id, len(memory_items), len(action_items))

        except Exception as e:
            logger.error(f"Error processing message at offset {msg.offset}: {e}", exc_info=True)
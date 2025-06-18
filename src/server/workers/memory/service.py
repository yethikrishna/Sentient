import asyncio
import logging
import json

from .kafka_clients import KafkaManager
from .db import MemoryMongoManager
from .utils import add_fact_to_supermemory

logger = logging.getLogger(__name__)

class MemoryService:
    def __init__(self, db_manager: MemoryMongoManager):
        self.db_manager = db_manager
        logger.info("MemoryService initialized.")

    async def process_message(self, msg):
        try:
            message_data = msg.value
            user_id = message_data.get("user_id")
            fact = message_data.get("fact")

            if not user_id or not fact:
                logger.warning(f"Skipping memory message due to missing user_id or fact: {message_data}")
                return

            user_profile = await self.db_manager.get_user_profile(user_id)
            if not user_profile:
                logger.error(f"Could not find profile for user {user_id}. Cannot store memory fact.")
                return
            
            mcp_url = user_profile.get("userData", {}).get("supermemory_mcp_url")
            if not mcp_url:
                logger.warning(f"User {user_id} has no Supermemory MCP URL configured. Cannot store memory fact: '{fact[:50]}...'")
                return

            logger.info(f"Processing memory fact for user {user_id}...")
            result = await add_fact_to_supermemory(user_id, mcp_url, fact)
            if result.get("status") == "error":
                logger.error(f"Failed to store memory for user {user_id}. Reason: {result.get('message')}")
            
        except Exception as e:
            logger.error(f"Error processing memory message at offset {msg.offset}: {e}", exc_info=True)

    async def run(self, shutdown_event: asyncio.Event):
        logger.info("Memory service running. Waiting for memory operations...")
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
                logger.error(f"An error occurred in the memory consumer loop: {e}", exc_info=True)
                await asyncio.sleep(5)
        
        logger.info("Shutdown signal received, exiting memory consumer loop.")
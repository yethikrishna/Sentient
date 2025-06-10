# src/server/workers/memory/service.py
import asyncio
import logging
import json
import traceback

from .kafka_clients import KafkaManager
from .llm import get_memory_qwen_agent
from .db import MemoryWorkerMongoManager

logger = logging.getLogger(__name__)

class MemoryService:
    def __init__(self, db_manager: MemoryWorkerMongoManager):
        self.db_manager = db_manager
        logger.info("MemoryService initialized.")
        self.agent_cache = {} # Cache agent instances per user

    async def _invoke_memory_agent_for_fact(self, user_id: str, fact_text: str):
        """
        Invokes a Qwen agent to process a single fact, which will decide whether
        to save it as a long-term or short-term memory via an MCP tool call.
        """
        try:
            logger.info(f"Invoking memory agent for user {user_id} with fact: '{fact_text[:80]}...'")
            
            # Get a cached or new Qwen agent instance configured for this specific user
            if user_id not in self.agent_cache:
                self.agent_cache[user_id] = get_memory_qwen_agent(user_id)
            agent = self.agent_cache[user_id]
            
            messages = [{'role': 'user', 'content': fact_text}]

            final_agent_response = None
            for response_chunk in agent.run(messages=messages):
                final_agent_response = response_chunk # Get the final state

            # Check if the agent made a successful tool call
            if final_agent_response and isinstance(final_agent_response, list):
                # A successful run is one where a tool was called and the tool's response indicates success.
                tool_call_successful = any(
                    msg.get('role') == 'function' and 'success' in str(msg.get('content', '')).lower()
                    for msg in final_agent_response
                )
                if tool_call_successful:
                    logger.info(f"Successfully processed fact for user {user_id}.")
                    await self.db_manager.log_processed_fact(user_id, fact_text, "success", json.dumps(final_agent_response))
                else:
                    logger.error(f"Agent tool call failed or did not report success for user {user_id}. Fact: '{fact_text}'. Response: {final_agent_response}")
                    await self.db_manager.log_processed_fact(user_id, fact_text, "failure", json.dumps(final_agent_response))
            else:
                logger.error(f"Agent did not produce a valid response for user {user_id}. Fact: '{fact_text}'")
                await self.db_manager.log_processed_fact(user_id, fact_text, "failure", "Agent produced no response.")

        except Exception as e:
            logger.error(f"Critical error invoking memory agent for user {user_id}: {e}", exc_info=True)
            await self.db_manager.log_processed_fact(user_id, fact_text, "critical_error", str(e))

    async def process_message_batch(self, msg):
        """Processes a batch of memory operations from a single Kafka message."""
        try:
            message_data = msg.value
            user_id = message_data.get("user_id")
            memory_items = message_data.get("memories", [])

            if not user_id or not isinstance(memory_items, list) or not memory_items:
                logger.warning(f"Skipping malformed message at offset {msg.offset}: {message_data}")
                return

            logger.info(f"Processing batch of {len(memory_items)} memory items for user {user_id}.")

            # Process each fact one by one to ensure they are handled correctly.
            for fact in memory_items:
                if isinstance(fact, str) and fact.strip():
                    await self._invoke_memory_agent_for_fact(user_id, fact)

        except Exception as e:
            logger.error(f"Error processing message batch at offset {msg.offset}: {e}")
            traceback.print_exc()

    async def run(self, shutdown_event: asyncio.Event):
        """The main consumer loop for the service."""
        logger.info("Memory service running. Waiting for messages on memory_operations topic...")
        consumer = await KafkaManager.get_consumer()
        
        while not shutdown_event.is_set():
            try:
                # Fetch a batch of messages
                result = await asyncio.wait_for(consumer.getmany(timeout_ms=1000), timeout=1.5)
                for tp, messages in result.items():
                    for msg in messages:
                        # Process each message (which contains a batch of facts)
                        await self.process_message_batch(msg)
            except asyncio.TimeoutError:
                continue # This is expected when no messages are available
            except Exception as e:
                logger.error(f"An error occurred in the memory consumer loop: {e}")
                await asyncio.sleep(5)
        
        logger.info("Shutdown signal received, exiting memory consumer loop.")
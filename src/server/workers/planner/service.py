import asyncio
import logging
import json
import re

from .kafka_clients import KafkaManager
from .llm import get_planner_agent
from .db import PlannerMongoManager

logger = logging.getLogger(__name__)

class PlannerService:
    def __init__(self, db_manager: PlannerMongoManager):
        self.db_manager = db_manager
        logger.info("PlannerService initialized.")

    async def process_message(self, msg):
        try:
            event_data = msg.value
            user_id = event_data.get("user_id")
            action_items = event_data.get("actions", [])
            source_event_id = event_data.get("source_event_id")
            original_context = event_data.get("original_context", {})

            if not all([user_id, action_items, source_event_id]):
                logger.warning(f"Skipping malformed action item message: {event_data}")
                return

            logger.info(f"Received {len(action_items)} action items for user {user_id} from event {source_event_id}.")

            available_tools = await self.db_manager.get_available_tools(user_id)
            if not available_tools:
                logger.warning(f"User {user_id} has no available tools. Cannot create a plan.")
                return

            agent = get_planner_agent(available_tools)
            
            # Combine action items into a single prompt for the planner
            user_prompt_content = "Please create a plan for the following action items:\n- " + "\n- ".join(action_items)
            messages = [{'role': 'user', 'content': user_prompt_content}]

            # Run the agent
            final_response_str = ""
            for chunk in agent.run(messages=messages):
                if isinstance(chunk, list) and chunk:
                    last_message = chunk[-1]
                    if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                        final_response_str = last_message["content"]

            if not final_response_str:
                logger.error(f"Planner agent for user {user_id} returned no response.")
                return

            # Parse the plan from the response
            try:
                # Clean potential markdown code blocks
                if "```json" in final_response_str:
                    final_response_str = re.search(r'```json\n(.*?)\n```', final_response_str, re.DOTALL).group(1)

                plan_data = json.loads(final_response_str)
                description = plan_data.get("description", "Proactively generated plan")
                plan_steps = plan_data.get("plan", [])

                if not plan_steps:
                    logger.warning(f"Planner agent for user {user_id} generated an empty plan.")
                    return

                # Save the plan to the database
                await self.db_manager.save_plan_as_task(
                    user_id, description, plan_steps, original_context, source_event_id
                )
            except (json.JSONDecodeError, AttributeError):
                logger.error(f"Failed to parse plan JSON from planner agent for user {user_id}. Response: {final_response_str}")
            except Exception as e:
                logger.error(f"Error saving plan for user {user_id}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error processing action item message at offset {msg.offset}: {e}", exc_info=True)

    async def run(self, shutdown_event: asyncio.Event):
        logger.info("Planner service running. Waiting for action items...")
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
                logger.error(f"An error occurred in the planner consumer loop: {e}")
                await asyncio.sleep(5)
        
        logger.info("Shutdown signal received, exiting planner consumer loop.")
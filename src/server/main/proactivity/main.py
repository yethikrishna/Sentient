import asyncio
import logging
from typing import Dict, Any, Optional

from src.server.main.proactivity.cognitive_scratchpad import CognitiveScratchpad
from src.server.main.proactivity.context_gatherer import ContextGatherer
from src.server.main.proactivity.reasoner import Reasoner
from src.server.main.proactivity.user_model import UserModel
from src.server.main.proactivity.suggestion_store import SuggestionStore
from src.server.main.proactivity.action_executor import ActionExecutor
from src.server.main.proactivity.constants import SuggestionType, SuggestionStatus

logger = logging.getLogger(__name__)

class ProactivityEngine:
    """
    The main engine for proactivity, orchestrating context gathering, reasoning,
    suggestion storage, and action execution.
    """

    def __init__(self, user_model: UserModel, context_gatherer: ContextGatherer,
                 reasoner: Reasoner, suggestion_store: SuggestionStore,
                 action_executor: ActionExecutor):
        self.user_model = user_model
        self.context_gatherer = context_gatherer
        self.reasoner = reasoner
        self.suggestion_store = suggestion_store
        self.action_executor = action_executor
        self._is_running = False
        self._engine_task: Optional[asyncio.Task] = None

    async def _run_proactivity_loop(self):
        """
        The main loop for the proactivity engine.
        It continuously gathers context, reasons, and acts.
        """
        logger.info("Proactivity engine started.")
        while self._is_running:
            try:
                # 1. Gather Context
                logger.debug("Gathering context...")
                cognitive_scratchpad: CognitiveScratchpad = await self.context_gatherer.gather_context()
                logger.debug(f"Context gathered: {cognitive_scratchpad.to_dict()}")

                # 2. Reason
                logger.debug("Reasoning based on context...")
                reasoner_result: Optional[Dict[str, Any]] = await self.reasoner.reason(cognitive_scratchpad)
                logger.debug(f"Reasoner result: {reasoner_result}")

                if reasoner_result and reasoner_result.get("suggestion_description"):
                    standardized_type = self._standardize_suggestion_type(reasoner_result.get("suggestion_type"))
                    
                    # 3. Store Suggestion
                    suggestion_data = {
                        "user_id": self.user_model.user_id,
                        "timestamp": cognitive_scratchpad.timestamp,
                        "status": SuggestionStatus.PENDING,
                        "suggestion_type": standardized_type,
                        "action_details": reasoner_result.get("suggestion_action_details"),
                        "gathered_context": cognitive_scratchpad,
                        "reasoning": reasoner_result.get("reasoning"),
                        "suggestion_description": reasoner_result.get("suggestion_description")
                    }
                    
                    user_facing_message = f"AI Suggestion: {reasoner_result.get('suggestion_description')}"
                    
                    # Store the suggestion and get its ID
                    suggestion_id = await self.suggestion_store.add_suggestion(
                        user_id=self.user_model.user_id,
                        message=user_facing_message,
                        suggestion_data=suggestion_data
                    )
                    logger.info(f"New suggestion stored with ID: {suggestion_id}. Message: '{user_facing_message}'")

                    # 4. Execute Action (if immediate execution is decided by the reasoner or policy)
                    # For now, we assume actions are executed based on user interaction via the store.
                    # In a more complex system, the reasoner might output an immediate_action_flag.
                    # if reasoner_result.get("immediate_action_flag"):
                    #     await self.action_executor.execute_suggestion(suggestion_id, suggestion_data)
                    #     await self.suggestion_store.update_suggestion_status(suggestion_id, SuggestionStatus.EXECUTED)
                    #     logger.info(f"Suggestion {suggestion_id} immediately executed.")

                else:
                    logger.debug("No actionable suggestion from reasoner or no description provided.")

            except Exception as e:
                logger.error(f"Error in proactivity loop: {e}", exc_info=True)

            # Introduce a delay to prevent busy-waiting and allow for periodic checks
            await asyncio.sleep(self.user_model.proactivity_check_interval_seconds)

    def _standardize_suggestion_type(self, raw_type: Optional[str]) -> SuggestionType:
        """Standardizes the suggestion type from the reasoner output."""
        if raw_type and isinstance(raw_type, str):
            try:
                return SuggestionType[raw_type.upper()]
            except KeyError:
                logger.warning(f"Unknown suggestion type '{raw_type}'. Defaulting to GENERIC.")
        return SuggestionType.GENERIC

    def start(self):
        """Starts the proactivity engine in a separate asyncio task."""
        if not self._is_running:
            logger.info("Starting proactivity engine...")
            self._is_running = True
            self._engine_task = asyncio.create_task(self._run_proactivity_loop())
        else:
            logger.warning("Proactivity engine is already running.")

    async def stop(self):
        """Stops the proactivity engine."""
        if self._is_running:
            logger.info("Stopping proactivity engine...")
            self._is_running = False
            if self._engine_task:
                self._engine_task.cancel()
                try:
                    await self._engine_task
                except asyncio.CancelledError:
                    logger.info("Proactivity engine task cancelled successfully.")
                except Exception as e:
                    logger.error(f"Error while stopping proactivity engine task: {e}")
            self._engine_task = None
        else:
            logger.warning("Proactivity engine is not running.")

    def is_running(self) -> bool:
        """Returns True if the engine is currently running, False otherwise."""
        return self._is_running

# Example of how it might be initialized and run (for conceptual understanding, not directly executed here)
async def main_proactivity_example():
    # Placeholder for actual dependency injection/creation
    user_model = UserModel(user_id="user123", proactivity_check_interval_seconds=60)
    context_gatherer = ContextGatherer()
    reasoner = Reasoner()
    suggestion_store = SuggestionStore()
    action_executor = ActionExecutor()

    engine = ProactivityEngine(user_model, context_gatherer, reasoner, suggestion_store, action_executor)

    engine.start()
    logger.info("Proactivity engine started in example.")

    # Let it run for a while
    await asyncio.sleep(300)

    await engine.stop()
    logger.info("Proactivity engine stopped in example.")

if __name__ == "__main__":
    # Configure basic logging for standalone execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # asyncio.run(main_proactivity_example()) # Uncomment to run the example
    logger.info("This file is part of a larger system and not meant to be run directly without proper setup.")
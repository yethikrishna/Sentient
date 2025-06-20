import uuid
import datetime
import motor.motor_asyncio
import logging
from typing import List, Dict, Any
import json

from .config import MONGO_URI, MONGO_DB_NAME, INTEGRATIONS_CONFIG
from server.main.auth.utils import aes_decrypt

# --- MCP Module Imports ---
# This approach assumes all MCPs are part of the same project structure
# and can be imported directly.
try:
    from server.mcp_hub.gmail import main as gmail_mcp
    from server.mcp_hub.gcal import main as gcal_mcp
    from server.mcp_hub.gdrive import main as gdrive_mcp
    from server.mcp_hub.gdocs import main as gdocs_mcp
    from server.mcp_hub.gslides import main as gslides_mcp
    from server.mcp_hub.gsheets import main as gsheets_mcp
    from server.mcp_hub.slack import main as slack_mcp
    from server.mcp_hub.notion import main as notion_mcp
    from server.mcp_hub.github import main as github_mcp
    from server.mcp_hub.news import main as news_mcp
    from server.mcp_hub.google_search import main as google_search_mcp
    from server.mcp_hub.gmaps import main as gmaps_mcp
    from server.mcp_hub.gshopping import main as gshopping_mcp
    from server.mcp_hub.accuweather import main as accuweather_mcp
    from server.mcp_hub.quickchart import main as quickchart_mcp
    from server.mcp_hub.progress_updater import main as progress_updater_mcp
    from server.mcp_hub.chat_tools import main as chat_tools_mcp
    
    # Map integration keys to their MCP modules
    ALL_MCPS = {
        "gmail": gmail_mcp, "gcalendar": gcal_mcp, "gdrive": gdrive_mcp,
        "gdocs": gdocs_mcp, "gslides": gslides_mcp, "gsheets": gsheets_mcp,
        "slack": slack_mcp, "notion": notion_mcp, "github": github_mcp,
        "news": news_mcp, "internet_search": google_search_mcp,
        "gmaps": gmaps_mcp, "gshopping": gshopping_mcp,
        "accuweather": accuweather_mcp, "quickchart": quickchart_mcp,
        "progress_updater": progress_updater_mcp, "chat_tools": chat_tools_mcp,
    }
except ImportError as e:
    logging.error(f"Could not import one or more MCP modules: {e}. Tool availability will be limited.")
    ALL_MCPS = {}

logger = logging.getLogger(__name__)

class PlannerMongoManager:
    """A MongoDB manager for the planner worker."""
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]
        self.user_profiles_collection = self.db["user_profiles"]
        self.tasks_collection = self.db["tasks"]
        logger.info("PlannerMongoManager initialized.")

    async def get_available_tools(self, user_id: str) -> List[str]:
        """
        Dynamically determines the list of available tool functions for a user
        based on their connections and granted OAuth scopes.
        """
        user_profile = await self.user_profiles_collection.find_one({"user_id": user_id})
        if not user_profile:
            return []
        
        user_data = user_profile.get("userData", {})
        user_integrations = user_data.get("integrations", {})
        google_auth_mode = user_data.get("googleAuth", {}).get("mode", "default")
        
        available_tools = []
        
        for mcp_prefix, mcp_module in ALL_MCPS.items():
            config = INTEGRATIONS_CONFIG.get(mcp_prefix)
            if not config:
                continue

            # Determine if the tool is a Google service
            is_google_service = mcp_prefix.startswith('g')

            # --- Handle Non-Google and Built-in Tools ---
            if not is_google_service or config.get("auth_type") == "builtin":
                is_available = (
                    config.get("auth_type") == "builtin" or
                    user_integrations.get(mcp_prefix, {}).get("connected", False)
                )
                if is_available:
                    for tool_name in mcp_module.mcp.tools:
                        available_tools.append(f"{mcp_prefix}_{tool_name}")
                continue
            
            # --- Handle Google Tools ---
            if is_google_service:
                if google_auth_mode == "custom":
                    for tool_name in mcp_module.mcp.tools:
                        available_tools.append(f"{mcp_prefix}_{tool_name}")
                    continue
                
                # Default Google mode: check connection and scopes
                connection_info = user_integrations.get(mcp_prefix, {})
                if not connection_info.get("connected"):
                    continue
                
                try:
                    encrypted_creds = connection_info.get("credentials")
                    if not encrypted_creds:
                        continue
                    decrypted_creds_str = aes_decrypt(encrypted_creds)
                    creds_info = json.loads(decrypted_creds_str)
                    granted_scopes = set(creds_info.get("scopes", []))
                except Exception as e:
                    logger.error(f"Error processing credentials for {mcp_prefix} for user {user_id}: {e}")
                    continue

                for tool_name, tool_func in mcp_module.mcp.tools.items():
                    # The `scopes` attribute is attached by the @mcp.tool decorator
                    required_scopes = set(getattr(tool_func, "scopes", []))
                    if not required_scopes or required_scopes.issubset(granted_scopes):
                        available_tools.append(f"{mcp_prefix}_{tool_name}")
                        
        return list(set(available_tools))

    async def save_plan_as_task(self, user_id: str, description: str, plan: list, original_context: dict, source_event_id: str):
        """Saves a generated plan to the tasks collection for user approval."""
        task_id = str(uuid.uuid4())
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        task_doc = {
            "task_id": task_id,
            "user_id": user_id,
            "description": description,
            "status": "approval_pending",
            "priority": 1,
            "plan": plan,
            "original_context": original_context,
            "source_event_id": source_event_id,
            "progress_updates": [],
            "created_at": now_utc,
            "updated_at": now_utc,
            "result": None,
            "error": None,
            "agent_id": "planner_agent"
        }
        await self.tasks_collection.insert_one(task_doc)
        logger.info(f"Saved new plan with task_id: {task_id} for user: {user_id}")
        return task_id

    async def close(self):
        if self.client:
            self.client.close()
            logger.info("Planner MongoDB connection closed.")
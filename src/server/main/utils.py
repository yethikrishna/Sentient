# src/server/main_server/utils.py
import datetime
from datetime import timezone # Ensure timezone is imported
import os

from server.main_server.dependencies import mongo_manager
from server.common_lib.utils.config import POLLING_INTERVALS, SUPPORTED_POLLING_SERVICES, DATA_SOURCES_CONFIG

async def get_data_sources_config_for_user(user_id: str):
    """
    Constructs the data sources list for the client, reflecting user's enabled status.
    """
    user_sources_config = []
    for source_name in SUPPORTED_POLLING_SERVICES: # Iterate only supported ones
        if source_name in DATA_SOURCES_CONFIG:
            config = DATA_SOURCES_CONFIG[source_name]
            polling_state = await mongo_manager.get_polling_state(user_id, source_name)
            
            is_enabled = False
            if polling_state:
                is_enabled = polling_state.get("is_enabled", False)
            else:
                # If no state, default to what's in general config (usually False unless specified)
                is_enabled = config.get("enabled_by_default", False)
            
            user_sources_config.append({
                "name": source_name,
                "enabled": is_enabled,
                "configurable": config.get("configurable", True) # Assume configurable unless specified
            })
    return user_sources_config

async def toggle_data_source_for_user(user_id: str, source_name: str, enable: bool):
    """
    Updates the polling state in MongoDB for a given data source and user.
    This change will be picked up by the polling_server.
    """
    if source_name not in SUPPORTED_POLLING_SERVICES or source_name not in DATA_SOURCES_CONFIG:
        raise ValueError(f"Data source '{source_name}' is not supported or configured.")

    update_payload = {"is_enabled": enable}
    now_utc = datetime.datetime.now(timezone.utc)

    if enable:
        print(f"[{datetime.datetime.now()}] [MainServer_Utils] Enabling {source_name} for user {user_id}")
        # When enabling, schedule the next poll immediately and reset error/backoff states.
        update_payload["next_scheduled_poll_time"] = now_utc
        update_payload["is_currently_polling"] = False 
        update_payload["error_backoff_until_timestamp"] = None
        update_payload["consecutive_failure_count"] = 0
        
        # Determine initial polling tier and interval upon enabling
        # A more sophisticated logic might check user activity here.
        # For simplicity, defaulting to ACTIVE_USER interval.
        update_payload["current_polling_tier"] = "newly_enabled" # Or "user_enabled"
        update_payload["current_polling_interval_seconds"] = POLLING_INTERVALS["ACTIVE_USER_SECONDS"]
        
        # The polling_server's `BasePollingEngine.initialize_polling_state` ensures the document exists.
        # If it doesn't, `update_polling_state` with upsert=True will create it.
        # We might also want to ensure the engine itself is "aware" or ready if this is the first time.
        # For now, the DB state change is the trigger.
    else:
        print(f"[{datetime.datetime.now()}] [MainServer_Utils] Disabling {source_name} for user {user_id}")
        # When disabling, just setting is_enabled to False is primary.
        # Polling server will stop picking it up.
        # Optionally, could set next_scheduled_poll_time to a very far future date.
        # update_payload["next_scheduled_poll_time"] = now_utc + datetime.timedelta(days=3650) # Far future


    success = await mongo_manager.update_polling_state(user_id, source_name, update_payload)
    if not success:
        # This could happen if the document didn't exist and upsert also failed,
        # or if the update_one call itself had an issue.
        # Try to initialize the state if it didn't exist, then re-apply the toggle.
        print(f"[{datetime.datetime.now()}] [MainServer_Utils_WARN] Initial update_polling_state failed for {user_id}/{source_name}. Attempting to initialize state.")
        # Call a method that ensures the state document exists (e.g., from the polling engine, or a dedicated mongo_manager method)
        # For now, let's assume `update_polling_state` with upsert handles creation.
        # If it failed even with upsert, it's a more serious DB issue.
        raise Exception(f"Failed to update data source '{source_name}' status in database.")
    
    print(f"[{datetime.datetime.now()}] [MainServer_Utils] Polling state for {user_id}/{source_name} set to enabled={enable}")
    return success


# Add other main_server specific utility functions here if needed.
# For example, functions to process onboarding data before saving, etc.
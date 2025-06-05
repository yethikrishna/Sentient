# src/server/main/chat/utils.py
import datetime
import uuid
import json
import asyncio
from typing import List, Dict, Any, Tuple, AsyncGenerator

from ..db import MongoManager # Use ..db to import MongoManager from parent's db.py

async def get_chat_history_util(user_id: str, db_manager: MongoManager, chat_id_param: Optional[str] = None) -> Tuple[List[Dict[str, Any]], str]:
    effective_chat_id = chat_id_param
    if not effective_chat_id:
        user_profile = await db_manager.get_user_profile(user_id)
        active_chat_id_from_profile = user_profile.get("userData", {}).get("active_chat_id") if user_profile else None
        
        if active_chat_id_from_profile:
            effective_chat_id = active_chat_id_from_profile
        else:
            all_chat_ids = await db_manager.get_all_chat_ids_for_user(user_id)
            if all_chat_ids:
                effective_chat_id = all_chat_ids[0] # Default to the most recent one
                if user_profile: 
                    await db_manager.update_user_profile(user_id, {"userData.active_chat_id": effective_chat_id})
            else: # No chats exist, create a new one
                new_chat_id = str(uuid.uuid4())
                # Create a chat document implicitly or update profile
                update_payload = {"userData.active_chat_id": new_chat_id}
                await db_manager.update_user_profile(user_id, update_payload)
                effective_chat_id = new_chat_id
    
    messages_from_db = await db_manager.get_chat_history(user_id, effective_chat_id)
    
    # Serialize datetime objects in messages
    serialized_messages = []
    for m in messages_from_db:
        if isinstance(m, dict) and 'timestamp' in m and isinstance(m['timestamp'], datetime.datetime):
            m['timestamp'] = m['timestamp'].isoformat()
        serialized_messages.append(m)
        
    return [m for m in serialized_messages if m.get("isVisible", True)], effective_chat_id


# Simplified OllamaRunnable logic for dummy response / direct LLM call
async def generate_chat_llm_stream(
    user_input: str, 
    username: str, 
    is_dev_environment: bool,
    ollama_runnable_instance: Optional[Any] = None, # Placeholder for actual OllamaRunnable from runnables.py
    openrouter_runnable_instance: Optional[Any] = None # Placeholder for actual OpenRouterRunnable
    ) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Handles LLM streaming logic.
    In a real scenario, this would use OllamaRunnable or OpenRouterRunnable.
    For now, it mimics the dummy stream.
    """
    assistant_message_id = str(uuid.uuid4())
    
    if is_dev_environment:
        print(f"[{datetime.datetime.now()}] [CHAT_LLM_DEV] Using Ollama (dummy-like stream) for chat response.")
        # Example using a dummy stream similar to original
        dummy_texts = [
            f"Hello {username}! ", "This ", "is ", "a ", "dev ", "Ollama-like ", 
            "response. ", f"You said: '{user_input[:20]}...'. "
        ]
        full_response_text = "".join(dummy_texts)
        for text_part in dummy_texts:
            yield {
                "type": "assistantStream", "token": text_part, "done": False, "messageId": assistant_message_id
            }
            await asyncio.sleep(0.05)
        yield {
            "type": "assistantStream", "token": "", "done": True, "messageId": assistant_message_id,
            "full_message": full_response_text,
            "memoryUsed": False, "agentsUsed": False, "internetUsed": False, "proUsed": False
        }
        # If using actual OllamaRunnable:
        # if ollama_runnable_instance:
        #     async for chunk in ollama_runnable_instance.astream_response({"query": user_input}):
        #         if chunk:
        #             yield {"type": "assistantStream", "token": chunk, "done": False, "messageId": assistant_message_id}
        #         else: # End of stream
        #             yield {"type": "assistantStream", "token": "", "done": True, "messageId": assistant_message_id, ...} # Add full message etc.
        # else: # fallback dummy
        #     ... (current dummy logic) ...
    else: # Production
        print(f"[{datetime.datetime.now()}] [CHAT_LLM_PROD] Using OpenRouter (dummy-like stream) for chat response.")
        # Example using a dummy stream similar to original
        dummy_texts = [
            f"Greetings {username}! ", "This ", "is ", "a ", "prod ", "OpenRouter-like ", 
            "response. ", f"You queried: '{user_input[:20]}...'. "
        ]
        full_response_text = "".join(dummy_texts)
        for text_part in dummy_texts:
            yield {
                "type": "assistantStream", "token": text_part, "done": False, "messageId": assistant_message_id
            }
            await asyncio.sleep(0.05)
        yield {
            "type": "assistantStream", "token": "", "done": True, "messageId": assistant_message_id,
            "full_message": full_response_text,
            "memoryUsed": False, "agentsUsed": False, "internetUsed": False, "proUsed": False # Adjust flags as needed
        }
        # If using actual OpenRouterRunnable:
        # if openrouter_runnable_instance:
        #     async for chunk in openrouter_runnable_instance.astream_response({"query": user_input}):
        #         if chunk:
        #             yield {"type": "assistantStream", "token": chunk, "done": False, "messageId": assistant_message_id}
        #         else: # End of stream
        #             yield {"type": "assistantStream", "token": "", "done": True, "messageId": assistant_message_id, ...}
        # else: # fallback dummy
        #     ... (current dummy logic) ...
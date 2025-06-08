# src/server/main/chat/utils.py
import datetime
import uuid
import os
import json
import asyncio
import threading
import logging
from typing import List, Dict, Any, Tuple, AsyncGenerator, Optional

from ..db import MongoManager
from ..llm import get_qwen_assistant # Import the Qwen Agent initializer
from ..config import MEMORY_MCP_SERVER_URL

logger = logging.getLogger(__name__)

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
                effective_chat_id = all_chat_ids[0] 
                if user_profile: 
                    await db_manager.update_user_profile(user_id, {"userData.active_chat_id": effective_chat_id})
            else: 
                new_chat_id = str(uuid.uuid4())
                update_payload = {"userData.active_chat_id": new_chat_id}
                await db_manager.update_user_profile(user_id, update_payload)
                effective_chat_id = new_chat_id
    
    messages_from_db = await db_manager.get_chat_history(user_id, effective_chat_id)
    
    serialized_messages = []
    for m in messages_from_db:
        if isinstance(m, dict) and 'timestamp' in m and isinstance(m['timestamp'], datetime.datetime):
            m['timestamp'] = m['timestamp'].isoformat()
        serialized_messages.append(m)
        
    return [m for m in serialized_messages if m.get("isVisible", True)], effective_chat_id


async def generate_chat_llm_stream(
    user_id: str,
    active_chat_id: str,
    user_input: str, 
    username: str, # Keep for potential future use in prompts
    db_manager: MongoManager,
    assistant_message_id_override: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
    assistant_message_id = assistant_message_id_override or str(uuid.uuid4())

    try:
        # 1. Save the user's message
        user_message_payload = {
            "id": str(uuid.uuid4()), "message": user_input, "isUser": True, "type": "text", "isVisible": True,
        }
        logger.info(f"Saved user message for user {user_id} in chat {active_chat_id}")

        # Construct tools for the Qwen agent, including memory tools
        tools = [{
            "mcpServers": {
                "memory_server": { "url": MEMORY_MCP_SERVER_URL, "headers": {"X-User-ID": user_id} },
                # Other MCP servers like gdrive could be added here
            }
        }]

        # 2. Save a placeholder for the assistant's response
        assistant_placeholder_payload = {
            "id": assistant_message_id, "message": "", "isUser": False, "type": "text", "isVisible": True,
            "memoryUsed": False, "agentsUsed": True, "internetUsed": False
        }
        await db_manager.add_chat_message(user_id, active_chat_id, assistant_placeholder_payload)
        logger.info(f"Saved assistant placeholder for user {user_id} in chat {active_chat_id}")

        # Save user message after placeholder to ensure chronological order for history fetching
        await db_manager.add_chat_message(user_id, active_chat_id, user_message_payload)
    except Exception as e:
        logger.error(f"Failed to save initial messages for user {user_id}: {e}", exc_info=True)
        yield {"type": "error", "message": "Failed to save message to the database. Please try again."}
        return

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[Optional[Any]] = asyncio.Queue()
    history_from_db, _ = await get_chat_history_util(user_id, db_manager, active_chat_id)
    qwen_formatted_history = []
    for msg_from_db in history_from_db:
        role = "user" if msg_from_db.get("isUser") else "assistant"
        content = str(msg_from_db.get("message", ""))
        qwen_formatted_history.append({"role": role, "content": content})

    full_response_accumulator = ""
    stream_interrupted = False

    try:
        # Worker thread to run the synchronous Qwen agent
        def worker(initial_history: List[Dict[str, Any]]):
            try:
                system_prompt = (
                    f"You are a helpful AI assistant. The user's name is {username}. "
                    "Before answering, ALWAYS use the `search_memories` tool to see if you already know relevant information. "
                    "When the user shares new information about themselves, their preferences, or relationships, use the `save_long_term_fact` tool to remember it."
                )
                qwen_assistant = get_qwen_assistant(system_message=system_prompt, function_list=tools)
                for new_history_step in qwen_assistant.run(messages=initial_history):
                    loop.call_soon_threadsafe(queue.put_nowait, new_history_step)
            except Exception as e:
                logger.error(f"Error in Qwen Agent worker thread for user {user_id}: {e}", exc_info=True)
                error_payload = {"_error": str(e)}
                loop.call_soon_threadsafe(queue.put_nowait, error_payload)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        thread = threading.Thread(target=worker, args=(qwen_formatted_history,), daemon=True)
        thread.start()

        last_yielded_content_str = ""

        while True:
            current_history = await queue.get()
            if current_history is None: break
            if isinstance(current_history, dict) and "_error" in current_history:
                raise Exception(f"Qwen Agent failed: {current_history['_error']}")
            if not isinstance(current_history, list): continue

            # This logic correctly diffs the agent's turn and yields chunks
            assistant_turn_start_index = next((i + 1 for i in range(len(current_history) - 1, -1, -1) if current_history[i].get('role') == 'user'), 0)
            assistant_messages = current_history[assistant_turn_start_index:]
            current_turn_str = "".join(
                (f"<tool_code name=\"{msg.get('function_call', {}).get('name')}\">\n{json.dumps(json.loads(msg.get('function_call', {}).get('arguments', '{}')), indent=2) if 'arguments' in msg.get('function_call', {}) else ''}\n</tool_code>\n" if msg.get('role') == 'assistant' and msg.get('function_call') else
                 f"<tool_result tool_name=\"{msg.get('name')}\">\n{msg.get('content', '')}\n</tool_result>\n" if msg.get('role') == 'function' else
                 msg.get('content', ''))
                for msg in assistant_messages
            )

            if len(current_turn_str) > len(last_yielded_content_str):
                new_chunk = current_turn_str[len(last_yielded_content_str):]
                full_response_accumulator += new_chunk
                yield {"type": "assistantStream", "token": new_chunk, "done": False, "messageId": assistant_message_id}
                last_yielded_content_str = current_turn_str

    except asyncio.CancelledError:
        logger.warning(f"Chat stream for user {user_id} was cancelled by the client.")
        stream_interrupted = True
        raise # Re-raise the error to be handled by the FastAPI framework
    finally:
        # 3. Update the final message in the database, whether complete or interrupted
        final_content = full_response_accumulator
        if stream_interrupted and not final_content.endswith("[STREAM STOPPED BY USER]"):
            final_content += "\n\n[STREAM STOPPED BY USER]"

        update_payload = {"message": final_content, "agentsUsed": True} # Add other final fields here

        if final_content.strip():
            await db_manager.update_chat_message(user_id, active_chat_id, assistant_message_id, update_payload)
            logger.info(f"Finalized assistant message for user {user_id} in chat {active_chat_id}. Interrupted: {stream_interrupted}")
        else:
            # If nothing was generated, we might want to remove the placeholder
            logger.info(f"No content generated for {user_id}, placeholder will remain empty.")

        yield {"type": "assistantStream", "token": "", "done": True, "messageId": assistant_message_id}
        await asyncio.to_thread(thread.join) # Ensure thread finishes


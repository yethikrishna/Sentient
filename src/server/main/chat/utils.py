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
from ..llm import get_qwen_assistant
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
        # 1. DYNAMIC TOOL SELECTION: Combine built-in tools with user-connected tools.
        from ..config import INTEGRATIONS_CONFIG

        user_profile_for_tools = await db_manager.get_user_profile(user_id)
        user_connected_integrations = user_profile_for_tools.get("userData", {}).get("integrations", {}) if user_profile_for_tools else {}

        active_mcp_servers = {}

        for service_name, config in INTEGRATIONS_CONFIG.items():
            if "mcp_server_config" not in config:
                continue

            mcp_config = config["mcp_server_config"]
            if mcp_config.get("url"):  # Ensure the server URL is configured
                mcp_server_name = mcp_config["name"]
                mcp_server_url = mcp_config["url"]

                # Add built-in tools unconditionally
                if config.get("auth_type") == "builtin":
                    active_mcp_servers[mcp_server_name] = {"url": mcp_server_url, "headers": {"X-User-ID": user_id}}

                # Add user-configurable tools only if the user has connected them
                elif config.get("auth_type") in ["oauth", "manual"]:
                    connection_details = user_connected_integrations.get(service_name, {})
                    if connection_details.get("connected"):
                        active_mcp_servers[mcp_server_name] = {"url": mcp_server_url, "headers": {"X-User-ID": user_id}}

        tools = [{"mcpServers": active_mcp_servers}]
        logger.info(f"User {user_id} has active tools: {list(active_mcp_servers.keys())}")

        # 2. Save the user's message
        user_message_payload = {
            "id": str(uuid.uuid4()), "message": user_input, "isUser": True, "type": "text", "isVisible": True,
        }

        # 3. Save a placeholder for the assistant's response
        assistant_placeholder_payload = {
            "id": assistant_message_id, "message": "", "isUser": False, "type": "text", "isVisible": True,
            "memoryUsed": False, "agentsUsed": True, "internetUsed": False
        }

        # The user's message must be saved BEFORE the assistant's placeholder to maintain
        # the correct conversational order (user -> assistant) for the LLM history.
        await db_manager.add_chat_message(user_id, active_chat_id, user_message_payload)
        logger.info(f"Saved user message for user {user_id} in chat {active_chat_id}")
        await db_manager.add_chat_message(user_id, active_chat_id, assistant_placeholder_payload)
        logger.info(f"Saved assistant placeholder for user {user_id} in chat {active_chat_id}")
    except Exception as e:
        logger.error(f"Failed to save initial messages for user {user_id}: {e}", exc_info=True)
        yield {"type": "error", "message": "Failed to save message to the database. Please try again."}
        return

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[Optional[Any]] = asyncio.Queue()

    # 1. CONTEXT FIX: Reconstruct full conversational history for the agent
    history_from_db, _ = await get_chat_history_util(user_id, db_manager, active_chat_id)
    qwen_formatted_history = []
    for msg_from_db in history_from_db:
        # Skip the empty placeholder for the current turn we are generating
        if msg_from_db.get("id") == assistant_message_id:
            continue

        # Include the latest user message which was just saved
        if msg_from_db.get("id") == user_message_payload["id"]:
             qwen_formatted_history.append({"role": "user", "content": str(msg_from_db.get("message", ""))})
             continue
        
        if msg_from_db.get('isUser'):
            qwen_formatted_history.append({"role": "user", "content": str(msg_from_db.get("message", ""))})
        else:
            # Use structured history if available and valid
            structured_history = msg_from_db.get('structured_history')
            if isinstance(structured_history, list) and structured_history:
                qwen_formatted_history.extend(structured_history)
            # Fallback for simple/older messages
            elif msg_from_db.get("message"):
                qwen_formatted_history.append({"role": "assistant", "content": str(msg_from_db.get("message", ""))})

    # This is the crucial part: Add the current user input as the last message in the history.
    # The agent will process this as the latest turn.
    qwen_formatted_history.append({"role": "user", "content": user_input})

    stream_interrupted = False

    try:
        # Worker thread to run the synchronous Qwen agent
        def worker(initial_history: List[Dict[str, Any]], dynamic_tools: List[Dict[str, Any]]):
            try:
                system_prompt = (
                    f"You are a helpful AI assistant named Sentient. The user's name is {username}. The current date is {datetime.datetime.now().strftime('%Y-%m-%d')}.\n\n You have access to certain tools that you can call. Do not use tools unless explicitly required to answer the user's query. Do not overuse tools, first check if any relevant context is available in the conversation history.\n\n"
                )
                logger.info(f"Qwen agent initialized with history: {initial_history}")
                qwen_assistant = get_qwen_assistant(system_message=system_prompt, function_list=dynamic_tools)
                for new_history_step in qwen_assistant.run(messages=initial_history):
                    loop.call_soon_threadsafe(queue.put_nowait, new_history_step)
            except Exception as e:
                logger.error(f"Error in Qwen Agent worker thread for user {user_id}: {e}", exc_info=True)
                error_payload = {"_error": str(e)}
                loop.call_soon_threadsafe(queue.put_nowait, error_payload)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        thread = threading.Thread(target=worker, args=(qwen_formatted_history, tools), daemon=True)
        thread.start()

        last_yielded_content_str = ""
        final_history_state = None

        while True:
            current_history = await queue.get()
            if current_history is None: break
            if isinstance(current_history, dict) and "_error" in current_history:
                raise Exception(f"Qwen Agent failed: {current_history['_error']}")
            if not isinstance(current_history, list): continue

            final_history_state = current_history

            # Find start of assistant's turn (everything after the last user message)
            assistant_turn_start_index = next((i + 1 for i in range(len(current_history) - 1, -1, -1) if current_history[i].get('role') == 'user'), 0)
            assistant_messages = current_history[assistant_turn_start_index:]

            def msg_to_str(msg: Dict[str, Any]) -> str:
                """Converts an agent message to the string format expected by the frontend."""
                if msg.get('role') == 'assistant' and msg.get('function_call'):
                    args_str = msg['function_call'].get('arguments', '')
                    args_pretty = args_str
                    try:
                        args_pretty = json.dumps(json.loads(args_str), indent=2)
                    except (json.JSONDecodeError, TypeError): pass # Keep original if not valid JSON
                    return f"<tool_code name=\"{msg['function_call'].get('name')}\">\n{args_pretty}\n</tool_code>\n"
                elif msg.get('role') == 'function':
                    content = msg.get('content', '')
                    content_pretty = content
                    try:
                        content_pretty = json.dumps(json.loads(content), indent=2)
                    except (json.JSONDecodeError, TypeError): pass
                    return f"<tool_result tool_name=\"{msg.get('name')}\">\n{content_pretty}\n</tool_result>\n"
                elif msg.get('role') == 'assistant' and msg.get('content'):
                    return msg.get('content', '')
                return ''

            current_turn_str = "".join(msg_to_str(m) for m in assistant_messages)

            if len(current_turn_str) > len(last_yielded_content_str):
                new_chunk = current_turn_str[len(last_yielded_content_str):]
                yield {"type": "assistantStream", "token": new_chunk, "done": False, "messageId": assistant_message_id}
                last_yielded_content_str = current_turn_str

    except asyncio.CancelledError:
        logger.warning(f"Chat stream for user {user_id} was cancelled by the client.")
        stream_interrupted = True
        raise # Re-raise the error to be handled by the FastAPI framework
    finally:
        # 3. CONTEXT FIX: Update DB with the full structured history of the agent's turn
        assistant_turn_messages = []
        if final_history_state:
            start_index = next((i for i in range(len(final_history_state) - 1, -1, -1) if final_history_state[i].get('role') == 'user'), -1)
            if start_index != -1:
                assistant_turn_messages = final_history_state[start_index + 1:]

        # The display message for ChatBubble is the full string we built and streamed
        final_text_content = last_yielded_content_str

        if stream_interrupted and not final_text_content.endswith("[STREAM STOPPED BY USER]"):
            final_text_content += "\n\n[STREAM STOPPED BY USER]"

        # Important: The 'message' field stores the string with tags for ChatBubble.
        # The 'structured_history' field stores the raw agent turn for context.
        update_payload = {
            "message": final_text_content, 
            "agentsUsed": True, 
            "structured_history": assistant_turn_messages
        }

        # Save if the agent produced any text or tool calls
        if final_text_content.strip():
            await db_manager.update_chat_message(user_id, active_chat_id, assistant_message_id, update_payload)
            logger.info(f"Finalized assistant message for user {user_id} in chat {active_chat_id}. Interrupted: {stream_interrupted}")
        else:
            logger.info(f"No content generated for {user_id}, placeholder will remain empty.")

        yield {"type": "assistantStream", "token": "", "done": True, "messageId": assistant_message_id}
        await asyncio.to_thread(thread.join) # Ensure thread finishes
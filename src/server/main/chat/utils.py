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
from ..config import INTEGRATIONS_CONFIG, SUPERMEMORY_MCP_BASE_URL, SUPERMEMORY_MCP_ENDPOINT_SUFFIX

logger = logging.getLogger(__name__)

async def generate_chat_title(user_input: str) -> str:
    """
    Generates a concise title for a new chat based on the first user query.
    """
    from ..llm import get_qwen_assistant # Local import to avoid circular dependencies
    
    logger.info(f"Generating chat title for input: '{user_input[:50]}...'")
    
    system_prompt = "You are a title generator. Based on the following user query, create a short, concise title for the conversation. The title should be no more than 5 words. Do not add quotes. Just return the title."
    summarizer_agent = get_qwen_assistant(system_message=system_prompt, function_list=[])
    messages = [{'role': 'user', 'content': user_input}]
    
    loop = asyncio.get_running_loop()
    
    def run_and_get_response():
        final_content = ""
        try:
            for response in summarizer_agent.run(messages=messages):
                if isinstance(response, list) and response:
                    last_message = response[-1]
                    if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                        final_content = last_message["content"]
            return final_content.strip().replace('"', '')
        except Exception as e:
            logger.error(f"Error during title generation agent run: {e}", exc_info=True)
            return ""

    generated_title = await loop.run_in_executor(None, run_and_get_response)
    
    # Fallback to the first 3 words if generation fails or returns empty
    return generated_title or ' '.join(user_input.split()[:3])

async def get_chat_history_util(user_id: str, db_manager: MongoManager, chat_id: str) -> List[Dict[str, Any]]:
    """
    Fetches and serializes chat history for a given user and chat ID.
    """
    if not chat_id:
        return []
    messages_from_db = await db_manager.get_chat_history(user_id, chat_id)
    
    serialized_messages = []
    for m in messages_from_db:
        if isinstance(m, dict) and 'timestamp' in m and isinstance(m['timestamp'], datetime.datetime): # type: ignore
            m['timestamp'] = m['timestamp'].isoformat()
        serialized_messages.append(m)
        
    return [m for m in serialized_messages if m.get("isVisible", True)]


async def generate_chat_llm_stream(
    user_id: str,
    messages: List[Dict[str, Any]], # This is now the history from the client
    username: str,
    db_manager: MongoManager,
    enable_internet: bool = False,
    enable_weather: bool = False,
    enable_news: bool = False,
    enable_maps: bool = False,
    enable_shopping: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
    assistant_message_id_override = None # Not needed for stateless overlay chat
    assistant_message_id = assistant_message_id_override or str(uuid.uuid4())

    try:
        user_profile = await db_manager.get_user_profile(user_id)
        supermemory_user_id = user_profile.get("userData", {}).get("supermemory_user_id") if user_profile else None
        
        active_mcp_servers = {}

        # Connect to Supermemory MCP if URL is configured
        if supermemory_user_id:
            full_supermemory_mcp_url = f"{SUPERMEMORY_MCP_BASE_URL.rstrip('/')}/{supermemory_user_id}{SUPERMEMORY_MCP_ENDPOINT_SUFFIX}"
            active_mcp_servers["supermemory"] = {
                "transport": "sse",
                "url": full_supermemory_mcp_url
            }
            logger.info(f"User {user_id} is connected to Supermemory MCP: {full_supermemory_mcp_url}")
        else:
            # This is expected for users who onboarded before this change. They will need to re-onboard or have it manually set.
            logger.warning(f"User {user_id} has no Supermemory User ID configured. Supermemory will be unavailable.")

        # Conditionally connect other tools based on toggles
        active_mcp_servers["chat_tools"] = {"url": INTEGRATIONS_CONFIG["chat_tools"]["mcp_server_config"]["url"], "headers": {"X-User-ID": user_id}}
        
        tool_flags = {
            "internet_search": enable_internet,
            "accuweather": enable_weather,
            "news": enable_news,
            "gmaps": enable_maps,
            "gshopping": enable_shopping
        }

        for service_name, is_enabled in tool_flags.items():
            if is_enabled:
                config = INTEGRATIONS_CONFIG.get(service_name)
                if config and "mcp_server_config" in config:
                    mcp_config = config["mcp_server_config"]
                    active_mcp_servers[mcp_config["name"]] = {"url": mcp_config["url"], "headers": {"X-User-ID": user_id}}

        tools = [{"mcpServers": active_mcp_servers}]

        # Removed saving messages to DB for stateless chat
    except Exception as e:
        logger.error(f"Failed during initial setup for chat stream for user {user_id}: {e}", exc_info=True)
        yield {"type": "error", "message": "Failed to set up chat stream."}
        return

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[Optional[Any]] = asyncio.Queue()

    # Convert the history from the client into the format Qwen Agent expects.
    # The client sends extra keys like 'id', so we strip them out.
    qwen_formatted_history = []
    for msg in messages:
        qwen_formatted_history.append({"role": msg["role"], "content": msg["content"]})

    stream_interrupted = False
    try:
        def worker():
            try:
                system_prompt = (
                    f"You are Sentient, a helpful AI assistant. The user's name is {username}. Today's date is {datetime.datetime.now().strftime('%Y-%m-%d')}.\n\n"
                    "MEMORY:\n"
                    f"- Your memory is handled by Supermemory. Use `supermemory-addToSupermemory` to remember new facts the user tells you (especially personal info or preferences) and `supermemory-search` to recall information.\n"
                    "TASK MANAGEMENT:\n"
                    "- If the user asks for an action that requires multiple steps or external tools (e.g., 'send an email', 'create a presentation', 'summarize a Google Doc'), use the `create_task_from_description` tool to hand it off to the planning system. Do not try to execute these complex actions yourself.\n"
                    "AVAILABLE TOOLS (via Task Management):\n"
                    f"- Internet search is currently {'ENABLED' if enable_internet else 'DISABLED'}.\n"
                    f"- News headlines and articles are currently {'ENABLED' if enable_news else 'DISABLED'}.\n"
                    f"- Google Maps for places and directions is currently {'ENABLED' if enable_maps else 'DISABLED'}.\n"
                    f"- Google Shopping for product searches is currently {'ENABLED' if enable_shopping else 'DISABLED'}.\n\n"
                    "Be conversational and helpful."
                )
                qwen_assistant = get_qwen_assistant(system_message=system_prompt, function_list=tools)
                for new_history_step in qwen_assistant.run(messages=qwen_formatted_history):
                    loop.call_soon_threadsafe(queue.put_nowait, new_history_step)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, {"_error": str(e)})
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        last_yielded_content_str, final_history_state = "", None
        while True:
            current_history = await queue.get()
            if current_history is None: break
            if isinstance(current_history, dict) and "_error" in current_history: raise Exception(f"Qwen Agent failed: {current_history['_error']}")
            if not isinstance(current_history, list): continue

            final_history_state = current_history
            assistant_turn_start_index = next((i + 1 for i in range(len(current_history) - 1, -1, -1) if current_history[i].get('role') == 'user'), 0)
            assistant_messages = current_history[assistant_turn_start_index:]
            current_turn_str = "".join(msg_to_str(m) for m in assistant_messages)
            if len(current_turn_str) > len(last_yielded_content_str):
                new_chunk = current_turn_str[len(last_yielded_content_str):]
                yield {"type": "assistantStream", "token": new_chunk, "done": False, "messageId": assistant_message_id}
                last_yielded_content_str = current_turn_str
    except asyncio.CancelledError:
        stream_interrupted = True; raise
    finally:
        assistant_turn_messages = []
        if final_history_state:
            start_index = next((i for i in range(len(final_history_state) - 1, -1, -1) if final_history_state[i].get('role') == 'user'), -1)
            if start_index != -1: assistant_turn_messages = final_history_state[start_index + 1:]
        
        final_text_content = last_yielded_content_str
        if stream_interrupted and not final_text_content.endswith("[STREAM STOPPED BY USER]"):
            final_text_content += "\n\n[STREAM STOPPED BY USER]"
        
        # Do not save the final response to DB for stateless chat.
        
        yield {"type": "assistantStream", "token": "", "done": True, "messageId": assistant_message_id}
        await asyncio.to_thread(thread.join)

def msg_to_str(msg: Dict[str, Any]) -> str:
    if msg.get('role') == 'assistant' and msg.get('function_call'):
        args_str = msg['function_call'].get('arguments', '')
        try: args_pretty = json.dumps(json.loads(args_str), indent=2)
        except: args_pretty = args_str
        return f"<tool_code name=\"{msg['function_call'].get('name')}\">\n{args_pretty}\n</tool_code>\n"
    elif msg.get('role') == 'function':
        content = msg.get('content', '')
        try: content_pretty = json.dumps(json.loads(content), indent=2)
        except: content_pretty = content
        return f"<tool_result tool_name=\"{msg.get('name')}\">\n{content_pretty}\n</tool_result>\n"
    elif msg.get('role') == 'assistant' and msg.get('content'):
        return msg.get('content', '')
    return ''
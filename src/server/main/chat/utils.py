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
    assistant_message_id = str(uuid.uuid4())

    try:
        user_profile = await db_manager.get_user_profile(user_id)
        supermemory_user_id = user_profile.get("userData", {}).get("supermemory_user_id") if user_profile else None
        
        active_mcp_servers = {}

        if supermemory_user_id:
            full_supermemory_mcp_url = f"{SUPERMEMORY_MCP_BASE_URL.rstrip('/')}/{supermemory_user_id}{SUPERMEMORY_MCP_ENDPOINT_SUFFIX}"
            active_mcp_servers["supermemory"] = {
                "transport": "sse",
                "url": full_supermemory_mcp_url
            }
        
        active_mcp_servers["chat_tools"] = {"url": INTEGRATIONS_CONFIG["chat_tools"]["mcp_server_config"]["url"], "headers": {"X-User-ID": user_id}}
        
        # ADDED: Journal Server
        active_mcp_servers["journal_server"] = {"url": INTEGRATIONS_CONFIG["journal"]["mcp_server_config"]["url"], "headers": {"X-User-ID": user_id}}


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

    except Exception as e:
        logger.error(f"Failed during initial setup for chat stream for user {user_id}: {e}", exc_info=True)
        yield {"type": "error", "message": "Failed to set up chat stream."}
        return

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[Optional[Any]] = asyncio.Queue()

    qwen_formatted_history = []
    for msg in messages:
        qwen_formatted_history.append({"role": msg["role"], "content": msg["content"]})

    stream_interrupted = False
    try:
        def worker():
            try:
                # ADDED: Updated system prompt
                system_prompt = ( # noqa
                    f"You are Sentient, a helpful AI assistant. The user's name is {username}. Today's date is {datetime.datetime.now().strftime('%Y-%m-%d')}.\n\n"
                    "**Core Directives:**\n"
                    "1.  **Think Step-by-Step**: Before responding, break down the user's request into smaller parts. Consider the context of the conversation and the available tools.\n"
                    "2.  **Be Proactive**: If a user's request implies a complex task (e.g., 'plan my trip', 'research this topic and write a summary'), use the `create_task_from_description` tool to delegate it to your planning system. This is your primary way to perform complex actions.\n"
                    "3.  **Utilize Your Memory**: Your memory is powered by Supermemory. To remember new facts about the user or the world, use `supermemory-addToSupermemory`. To recall information, use `supermemory-search`. Always check your memory first before asking the user for information they've already provided.\n"
                    "4.  **Interact with the Journal**: You have access to the user's journal. You can search it with `search_journal(query='...')`, get a summary for a day with `summarize_day(date='YYYY-MM-DD')`, or add new entries with `add_journal_entry(content='...', date='YYYY-MM-DD')`.\n"
                    "5.  **Be Thorough and Clear**: Provide comprehensive and well-reasoned answers. If you use a tool, explain the outcome to the user in a clear, narrative format. Don't just show raw data.\n\n"
                    "**Example Thought Process:**\n"
                    "User: 'Remember that I'm learning to play the guitar.'\n"
                    "Your Thought: 'This is a long-term fact about the user. I should use Supermemory to store it.' -> Call `supermemory-addToSupermemory(memory='The user is learning to play the guitar.')`\n"
                    "User: 'Can you help me plan my marketing campaign for next quarter?'\n"
                    "Your Thought: 'This is a complex task that requires multiple steps like research, content creation, etc. I should hand this off to the planning system.' -> Call `create_task_from_description(task_description='Plan marketing campaign for next quarter')`"
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
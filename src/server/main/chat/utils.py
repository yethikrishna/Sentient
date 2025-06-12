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
                await db_manager.create_new_chat_session(user_id, new_chat_id)
                await db_manager.update_user_profile(user_id, {"userData.active_chat_id": new_chat_id})
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
    username: str,
    db_manager: MongoManager,
    assistant_message_id_override: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
    assistant_message_id = assistant_message_id_override or str(uuid.uuid4())

    try:
        from ..config import INTEGRATIONS_CONFIG
        user_profile_for_tools = await db_manager.get_user_profile(user_id)
        user_connected_integrations = user_profile_for_tools.get("userData", {}).get("integrations", {}) if user_profile_for_tools else {}
        active_mcp_servers = {}
        for service_name, config in INTEGRATIONS_CONFIG.items():
            if "mcp_server_config" not in config: continue
            mcp_config = config["mcp_server_config"]
            if mcp_config.get("url"):
                if config.get("auth_type") == "builtin" or user_connected_integrations.get(service_name, {}).get("connected"):
                    active_mcp_servers[mcp_config["name"]] = {"url": mcp_config["url"], "headers": {"X-User-ID": user_id}}
        tools = [{"mcpServers": active_mcp_servers}]
        
        user_message_payload = {"id": str(uuid.uuid4()), "message": user_input, "isUser": True, "type": "text", "isVisible": True}
        assistant_placeholder_payload = {"id": assistant_message_id, "message": "", "isUser": False, "type": "text", "isVisible": True, "agentsUsed": True}
        
        await db_manager.add_chat_message(user_id, active_chat_id, user_message_payload)
        await db_manager.add_chat_message(user_id, active_chat_id, assistant_placeholder_payload)
    except Exception as e:
        logger.error(f"Failed to save initial messages for user {user_id}: {e}", exc_info=True)
        yield {"type": "error", "message": "Failed to save message."}
        return

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[Optional[Any]] = asyncio.Queue()
    history_from_db, _ = await get_chat_history_util(user_id, db_manager, active_chat_id)
    qwen_formatted_history = []
    for msg in history_from_db:
        if msg.get("id") == assistant_message_id: continue
        if msg.get('isUser'): qwen_formatted_history.append({"role": "user", "content": str(msg.get("message", ""))})
        else:
            if isinstance(msg.get('structured_history'), list) and msg['structured_history']: qwen_formatted_history.extend(msg['structured_history'])
            elif msg.get("message"): qwen_formatted_history.append({"role": "assistant", "content": str(msg.get("message", ""))})
    
    stream_interrupted = False
    try:
        def worker():
            try:
                system_prompt = f"You are a helpful AI assistant. The user's name is {username}. The current date is {datetime.datetime.now().strftime('%Y-%m-%d')}."
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
        
        update_payload = {"message": final_text_content, "structured_history": assistant_turn_messages, "agentsUsed": True}
        if final_text_content.strip(): await db_manager.update_chat_message(user_id, active_chat_id, assistant_message_id, update_payload)
        
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

async def process_voice_command(user_id: str, active_chat_id: str, transcribed_text: str, username: str, db_manager: MongoManager) -> Tuple[str, str]:
    assistant_message_id = str(uuid.uuid4())
    logger.info(f"Processing voice command for user {user_id}: '{transcribed_text}'")

    try:
        user_message_payload = {"id": str(uuid.uuid4()), "message": transcribed_text, "isUser": True, "type": "text", "isVisible": True}
        assistant_placeholder_payload = {"id": assistant_message_id, "message": "[Thinking...]", "isUser": False, "type": "text", "isVisible": True}
        await db_manager.add_chat_message(user_id, active_chat_id, user_message_payload)
        await db_manager.add_chat_message(user_id, active_chat_id, assistant_placeholder_payload)
    except Exception as e:
        logger.error(f"DB Error before voice command processing for {user_id}: {e}", exc_info=True)
        return "I had trouble saving our conversation.", assistant_message_id

    history_from_db, _ = await get_chat_history_util(user_id, db_manager, active_chat_id)
    qwen_formatted_history = []
    for msg in history_from_db:
        if msg.get("id") == assistant_message_id: continue
        if msg.get('isUser'): qwen_formatted_history.append({"role": "user", "content": str(msg.get("message", ""))})
        else:
            if isinstance(msg.get('structured_history'), list) and msg['structured_history']: qwen_formatted_history.extend(msg['structured_history'])
            elif msg.get("message"): qwen_formatted_history.append({"role": "assistant", "content": str(msg.get("message", ""))})

    final_text_response = "I'm sorry, I couldn't process that."
    final_structured_history = []
    try:
        from ..config import INTEGRATIONS_CONFIG
        user_profile_for_tools = await db_manager.get_user_profile(user_id)
        user_integrations = user_profile_for_tools.get("userData", {}).get("integrations", {}) if user_profile_for_tools else {}
        active_mcp_servers = {}
        for service_name, config in INTEGRATIONS_CONFIG.items():
            if "mcp_server_config" not in config: continue
            if config.get("auth_type") == "builtin" or user_integrations.get(service_name, {}).get("connected"):
                mcp_config = config["mcp_server_config"]
                active_mcp_servers[mcp_config["name"]] = {"url": mcp_config["url"], "headers": {"X-User-ID": user_id}}
        tools = [{"mcpServers": active_mcp_servers}]

        system_prompt = f"You are a helpful AI assistant. The user's name is {username}. The current date is {datetime.datetime.now().strftime('%Y-%m-%d')}."
        qwen_assistant = get_qwen_assistant(system_message=system_prompt, function_list=tools)
        
        final_run_response = None
        for response in qwen_assistant.run(messages=qwen_formatted_history):
            final_run_response = response

        if final_run_response and isinstance(final_run_response, list):
            start_index = next((i for i in range(len(final_run_response) - 1, -1, -1) if final_run_response[i].get('role') == 'user'), -1)
            final_structured_history = final_run_response[start_index + 1:] if start_index != -1 else final_run_response
            
            final_agent_message = final_run_response[-1]
            if final_agent_message.get('role') == 'assistant' and final_agent_message.get('content'):
                final_text_response = final_agent_message.get('content', '')
            # Handle cases where the last message might be a tool result
            elif final_agent_message.get('role') == 'function':
                final_text_response = "I have completed the requested action."
                
    except Exception as e:
        logger.error(f"Error in Qwen agent for voice command for {user_id}: {e}", exc_info=True)
        final_text_response = "I encountered an error while thinking about your request."

    update_payload = {"message": final_text_response, "structured_history": final_structured_history, "agentsUsed": True}
    await db_manager.update_chat_message(user_id, active_chat_id, assistant_message_id, update_payload)

    return final_text_response, assistant_message_id
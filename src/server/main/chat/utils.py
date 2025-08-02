import datetime
import uuid
import os
import json
import asyncio
import logging
import datetime
import threading
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Callable, Coroutine, Union

from qwen_agent.tools.base import BaseTool, register_tool

from main.chat.prompts import STAGE_1_SYSTEM_PROMPT, STAGE_2_SYSTEM_PROMPT
from main.db import MongoManager
from main.llm import run_agent_with_fallback
from main.config import (INTEGRATIONS_CONFIG, ENVIRONMENT)
from json_extractor import JsonExtractor

logger = logging.getLogger(__name__)

@register_tool('json_validator')
class JsonValidatorTool(BaseTool):
    description = (
        "Validates and cleans a string that is supposed to be a JSON object or list. "
        "Use this tool to fix any syntax errors in a JSON string before passing it to another tool that requires valid JSON."
    )
    parameters = [{
        'name': 'json_string',
        'type': 'string',
        'description': 'The string to be validated and cleaned as JSON.',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        logger.info(f"JsonValidatorTool called with params: {params}")
        try:
            if isinstance(params, dict):
                 parsed_params = params
            else:
                 parsed_params = json.loads(params)
            json_string_to_validate = parsed_params.get('json_string', '')
            if not json_string_to_validate:
                return json.dumps({"status": "failure", "error": "Input json_string is empty."})
            valid_json = JsonExtractor.extract_valid_json(json_string_to_validate)
            if valid_json:
                cleaned_json_string = json.dumps(valid_json)
                logger.info(f"Successfully cleaned JSON: {cleaned_json_string}")
                return json.dumps({"status": "success", "cleaned_json": cleaned_json_string})
            else:
                logger.warning(f"Could not extract valid JSON from: {json_string_to_validate}")
                return json.dumps({"status": "failure", "error": "Could not extract any valid JSON from the input string."})
        except Exception as e:
            logger.error(f"JsonValidatorTool encountered an unexpected error: {e}", exc_info=True)
            return json.dumps({"status": "failure", "error": str(e)})

async def _get_stage1_response(messages: List[Dict[str, Any]], connected_tools_map: Dict[str, str], disconnected_tools_map: Dict[str, str], user_id: str) -> Union[List[str], str]:
    """
    Uses the Stage 1 LLM to either respond directly or select relevant tools.
    Returns a list of tool names if tools are selected, or a string response if it's a direct answer.
    """
    # Core tools for Stage 1 agent. No access given for now.
    # core_tools = ["memory", "history", "tasks"]
    # mcp_servers_for_stage1 = {}
    # for tool_name in core_tools:
    #     config = INTEGRATIONS_CONFIG.get(tool_name, {})
    #     if config:
    #         mcp_config = config.get("mcp_server_config", {})
    #         if mcp_config and mcp_config.get("url") and mcp_config.get("name"):
    #             mcp_servers_for_stage1[mcp_config["name"]] = {
    #                 "url": mcp_config["url"],
    #                 "headers": {"X-User-ID": user_id},
    #                 "transport": "sse"
    #             }
    # tools_for_agent = [{"mcpServers": mcp_servers_for_stage1}]
    
    # The above section allows adding history, memory and tasks tools to the Stage 1 agent. Commented out for weaker models.

    tools_for_agent = []

    # Format history for the prompt
    # Expand messages so each history item is a separate message dict
    expanded_messages = []
    for msg in messages:
        expanded_messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })

    selector_agent = get_qwen_assistant(system_message=STAGE_1_SYSTEM_PROMPT, function_list=tools_for_agent)
    messages = expanded_messages

    def _run_stage1_sync():
        final_content_str = ""
        for chunk in run_agent_with_fallback(system_message=STAGE_1_SYSTEM_PROMPT, function_list=tools_for_agent, messages=messages):
            if isinstance(chunk, list) and chunk:
                last_message = chunk[-1]
                if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                    final_content_str = last_message["content"]
        return final_content_str

    final_content_str = await asyncio.to_thread(_run_stage1_sync)

    # Now, parse the output. Is it a JSON list or a text response?
    cleaned_output = final_content_str.strip()

    # Try to parse as JSON list first. This is the tool selection case.
    json_tools = JsonExtractor.extract_valid_json(cleaned_output)
    if isinstance(json_tools, list):
        logger.info(f"Stage 1 selected tools: {json_tools}")
        # Validate that the selected tools are from the available list
        valid_tools = [tool for tool in json_tools if tool in connected_tools_map]
        return valid_tools

    # If it's not a JSON list, it's a direct response.
    logger.info("Stage 1 is providing a direct response.")
    return final_content_str # Return the full string with tags for the stream generator to parse.

def _extract_answer_from_llm_response(llm_output: str) -> str:
    """
    Extracts content from the first <answer> tag in the LLM's output.
    This ensures only the user-facing response is used for TTS.
    """
    if not llm_output:
        return ""
    match = re.search(r'<answer>([\s\S]*?)</answer>', llm_output, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: if no answer tag, strip all other tags and return what's left.
    return re.sub(r'<(think|tool_code|tool_result)>.*?</\1>', '', llm_output, flags=re.DOTALL).strip()

def _get_tool_lists(user_integrations: Dict) -> Tuple[Dict, Dict]:
    """Separates tools into connected and disconnected lists."""
    connected_tools = {} # Tools that are built-in or connected by the user
    disconnected_tools = {}
    for tool_name, config in INTEGRATIONS_CONFIG.items():
        auth_type = config.get("auth_type")
        # Skip internal tools that shouldn't be exposed to the planner/user
        if tool_name in ["progress_updater", "chat_tools"]:
            continue

        # Built-in tools are always considered "connected" and available
        if auth_type == "builtin":
            connected_tools[tool_name] = config.get("description", "")
        # For user-configured tools, check the 'connected' flag from the DB
        elif auth_type in ["oauth", "manual"]:
            if user_integrations.get(tool_name, {}).get("connected", False):
                connected_tools[tool_name] = config.get("description", "")
            else:
                disconnected_tools[tool_name] = config.get("description", "")
    return connected_tools, disconnected_tools

async def generate_chat_llm_stream(
    user_id: str,
    messages: List[Dict[str, Any]],
    user_context: Dict[str, Any], # Basic context like name, timezone
    db_manager: MongoManager) -> AsyncGenerator[Dict[str, Any], None]:
    assistant_message_id = str(uuid.uuid4())

    try:
        yield {"type": "status", "message": "Analyzing context..."}

        username = user_context.get("name", "User")
        timezone_str = user_context.get("timezone", "UTC")
        location_raw = user_context.get("location")

        if isinstance(location_raw, dict) and 'latitude' in location_raw:
            location = f"latitude: {location_raw.get('latitude')}, longitude: {location_raw.get('longitude')}"
        elif isinstance(location_raw, str):
            location = location_raw
        else:
            location = "Not specified"
        try:
            user_timezone = ZoneInfo(timezone_str)
        except ZoneInfoNotFoundError:
            user_timezone = ZoneInfo("UTC")

        current_user_time = datetime.datetime.now(user_timezone).strftime('%Y-%m-%d %H:%M:%S %Z')

        user_profile = await db_manager.get_user_profile(user_id)
        user_integrations = user_profile.get("userData", {}).get("integrations", {}) if user_profile else {}

        # Get both connected and disconnected tools
        connected_tools, disconnected_tools = _get_tool_lists(user_integrations)

        all_available_mcp_servers = {}
        # Populate MCP servers for all tools that Stage 2 might use:
        # 1. User-connected tools (from connected_tools)
        # 2. Built-in tools (memory, history, tasks)
        tools_for_mcp_server_list = set(connected_tools.keys()) | {"memory", "history", "tasks"}

        for tool_name in tools_for_mcp_server_list:
            config = INTEGRATIONS_CONFIG.get(tool_name, {})
            if config:
                mcp_config = config.get("mcp_server_config", {})
                if mcp_config and mcp_config.get("url") and mcp_config.get("name"):
                    all_available_mcp_servers[mcp_config["name"]] = {"url": mcp_config["url"], "headers": {"X-User-ID": user_id}, "transport": "sse"}

        yield {"type": "status", "message": "Thinking..."}

        # --- STAGE 1 ---
        stage1_output = await _get_stage1_response(messages, connected_tools, disconnected_tools, user_id)

        if isinstance(stage1_output, str):
            # --- DIRECT RESPONSE FROM STAGE 1 ---
            logger.info(f"Stage 1 provided a direct response for user {user_id}. Streaming it back.")
            yield {"type": "assistantStream", "token": stage1_output, "done": True, "messageId": assistant_message_id}
            return # End of stream

        # --- TOOL SELECTION, PROCEED TO STAGE 2 ---
        relevant_tool_names = stage1_output

        tool_display_names = [INTEGRATIONS_CONFIG.get(t, {}).get('display_name', t) for t in relevant_tool_names if t != 'memory']
        if tool_display_names:
            yield {"type": "status", "message": f"Using: {', '.join(tool_display_names)}"}

        # Stage 2 agent also needs access to core tools
        mandatory_tools = {"memory", "history", "tasks"}
        final_tool_names = set(relevant_tool_names) | mandatory_tools

        filtered_mcp_servers = {}
        # Build the list of tools for the agent, including MCPs and local tools
        for server_name, server_config in all_available_mcp_servers.items():
            tool_name_for_server = next((tn for tn, tc in INTEGRATIONS_CONFIG.items() if tc.get("mcp_server_config", {}).get("name") == server_name), None)
            if tool_name_for_server in final_tool_names:
                filtered_mcp_servers[server_name] = server_config

        tools = [{"mcpServers": filtered_mcp_servers}]

        logger.info(f"Final tools for agent: {list(filtered_mcp_servers.keys())}")
        
    except Exception as e:
        logger.error(f"Failed during initial setup for chat stream for user {user_id}: {e}", exc_info=True)
        yield {"type": "error", "message": "Failed to set up chat stream."}
        return

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[Optional[Any]] = asyncio.Queue()
    
    # Prepare message history for the LLM, including IDs for user messages
    # history_for_llm = []
    # for msg in messages[-30:]: # Limit context to the last 30 messages
    #     history_for_llm.append(f"<{msg['role']}" + (f" id='{msg.get('id')}'" if msg.get('id') and msg['role'] == 'user' else "") + f">{msg['content']}</{msg['role']}>")
        
    stage_2_expanded_messages = []
    for msg in messages:
        stage_2_expanded_messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })

    system_prompt = STAGE_2_SYSTEM_PROMPT.format(
        username=username,
        location=location,
        current_user_time=current_user_time
    )

    def worker():
        try:
            # Use the new formatted history with IDs
            qwen_formatted_history = [{"role": "user", "content": "\n".join(history_for_llm)}]
            for new_history_step in run_agent_with_fallback(system_message=system_prompt, function_list=tools, messages=qwen_formatted_history):
                loop.call_soon_threadsafe(queue.put_nowait, new_history_step)
        except Exception as e:
            logger.error(f"Error in chat worker thread for user {user_id}: {e}", exc_info=True)
            loop.call_soon_threadsafe(queue.put_nowait, {"_error": str(e)})
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    try:
        first_chunk = True
        last_yielded_content_str = ""
        while True:
            current_history = await queue.get()
            if current_history is None:
                break
            if isinstance(current_history, dict) and "_error" in current_history:
                raise Exception(f"Qwen Agent worker failed: {current_history['_error']}")
            if not isinstance(current_history, list):
                continue
            
            assistant_turn_start_index = next((i + 1 for i in range(len(current_history) - 1, -1, -1) if current_history[i].get('role') == 'user'), 0)
            assistant_messages = current_history[assistant_turn_start_index:]
            current_turn_str = "".join(msg_to_str(m) for m in assistant_messages)
            if len(current_turn_str) > len(last_yielded_content_str):
                new_chunk = current_turn_str[len(last_yielded_content_str):]
                event_payload = {"type": "assistantStream", "token": new_chunk, "done": False, "messageId": assistant_message_id}
                if first_chunk and new_chunk.strip():
                    event_payload["tools"] = list(final_tool_names)
                    first_chunk = False
                yield event_payload
                last_yielded_content_str = current_turn_str

    except asyncio.CancelledError:
        stream_interrupted = True
        raise
    except Exception as e:
        logger.error(f"Error during main chat agent run for user {user_id}: {e}", exc_info=True)
        yield {"type": "error", "message": "An unexpected error occurred in the chat agent."}
    finally:
        yield {"type": "assistantStream", "token": "", "done": True, "messageId": assistant_message_id}

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

async def process_voice_command(
    user_id: str,
    transcribed_text: str,
    send_status_update: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]],
    db_manager: MongoManager
) -> Tuple[str, str]:
    """
    Processes a transcribed voice command with full agentic capabilities,
    providing status updates and returning a final text response for TTS.
    """
    assistant_message_id = str(uuid.uuid4())
    logger.info(f"Processing voice command for user {user_id}: '{transcribed_text}'")

    try:
        # 1. Save user message and a placeholder for the assistant's response
        await db_manager.add_message(user_id=user_id, role="user", content=transcribed_text)
        await db_manager.add_message(user_id=user_id, role="assistant", content="[Thinking...]", message_id=assistant_message_id)

        # 2. Fetch history and user context
        history_from_db = await db_manager.get_message_history(user_id, limit=30)
        messages = list(reversed(history_from_db))
        qwen_formatted_history = [msg for msg in messages if msg.get("message_id") != assistant_message_id]

        user_profile = await db_manager.get_user_profile(user_id)
        user_data = user_profile.get("userData", {}) if user_profile else {}
        personal_info = user_data.get("personalInfo", {})
        
        username = personal_info.get("name", "User")
        timezone_str = personal_info.get("timezone", "UTC")
        location_raw = personal_info.get("location")

        if isinstance(location_raw, dict) and 'latitude' in location_raw:
            location = f"latitude: {location_raw.get('latitude')}, longitude: {location_raw.get('longitude')}"
        elif isinstance(location_raw, str):
            location = location_raw
        else:
            location = "Not specified"
        try:
            user_timezone = ZoneInfo(timezone_str)
        except ZoneInfoNotFoundError:
            user_timezone = ZoneInfo("UTC")
        current_user_time = datetime.datetime.now(user_timezone).strftime('%Y-%m-%d %H:%M:%S %Z')

        # 3. Full tool selection logic
        await send_status_update({"type": "status", "message": "choosing_tools"})
        
        user_integrations = user_data.get("integrations", {})
        connected_tools, disconnected_tools = _get_tool_lists(user_integrations)

        all_available_mcp_servers = {}
        # Populate MCP servers for all tools that Stage 2 might use:
        # 1. User-connected tools (from connected_tools)
        # 2. Built-in tools (memory, history, tasks)
        tools_for_mcp_server_list = set(connected_tools.keys()) | {"memory", "history", "tasks"}

        for tool_name in tools_for_mcp_server_list:
            config = INTEGRATIONS_CONFIG.get(tool_name, {})
            if config:
                mcp_config = config.get("mcp_server_config", {})
                if mcp_config and mcp_config.get("url") and mcp_config.get("name"):
                    all_available_mcp_servers[mcp_config["name"]] = {"url": mcp_config["url"], "headers": {"X-User-ID": user_id}, "transport": "sse"}

        # Call Stage 1
        stage1_output = await _get_stage1_response(qwen_formatted_history, connected_tools, disconnected_tools, user_id)

        final_text_response = "I'm sorry, I couldn't process that." # Default error message

        if isinstance(stage1_output, str):
            # Stage 1 provided a direct response
            logger.info(f"Stage 1 provided a direct response for voice command for user {user_id}.")
            final_text_response = _extract_answer_from_llm_response(stage1_output)
        else:
            # Stage 1 selected tools, proceed to Stage 2
            relevant_tool_names = stage1_output
            mandatory_tools = {"memory", "history", "tasks"}
            final_tool_names = set(relevant_tool_names) | mandatory_tools

            filtered_mcp_servers = {}
            for server_name, server_config in all_available_mcp_servers.items():
                tool_name_for_server = next((tn for tn, tc in INTEGRATIONS_CONFIG.items() if tc.get("mcp_server_config", {}).get("name") == server_name), None)
                if tool_name_for_server in final_tool_names:
                    filtered_mcp_servers[server_name] = server_config

            tools = [{"mcpServers": filtered_mcp_servers}]
            logger.info(f"Voice Command Tools (Stage 2): {list(filtered_mcp_servers.keys())}")
                
            expanded_messages = []
            for msg in qwen_formatted_history:
                expanded_messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
            
            system_prompt = STAGE_2_SYSTEM_PROMPT.format(
                username=username,
                location=location,
                current_user_time=current_user_time
            )
            
            await send_status_update({"type": "status", "message": "thinking"})
            
            # --- MODIFICATION: Run blocking agent code in a separate thread ---
            loop = asyncio.get_running_loop()
            def agent_worker():
                final_run_response = None
                try:
                    for response in run_agent_with_fallback(system_message=system_prompt, function_list=tools, messages=qwen_formatted_history_for_agent):

                        if isinstance(response, list) and response:
                                # Schedule the async status update on the main event loop
                                asyncio.run_coroutine_threadsafe(
                                    send_status_update({"type": "status", "message": f"using_tool_{tool_name}"}),
                                    loop
                                )
                    return final_run_response
                except Exception as e:
                    logger.error(f"Error inside agent_worker thread for voice command: {e}", exc_info=True)
                    return None

            final_run_response = await asyncio.to_thread(agent_worker)
            # --- END MODIFICATION ---
            
            if final_run_response and isinstance(final_run_response, list):
                assistant_content_parts = [
                    msg.get('content', '') 
                    for msg in final_run_response 
                    if msg.get('role') == 'assistant' and msg.get('content')
                ]
                full_response_str = "".join(assistant_content_parts)
                final_text_response = _extract_answer_from_llm_response(full_response_str)

                if not final_text_response:
                    last_message = final_run_response[-1]
                    if last_message.get('role') == 'function':
                        final_text_response = "I have completed the requested action."

        await db_manager.messages_collection.update_one(
            {"message_id": assistant_message_id},
            {"$set": {"content": final_text_response}}
        )

        return final_text_response, assistant_message_id
    except Exception as e:
        logger.error(f"Error processing voice command for {user_id}: {e}", exc_info=True)
        error_msg = "I encountered an error while processing your request."
        await db_manager.messages_collection.update_one(
            {"message_id": assistant_message_id},
            {"$set": {"content": error_msg}}
        )
        return error_msg, assistant_message_id
import datetime
import uuid
import os
import json
import asyncio
import logging
import datetime
import threading
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from qwen_agent.tools.base import BaseTool, register_tool

from main.chat.prompts import TOOL_SELECTOR_SYSTEM_PROMPT
from main.db import MongoManager
from main.llm import get_qwen_assistant
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

async def _select_relevant_tools(query: str, available_tools_map: Dict[str, str]) -> List[str]:
    """
    Uses a lightweight LLM call to select relevant tools for a given query.
    This now runs the synchronous generator in a thread to avoid blocking.
    """
    if not available_tools_map:
        return []

    try:
        tools_description = "\n".join(f"- `{name}`: {desc}" for name, desc in available_tools_map.items())
        prompt = f"User Query: \"{query}\"\n\nAvailable Tools:\n{tools_description}"

        selector_agent = get_qwen_assistant(system_message=TOOL_SELECTOR_SYSTEM_PROMPT, function_list=[])
        messages = [{'role': 'user', 'content': prompt}]

        def _run_selector_sync():
            """Synchronous worker function to run the generator."""
            final_content_str = ""
            for chunk in selector_agent.run(messages=messages):
                if isinstance(chunk, list) and chunk:
                    last_message = chunk[-1]
                    if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                        final_content_str = last_message["content"]
            return final_content_str

        # Run the synchronous function in a separate thread
        final_content_str = await asyncio.to_thread(_run_selector_sync)

        selected_tools = JsonExtractor.extract_valid_json(final_content_str)
        if isinstance(selected_tools, list):
            logger.info(f"Tool selector identified relevant tools: {selected_tools}")
            return selected_tools
        return []
    except Exception as e:
        logger.error(f"Error during tool selection LLM call: {e}", exc_info=True)
        return list(available_tools_map.keys())

def _get_tool_lists(user_integrations: Dict) -> Tuple[Dict, Dict]:
    """Separates tools into connected and disconnected lists."""
    connected_tools = {}
    disconnected_tools = {}
    for tool_name, config in INTEGRATIONS_CONFIG.items():
        # We only care about tools that require user connection (oauth or manual)
        if config.get("auth_type") not in ["oauth", "manual"]:
            continue

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
        tool_name_to_desc_map = connected_tools.copy() # Start with connected tools

        # Add other built-in tools
        for tool_name, config in INTEGRATIONS_CONFIG.items():
            if config.get("auth_type") == "builtin":
                 tool_name_to_desc_map[tool_name] = config.get("description")

        # Now, populate MCP servers for all available (connected + built-in) tools
        for tool_name in tool_name_to_desc_map.keys():
            config = INTEGRATIONS_CONFIG.get(tool_name, {})
            if config:
                mcp_config = config.get("mcp_server_config", {})
                if mcp_config and mcp_config.get("url") and mcp_config.get("name"):
                    all_available_mcp_servers[mcp_config["name"]] = {"url": mcp_config["url"], "headers": {"X-User-ID": user_id}, "transport": "sse"}

        last_user_query = messages[-1].get("content", "") if messages else ""
        relevant_tool_names = await _select_relevant_tools(last_user_query, tool_name_to_desc_map)

        mandatory_tools = {"memory"}
        final_tool_names = set(relevant_tool_names) | mandatory_tools

        filtered_mcp_servers = {}
        # Build the list of tools for the agent, including MCPs and local tools
        for server_name, server_config in all_available_mcp_servers.items():
            tool_name_for_server = next((tn for tn, tc in INTEGRATIONS_CONFIG.items() if tc.get("mcp_server_config", {}).get("name") == server_name), None)
            if tool_name_for_server in final_tool_names:
                filtered_mcp_servers[server_name] = server_config

        tools = [{"mcpServers": filtered_mcp_servers}, 'json_validator']

        logger.info(f"Final tools for agent: {list(filtered_mcp_servers.keys())}  json_validator")
        
    except Exception as e:
        logger.error(f"Failed during initial setup for chat stream for user {user_id}: {e}", exc_info=True)
        yield {"type": "error", "message": "Failed to set up chat stream."}
        return

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[Optional[Any]] = asyncio.Queue()
    stream_interrupted = False
    
    disconnected_tools_list_str = "\n".join([f"- `{name}`: {desc}" for name, desc in disconnected_tools.items()])
    disconnected_tools_prompt_section = (
        f"**Disconnected Tools (User needs to connect these in Settings):**\n{disconnected_tools_list_str}\n\n"
        if disconnected_tools_list_str else ""
    )

    # Prepare message history for the LLM, including IDs for user messages
    history_for_llm = []
    for msg in messages[-30:]: # Limit context to the last 30 messages
        history_for_llm.append(f"<{msg['role']}" + (f" id='{msg['id']}'" if msg.get('id') and msg['role'] == 'user' else "") + f">{msg['content']}</{msg['role']}>")

    system_prompt = (
        f"You are Sentient, a personalized AI assistant. Your goal is to be as helpful as possible by using your available tools to directly execute tasks and help the user track their schedule.\n\n"
        f"**Accessing Your Memory:**\n"
        f"Your immediate context is limited to the last 30 messages of this conversation. To recall older information, you MUST use the following tools:\n"
        f"- `history_mcp-semantic_search`: Use this when the user asks about a topic or concept from the past (e.g., \"What did we decide about the marketing plan?\").\n"
        f"- `history_mcp-time_based_search`: Use this when the user asks about a specific time period (e.g., \"Remind me what we talked about last Tuesday.\").\n" # noqa
        f"- `memory_mcp-search_memory`: Use this to recall specific facts, preferences, or details about the user that have been explicitly saved to your memory.\n" # noqa
        f"Always check your memory and conversation history before asking the user a question you might already know the answer to.\n\n"
        f"**Critical Instructions:**\n"
        f"1. **Replying to a Specific Message:** The conversation history is provided with unique IDs for each user message (e.g., `<user id='user-162...'>`). If your response is a direct answer to a specific earlier message, you MUST wrap your final answer in a `<reply_to>` tag with that message's ID. Example: `<reply_to id='user-162...'>Your analysis is correct.</reply_to>`.\n"
        f"2. **Validate Complex JSON:** Before calling any tool that requires a complex JSON string as a parameter (like Notion's `content_blocks_json`), you MUST first pass your generated JSON string to the `json_validator` tool to ensure it is syntactically correct. Use the cleaned output from `json_validator` in the subsequent tool call.\n" # noqa
        f"3. **Handle Disconnected Tools:** You have a list of tools the user has not connected yet. If the user's query clearly refers to a capability from this list (e.g., asking to 'send a slack message' when Slack is disconnected), you MUST stop and politely inform the user that they need to connect the tool in the Integrations page. Do not proceed with other tools.\n"
        f"4. For any command to create, send, search, or read information (e.g., create a document, send an email, search for files), you MUST call the appropriate tool directly. Complete the task within the chat and provide the result to the user.\n"
        f"5. **Saving New Information:** If you learn a new, permanent fact about the user (e.g., their manager's name, a new preference), you MUST use `memory_mcp-cud_memory` to save it for future reference. This is an asynchronous operation, so inform the user that the memory \n" # noqa
        f"6. **Final Answer Format:** When you have a complete, final answer for the user that is not a tool call, you MUST wrap it in `<answer>` tags. For example: `<answer>The weather in London is 15°C and cloudy.</answer>`.\n\n" # noqa
        f"{disconnected_tools_prompt_section}"
        f"**User Context (for your reference):**\n"
        f"-   **User's Name:** {username}\n"
        f"-   **User's Location:** {location}\n"
        f"-   **Current Time:** {current_user_time}\n\n"
        f"Your primary directive is to be as personalized and helpful as possible by actively using your memory and tools."
    )

    def worker():
        try:
            qwen_assistant = get_qwen_assistant(system_message=system_prompt, function_list=tools)
            # Use the new formatted history with IDs
            qwen_formatted_history = [{"role": "user", "content": "\n".join(history_for_llm)}]
            for new_history_step in qwen_assistant.run(messages=qwen_formatted_history):
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

async def process_voice_command(user_id: str, transcribed_text: str, username: str, db_manager: MongoManager) -> Tuple[str, str]:
    """
    Processes a transcribed voice command. It's a non-streaming version of the chat logic.
    It fetches history, calls the LLM once, gets a complete response, and saves messages.
    """
    assistant_message_id = str(uuid.uuid4())
    logger.info(f"Processing voice command for user {user_id}: '{transcribed_text}'")

    try:
        # Save user message
        await db_manager.add_message(user_id=user_id, role="user", content=transcribed_text)
        # Save a placeholder for the assistant's response
        await db_manager.add_message(user_id=user_id, role="assistant", content="[Thinking...]", message_id=assistant_message_id)
    except Exception as e:
        logger.error(f"DB Error before voice command processing for {user_id}: {e}", exc_info=True)
        return "I had trouble saving our conversation.", assistant_message_id

    # Fetch history for context
    history_from_db = await db_manager.get_message_history(user_id, limit=30)
    qwen_formatted_history = [msg for msg in reversed(history_from_db) if msg.get("id") != assistant_message_id]
    qwen_formatted_history.append({"role": "user", "content": transcribed_text})

    final_text_response = "I'm sorry, I couldn't process that."
    final_structured_history = []
    try:
        user_profile_for_tools = await db_manager.get_user_profile(user_id)
        user_integrations = user_profile_for_tools.get("userData", {}).get("integrations", {}) if user_profile_for_tools else {}
        
        active_mcp_servers = {}
        for service_name, config in INTEGRATIONS_CONFIG.items():
            if "mcp_server_config" not in config: continue
            if config.get("auth_type") == "builtin" or user_integrations.get(service_name, {}).get("connected"):
                mcp_config = config["mcp_server_config"]
                active_mcp_servers[mcp_config["name"]] = {"url": mcp_config["url"], "headers": {"X-User-ID": user_id}}
        tools = [{"mcpServers": active_mcp_servers}]

        system_prompt = (
            f"You are a helpful AI assistant named Sentient. The user's name is {username}. The current date is {datetime.datetime.now().strftime('%Y-%m-%d')}.\n\n"
            "You have access to tools. For voice conversations, keep your responses concise and natural."
        )
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
            elif final_agent_message.get('role') == 'function':
                final_text_response = "I have completed the requested action."
                
    except Exception as e:
        logger.error(f"Error in Qwen agent for voice command for {user_id}: {e}", exc_info=True)
        final_text_response = "I encountered an error while thinking about your request."

    await db_manager.messages_collection.update_one(
        {"message_id": assistant_message_id},
        {"$set": {"content": final_text_response, "structured_history": final_structured_history}}
    )

    return final_text_response, assistant_message_id
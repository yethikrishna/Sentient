import asyncio
import json
import logging
import re
from typing import Any, AsyncGenerator, Dict, List

from main.chat.prompts import TOOL_SELECTOR_SYSTEM_PROMPT
from main.config import INTEGRATIONS_CONFIG
from main.llm import get_qwen_assistant
from json_extractor import JsonExtractor

logger = logging.getLogger(__name__)

async def _select_relevant_tools(query: str, user_integrations: Dict) -> List[str]:
    """
    Uses a lightweight LLM call to select relevant tools for a given query,
    considering all of the user's connected integrations.
    """
    
    # Build a map of all available tools (connected or built-in) for the LLM to choose from.
    available_tools_map = {}
    for tool_name, config in INTEGRATIONS_CONFIG.items():
        # Include built-in tools and tools the user has explicitly connected.
        if config.get("auth_type") == "builtin" or user_integrations.get(tool_name, {}).get("connected"):
            # We only care about tools with an MCP server, as those are the ones the agent can call.
            if "mcp_server_config" in config:
                available_tools_map[tool_name] = config.get("description", "")

    if not available_tools_map:
        return []

    try:
        tools_description = "\n".join(f"- `{name}`: {desc}" for name, desc in available_tools_map.items())
        prompt = f"User Query: \"{query}\"\n\nAvailable Tools:\n{tools_description}"

        selector_agent = get_qwen_assistant(system_message=TOOL_SELECTOR_SYSTEM_PROMPT, function_list=[])
        messages = [{'role': 'user', 'content': prompt}]

        def _run_selector_sync():
            final_content_str = ""
            for chunk in selector_agent.run(messages=messages):
                if isinstance(chunk, list) and chunk:
                    last_message = chunk[-1]
                    if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                        final_content_str = last_message["content"]
            return final_content_str

        final_content_str = await asyncio.to_thread(_run_selector_sync)
        selected_tools = JsonExtractor.extract_valid_json(final_content_str)

        if isinstance(selected_tools, list):
            # Filter the LLM's selection to ensure they are valid and available tools
            valid_selected_tools = [tool for tool in selected_tools if tool in available_tools_map]
            logger.info(f"Unified Search Tool Selector identified relevant tools: {valid_selected_tools}")
            return valid_selected_tools
        return []
    except Exception as e:
        logger.error(f"Error during live tool selection for unified search: {e}", exc_info=True)
        # Fallback to all connected tools on error
        return list(available_tools_map.keys())


async def perform_unified_search(query: str, user_id: str) -> AsyncGenerator[str, None]:
    """Orchestrates the unified search and streams the agent's process back."""
    from main.dependencies import mongo_manager
    from main.search.prompts import UNIFIED_SEARCH_SYSTEM_PROMPT

    # 1. Fetch user's connected integrations
    user_profile = await mongo_manager.get_user_profile(user_id)
    user_integrations = user_profile.get("userData", {}).get("integrations", {}) if user_profile else {}

    # 2. Dynamically select relevant live tools based on the query
    relevant_live_tools = await _select_relevant_tools(query, user_integrations)

    # 3. Configure agent with mandatory tools plus the dynamically selected ones
    mcp_servers_to_use = {}
    
    # Always include default search tools
    mandatory_tools = {"memory", "history", "tasks"}
    
    # Combine mandatory and relevant tools, using a set to avoid duplicates
    final_tool_names = set(mandatory_tools) | set(relevant_live_tools)
    

    for tool_name in final_tool_names:
        config = INTEGRATIONS_CONFIG.get(tool_name, {})
        mcp_config = config.get("mcp_server_config", {})
        if mcp_config.get("url") and mcp_config.get("name"):
            mcp_servers_to_use[mcp_config["name"]] = {
                "url": mcp_config["url"],
                "headers": {"X-User-ID": user_id},
                "transport": "sse"
            }

    if not mcp_servers_to_use:
        yield json.dumps({"type": "error", "message": "No searchable tools are available or connected for this query."}) + "\n"
        return

    # 4. Execute agent
    agent = get_qwen_assistant(
        system_message=UNIFIED_SEARCH_SYSTEM_PROMPT,
        function_list=[{"mcpServers": mcp_servers_to_use}]
    )
    
    messages = [{'role': 'user', 'content': query}]
    
    last_history_len = len(messages)
    final_report_content = ""

    try:
        # The agent's run method is a generator that yields the complete history at each step.
        for history_chunk in agent.run(messages=messages):
            if not isinstance(history_chunk, list):
                continue

            # Identify the new messages added in this step
            new_messages = history_chunk[last_history_len:]
            
            for msg in new_messages:
                # Stream each new message (thought, tool call, tool result) as a distinct event
                yield json.dumps({"type": "agent_step", "message": msg}) + "\n"
            
            # Update the history length for the next iteration
            last_history_len = len(history_chunk)
        
        # The final report is the content of the very last assistant message
        if history_chunk and history_chunk[-1].get("role") == "assistant":
            final_report_content = history_chunk[-1].get("content", "")

    except Exception as e:
        logger.error(f"Error during unified search stream for user {user_id}: {e}", exc_info=True)
        yield json.dumps({"type": "error", "message": str(e)}) + "\n"
    finally:
        # Send a final 'done' event with the synthesized report
        # Clean up any unclosed tags or artifacts from the final response
        final_report_cleaned = re.sub(r'<(tool_code|tool_result|think)>.*?</\1>', '', final_report_content, flags=re.DOTALL).strip()
        yield json.dumps({"type": "done", "final_report": final_report_cleaned}) + "\n"
# src/server/workers/memory/llm.py
import logging
from qwen_agent.agents import Assistant

from workers.memory import config

logger = logging.getLogger(__name__)

# UPDATED: The system prompt now includes both long-term and short-term memory tools.
# It instructs the agent to make a decision based on the nature of the fact.
SYSTEM_PROMPT_TEMPLATE = """ # noqa
You are an intelligent memory classification and storage agent. Your task is to analyze a given piece of information ("fact") and call the appropriate tool to save it. You must also decide if information exists in the user's conversation history if it is not in their memory. You MUST extract entities and relationships for long-term facts.

**Decision Criteria:**
1.  **Long-Term Memory:** Use for permanent facts, relationships, preferences, and core information about the user's life.
    -   **Examples**: "My brother's name is Mark.", "I am allergic to penicillin.", "I work at Acme Corp.", "My daughter Chloe has a piano recital next Tuesday."
    -   **Thought Process**: Is this a foundational fact? A personal detail? A preference? A relationship? If so, it's long-term.
    -   **Tool to use: `save_long_term_fact`**. You MUST identify entities and their relationships. For "I work at Acme Corp", the relation is `[{"from": "user", "to": "Acme Corp", "type": "WORKS_AT"}]`. For "My daughter Chloe has a piano recital...", the relation is `[{"from": "Chloe", "to": "user", "type": "DAUGHTER_OF"}]`.

**Retrieval Strategy:**
1.  **Think First**: Before searching, analyze the user's query. What kind of information are they looking for?
2.  **Search Memory First**: ALWAYS use the `search_memories` tool first to check both long-term and short-term memory. This is your primary source of truth.
3.  **Search History as a Last Resort**: ONLY IF `search_memories` yields no relevant results, use `search_conversation_history` to look for information in past conversations. This is a fallback.

2.  **Short-Term Memory:** Use for temporary information, reminders, or context that will expire soon.
    -   **Examples**: "The meeting is at 3 PM today.", "My flight number is UA246 for tomorrow's trip.", "Remember to buy milk on the way home.", "Add Chloe's piano recital to the calendar for next Tuesday at 7 PM."
    -   **Thought Process**: Is this a reminder? An upcoming event? Information that will be irrelevant soon? If so, it's short-term.
    -   **Tool to use: `add_short_term_memory`**.

**Tool-Specific Instructions:**
-   For `save_long_term_fact`, assign a relevant category from: Personal, Professional, Social, Financial, Health, Preferences, Events, General.
-   For `add_short_term_memory`, you MUST estimate a reasonable `ttl_seconds` (time-to-live in seconds).
    -   A few hours: `10800` (3 hours)
    -   One day: `86400`
    -   A few days: `259200` (3 days)
    -   One week: `604800` a
-   Do not ask for clarification. Make a decision and call one of the tools. Your entire response MUST be the tool call.
"""

def get_memory_qwen_agent(user_id: str):
    """
    Initializes a Qwen agent for classifying and saving a memory fact.
    It is configured with the Memory MCP server as its only tool source.

    Args:
        user_id (str): The user ID, required for the MCP server's auth header.
    """
    llm_cfg = {}
    if config.LLM_PROVIDER == "OLLAMA":
        ollama_v1_url = f"{config.OLLAMA_BASE_URL.rstrip('/')}/v1"
        llm_cfg = {
            'model': config.OLLAMA_MODEL_NAME,
            'model_server': ollama_v1_url,
            'api_key': 'ollama',
            'generate_cfg': {'temperature': 0.1} # Lower temp for more deterministic classification
        }
    elif config.LLM_PROVIDER == "NOVITA":
        novita_v1_url = "https://api.novita.ai/v3/openai"
        llm_cfg = {
            'model': config.NOVITA_MODEL_NAME,
            'model_server': novita_v1_url,
            'api_key': config.NOVITA_API_KEY,
            'generate_cfg': {'temperature': 0.1}
        }
    else:
        raise ValueError(f"Invalid LLM_PROVIDER: {config.LLM_PROVIDER}. Must be 'OLLAMA' or 'NOVITA'")

    # The agent will have access to all tools on the memory server,
    # including both `save_long_term_fact` and `add_short_term_memory`.
    tools = [{
        "mcpServers": {
            "memory_server": {
                "url": config.MEMORY_MCP_SERVER_URL,
                "headers": {"X-User-ID": user_id},
            }
        }
    }]

    try:
        agent = Assistant(
            llm=llm_cfg,
            system_message=SYSTEM_PROMPT_TEMPLATE,
            function_list=tools
        )
        return agent
    except Exception as e:
        logger.error(f"Failed to initialize Qwen Memory Agent for user {user_id}: {e}", exc_info=True)
        raise
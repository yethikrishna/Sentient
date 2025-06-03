# This file can be significantly reduced or removed if dummy responses are hardcoded.
# If a very simple local LLM is used for the dummy chat, a minimal prompt might be kept.

# For a truly dummy response, no prompts are needed.
# If using a local LLM for a slightly more dynamic dummy response:
DUMMY_CHAT_SYSTEM_PROMPT_TEMPLATE = """You are a helpful AI assistant. Provide a very short, generic, and placeholder-like response. Indicate that you are in a simplified mode."""

DUMMY_CHAT_USER_PROMPT_TEMPLATE = """The user said: {query}. Your brief dummy reply:"""

# All other complex prompts can be deleted from this file.
# (elaborator_system_prompt_template, elaborator_user_prompt_template, 
# unified_classification_system_prompt_template, unified_classification_user_prompt_template,
# internet_query_reframe_system_prompt_template, internet_query_reframe_user_prompt_template,
# internet_summary_system_prompt_template, internet_summary_user_prompt_template,
# and the original chat_system_prompt_template, chat_user_prompt_template can be removed)

# Keeping original chat prompts commented out for reference if a slightly more sophisticated dummy is desired later.
"""
chat_system_prompt_template = \"\"\"You are Sentient, a personalized AI companion... (original content) ...\"\"\"
chat_user_prompt_template = \"\"\"
User Query (ANSWER THIS QUESTION OR RESPOND TO THIS MESSAGE): {query}
Context (ONLY USE THIS AS CONTEXT TO GENERATE A RESPONSE. DO NOT REPEAT THIS INFORMATION TO THE USER.): {user_context}
Internet Search Results (USE THIS AS ADDITIONAL CONTEXT TO RESPOND TO THE QUERY, ONLY IF PROVIDED.): {internet_context}
Username (ONLY CALL THE USER BY THEIR NAME WHEN REQUIRED. YOU DO NOT NEED TO CALL THE USER BY THEIR NAME IN EACH MESSAGE.): {name}
\"\"\"
"""
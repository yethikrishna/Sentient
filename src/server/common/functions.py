import os
import asyncio
from typing import Optional, Any, Dict, List, Tuple
import traceback
import json
from dotenv import load_dotenv

# For dummy chat response, if using a simple LLM
from server.app.base import BaseRunnable, OllamaRunnable, get_selected_model 

# Removed imports for Neo4j, complex runnables, internet search related functions.

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

async def generate_dummy_streaming_response(user_input: str, username: str):
    """
    Generates a dummy streaming response.
    This can be hardcoded or use a very simple local LLM if desired.
    """
    print(f"[{datetime.datetime.now()}] [DUMMY_CHAT] Generating dummy stream for input: '{user_input[:30]}...' by {username}")
    
    # Option 1: Completely hardcoded dummy response
    dummy_texts = [
        "This ", "is ", "a ", "dummy ", "streaming ", "response ", "from ", "Sentient. ",
        "I ", "am ", "currently ", "in ", "a ", "simplified ", "mode. "
    ]
    for text_part in dummy_texts:
        yield text_part
        await asyncio.sleep(0.05) # Simulate streaming delay
    
    # Option 2: Use a local Ollama model for a slightly more dynamic dummy response (if configured)
    # model_name, provider = get_selected_model()
    # if provider == "ollama" and model_name != "dummy_model":
    #     try:
    #         # A very simple prompt for Ollama
    #         ollama_runnable = OllamaRunnable(
    #             model_name=model_name,
    #             system_prompt_template="You are a helpful assistant. Respond briefly.",
    #             user_prompt_template="User said: {query}. Your brief dummy reply:",
    #             stream=True
    #         )
    #         async for token in ollama_runnable.stream_response(inputs={"query": f"User '{username}' said: {user_input}"}):
    #             if token:
    #                 yield token
    #             await asyncio.sleep(0.01)
    #     except Exception as e:
    #         print(f"[{datetime.datetime.now()}] [DUMMY_CHAT_OLLAMA_ERROR] Error with Ollama for dummy response: {e}")
    #         yield "Error generating dummy Ollama response."
    # else:
    #     # Fallback to hardcoded if Ollama not configured or dummy_model is selected
    #     dummy_texts = [
    #         "This ", "is ", "a ", "dummy ", "response. ",
    #         "Ollama ", "is ", "not ", "configured ", "for ", "dynamic ", "dummy ", "replies. "
    #     ]
    #     for text_part in dummy_texts:
    #         yield text_part
    #         await asyncio.sleep(0.05)
            
    yield None # Signal end of stream


# The following functions related to complex context building, Neo4j, internet search,
# and specific LLM runnables are no longer needed for the revamped server functionality
# and have been removed or commented out.

# Removed: get_reframed_internet_query
# Removed: get_search_results
# Removed: get_search_summary
# Removed: update_neo4j_with_onboarding_data
# Removed: update_neo4j_with_personal_info
# Removed: query_user_profile (if only basic profile from mongo_manager.get_user_profile is needed)
# Removed: get_unified_classification_runnable (classification is simplified or bypassed for dummy chat)
# Removed: get_priority_runnable (task prioritization is out of scope for dummy chat)

# Kept: generate_response (though it might be unused if dummy chat is hardcoded in endpoint)
# Kept: generate_streaming_response (if dummy chat uses a runnable, otherwise also unused)

# If `generate_response` is still needed for some non-streaming dummy interaction (less likely):
async def generate_dummy_response(
    message: str, username: str
) -> Optional[Dict[str, Any]]:
    """
    Generates a dummy non-streaming response.
    """
    print(f"[{datetime.datetime.now()}] [DUMMY_CHAT] Generating dummy non-stream for input: '{message[:30]}...' by {username}")
    # Option 1: Hardcoded
    return {"response": f"This is a dummy response to '{message}'. Hello {username}!"}

    # Option 2: Simple Ollama call
    # model_name, provider = get_selected_model()
    # if provider == "ollama" and model_name != "dummy_model":
    #     try:
    #         ollama_runnable = OllamaRunnable(
    #             model_name=model_name,
    #             system_prompt_template="You are a helpful assistant. Respond briefly.",
    #             user_prompt_template="User said: {query}. Your brief dummy reply:",
    #             stream=False
    #         )
    #         response_content = await asyncio.to_thread(
    #             ollama_runnable.invoke, 
    #             inputs={"query": f"User '{username}' said: {message}"}
    #         )
    #         return {"response": response_content}
    #     except Exception as e:
    #         print(f"[{datetime.datetime.now()}] [DUMMY_CHAT_OLLAMA_ERROR] Error with Ollama for dummy response: {e}")
    #         return {"response": "Error generating dummy Ollama response."}
    # else:
    #     return {"response": "Dummy response. Ollama not configured for dynamic dummy replies."}
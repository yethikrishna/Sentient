import os
from model.app.base import *
from model.context.prompts import *
from model.context.formats import *

def get_gmail_context_runnable():
    """Configure and return a Runnable for the Gmail Context Engine."""
    # Example assumes you have a BaseRunnable and specific implementations like OllamaRunnable
    # Adjust imports and classes based on your actual LLM setup
    model_mapping = {
        "openai": (os.getenv("OPENAI_API_URL"), OpenAIRunnable),
        "claude": (os.getenv("CLAUDE_API_URL"), ClaudeRunnable),
        "gemini": (os.getenv("GEMINI_API_URL"), GeminiRunnable),
    }
    model_name, provider = get_selected_model()  # Assume this function exists to get model config

    if provider and provider in model_mapping:
        model_url, runnable_class = model_mapping[provider]
    else:
        model_url = os.getenv("BASE_MODEL_URL")
        runnable_class = OllamaRunnable  # Default fallback, adjust as needed

    return runnable_class(
        model_url=model_url,
        model_name=model_name,
        system_prompt_template=gmail_context_engine_system_prompt_template,
        user_prompt_template=gmail_context_engine_user_prompt_template,
        input_variables=["new_information", "related_memories", "ongoing_tasks", "chat_history"],
        required_format=context_engine_required_format,  
        response_type="json",
        stateful=False,
    )

# Placeholder for get_selected_model; implement based on your system
def get_selected_model():
    return os.getenv("BASE_MODEL_REPO_ID"), "llama3.2:3b" # Replace with actual logic
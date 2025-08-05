import asyncio
import json
from qwen_agent.agents import Assistant

# --- Configuration ---

# 1. LLM Configuration (uses a local Ollama server by default)
#    Make sure you have an OpenAI-compatible API server running.
#    (e.g., run `ollama serve` and `ollama pull qwen` in your terminal)
llm_cfg = {
    'model': 'qwen3:4b',  # or 'qwen:7b', 'qwen2:7b' etc.
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY', # Ollama does not require an API key
}

# 2. Gmail MCP Server Configuration
#    This must match the host and port your Gmail server is running on.
#    The `/sse` endpoint is used by FastMCP's streamable-http transport.
mcp_server_url = "http://127.0.0.1:9001/sse"

# 3. User Authentication
#    IMPORTANT: Replace this with a valid User ID that exists in your MongoDB
#    and has an associated Google token. This ID is sent in the 'X-User-ID' header.
USER_ID = "YOUR_USER_ID_HERE"


# --- Agent Setup ---

# Define the tools by pointing to the remote MCP server.
# The qwen-agent will automatically discover the tools available on the server.
tools = [{
    "mcpServers": {
        "gmail_server": {  # A custom name for your server connection
            "url": mcp_server_url,
            "headers": {
                "X-User-ID": USER_ID
            },
        }
    }
}]

# Initialize the Assistant agent
print("Initializing Qwen agent...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="GmailAgentClient",
    description="An agent that uses a remote MCP server to manage Gmail.",
    system_message="You are a helpful assistant that can manage a user's Gmail account by calling the appropriate tools. Be concise and clear in your responses."
)

# --- Interactive Chat Loop ---

def run_agent_interaction():
    """
    Runs an interactive loop to chat with the agent.
    """
    print("\n--- GMail Agent Ready ---")
    print("You can now interact with your GMail account.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample Commands:")
    print("  - Search for emails from 'noreply@github.com'")
    print("  - Send an email to 'test@example.com' with subject 'Hello' and body 'This is a test from the Qwen agent.'")
    print("  - what are my unread emails?")
    print("  - get me a summary of my unread mail")
    print("  - find the latest email about a 'shipment confirmation' and then mark it as read")
    print("  - what labels do I have?")
    print("-" * 25)

    # Use a simple list to maintain conversation history for context
    messages = []

    while True:
        try:
            print("\nYou: ", end="")
            user_input = input()
            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋  Goodbye!")
                break

            # Add user message to history
            messages.append({'role': 'user', 'content': user_input})
            
            print("\nAgent: ", end="", flush=True)
            
            last_assistant_text = ""
            final_response_from_run = None
            final_assistant_message = None
            # The agent.run is a generator. We iterate to get the final state.
            for response in agent.run(messages=messages):
                if isinstance(response, list) and response and response[-1].get("role") == "assistant":
                    current_text = response[-1].get("content", "")
                    if isinstance(current_text, str):
                        delta = current_text[len(last_assistant_text):]
                        print(delta, end="", flush=True)
                        last_assistant_text = current_text
                    final_assistant_message = response[-1]

            print()
            if final_assistant_message:
                messages.append(final_assistant_message)
            else:
                print("I could not process that request.")
                messages.pop()

        except KeyboardInterrupt:
            print("\n👋  Goodbye!")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            # Optionally reset messages history on error
            # messages = []


if __name__ == "__main__":
    run_agent_interaction()
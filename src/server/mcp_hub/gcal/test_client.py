# server/mcp_hub/gcal/test_client.py

import asyncio
import json
from qwen_agent.agents import Assistant

# --- Configuration ---

# 1. LLM Configuration (uses a local Ollama server by default)
llm_cfg = {
    'model': 'qwen3:4b', # or 'qwen:7b', etc.
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

# 2. GCal MCP Server Configuration
#    Must match the host/port from your .env file
mcp_server_url = "http://127.0.0.1:9002/sse"

# 3. User Authentication
#    IMPORTANT: Replace with a valid User ID from your MongoDB that has gcalendar connected
USER_ID = "google-oauth2|100870952531954264970"


# --- Agent Setup ---

# Define the tools by pointing to the remote MCP server.
tools = [{
    "mcpServers": {
        "gcal_server": {  # A custom name for your server connection
            "url": mcp_server_url,
            "headers": {
                "X-User-ID": USER_ID
            },
        }
    }
}]

# Initialize the Assistant agent
print("Initializing Qwen agent for Google Calendar...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="GCalAgentClient",
    description="An agent that uses a remote MCP server to manage Google Calendar.",
    system_message="You are a helpful assistant that can manage a user's Google Calendar by calling the appropriate tools. Be concise and clear. The current year is 2024."
)

# --- Interactive Chat Loop ---

def run_agent_interaction():
    """Runs an interactive loop to chat with the agent."""
    print("\n--- GCal Agent Ready ---")
    print("You can now interact with your Google Calendar.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample Commands:")
    print("  - what are my next 5 events on my primary calendar?")
    print("  - create an event titled 'Project Kickoff' for tomorrow at 2pm for 90 minutes")
    print("  - search for any events about 'lunch' this week")
    print("  - what calendars do I have access to?")
    print("  - delete the event with ID '...event_id...'")
    print("-" * 25)

    messages = []
    while True:
        try:
            print("\nYou: ", end="")
            user_input = input()
            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋  Goodbye!")
                break

            messages.append({'role': 'user', 'content': user_input})
            print("\nAgent: ", end="", flush=True)
            
            last_assistant_text = ""
            final_response_from_run = None
            for response in agent.run(messages=messages):
                if isinstance(response, list) and response and response[-1].get("role") == "assistant":
                    current_text = response[-1].get("content", "")
                    if isinstance(current_text, str):
                        delta = current_text[len(last_assistant_text):]
                        print(delta, end="", flush=True)
                        last_assistant_text = current_text
                final_response_from_run = response

            print()
            if final_response_from_run:
                messages = final_response_from_run
            else:
                print("I could not process that request.")
                messages.pop()

        except KeyboardInterrupt:
            print("\n👋  Goodbye!")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    run_agent_interaction()
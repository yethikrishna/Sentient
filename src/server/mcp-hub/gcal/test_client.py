# server/mcp-hub/gcal/test_client.py

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
#    IMPORTANT: Replace with a valid User ID from your MongoDB
USER_ID = "kabeer"


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
    print("\nExample commands:")
    print("  - what are my next 5 events?")
    print("  - schedule a meeting with the team for tomorrow at 3pm for one hour titled 'Project Sync'")
    print("  - add an event 'Dentist Appointment' for 2024-10-25 from 10:00 to 10:30")
    print("  - find my 'Project Sync' meeting and delete it")
    print("  - search for any events about 'lunch'")
    print("-" * 25)

    messages = []
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ["quit", "exit"]:
                print("Exiting agent...")
                break

            messages.append({'role': 'user', 'content': user_input})
            print("\n--- Agent is processing... ---")
            
            full_response_history = None
            for response in agent.run(messages=messages):
                full_response_history = response

            if full_response_history:
                print("\n--- Full Internal History ---")
                print(json.dumps(full_response_history, indent=2))
                print("-----------------------------\n")

                messages = full_response_history
                
                final_answer = "No final textual answer from agent."
                if messages and messages[-1]['role'] == 'assistant':
                    content = messages[-1].get('content')
                    if content:
                       final_answer = content
                
                print(f"Agent: {final_answer}")
            else:
                print("Agent: I could not process that request.")
                messages.pop()

        except KeyboardInterrupt:
            print("\nExiting agent...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    run_agent_interaction()
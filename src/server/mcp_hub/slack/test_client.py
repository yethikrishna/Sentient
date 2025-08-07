# server/mcp_hub/slack/test_client.py

import json
from qwen_agent.agents import Assistant

# --- Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

# Slack MCP Server Configuration
mcp_server_url = "http://127.0.0.1:9006/sse"

# IMPORTANT: Replace with a valid User ID from your MongoDB that has Slack credentials
USER_ID = "YOUR_USER_ID_HERE" # Or whatever you entered in generate_slack_token.py

# --- Agent Setup ---
tools = [{
    "mcpServers": {
        "slack_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for Slack...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="SlackAgent",
    description="An agent that can interact with a Slack workspace.",
    system_message=(
        "You are a helpful Slack assistant. Use the available tools to interact with the "
        "workspace on the user's behalf. Be sure to find channel and user IDs before trying to post messages."
    )
)

# --- Interactive Chat Loop ---
def run_agent_interaction():
    print("\n--- Slack Agent Ready ---")
    print("You can now interact with your Slack workspace.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample commands:")
    print("  - list the first 5 public channels")
    print("  - what are the last 3 messages in the #general channel? (You'll need to find the channel ID first)")
    print("  - post 'Hello from my AI agent!' to the #random channel")
    print("  - who are the users in this workspace?")
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
            final_assistant_message = None
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

if __name__ == "__main__":
    run_agent_interaction()
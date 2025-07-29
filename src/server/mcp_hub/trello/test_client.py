# src/server/mcp_hub/trello/test_client.py
import json
from qwen_agent.agents import Assistant

# --- Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

# Trello MCP Server Configuration
mcp_server_url = "http://127.0.0.1:9025/sse"

# IMPORTANT: Replace with a valid User ID from your MongoDB that has Trello credentials
USER_ID = "YOUR_USER_ID_HERE"

# --- Agent Setup ---
tools = [{
    "mcpServers": {
        "trello_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for Trello...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="TrelloAgent",
    description="An agent that can manage Trello boards and cards.",
    system_message="You are a helpful Trello assistant. Use the available tools to manage boards, lists, and cards. You need to find board and list IDs before creating cards."
)

# --- Interactive Chat Loop ---
def run_agent_interaction():
    print("\n--- Trello Agent Ready ---")
    print("You can now manage your Trello boards.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample commands:")
    print("  - list my Trello boards")
    print("  - show me the lists on board with ID '...'")
    print("  - create a card named 'New Feature Idea' in list with ID '...'")
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


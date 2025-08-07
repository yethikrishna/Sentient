import asyncio
import json
from qwen_agent.agents import Assistant

# --- Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

# History MCP Server Configuration
mcp_server_url = "http://127.0.0.1:9020/sse"

# IMPORTANT: Replace with a valid User ID from your MongoDB
USER_ID = "YOUR_USER_ID_HERE"

# --- Agent Setup ---
tools = [{
    "mcpServers": {
        "history_mcp": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for Chat History...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="HistoryAgentClient",
    description="An agent that can search through the user's long-term conversation history.",
    system_message="You are a helpful assistant that can search a user's conversation history. Use `semantic_search` for topics and `time_based_search` for specific dates."
)

# --- Interactive Chat Loop ---
def run_agent_interaction():
    print("\n--- Chat History Agent Ready ---")
    print("You can now search your conversation history.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample commands:")
    print("  - what did we talk about regarding the Q3 marketing plan?")
    print("  - search for messages between 2024-07-20 and 2024-07-22")
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
import json
from qwen_agent.agents import Assistant

# --- Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

# Progress Updater MCP Server Configuration
mcp_server_url = "http://127.0.0.1:9011/sse"
USER_ID = "test_user"

# --- Agent Setup ---
tools = [{
    "mcpServers": {
        "progress_updater_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for Progress Updater...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="ProgressUpdaterAgent",
    description="An agent that can send progress updates for a task.",
    system_message="You are an executor agent. When you perform an action, you must report it using the `update_progress` tool."
)

# --- Interactive Chat Loop ---
def run_agent_interaction():
    print("\n--- Progress Updater Agent Ready ---")
    print("Simulate an executor agent sending progress updates.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample command:")
    print("  - update progress for task 'task-123' with message 'Step 1 completed successfully.'")
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


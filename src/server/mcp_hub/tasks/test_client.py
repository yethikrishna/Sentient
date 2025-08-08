import json
from qwen_agent.agents import Assistant

# --- Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

# Tasks MCP Server Configuration
mcp_server_url = "http://127.0.0.1:9018/sse"

# IMPORTANT: Replace with a valid User ID from your MongoDB
USER_ID = "google-oauth2|115437244827618197332"

# --- Agent Setup ---
tools = [{
    "mcpServers": {
        "tasks_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for Tasks...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="TaskCreatorAgent",
    description="An agent that creates tasks from natural language.",
    system_message="You are an assistant that creates tasks. Use the `create_task_from_prompt` tool to do so."
)

# --- Interactive Chat Loop ---
def run_agent_interaction():
    print("\n--- Task Creator Agent Ready ---")
    print("Describe the task you want to create.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample commands:")
    print("  - create a task to write a blog post about AI for next Friday")
    print("  - add a to-do to call the doctor tomorrow morning")
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
                print(messages)
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


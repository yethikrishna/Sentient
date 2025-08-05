import json
from qwen_agent.agents import Assistant

# --- Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

# GitHub MCP Server Configuration
mcp_server_url = "http://127.0.0.1:9010/sse"

# IMPORTANT: Replace with a valid User ID from your MongoDB that has GitHub credentials
USER_ID = "YOUR_USER_ID_HERE"

# --- Agent Setup ---
tools = [{
    "mcpServers": {
        "github_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for GitHub...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="GitHubAgent",
    description="An agent that can interact with GitHub.",
    system_message=(
        "You are a helpful GitHub assistant. Use the available tools to find information, "
        "create issues, and manage repositories as requested by the user."
    )
)

# --- Interactive Chat Loop ---
def run_agent_interaction():
    print("\n--- GitHub Agent Ready ---")
    print("You can now interact with your GitHub account.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample commands:")
    print("  - search for repositories about 'fastapi'")
    print("  - list my personal repositories")
    print("  - get details for the repo 'tiangolo/fastapi'")
    print("  - list the open issues for 'qwen-agent/qwen-agent'")
    print("  - create an issue in 'your_username/your_test_repo' with the title 'Test Issue from Agent' and body 'This is a test.'")
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
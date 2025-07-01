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
USER_ID = "kabeer"

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
            user_input = input("You: ")
            if user_input.lower() in ["quit", "exit"]:
                break

            messages.append({'role': 'user', 'content': user_input})
            print("\n--- Agent is processing... ---")
            
            final_response = None
            for response in agent.run(messages=messages):
                final_response = response

            if final_response:
                print("\n--- Full Internal History ---")
                print(json.dumps(final_response, indent=2))
                print("-----------------------------\n")

                messages = final_response
                
                final_answer = "No textual answer from agent."
                if messages and messages[-1]['role'] == 'assistant':
                    content = messages[-1].get('content')
                    if isinstance(content, str):
                        final_answer = content
                
                print(f"Agent: {final_answer}")
            else:
                print("Agent: I could not process that request.")
                messages.pop()

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    run_agent_interaction()
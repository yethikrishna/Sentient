# server/mcp_hub/gdrive/test_client.py

import json
from qwen_agent.agents import Assistant

# --- Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

# GDrive MCP Server Configuration (must match .env)
mcp_server_url = "http://127.0.0.1:9003/sse"

# IMPORTANT: Replace with a valid User ID from your MongoDB
USER_ID = "kabeer"

# --- Agent Setup ---
tools = [{
    "mcpServers": {
        "gdrive_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for Google Drive...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="GDriveAgentClient",
    description="An agent that uses a remote MCP server to manage Google Drive files.",
    system_message=(
        "You are a helpful assistant that can search and read files from a user's Google Drive. "
        "First, search for files. Then, if the user asks for content, use the file ID from the search results to read the file."
    )
)

# --- Interactive Chat Loop ---
def run_agent_interaction():
    print("\n--- GDrive Agent Ready ---")
    print("You can now interact with your Google Drive.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample commands:")
    print("  - find all spreadsheets named 'Q3 Report'")
    print("  - search for a presentation about 'marketing strategy'")
    print("  - find the document with 'project proposal' in the title and then read its contents")
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
import json
from qwen_agent.agents import Assistant

# --- Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

# Notion MCP Server Configuration
mcp_server_url = "http://127.0.0.1:9009/sse"

# IMPORTANT: Replace with a valid User ID from your MongoDB that has Notion credentials
USER_ID = "kabeer"

# --- Agent Setup ---
tools = [{
    "mcpServers": {
        "notion_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for Notion...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="NotionAgent",
    description="An agent that can interact with a Notion workspace.",
    system_message=(
        "You are a helpful Notion assistant. Use the available tools to find information, "
        "create new pages, and append content to existing pages as requested by the user."
    )
)

# --- Interactive Chat Loop ---
def run_agent_interaction():
    print("\n--- Notion Agent Ready ---")
    print("You can now interact with your Notion workspace.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample commands:")
    print("  - search for a page titled 'Meeting Notes'")
    print("  - find a page about 'Q3 planning' and then tell me its contents")
    print("  - create a new page titled 'My Awesome New Page' inside the page with ID '...'. Add a heading 'Welcome' and a paragraph 'This is a test.'")
    print("  - append a to-do item 'Follow up with team' to the page with ID '...'")
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
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
USER_ID = "google-oauth2|115437244827618197332"

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
    print("\nExample Commands:")
    print("  - list the available databases")
    print("  - create a page titled 'My New Test Page' under parent page ID '...'")
    print("  - get the page with ID '...'")
    print("  - add a comment 'This is a test comment' to page with ID '...'")
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
            final_assistant_message = None
            final_response = None
            for response in agent.run(messages=messages):
                if isinstance(response, list) and response and response[-1].get("role") == "assistant":
                    current_text = response[-1].get("content", "")
                    if isinstance(current_text, str):
                        delta = current_text[len(last_assistant_text):]
                        print(delta, end="", flush=True)
                        last_assistant_text = current_text
                    final_assistant_message = response[-1]
                final_response = response
                
            
            print ("\n FINAL RESPONSE: ", final_response)

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
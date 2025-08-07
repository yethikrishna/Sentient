import json
from qwen_agent.agents import Assistant

# --- Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

# GPeople MCP Server Configuration
mcp_server_url = "http://127.0.0.1:9019/sse"

# IMPORTANT: Replace with a valid User ID from your MongoDB
USER_ID = "YOUR_USER_ID_HERE"

# --- Agent Setup ---
tools = [{
    "mcpServers": {
        "gpeople_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for Google People...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="GPeopleAgentClient",
    description="An agent that can manage Google Contacts.",
    system_message="You are a helpful assistant for managing contacts. Use the available tools to search, create, update, or delete contacts."
)

# --- Interactive Chat Loop ---
def run_agent_interaction():
    print("\n--- Google People Agent Ready ---")
    print("You can now manage your Google Contacts.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample commands:")
    print("  - search for a contact named 'John Doe'")
    print("  - create a new contact for 'Jane Smith' with email 'jane.smith@example.com'")
    print("  - find the contact for 'John Doe' and then update their phone to '123-456-7890'")
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
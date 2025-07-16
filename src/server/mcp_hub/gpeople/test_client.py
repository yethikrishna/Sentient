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
USER_ID = "google-oauth2|115592889721747070841"

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
                
                final_answer = "No final textual answer from agent."
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
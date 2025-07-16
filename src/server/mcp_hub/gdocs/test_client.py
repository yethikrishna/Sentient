import json
from qwen_agent.agents import Assistant

llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

mcp_server_url = "http://127.0.0.1:9004/sse"
USER_ID = "kabeer" # Replace with a valid User ID from your MongoDB

tools = [{
    "mcpServers": {
        "gdocs_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for Google Docs...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="GDocsAgentClient",
    description="An agent that uses a remote MCP server to create Google Docs.",
    system_message="You are a helpful assistant that can create Google Docs from a user's request."
)

def run_agent_interaction():
    print("\n--- Google Docs Agent Ready ---")
    print("Describe the document you want to create.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample command:")
    print("  - list my google docs")
    print("  - create a new document titled 'Meeting Notes'")
    print("  - append 'This is a test.' to the document with ID 'YOUR_DOC_ID'")
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
            for response in agent.run(messages=messages):
                if isinstance(response, list) and response and response[-1].get("role") == "assistant":
                    current_text = response[-1].get("content", "")
                    if isinstance(current_text, str):
                        delta = current_text[len(last_assistant_text):]
                        print(delta, end="", flush=True)
                        last_assistant_text = current_text
                final_response_from_run = response

            print()
            if final_response_from_run:
                messages = final_response_from_run
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
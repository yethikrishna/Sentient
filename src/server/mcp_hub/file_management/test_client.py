import json
import base64
from qwen_agent.agents import Assistant

# --- Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

mcp_server_url = "http://127.0.0.1:9026/sse"
USER_ID = "test-file-user"

# --- Agent Setup ---
tools = [{
    "mcpServers": {
        "file_management_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for File Management...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="FileManagementAgent",
    description="An agent that can manage temporary files.",
    system_message="You are a helpful file management assistant. Use the available tools to read, write, and list files."
)

# --- Interactive Chat Loop ---
def run_agent_interaction():
    print("\n--- File Management Agent Ready ---")
    print("You can now manage temporary files.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample commands:")
    print("  - write a file named 'hello.txt' with the content 'Hello, world!'")
    print("  - list my files")
    print("  - read the file 'hello.txt'")
    print(f"  - write a binary file named 'test.bin' with the base64 content '{base64.b64encode(b'binary data').decode()}'")
    print("  - read 'test.bin' in binary mode")
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
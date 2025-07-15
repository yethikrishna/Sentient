import json
from qwen_agent.agents import Assistant

# --- Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

mcp_server_url = "http://127.0.0.1:9016/sse"
USER_ID = "kabeer" # Replace with a valid User ID from your MongoDB

# --- Agent Setup ---
tools = [{
    "mcpServers": {
        "gmaps_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for Google Maps...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="GMapsAgentClient",
    description="An agent that can use Google Maps tools.",
    system_message="You are a helpful assistant that can search for places and get directions using Google Maps."
)

def run_agent_interaction():
    print("\n--- Google Maps Agent Ready ---")
    print("Ask me to find places or get directions.")
    print("Type 'quit', 'exit', or 'q' to end the session.")
    print("\nExample commands:")
    print("  - find cafes near the Eiffel Tower")
    print("  - get driving directions from Los Angeles, CA to Las Vegas, NV")
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

            print() # Newline after agent's response
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
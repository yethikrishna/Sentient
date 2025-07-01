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
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample commands:")
    print("  - find cafes near the Eiffel Tower")
    print("  - get driving directions from Los Angeles, CA to Las Vegas, NV")
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
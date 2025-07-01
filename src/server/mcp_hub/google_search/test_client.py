# server/mcp_hub/google_search/test_client.py

import json
from qwen_agent.agents import Assistant

# --- Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

# Google Search MCP Server Configuration
mcp_server_url = "http://127.0.0.1:9005/sse"

# User ID for header consistency
USER_ID = "test_user"

# --- Agent Setup ---
tools = [{
    "mcpServers": {
        "google_search_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for Google Search...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="GoogleSearchAgent",
    description="An agent that can use Google Search to find real-time information.",
    system_message=(
        "You are a helpful research assistant. Use the google_search tool to find answers "
        "to user questions about current events, facts, or topics outside your training data. "
        "Summarize the findings for the user based on the search result snippets."
    )
)

# --- Interactive Chat Loop ---
def run_agent_interaction():
    print("\n--- Google Search Agent Ready ---")
    print("Ask me anything! I can use Google Search for the latest information.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample questions:")
    print("  - Who is the current CEO of OpenAI?")
    print("  - What were the key announcements from the last Apple event?")
    print("  - What is the capital of Australia?")
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
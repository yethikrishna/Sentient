# server/mcp-hub/brave/test_client.py

import json
from qwen_agent.agents import Assistant

# --- Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

# Brave MCP Server Configuration (must match .env)
mcp_server_url = "http://127.0.0.1:9004/sse"

# User ID for header consistency
USER_ID = "test_user"

# --- Agent Setup ---
tools = [{
    "mcpServers": {
        "brave_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for Web Search...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="WebSearchAgent",
    description="An agent that can search the web for real-time information.",
    system_message=(
        "You are a helpful research assistant. Use the web_search tool to find answers "
        "to user questions about current events, facts, or topics outside your training data. "
        "Summarize the findings for the user."
    )
)

# --- Interactive Chat Loop ---
def run_agent_interaction():
    print("\n--- Web Search Agent Ready ---")
    print("Ask me anything! I can search the web for the latest information.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample questions:")
    print("  - Who won the last Formula 1 race?")
    print("  - What are the main features of the new Python 3.12 release?")
    print("  - What is the weather forecast for London tomorrow?")
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
import json
from qwen_agent.agents import Assistant

# --- Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

# News MCP Server Configuration
mcp_server_url = "http://127.0.0.1:9012/sse"

# User ID for header consistency
USER_ID = "news_test_user"

# --- Agent Setup ---
tools = [{
    "mcpServers": {
        "news_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for News...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="NewsAgent",
    description="An agent that can fetch news and headlines.",
    system_message=(
        "You are a helpful news assistant. Use the available tools to find articles and "
        "summarize them for the user."
    )
)

# --- Interactive Chat Loop ---
def run_agent_interaction():
    print("\n--- News Agent Ready ---")
    print("Ask me for the news!")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample commands:")
    print("  - what are the top headlines in technology from the US?")
    print("  - find me articles about Tesla")
    print("  - what's the latest in business news?")
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
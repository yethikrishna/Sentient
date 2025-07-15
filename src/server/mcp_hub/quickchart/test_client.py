# server/mcp_hub/quickchart/test_client.py

import json
from qwen_agent.agents import Assistant

# --- Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

# QuickChart MCP Server Configuration
mcp_server_url = "http://127.0.0.1:9008/sse"

# User ID for header consistency
USER_ID = "chart_user"

# --- Agent Setup ---
tools = [{
    "mcpServers": {
        "quickchart_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for QuickChart...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="ChartAgent",
    description="An agent that can generate data visualizations using QuickChart.",
    system_message=(
        "You are a helpful data visualization assistant. Your goal is to create a valid "
        "Chart.js JSON configuration based on the user's request and use the provided tools "
        "to generate a chart URL or download the image."
    )
)

# --- Interactive Chat Loop ---
def run_agent_interaction():
    print("\n--- QuickChart Agent Ready ---")
    print("Describe the chart you want to create.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample commands:")
    print("  - Create a bar chart for sales data: Apples 50, Oranges 75, Bananas 30.")
    print("  - Generate a pie chart showing market share: Google 60%, Bing 25%, DuckDuckGo 15%.")
    print("  - Make a line chart of my website visitors: [150, 230, 220, 300, 280] for the last 5 days and download it.")
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
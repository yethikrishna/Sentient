# server/mcp_hub/accuweather/test_client.py

import json
from qwen_agent.agents import Assistant

# --- Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

# AccuWeather MCP Server Configuration
mcp_server_url = "http://127.0.0.1:9007/sse"

USER_ID = "google-oauth2|115592889721747070841"

# --- Agent Setup ---
tools = [{
    "mcpServers": {
        "weather_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for AccuWeather...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="WeatherAgent",
    description="An agent that can get current weather and forecasts.",
    system_message=(
        "You are a helpful weather assistant. Use the available tools to get weather "
        "information and present it clearly to the user."
    )
)

# --- Interactive Chat Loop ---
def run_agent_interaction():
    print("\n--- Weather Agent Ready ---")
    print("Ask me for the weather!")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample questions:")
    print("  - what's the weather like in san francisco right now?")
    print("  - can you give me the 3-day forecast for tokyo?")
    print("  - how hot is it in dubai?")
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
import json
from qwen_agent.agents import Assistant

# --- Configuration ---
llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

mcp_server_url = "http://127.0.0.1:9022/sse"
USER_ID = "google-oauth2|115437244827618197332"

tools = [{
    "mcpServers": {
        "discord_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for Discord...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="DiscordAgent",
    description="An agent that can interact with Discord.",
    system_message="You are a helpful Discord assistant. Use the available tools to find channels and send messages."
)

def run_agent_interaction():
    print("\n--- Discord Agent Ready ---")
    print("You can now interact with your Discord account.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample commands:")
    print("  - list my discord servers")
    print("  - what channels are in the server with ID '...'?")
    print("  - send a message to the 'general' channel in my main server saying 'Hello from my agent!'")
    print("-" * 25)
    messages = []
    while True:
        try:
            print("\nYou: ", end="")
            user_input = input()
            if user_input.lower() in ["quit", "exit", "q"]:
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
            
            print() # Newline after agent's response
            if final_assistant_message:
                messages.append(final_assistant_message)
            else:
                print("I could not process that request.")
                messages.pop()

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    run_agent_interaction()
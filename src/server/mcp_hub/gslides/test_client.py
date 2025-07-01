import json
from qwen_agent.agents import Assistant

llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

mcp_server_url = "http://127.0.0.1:9014/sse"
USER_ID = "kabeer" # Replace with a valid User ID

tools = [{
    "mcpServers": {
        "gslides_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for Google Slides...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="GSlidesAgentClient",
    description="An agent that creates Google Slides presentations.",
    system_message="You are a helpful assistant that creates Google Slides presentations based on user requests."
)

def run_agent_interaction():
    print("\n--- GSlides Agent Ready ---")
    print("Describe the presentation you want to create.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample command:")
    print("  - make a presentation about the importance of bees for the ecosystem")
    print("  - create a presentation on the quarterly sales results, including a bar chart showing sales of 50, 75, and 60 for Q1, Q2, and Q3")
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
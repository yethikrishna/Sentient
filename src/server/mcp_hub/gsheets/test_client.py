import json
from qwen_agent.agents import Assistant

llm_cfg = {
    'model': 'qwen3:4b',
    'model_server': 'http://localhost:11434/v1/',
    'api_key': 'EMPTY',
}

mcp_server_url = "http://127.0.0.1:9015/sse"
USER_ID = "kabeer" # Replace with a valid User ID

tools = [{
    "mcpServers": {
        "gsheets_server": {
            "url": mcp_server_url,
            "headers": {"X-User-ID": USER_ID},
        }
    }
}]

print("Initializing Qwen agent for Google Sheets...")
agent = Assistant(
    llm=llm_cfg,
    function_list=tools,
    name="GSheetsAgentClient",
    description="An agent that creates Google Sheets with data.",
    system_message="You are a helpful assistant that creates Google Sheets from user requests. You must structure the data into the correct JSON format."
)

def run_agent_interaction():
    print("\n--- GSheets Agent Ready ---")
    print("Describe the spreadsheet you want to create.")
    print("Type 'quit' or 'exit' to end the session.")
    print("\nExample command:")
    print("  - create a spreadsheet for my Q3 budget with columns 'Item', 'Category', 'Cost'. Add a row for 'Software' in 'Tech' category costing $500.")
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
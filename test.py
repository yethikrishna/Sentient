import ollama
import json
from playwright.sync_api import sync_playwright
from extract import *

# Function to get JSON response from Ollama
def get_llama_response(task):
    prompt = f"""
    You are an AI assistant that converts user instructions into structured JSON for browser automation. 
    Convert the following command into a JSON format with actions:

    Task: "{task}"

    Output format:
    {{
        "actions": [
            {{"type": "goto", "url": "https://example.com"}},
            {{"type": "scroll", "direction": "down"}},
            {{"type": "click", "selector": "text='CUDA 12.4'"}},
            {{"type": "copy_text", "selector": "code"}}
        ]
    }}
    """

    response = ollama.chat(model="llama3.2:3b", messages=[{"role": "user", "content": prompt}])

    
    # Extract response text
    response_text = response.get("message", {}).get("content", "")
    
    # Try parsing JSON
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        print("Error: Failed to parse JSON response from Ollama")
        return None

def get_context(task):
    context = extract_text_from_url("https://pytorch.org")
    print(context)
    prompt = f"""
    You are an AI assistant that takes the whole context and extracts only the information that user has asked for and do not give any explaination. If user has asked for some specific information then just provide that information. It can be of one line also.
    Extract the information from the following context:

    Context: "{context}"

    Task: "{task}"
    """
    response = ollama.chat(model="llama3.2:3b", messages=[{"role": "user", "content": prompt}])
    
        # Extract response text
    response_text = response.get("message", {}).get("content", "")
    
    return response_text
    
    # Try parsing JSON
    # try:
    #     return json.loads(response_text)
    # except json.JSONDecodeError:
    #     print("Error: Failed to parse JSON response from Ollama")
    #     return None

    

# Function to execute browser automation based on JSON response
def execute_browser_tasks(actions, task):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        for action in actions:
            if action["type"] == "goto":
                print(f"🔗 Visiting: {action['url']}")
                page.goto(action["url"])

            elif action["type"] == "scroll":
                print(f"⬇ Scrolling {action['direction']}")
                page.evaluate(f"window.scrollBy(0, {'500' if action['direction'] == 'down' else '-500'})")

            elif action["type"] == "click":
                print(f"🖱 Clicking: {action['selector']}")
                page.locator(action["selector"]).click()

            elif action["type"] == "copy_text":
                # text = page.locator(action["selector"]).inner_text()
                text = get_context(task)
                print(f"📋 Copied text: {text}")

        browser.close()


# Main execution
if __name__ == "__main__":
    user_task = input("Enter your browser automation task: ")
    
    # Get structured JSON from Ollama
    # task_json = get_llama_response(user_task)
    task_json = {
        "actions": [
            {"type": "goto", "url": "https://pytorch.org"},
            {"type": "scroll", "direction": "down"},
            {"type": "click", "selector": "text='CUDA 12.6'"},
            {"type": "copy_text", "selector": "code"}
        ]
    }

    
    if task_json and "actions" in task_json:
        execute_browser_tasks(task_json["actions"], user_task)
    else:
        print("No valid actions received.")

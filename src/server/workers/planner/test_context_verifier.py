import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, List, Optional

# --- Add the project root to the Python path ---
# This allows us to import modules from the main application and workers
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from workers.tasks import _get_tool_lists, _select_relevant_tools, clean_llm_output
from workers.planner.llm import get_question_generator_agent
from workers.planner.db import PlannerMongoManager
from main.config import INTEGRATIONS_CONFIG
from json_extractor import JsonExtractor

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# IMPORTANT: Set this to the user ID you want to test with.
# This user MUST have integrations connected for the tool selection to work.
TEST_USER_ID = "google-oauth2|100870952531954264970" # Replace with your test user's ID

async def test_context_verification(task_description: str):
    """
    Isolates and tests the context verification and question generation logic.
    """
    print("\n" + "="*50)
    print(f"🚀 Starting Context Verification Test for Task:")
    print(f"   '{task_description}'")
    print("="*50 + "\n")

    db_manager = PlannerMongoManager()
    try:
        # 1. --- Fetch User Profile and Available Tools ---
        user_profile = await db_manager.user_profiles_collection.find_one({"user_id": TEST_USER_ID})
        if not user_profile:
            print(f"❌ ERROR: User profile not found for user_id: {TEST_USER_ID}. Please check the ID.")
            return

        user_integrations = user_profile.get("userData", {}).get("integrations", {})

        # 2. --- Dynamic Tool Selection ---
        connected_tools, _ = _get_tool_lists(user_integrations)
        print(f"🛠️  Available Tools for User: {list(connected_tools.keys())}")

        llm_selected_tools = await _select_relevant_tools(task_description, connected_tools)
        print(f"🤖 LLM Suggested Tools: {llm_selected_tools}")
        
        # CRITICAL VALIDATION STEP
        relevant_tool_names = [tool for tool in llm_selected_tools if tool in connected_tools]

        final_tool_names = set(relevant_tool_names)
        final_tool_names.add("memory") # memory is mandatory

        print(f"✅ Final Validated Tools for Context Search: {list(final_tool_names)}")

        # 3. --- Build Agent Configuration ---
        mcp_servers_for_agent = {}
        available_tools_for_prompt = {}

        for tool_name in final_tool_names:
            config = INTEGRATIONS_CONFIG.get(tool_name)
            if not config: continue

            available_tools_for_prompt[tool_name] = config.get("description", "")

            mcp_config = config.get("mcp_server_config")
            if mcp_config and mcp_config.get("url"):
                 mcp_servers_for_agent[mcp_config["name"]] = {"url": mcp_config["url"], "headers": {"X-User-ID": TEST_USER_ID}}

        if not mcp_servers_for_agent:
            print("❌ ERROR: No MCP servers could be configured for the selected tools. Cannot proceed.")
            return

        # 4. --- Instantiate and Run the Agent ---
        original_context = {"source": "manual_test", "content": task_description}
        agent = get_question_generator_agent(
            original_context=original_context,
            available_tools_for_prompt=available_tools_for_prompt,
            mcp_servers_for_agent=mcp_servers_for_agent
        )

        user_prompt = f"Based on the task '{task_description}' and the provided context, please use your tools to find relevant information and then determine if any clarifying questions are necessary."
        messages = [{'role': 'user', 'content': user_prompt}]

        print("\n" + "-"*50)
        print("🤖 Agent Internal Trace (Streaming):")
        print("-" * 50)

        last_assistant_text = ""
        final_response_str = ""
        # for response in agent.run(messages=messages):
        #     if isinstance(response, list) and response and response[-1].get("role") == "assistant":
        #         current_text = response[-1].get("content", "")
        #         if isinstance(current_text, str):
        #             delta = current_text[len(last_assistant_text):]
        #             print(delta, end="", flush=True)
        #             last_assistant_text = current_text
        #     final_response_str = last_assistant_text
        
        for response in agent.run(messages=messages):
            final_response_str = response
        
        print("\n" + "-"*50)
        print("✅ Agent Run Complete.")
        print("-" * 50 + "\n")
        
        print ("FINAL RESPONSE:", final_response_str)

        # 5. --- Process Final Output ---
        response_data = JsonExtractor.extract_valid_json(clean_llm_output(final_response_str))

        if response_data and isinstance(response_data.get("clarifying_questions"), list):
            questions = response_data["clarifying_questions"]
            print("🎯 Final Result: Clarifying Questions")
            print("-" * 35)
            if questions:
                for i, q in enumerate(questions):
                    print(f"  {i1}. {q}")
            else:
                print("  (No questions needed, agent found enough context)")
            print("-" * 35)
        else:
            print("❌ ERROR: Agent returned invalid or non-JSON data.")
            print("Raw Final Response:")
            print(final_response_str)

    except Exception as e:
        logging.error("An error occurred during the test.", exc_info=True)
    finally:
        await db_manager.close()


async def main():
    # --- You can hard-code tasks here for quick testing ---
    test_tasks = [
        "Create a synopsis of the pivot features file and send it to the team.",
        # Add more hard-coded tasks here if you want
    ]

    if test_tasks:
        for task in test_tasks:
            await test_context_verification(task)
    else:
        # --- Or run in interactive mode ---
        print("\n--- Interactive Context Verifier Test ---")
        print("Enter a task description to test, or type 'quit' to exit.")
        while True:
            task_input = input("\n> Task: ")
            if task_input.lower() in ['quit', 'exit']:
                break
            await test_context_verification(task_input)

if __name__ == "__main__":
    asyncio.run(main())
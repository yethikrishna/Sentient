import os
import asyncio
import json
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from qwen_agent.agents import Assistant
from json_extractor import JsonExtractor

from .tools import register_tools
from . import auth, prompts, utils

# --- LLM and Environment Configuration ---
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

OPENAI_API_BASE_URL = os.getenv("OPENAI_API_BASE_URL", "http://localhost:11434/v1/")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "qwen3:4b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "ollama")

def get_generator_agent():
    llm_cfg = {
        'model': OPENAI_MODEL_NAME,
        'model_server': f"{OPENAI_API_BASE_URL.rstrip('/')}/v1",
        'api_key': OPENAI_API_KEY,
    }
    return Assistant(llm=llm_cfg, system_message=prompts.JSON_GENERATOR_SYSTEM_PROMPT, function_list=[])

mcp = FastMCP(
    name="GSheetsServer",
    instructions="Provides tools to create, manage, and interact with Google Sheets, including reading/writing data and managing the spreadsheet structure.",
)

# Register all 19 Google-Sheets tools
register_tools(mcp)

@mcp.resource("prompt://gsheets-agent-system")
def get_gsheets_system_prompt() -> str:
    return prompts.MAIN_AGENT_SYSTEM_PROMPT

@mcp.tool()
async def generate_sheet_json(ctx: Context, topic: str, previous_tool_response: Optional[str] = "{}") -> Dict[str, Any]:
    """
    Step 1 of 2 for creating a complex sheet. Generates the structured JSON required by `execute_sheet_creation`.
    Provide a `topic` for the sheet. The tool's internal AI will design the sheet's title, tabs, headers, and data.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)
        user_profile = await auth.users_collection.find_one({"user_id": user_id})
        username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", "User") if user_profile else "User"

        agent = get_generator_agent()
        user_prompt = prompts.gsheets_internal_user_prompt.format(
            topic=topic,
            username=username,
            previous_tool_response=previous_tool_response
        )
        messages = [{'role': 'user', 'content': user_prompt}]
        
        final_content_str = ""
        for chunk in agent.run(messages=messages):
            if isinstance(chunk, list) and chunk:
                last_message = chunk[-1]
                if last_message.get("role") == "assistant" and isinstance(last_message.get("content"), str):
                    final_content_str = last_message["content"]

        if not final_content_str:
            raise Exception("The sheet generator agent returned an empty response.")
        
        sheet_json = JsonExtractor.extract_valid_json(final_content_str)
        if not sheet_json or "title" not in sheet_json or "sheets_json" not in sheet_json:
            raise Exception(f"Generator agent failed to produce valid JSON. Response: {final_content_str}")

        return {"status": "success", "result": sheet_json}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def execute_sheet_creation(ctx: Context, title: str, sheets_json: str) -> Dict[str, Any]:
    """
    Step 2 of 2 for creating a complex sheet. Takes the `title` and `sheets_json` output from `generate_sheet_json` and builds the actual Google Spreadsheet file, populating it with data and formatting.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gsheets(creds)
        
        sheets_data = JsonExtractor.extract_valid_json(sheets_json)
        if not sheets_data:
            raise ToolError("Invalid sheets_json provided.")

        spreadsheet_result = await asyncio.to_thread(
            utils.create_spreadsheet_with_data, service, title, sheets_data
        )
        
        return spreadsheet_result
    except Exception as e:
        return {"status": "failure", "error": str(e)}

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9015))
    
    print(f"Starting GSheets MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)
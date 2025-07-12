import os
import asyncio
import json
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from qwen_agent.agents import Assistant
from json_extractor import JsonExtractor

from . import auth, prompts, utils

# --- LLM and Environment Configuration ---
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "OLLAMA")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "qwen3:4b")
NOVITA_API_KEY = os.getenv("NOVITA_API_KEY")
NOVITA_MODEL_NAME = os.getenv("NOVITA_MODEL_NAME", "qwen/qwen3-4b-fp8")

def get_generator_agent(username: str):
    system_prompt = prompts.JSON_GENERATOR_SYSTEM_PROMPT.format(username=username)
    llm_cfg = {}
    if LLM_PROVIDER == "OLLAMA":
        llm_cfg = {'model': OLLAMA_MODEL_NAME, 'model_server': f"{OLLAMA_BASE_URL.rstrip('/')}/v1/", 'api_key': 'ollama'}
    elif LLM_PROVIDER == "NOVITA":
        llm_cfg = {'model': NOVITA_MODEL_NAME, 'model_server': "https://api.novita.ai/v3/openai", 'api_key': NOVITA_API_KEY}
    else:
        raise ValueError(f"Invalid LLM_PROVIDER: {LLM_PROVIDER}")
    return Assistant(llm=llm_cfg, system_message=system_prompt, function_list=[])

mcp = FastMCP(
    name="GSlidesServer",
    instructions="This server provides tools to create Google Slides presentations in a two-step process.",
)

@mcp.resource("prompt://gslides-agent-system")
def get_gslides_system_prompt() -> str:
    return prompts.MAIN_AGENT_SYSTEM_PROMPT

@mcp.tool()
async def generate_presentation_json(ctx: Context, topic: str, previous_tool_response: Optional[str] = "{}") -> Dict[str, Any]:
    """
    Step 1: Generates the structured JSON outline needed to create a Google Slides presentation.
    Provide a topic and optionally the JSON result from a previous tool. This tool will use an internal AI to create the detailed JSON for the presentation.
    The output of this tool should be passed directly to the `execute_presentation_creation` tool.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)
        user_profile = await auth.users_collection.find_one({"user_id": user_id})
        username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", "User") if user_profile else "User"

        agent = get_generator_agent(username)
        # Correctly pass the username to the internal prompt
        user_prompt = prompts.gslides_internal_user_prompt.format(
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
            raise Exception("The presentation generator agent returned an empty response.")
        
        outline_json_obj = JsonExtractor.extract_valid_json(final_content_str)
        if not outline_json_obj:
            raise Exception(f"Generator agent failed to produce valid JSON. Response: {final_content_str}")

        return {"status": "success", "result": {"outline_json": json.dumps(outline_json_obj)}}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def execute_presentation_creation(ctx: Context, outline_json: str) -> Dict[str, Any]:
    """
    Step 2: Creates the actual Google Slides presentation from the structured JSON outline.
    This tool takes the JSON output from `generate_presentation_json` and creates the file.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        slides_service = auth.authenticate_gslides(creds)
        drive_service = auth.authenticate_gdrive(creds)
        
        outline = json.loads(outline_json)

        presentation_result = await utils.create_presentation_from_outline(
            slides_service, drive_service, outline
        )
        
        return presentation_result
    except Exception as e:
        return {"status": "failure", "error": str(e)}

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9014))
    
    print(f"Starting GSlides MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)
import os
from typing import Dict, Any
from fastmcp.exceptions import ToolError
import asyncio
import textract

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message

from . import auth
# --- Environment Setup ---
# Load environment variables from a .env file.
# By default, load_dotenv() looks for .env in the current directory and its parents.
load_dotenv()

# Define the base temporary directory for file management
FILE_MANAGEMENT_TEMP_DIR = os.getenv('FILE_MANAGEMENT_TEMP_DIR', '/tmp/mcp_file_management_temp')

# Ensure the base temporary directory exists at startup
os.makedirs(FILE_MANAGEMENT_TEMP_DIR, exist_ok=True)

# --- MCP Server Initialization ---
mcp = FastMCP(
    name="FileManagementServer",
    instructions="Provides tools to read and write files in a temporary storage area, useful for handling uploads and generating files for download.",
)

def _get_safe_filepath(filename: str) -> str:
    """
    Constructs a full, safe path to a file within the temp directory and validates it.
    Prevents path traversal attacks.
    """
    # Base directory where all user files are stored
    base_dir = os.path.abspath(FILE_MANAGEMENT_TEMP_DIR)
    
    # Create the full path by joining the base directory and the relative filename
    # The filename from the agent already includes the user's subdirectory, e.g., "user-id/report.pdf"
    full_path = os.path.abspath(os.path.join(base_dir, filename))
    
    # SECURITY CHECK: Ensure the resolved path is still inside the base directory
    if not full_path.startswith(base_dir):
        raise ToolError("Access denied: Path traversal attempt detected.")
        
    return full_path

# --- Tool Definitions ---
@mcp.tool()
async def read_file(ctx: Context, filename: str) -> Dict[str, Any]:
    """
    Reads the content of a specified file from the temporary storage and extracts its text content. The `filename` should be one of the files returned by `list_files`.
    """
    try:
        safe_path = _get_safe_filepath(filename)
        if not os.path.exists(safe_path):
            return {"status": "failure", "error": "File not found."}
        
        def process_file():
            try:
                # textract returns bytes, so we need to decode
                extracted_bytes = textract.process(safe_path)
                return extracted_bytes.decode('utf-8', errors='ignore')
            except Exception as e:
                # textract can raise various exceptions for different file types
                return f"Error extracting text from file: {str(e)}"

        content = await asyncio.to_thread(process_file)

        return {"status": "success", "result": content}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def write_file(ctx: Context, filename: str, content: str) -> Dict[str, Any]:
    """
    Writes or overwrites a file in the temporary storage with the provided `content`.
    """
    try:
        safe_path = _get_safe_filepath(filename)
        # Ensure the directory exists before writing
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "success", "result": f"File '{filename}' written successfully."}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def list_files(ctx: Context) -> Dict[str, Any]:
    """
    Lists all files currently available in the user's temporary storage area.
    """
    try:
        user_id = auth.get_user_id_from_context(ctx)
        # Sanitize user_id to ensure it's safe for use in a file path
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ('-', '_'))
        user_dir = os.path.join(FILE_MANAGEMENT_TEMP_DIR, safe_user_id)

        if not os.path.isdir(user_dir):
            return {"status": "success", "result": []} # User has no files yet

        files = [f for f in os.listdir(user_dir) if os.path.isfile(os.path.join(user_dir, f))]
        
        # Return the relative path for the agent to use (e.g., "user-id/my_file.txt")
        relative_files = [os.path.join(safe_user_id, f) for f in files]
        return {"status": "success", "result": relative_files}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9026))
    
    print(f"Starting File Management MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)
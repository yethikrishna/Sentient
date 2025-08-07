import os
import motor.motor_asyncio
from dotenv import load_dotenv
from fastmcp import Context
from fastmcp.exceptions import ToolError

# Load .env file for 'dev-local' environment.
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]
users_collection = db["user_profiles"]

def get_user_id_from_context(ctx: Context) -> str:
    """
    Extracts the User ID from the 'X-User-ID' header in the HTTP request.
    """
    http_request = ctx.get_http_request()
    if not http_request:
        raise ToolError("HTTP request context is not available.")
    user_id = http_request.headers.get("X-User-ID")
    if not user_id:
        raise ToolError("Authentication failed: 'X-User-ID' header is missing.")
    return user_id

async def check_linkedin_integration(user_id: str):
    """Checks if the user has the LinkedIn integration connected."""
    user_doc = await users_collection.find_one({"user_id": user_id})
    if not user_doc:
        raise ToolError(f"User profile not found for user_id: {user_id}.")

    linkedin_data = user_doc.get("userData", {}).get("integrations", {}).get("linkedin", {})
    if not linkedin_data.get("connected"):
        raise ToolError("LinkedIn integration is not connected. Please enable it in the Integrations page.")
    return True
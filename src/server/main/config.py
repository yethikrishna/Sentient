import os
from dotenv import load_dotenv
import datetime

# Load .env from the current 'main' directory's parent, which is 'server'
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path):
    print(f"[{datetime.datetime.now()}] [MainServer_Config] Loading .env from: {dotenv_path}")
    load_dotenv(dotenv_path=dotenv_path)

APP_SERVER_PORT = int(os.getenv("APP_SERVER_PORT", "5000"))

# Auth0 Configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE") 
ALGORITHMS = ["RS256"]
# For Management API
AUTH0_MANAGEMENT_CLIENT_ID = os.getenv("AUTH0_MANAGEMENT_CLIENT_ID")
AUTH0_MANAGEMENT_CLIENT_SECRET = os.getenv("AUTH0_MANAGEMENT_CLIENT_SECRET")

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# GitHub OAuth Configuration
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

# News API Configuration
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sentient_agent_db")

# AES Encryption Keys
AES_SECRET_KEY_HEX = os.getenv("AES_SECRET_KEY")
AES_IV_HEX = os.getenv("AES_IV")

AES_SECRET_KEY = None
AES_IV = None

if AES_SECRET_KEY_HEX:
    if len(AES_SECRET_KEY_HEX) == 64: # 32 bytes = 64 hex chars
        AES_SECRET_KEY = bytes.fromhex(AES_SECRET_KEY_HEX)
    else:
        print(f"[{datetime.datetime.now()}] [MainServer_Config_WARNING] AES_SECRET_KEY is invalid (must be 64 hex characters for a 256-bit key). Encryption/Decryption will fail.")
else:
    print(f"[{datetime.datetime.now()}] [MainServer_Config_WARNING] AES_SECRET_KEY is not set. Encryption/Decryption will fail.")

if AES_IV_HEX:
    if len(AES_IV_HEX) == 32: # 16 bytes = 32 hex chars
        AES_IV = bytes.fromhex(AES_IV_HEX)
    else:
        print(f"[{datetime.datetime.now()}] [MainServer_Config_WARNING] AES_IV is invalid (must be 32 hex characters for a 128-bit IV). Encryption/Decryption will fail.")
else:
    print(f"[{datetime.datetime.now()}] [MainServer_Config_WARNING] AES_IV is not set. Encryption/Decryption will fail.")


# Google API Config (mainly for token storage path if server handles auth code exchange)
_SERVER_DIR_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) # main -> server
GOOGLE_TOKEN_STORAGE_DIR = os.path.join(_SERVER_DIR_ROOT, "google_tokens")
os.makedirs(GOOGLE_TOKEN_STORAGE_DIR, exist_ok=True)


# Polling related constants
POLLING_INTERVALS = {
    "ACTIVE_USER_SECONDS": int(os.getenv("POLL_GMAIL_ACTIVE_USER_SECONDS", 5 * 60)),
}
SUPPORTED_POLLING_SERVICES = ["gmail", "gcalendar"] 

# Note: For "oauth" type, the client ID will be added dynamically in the /sources endpoint
INTEGRATIONS_CONFIG = {
    "github": {
        "display_name": "GitHub",
        "description": (
            "Connect to manage repositories, issues, and more. "
            "Enables the agent to interact with your GitHub account."),
        "auth_type": "oauth",
        "icon": "IconBrandGithub",
        "mcp_server_config": {
            "name": "github_server",
            "url": os.getenv("GITHUB_MCP_SERVER_URL", "http://localhost:9010/sse")
        }
    },
    "gdrive": { # User-configurable OAuth
        "display_name": "Google Drive",
        "description": (
            "Access and manage files in your Google Drive. "
            "Allows the agent to search and read your documents."),
        "auth_type": "oauth",
        "icon": "IconBrandGoogleDrive",
        "mcp_server_config": {
            "name": "gdrive_server",
            "url": os.getenv("GDRIVE_MCP_SERVER_URL", "http://localhost:9003/sse")
        }
    },
    "gcalendar": { # User-configurable OAuth
        "display_name": "Google Calendar",
        "description": (
            "Read and manage events on your Google Calendar. "
            "Enables the agent to check your schedule and create events."),
        "auth_type": "oauth",
        "icon": "IconCalendarEvent",
        "mcp_server_config": {
            "name": "gcal_server",
            "url": os.getenv("GCAL_MCP_SERVER_URL", "http://localhost:9002/sse")
        }
    },
    "gmail": { # User-configurable OAuth
        "display_name": "Gmail",
        "description": (
            "Read, send, and manage emails. "
            "Lets the agent interact with your Gmail inbox."),
        "auth_type": "oauth",
        "icon": "IconMail",
        "mcp_server_config": {
            "name": "gmail_server",
            "url": os.getenv("GMAIL_MCP_SERVER_URL", "http://localhost:9001/sse")
        }
    },
    "gdocs": {
        "display_name": "Google Docs",
        "description": (
            "Create and manage documents in your Google Docs. "
            "Allows the agent to generate new documents for you."),
        "auth_type": "oauth",
        "icon": "IconFileText",
        "mcp_server_config": {
            "name": "gdocs_server",
            "url": os.getenv("GDOCS_MCP_SERVER_URL", "http://localhost:9004/sse")
        }
    },
    "gslides": {
        "display_name": "Google Slides",
        "description": (
            "Create and manage presentations in Google Slides. "
            "The agent can build slide decks based on your requests."),
        "auth_type": "oauth",
        "icon": "IconPresentation",
        "mcp_server_config": {
            "name": "gslides_server",
            "url": os.getenv("GSLIDES_MCP_SERVER_URL", "http://localhost:9014/sse")
        }
    },
    "gsheets": {
        "display_name": "Google Sheets",
        "description": (
            "Create and manage spreadsheets in Google Sheets. "
            "The agent can help organize data into tables."),
        "auth_type": "oauth",
        "icon": "IconTable",
        "mcp_server_config": {
            "name": "gsheets_server",
            "url": os.getenv("GSHEETS_MCP_SERVER_URL", "http://localhost:9015/sse")
        }
    },
    "gmaps": {
        "display_name": "Google Maps",
        "description": (
            "Search for places and get directions. "
            "The agent can look up locations and routes for you."),
        "auth_type": "builtin",
        "icon": "IconMapPin",
        "mcp_server_config": {
            "name": "gmaps_server",
            "url": os.getenv("GMAPS_MCP_SERVER_URL", "http://localhost:9016/sse")
        }
    },
    "gshopping": {
        "display_name": "Google Shopping",
        "description": (
            "Search for products online. "
            "The agent can help you find items to purchase."),
        "auth_type": "builtin",
        "icon": "IconShoppingCart",
        "mcp_server_config": {
            "name": "gshopping_server",
            "url": os.getenv("GSHOPPING_MCP_SERVER_URL", "http://localhost:9017/sse")
        }
    },
    "slack": { # User-configurable Manual
        "display_name": "Slack",
        "description": (
            "Connect to your Slack workspace to send messages and more. "
            "Allows the agent to communicate in your Slack channels."),
        "auth_type": "manual",
        "icon": "IconBrandSlack",
        "manual_auth_info": {
            "instructions": [
                "1. Go to api.slack.com/apps and create a new app from scratch.",
                "2. In 'OAuth & Permissions', add User Token Scopes like `chat:write`, `channels:read`.",
                "3. Install the app and copy the 'User OAuth Token' (starts with `xoxp-`).",
                "4. Find your 'Team ID' (starts with `T`) from your Slack URL or settings."
            ],
            "fields": [
                {"id": "token", "label": "User OAuth Token", "type": "password"},
                {"id": "team_id", "label": "Team ID", "type": "text"}
            ]
        },
        "mcp_server_config": {
            "name": "slack_server",
            "url": os.getenv("SLACK_MCP_SERVER_URL", "http://localhost:9006/sse")
        }
    },
    "notion": {
        "display_name": "Notion",
        "description": (
            "Connect to your Notion workspace to search, create, and manage pages. "
            "Lets the agent organize information in your Notion."),
        "auth_type": "manual",
        "icon": "IconBrandNotion",
        "manual_auth_info": {
            "instructions": [
                "1. Go to notion.so/my-integrations to create a new integration.",
                "2. Give it a name and associate it with a workspace.",
                "3. On the next screen, copy the 'Internal Integration Token'.",
                "4. Share the specific pages or databases you want Sentient to access with your new integration."
            ],
            "fields": [
                {"id": "token", "label": "Internal Integration Token", "type": "password"}
            ]
        },
        "mcp_server_config": {
            "name": "notion_server",
            "url": os.getenv("NOTION_MCP_SERVER_URL", "http://localhost:9009/sse")
        }
    },
    "news": { # Built-in
        "display_name": "News",
        "description": "Fetches top headlines and news articles from around the world.",
        "auth_type": "builtin",
        "icon": "IconNews",
        "mcp_server_config": {
            "name": "news_server",
            "url": os.getenv("NEWS_MCP_SERVER_URL", "http://localhost:9012/sse")
        }
    },
    "internet_search": { # Built-in
        "display_name": "Internet Search",
        "description": "Allows the agent to search the web using Google Search.",
        "auth_type": "builtin",
        "icon": "IconWorldSearch",
        "mcp_server_config": {
            "name": "google_search",
            "url": os.getenv("GOOGLE_SEARCH_MCP_SERVER_URL", "http://localhost:9005/sse")
        }
    },
    "accuweather": { # Built-in
        "display_name": "AccuWeather",
        "description": "Provides current weather conditions and forecasts.",
        "auth_type": "builtin",
        "icon": "IconCloud", # Frontend needs to map this string to the icon component
        "mcp_server_config": {
            "name": "weather_server",
            "url": os.getenv("ACCUWEATHER_MCP_SERVER_URL", "http://localhost:9007/sse")
        }
    },
    "quickchart": { # Built-in
        "display_name": "QuickChart",
        "description": "Generates charts and data visualizations on the fly.",
        "auth_type": "builtin",
        "icon": "IconChartPie", # Frontend needs to map this
        "mcp_server_config": {
            "name": "quickchart_server",
            "url": os.getenv("QUICKCHART_MCP_SERVER_URL", "http://localhost:9008/sse")
        }
    },
    "progress_updater": { # Built-in tool for executor
        "display_name": "Progress Updater",
        "description": "Allows an executor agent to update task progress.",
        "auth_type": "builtin",
        "icon": "IconActivity", # Will need to add this icon
        "mcp_server_config": {
            "name": "progress_updater_server",
            "url": os.getenv("PROGRESS_UPDATER_MCP_SERVER_URL", "http://localhost:9011/sse")
        }
    },
    "chat_tools": { # Built-in, for chat agent
        "display_name": "Chat Agent Tools",
        "description": "Tools for the main conversational agent, like task handoff.",
        "auth_type": "builtin",
        "icon": "IconMessage", # Frontend can map this
        "mcp_server_config": {
            "name": "chat_tools_server",
            "url": os.getenv("CHAT_TOOLS_MCP_SERVER_URL", "http://localhost:9013/sse")
        }
    },
    "journal": { # Built-in, for chat agent
        "display_name": "Journal Tools",
        "description": "Tools for the managing the user's Journal.",
        "auth_type": "builtin",
        "icon": "IconMessage", # Frontend can map this
        "mcp_server_config": {
            "name": "journal_server",
            "url": os.getenv("JOURNAL_MCP_SERVER_URL", "http://localhost:9018/sse")
        }
    },
}

# --- Service Provider Configuration ---
# These variables allow for flexible switching between different service providers.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "OLLAMA") # Options: "OLLAMA", "NOVITA"
# STT_PROVIDER = os.getenv("STT_PROVIDER", "FASTER_WHISPER") # Voice removed
# TTS_PROVIDER = os.getenv("TTS_PROVIDER", "ORPHEUS") # Voice removed

# --- Service-Specific API Keys and Paths ---
# ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY") # Voice removed
# ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb") # Voice removed

# Voice related model paths and settings removed


# LLM Endpoint Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434") 
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "qwen3:4b") 
NOVITA_API_KEY = os.getenv("NOVITA_API_KEY")
NOVITA_MODEL_NAME = os.getenv("NOVITA_MODEL_NAME", "qwen/qwen3-4b-fp8")
# MCP Server URLs
PROGRESS_UPDATER_MCP_SERVER_URL=os.getenv("PROGRESS_UPDATER_MCP_SERVER_URL", "http://localhost:9011/sse")
CHAT_TOOLS_MCP_SERVER_URL=os.getenv("CHAT_TOOLS_MCP_SERVER_URL", "http://localhost:9013/sse") # For agent action handoff
SUPERMEMORY_MCP_BASE_URL = os.getenv("SUPERMEMORY_MCP_BASE_URL", "https://mcp.supermemory.ai/")
SUPERMEMORY_MCP_ENDPOINT_SUFFIX = os.getenv("SUPERMEMORY_MCP_ENDPOINT_SUFFIX", "/sse")

print(f"[{datetime.datetime.now()}] [MainServer_Config] Configuration loaded. AUTH0_DOMAIN: {'SET' if AUTH0_DOMAIN else 'NOT SET'}")
print(f"[{datetime.datetime.now()}] [MainServer_Config] LLM Provider: {LLM_PROVIDER}")
# print(f"[{datetime.datetime.now()}] [MainServer_Config] STT Provider: {STT_PROVIDER}") # Voice removed
# print(f"[{datetime.datetime.now()}] [MainServer_Config] TTS Provider: {TTS_PROVIDER}") # Voice removed
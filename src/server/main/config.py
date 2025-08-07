import os
from dotenv import load_dotenv
import datetime
import logging


# --- Environment Loading Logic ---
# This is the primary determinant of the runtime environment.
# It should be set in the runtime environment (e.g., Docker `environment` or shell `export`).
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
logging.info(f"[{datetime.datetime.now()}] [Config] Initializing configuration for ENVIRONMENT='{ENVIRONMENT}'")

server_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ENVIRONMENT == 'dev-local':
    # Prefer .env.local, fall back to .env
    dotenv_local_path = os.path.join(server_root, '.env.local')
    dotenv_path = os.path.join(server_root, '.env')
    load_path = dotenv_local_path if os.path.exists(dotenv_local_path) else dotenv_path
    logging.info(f"[{datetime.datetime.now()}] [Config] Loading .env file for 'dev-local' mode from: {load_path}")
    if os.path.exists(load_path):
        load_dotenv(dotenv_path=load_path)
elif ENVIRONMENT == 'selfhost':
    # Self-hosting with Docker. docker-compose injects variables from src/.env for substitution.
    # python-dotenv loads .env.selfhost to get the rest of the config.
    dotenv_path = os.path.join(server_root, '.env.selfhost')
    logging.info(f"[{datetime.datetime.now()}] [Config] Loading .env file for 'selfhost' mode from: {dotenv_path}")
    load_dotenv(dotenv_path=dotenv_path)
else:
    # For 'dev-cloud', 'stag', 'prod', variables are loaded by start.sh or the cloud environment.
    logging.info(f"[{datetime.datetime.now()}] [Config] Skipping python-dotenv loading for '{ENVIRONMENT}' mode. Expecting variables from shell environment.")

APP_SERVER_PORT = int(os.getenv("APP_SERVER_PORT", "5000"))

# Auth0 Configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE") 
AUTH0_SCOPE = os.getenv("AUTH0_SCOPE")
ALGORITHMS = ["RS256"]
SELF_HOST_AUTH_SECRET = os.getenv("SELF_HOST_AUTH_SECRET")
# For Management API
AUTH0_MANAGEMENT_CLIENT_ID = os.getenv("AUTH0_MANAGEMENT_CLIENT_ID")
AUTH0_MANAGEMENT_CLIENT_SECRET = os.getenv("AUTH0_MANAGEMENT_CLIENT_SECRET")

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Google API Key for services like Maps, Custom Search
GOOGLE_API_KEYS = list(filter(None, [
    os.getenv("GOOGLE_API_KEY"),
    os.getenv("GOOGLE_API_KEY_FALLBACK_1"),
    os.getenv("GOOGLE_API_KEY_FALLBACK_2"),
]))

# GitHub OAuth Configuration
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

# Slack & Notion OAuth Configuration
SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
NOTION_CLIENT_ID = os.getenv("NOTION_CLIENT_ID")
NOTION_CLIENT_SECRET = os.getenv("NOTION_CLIENT_SECRET")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
TODOIST_CLIENT_ID = os.getenv("TODOIST_CLIENT_ID")
TODOIST_CLIENT_SECRET = os.getenv("TODOIST_CLIENT_SECRET")
TRELLO_CLIENT_ID = os.getenv("TRELLO_CLIENT_ID")

# News API Configuration
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_KEYS = list(filter(None, [
    os.getenv("NEWS_API_KEY"),
    os.getenv("NEWS_API_KEY_FALLBACK_1"),
    os.getenv("NEWS_API_KEY_FALLBACK_2"),
]))

ACCUWEATHER_API_KEYS = list(filter(None, [
    os.getenv("ACCUWEATHER_API_KEY"),
    os.getenv("ACCUWEATHER_API_KEY_FALLBACK_1"),
    os.getenv("ACCUWEATHER_API_KEY_FALLBACK_2"),
]))

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

# WAHA Configuration
WAHA_URL = os.getenv("WAHA_URL", "http://localhost:3000")
WAHA_API_KEY = os.getenv("WAHA_API_KEY")

# Google API Config (mainly for token storage path if server handles auth code exchange)
_SERVER_DIR_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) # main -> server
GOOGLE_TOKEN_STORAGE_DIR = os.path.join(_SERVER_DIR_ROOT, "google_tokens")
os.makedirs(GOOGLE_TOKEN_STORAGE_DIR, exist_ok=True)

# File Management Configuration
FILE_MANAGEMENT_TEMP_DIR = os.getenv("FILE_MANAGEMENT_TEMP_DIR", "/tmp/sentient_files")
os.makedirs(FILE_MANAGEMENT_TEMP_DIR, exist_ok=True)

# Polling related constants
POLLING_INTERVALS = {
    "ACTIVE_USER_SECONDS": int(os.getenv("POLL_GMAIL_ACTIVE_USER_SECONDS", 5 * 60)),
}
SUPPORTED_POLLING_SERVICES = ["gmail", "gcalendar"] 

# Note: For "oauth" type, the client ID will be added dynamically in the /sources endpoint
INTEGRATIONS_CONFIG = {
    "github": {
        "display_name": "GitHub",
        "description": "Connect to manage repositories, issues, and more. Enables the agent to search public and private repos, list your repos, view repository details, list issues, create new issues, and read file contents.",
        "auth_type": "oauth",
        "icon": "IconBrandGithub",
        "category": "Development",
        "mcp_server_config": {
            "name": "github_server",
            "url": os.getenv("GITHUB_MCP_SERVER_URL", "http://localhost:9010/sse")
        }
    },
    "gdrive": { # User-configurable OAuth
        "display_name": "Google Drive",
        "description": "Access and manage files in your Google Drive. Allows the agent to search for files by name or content and read the contents of various file types like documents and spreadsheets.",
        "auth_type": "oauth",
        "icon": "IconBrandGoogleDrive",
        "category": "Productivity",
        "mcp_server_config": {
            "name": "gdrive_server",
            "url": os.getenv("GDRIVE_MCP_SERVER_URL", "http://localhost:9003/sse")
        }
    },
    "gcalendar": { # User-configurable OAuth
        "display_name": "Google Calendar",
        "description": "Read and manage events on your Google Calendar. Enables the agent to list upcoming events, add new events, search for specific events, update event details, and delete events.",
        "auth_type": "oauth",
        "icon": "IconCalendarEvent",
        "category": "Productivity",
        "mcp_server_config": {
            "name": "gcal_server",
            "url": os.getenv("GCAL_MCP_SERVER_URL", "http://localhost:9002/sse")
        }
    },
    "gmail": { # User-configurable OAuth
        "display_name": "Gmail",
        "description": "Read, send, and manage emails. The agent can search your inbox, send new emails, create drafts, reply to threads, forward messages, and manage emails by deleting them or marking them as read/unread.",
        "auth_type": "oauth",
        "icon": "IconMail",
        "category": "Communication",
        "mcp_server_config": {
            "name": "gmail_server",
            "url": os.getenv("GMAIL_MCP_SERVER_URL", "http://localhost:9001/sse")
        }
    },
    "gdocs": {
        "display_name": "Google Docs",
        "description": "Create and manage documents in Google Docs. Allows the agent to generate new, multi-section documents with titles, headings, paragraphs, and bullet points.",
        "auth_type": "oauth",
        "icon": "IconFileText",
        "category": "Productivity",
        "mcp_server_config": {
            "name": "gdocs_server",
            "url": os.getenv("GDOCS_MCP_SERVER_URL", "http://localhost:9004/sse")
        }
    },
    "gslides": {
        "display_name": "Google Slides",
        "description": "Create and manage presentations in Google Slides. The agent can build new slide decks with titles, content, images, and charts based on a structured outline you provide.",
        "auth_type": "oauth",
        "icon": "IconPresentation",
        "category": "Productivity",
        "mcp_server_config": {
            "name": "gslides_server",
            "url": os.getenv("GSLIDES_MCP_SERVER_URL", "http://localhost:9014/sse")
        }
    },
    "gsheets": {
        "display_name": "Google Sheets",
        "description": "Create and manage spreadsheets in Google Sheets. The agent can help organize data by creating new spreadsheets with one or more sheets, including headers and rows.",
        "auth_type": "oauth",
        "icon": "IconTable",
        "category": "Productivity",
        "mcp_server_config": {
            "name": "gsheets_server",
            "url": os.getenv("GSHEETS_MCP_SERVER_URL", "http://localhost:9015/sse")
        }
    },
    "gpeople": {
        "display_name": "Google People",
        "description": "Manage your contacts. The agent can search, create, update, and delete contacts in your Google account, helping you keep your address book organized.",
        "auth_type": "oauth",
        "icon": "IconUsers",
        "category": "Productivity",
        "mcp_server_config": {
            "name": "gpeople_server",
            "url": os.getenv("GPEOPLE_MCP_SERVER_URL", "http://localhost:9019/sse")
        }
    },
    "gmaps": {
        "display_name": "Google Maps",
        "description": "Search for places and get directions. The agent can look up addresses, points of interest, and find routes for driving, walking, bicycling, or transit.",
        "auth_type": "builtin",
        "icon": "IconMapPin",
        "category": "Utilities",
        "mcp_server_config": {
            "name": "gmaps_server",
            "url": os.getenv("GMAPS_MCP_SERVER_URL", "http://localhost:9016/sse")
        }
    },
    "gshopping": {
        "display_name": "Google Shopping",
        "description": "Search for products online. The agent can find items to purchase by searching Google Shopping and returning a list of products with titles, links, and prices.",
        "auth_type": "builtin",
        "icon": "IconShoppingCart",
        "category": "Utilities",
        "mcp_server_config": {
            "name": "gshopping_server",
            "url": os.getenv("GSHOPPING_MCP_SERVER_URL", "http://localhost:9017/sse")
        }
    },
    "slack": { # User-configurable Manual
        "display_name": "Slack",
        "description": "Connect to your Slack workspace. Allows the agent to list channels, post messages, reply in threads, add reactions, read channel history, and get user information.",
        "auth_type": "oauth",
        "icon": "IconBrandSlack",
        "category": "Communication",
        "mcp_server_config": {
            "name": "slack_server",
            "url": os.getenv("SLACK_MCP_SERVER_URL", "http://localhost:9006/sse")
        }
    },
    "notion": {
        "display_name": "Notion",
        "description": "Connect to your Notion workspace. The agent can search for pages and databases, read page content, create new pages, append content to existing pages, and query databases with filters.",
        "auth_type": "oauth",
        "icon": "IconBrandNotion",
        "category": "Productivity",
        "mcp_server_config": {
            "name": "notion_server",
            "url": os.getenv("NOTION_MCP_SERVER_URL", "http://localhost:9009/sse")
        }
    },
    "trello": {
        "display_name": "Trello",
        "description": "Organize projects and tasks. The agent can list your boards, lists, and cards, as well as create new cards on your behalf.",
        "auth_type": "oauth",
        "icon": "IconBrandTrello",
        "category": "Productivity",
        "mcp_server_config": {
            "name": "trello_server",
            "url": os.getenv("TRELLO_MCP_SERVER_URL", "http://localhost:9025/sse")
        }
    },
    "todoist": {
        "display_name": "Todoist",
        "description": "Manage your tasks and projects in Todoist. The agent can list projects, get tasks (e.g., today's tasks), and create new tasks.",
        "auth_type": "oauth",
        "icon": "IconBrandTodoist",
        "category": "Productivity",
        "mcp_server_config": {
            "name": "todoist_server",
            "url": os.getenv("TODOIST_MCP_SERVER_URL", "http://localhost:9021/sse")
        }
    },
    "discord": {
        "display_name": "Discord",
        "description": "Connect to your Discord account to send messages to channels in servers your bot is in.",
        "auth_type": "oauth",
        "icon": "IconBrandDiscord",
        "category": "Communication",
        "mcp_server_config": {
            "name": "discord_server",
            "url": os.getenv("DISCORD_MCP_SERVER_URL", "http://localhost:9022/sse")
        }
    },
    "file_management": {
        "display_name": "File Management",
        "description": "Read and write files to and from a temporary storage area. Useful for handling uploads, reading files which are uploaded and mentioned by the user, generating files for download, and data analysis.",
        "auth_type": "builtin",
        "icon": "IconFile",
        "category": "Utilities",
        "mcp_server_config": {
            "name": "file_management_server",
            "url": os.getenv("FILE_MANAGEMENT_MCP_SERVER_URL", "http://localhost:9026/sse")
        }
    },
    "news": { # Built-in
        "display_name": "News",
        "description": "Fetches top headlines and news articles from around the world. The agent can get top headlines by country or category, or search for articles on any topic.",
        "auth_type": "builtin",
        "icon": "IconNews",
        "category": "Data & Search",
        "mcp_server_config": {
            "name": "news_server",
            "url": os.getenv("NEWS_MCP_SERVER_URL", "http://localhost:9012/sse")
        }
    },
    "internet_search": { # Built-in
        "display_name": "Internet Search",
        "description": "Allows the agent to search the web using Google Search to find real-time, factual information on any topic.",
        "auth_type": "builtin",
        "icon": "IconWorldSearch",
        "category": "Data & Search",
        "mcp_server_config": {
            "name": "google_search",
            "url": os.getenv("GOOGLE_SEARCH_MCP_SERVER_URL", "http://localhost:9005/sse")
        }
    },
    "accuweather": { # Built-in
        "display_name": "AccuWeather",
        "description": "Provides current weather conditions and daily forecasts. The agent can get the current weather for any location or a forecast for the next 1-5 days.",
        "auth_type": "builtin",
        "icon": "IconCloud", # Frontend needs to map this string to the icon component
        "category": "Utilities",
        "mcp_server_config": {
            "name": "weather_server",
            "url": os.getenv("ACCUWEATHER_MCP_SERVER_URL", "http://localhost:9007/sse")
        }
    },
    "history": {
        "display_name": "Conversation History",
        "description": "Searches the user's long-term conversation history. Use 'semantic_search' for topic-based queries (e.g., 'what did we decide about X?') and 'time_based_search' for date-based queries (e.g., 'what did we talk about last Tuesday?').",
        "auth_type": "builtin",
        "icon": "IconHistory", # Frontend will need to add this if it's ever displayed
        "category": "Data & Search",
        "mcp_server_config": {
            "name": "history_mcp",
            "url": os.getenv("HISTORY_MCP_SERVER_URL", "http://localhost:9020/sse")
        }
    },
    "quickchart": { # Built-in
        "display_name": "QuickChart",
        "description": "Generates charts and data visualizations on the fly. The agent can create bar charts, line charts, pie charts, and more, then provide a URL or download the image.",
        "auth_type": "builtin",
        "icon": "IconChartPie", # Frontend needs to map this
        "category": "Utilities",
        "mcp_server_config": {
            "name": "quickchart_server",
            "url": os.getenv("QUICKCHART_MCP_SERVER_URL", "http://localhost:9008/sse")
        }
    },
    "progress_updater": { # Built-in tool for executor
        "display_name": "Progress Updater",
        "description": "Internal tool for the system to provide real-time progress updates on long-running tasks.",
        "auth_type": "builtin",
        "icon": "IconActivity", # Will need to add this icon
        "category": "Utilities",
        "mcp_server_config": {
            "name": "progress_updater_server",
            "url": os.getenv("PROGRESS_UPDATER_MCP_SERVER_URL", "http://localhost:9011/sse")
        }
    },
    "memory": {
        "display_name": "Memory",
        "description": "Manages the user's memory. Use 'search_memory' to find facts, and 'cud_memory' to add, update, or delete information. This is critical for personalization.",
        "auth_type": "builtin",
        "icon": "IconBrain",
        "category": "Data & Search",
        "mcp_server_config": {
            "name": "memory_mcp",
            "url": os.getenv("MEMORY_MCP_SERVER_URL", "http://localhost:8001/sse")
        }
    },
    "whatsapp": {
        "display_name": "WhatsApp",
        "description": "Connect a WhatsApp number to allow your agent to send messages to yourself. This can be different from your notification number.",
        "auth_type": "manual",
        "category": "Communication",
        "icon": "IconBrandWhatsapp",
        "mcp_server_config": {
            "name": "whatsapp_server",
            "url": os.getenv("WHATSAPP_MCP_SERVER_URL", "http://localhost:9024/sse")
        }
    },
    "linkedin": {
        "display_name": "LinkedIn",
        "description": "Search for job listings on LinkedIn using the system's connection.",
        "auth_type": "manual",
        "icon": "IconBrandLinkedin",
        "category": "Data & Search",
        "mcp_server_config": {
            "name": "linkedin_server",
            "url": os.getenv("LINKEDIN_MCP_SERVER_URL", "http://localhost:9027/sse")
        }
    },
    "tasks": {
        "display_name": "Internal Task Manager",
        "description": "Manages asynchronous, background tasks. Use 'create_task_from_prompt' to create a new task from a natural language prompt. Use 'process_collection_in_parallel' to perform an action on each item in a list in parallel (e.g., summarize a list of articles).",
        "auth_type": "builtin",
        "icon": "IconChecklist",
        "mcp_server_config": {
            "name": "tasks_server",
            "url": os.getenv("TASKS_MCP_SERVER_URL", "http://localhost:9018/sse/")
        }
    }
}

# --- Service Provider Configuration ---
STT_PROVIDER = os.getenv("STT_PROVIDER", "FASTER_WHISPER")
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "ORPHEUS")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_API_KEYS = list(filter(None, [
    os.getenv("ELEVENLABS_API_KEY"),
    os.getenv("ELEVENLABS_API_KEY_FALLBACK_1"),
    os.getenv("ELEVENLABS_API_KEY_FALLBACK_2"),
]))

# For Orpheus (Dev TTS)
ORPHEUS_MODEL_PATH = os.getenv("ORPHEUS_MODEL_PATH", os.path.join(os.path.dirname(__file__), "voice", "models", "orpheus-3b-0.1-ft-q4_k_m.gguf"))
ORPHEUS_N_GPU_LAYERS = int(os.getenv("ORPHEUS_N_GPU_LAYERS", -1))

# FasterWhisper STT (Dev STT)
FASTER_WHISPER_MODEL_SIZE = os.getenv("FASTER_WHISPER_MODEL_SIZE", "base")
FASTER_WHISPER_DEVICE = os.getenv("FASTER_WHISPER_DEVICE", "cpu")
FASTER_WHISPER_COMPUTE_TYPE = os.getenv("FASTER_WHISPER_COMPUTE_TYPE", "int8")
HF_TOKEN = os.getenv("HF_TOKEN")

# LLM Endpoint Configuration
# --- OpenAI API Standard Configuration ---
# This can point to OpenAI, Ollama, Groq, or any other compatible service.
OPENAI_API_BASE_URL = os.getenv("OPENAI_API_BASE_URL", "http://localhost:11434/v1/")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "qwen3:4b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "ollama") # Default key for Ollama
OPENAI_API_KEYS = list(filter(None, [
    os.getenv("OPENAI_API_KEY"),
    os.getenv("OPENAI_API_KEY_FALLBACK_1"),
    os.getenv("OPENAI_API_KEY_FALLBACK_2"),
]))

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "models/gemini-embedding-001") # Default to same as LLM, can be overridden
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# MCP Server URLs
PROGRESS_UPDATER_MCP_SERVER_URL=os.getenv("PROGRESS_UPDATER_MCP_SERVER_URL", "http://localhost:9011/sse")
FILE_MANAGEMENT_MCP_SERVER_URL=os.getenv("FILE_MANAGEMENT_MCP_SERVER_URL", "http://localhost:9026/sse")

print(f"[{datetime.datetime.now()}] [MainServer_Config] Configuration loaded. AUTH0_DOMAIN: {'SET' if AUTH0_DOMAIN else 'NOT SET'}")
print(f"[{datetime.datetime.now()}] [MainServer_Config] LLM Endpoint: {OPENAI_API_BASE_URL}")
print(f"[{datetime.datetime.now()}] [MainServer_Config] LLM Model: {OPENAI_MODEL_NAME}")
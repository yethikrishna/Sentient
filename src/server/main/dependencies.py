# src/server/main/dependencies.py
from main.db import MongoManager
from main.auth.utils import AuthHelper
from main.websocket import MainWebSocketManager

# --- Global Instances ---
# These instances are created once here and imported by other modules
# to ensure a single, shared instance across the application.
mongo_manager = MongoManager()
auth_helper = AuthHelper()
websocket_manager = MainWebSocketManager()

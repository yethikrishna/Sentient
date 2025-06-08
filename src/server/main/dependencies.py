# src/server/main/dependencies.py
from .db import MongoManager
from .auth.utils import AuthHelper
from .websocket import MainWebSocketManager

# --- Global Instances ---
# These instances are created once here and imported by other modules
# to ensure a single, shared instance across the application.
mongo_manager = MongoManager()
auth_helper = AuthHelper()
websocket_manager = MainWebSocketManager()
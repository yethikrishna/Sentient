# src/server/main_server/dependencies.py
from server.common_lib.db.mongo_manager import MongoManager
from server.common.ws_manager import WebSocketManager
from server.common_lib.utils.auth import AuthHelper, PermissionChecker
import httpx # For making requests to other services

# Instantiate shared components for this server
mongo_manager_instance = MongoManager()
auth_helper_instance = AuthHelper()
main_websocket_manager = WebSocketManager()
http_client = httpx.AsyncClient() # For server-to-server communication

# Make them easily importable
mongo_manager = mongo_manager_instance
auth = auth_helper_instance

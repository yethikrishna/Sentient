# src/server/chat_server/dependencies.py
from server.common_lib.db.mongo_manager import MongoManager
from server.common_lib.utils.auth import AuthHelper, PermissionChecker

mongo_manager_instance = MongoManager()
auth_helper_instance = AuthHelper()

mongo_manager = mongo_manager_instance
auth = auth_helper_instance
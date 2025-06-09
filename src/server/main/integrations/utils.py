import datetime
import json
from typing import Dict, Any, Optional

from ..db import MongoManager
from ..auth.utils import aes_encrypt, aes_decrypt

async def store_encrypted_integration_token(user_id: str, service_name: str, token_data: Dict[str, Any], db_manager: MongoManager) -> bool:
    """Encrypts and stores the entire token object for a service."""
    token_data_str = json.dumps(token_data)
    encrypted_token_blob = aes_encrypt(token_data_str)
    
    update_payload = {
        f"userData.integrations.{service_name}": {
            "encrypted_token": encrypted_token_blob,
            "connected_at": datetime.datetime.now(datetime.timezone.utc)
        }
    }
    return await db_manager.update_user_profile(user_id, update_payload)

async def remove_integration(user_id: str, service_name: str, db_manager: MongoManager) -> bool:
    """Removes an integration and its token for a user."""
    field_path = f"userData.integrations.{service_name}"
    update_payload = {"$unset": {field_path: ""}}
    
    result = await db_manager.user_profiles_collection.update_one(
        {"user_id": user_id}, update_payload
    )
    return result.modified_count > 0

async def get_decrypted_integration_token(user_id: str, service_name: str, db_manager: MongoManager) -> Optional[Dict[str, Any]]:
    """Retrieves and decrypts an integration token for a user."""
    user_profile = await db_manager.get_user_profile(user_id)
    if not user_profile:
        return None
    
    integration_data = user_profile.get("userData", {}).get("integrations", {}).get(service_name)
    if not integration_data or "encrypted_token" not in integration_data:
        return None
        
    try:
        decrypted_token_str = aes_decrypt(integration_data["encrypted_token"])
        return json.loads(decrypted_token_str)
    except Exception:
        # Handle decryption or JSON parsing errors
        return None
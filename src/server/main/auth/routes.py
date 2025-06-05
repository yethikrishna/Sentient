# src/server/main/auth/routes.py
import datetime
import traceback
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from .utils import aes_encrypt, PermissionChecker
from .models import AuthTokenStoreRequest, GoogleTokenStoreRequest, EncryptionRequest, DecryptionRequest
from ..db import MongoManager
from ..config import DATA_SOURCES_CONFIG # For validating service_name
from ..app import auth_helper # Import the global auth_helper instance

router = APIRouter(
    prefix="/auth",
    tags=["Authentication & Authorization"]
)

# This instance of MongoManager will be initialized in app.py and used globally
# For routers, we can either import it or pass it via Depends if that's preferred.
# Here, importing the global instance from app.py for mongo_manager.
from ..app import mongo_manager_instance as mongo_manager


@router.post("/store_session")
async def store_session_tokens(
    request: AuthTokenStoreRequest, 
    user_id: str = Depends(auth_helper.get_current_user_id) 
):
    print(f"[{datetime.datetime.now()}] [AUTH_STORE_SESSION] Storing Auth0 refresh token for user {user_id}")
    try:
        encrypted_refresh_token = aes_encrypt(request.refresh_token)
        update_payload = {"userData.encrypted_refresh_token": encrypted_refresh_token}
        success = await mongo_manager.update_user_profile(user_id, update_payload)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store Auth0 refresh token.")
        return JSONResponse(content={"message": "Auth0 session tokens stored securely."})
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [AUTH_STORE_SESSION_ERROR] User {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error storing Auth0 session: {str(e)}")

@router.post("/google/store_token", summary="Store Google OAuth Refresh Token")
async def store_google_token_endpoint(
    request_body: GoogleTokenStoreRequest, 
    user_id: str = Depends(PermissionChecker(required_permissions=["manage:google_auth"])) 
):
    print(f"[{datetime.datetime.now()}] [GOOGLE_TOKEN_STORE] Storing Google refresh token for user {user_id}, service: {request_body.service_name}")
    if not request_body.service_name or request_body.service_name not in DATA_SOURCES_CONFIG: 
        raise HTTPException(status_code=400, detail=f"Invalid service name: {request_body.service_name}")
    try:
        encrypted_google_refresh_token = aes_encrypt(request_body.google_refresh_token)
        field_path = f"userData.google_services.{request_body.service_name}.encrypted_refresh_token"
        update_payload = {field_path: encrypted_google_refresh_token}
        
        success = await mongo_manager.update_user_profile(user_id, update_payload)

        if not success:
            print(f"[{datetime.datetime.now()}] [GOOGLE_TOKEN_STORE_ERROR] Failed to store token for user {user_id}, service {request_body.service_name}.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to store Google refresh token.")
        
        print(f"[{datetime.datetime.now()}] [GOOGLE_TOKEN_STORE] Successfully stored Google refresh token for user {user_id}, service {request_body.service_name}.")
        return JSONResponse(content={"message": f"Google refresh token for {request_body.service_name} stored successfully."})
    except ValueError as ve: 
        print(f"[{datetime.datetime.now()}] [GOOGLE_TOKEN_STORE_ERROR] User {user_id}: Encryption error - {ve}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Server configuration error: {str(ve)}")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [GOOGLE_TOKEN_STORE_ERROR] User {user_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error storing Google refresh token: {str(e)}")

@router.post("/utils/encrypt", summary="Encrypt Data (AES)") # Kept /utils prefix for consistency if client expects it
async def encrypt_data_endpoint(request: EncryptionRequest):
    # This endpoint does not strictly need authentication if it's a generic utility endpoint
    # If it needs auth, add: user_id: str = Depends(auth_helper.get_current_user_id)
    return JSONResponse(content={"encrypted_data": aes_encrypt(request.data)})

@router.post("/utils/decrypt", summary="Decrypt Data (AES)")
async def decrypt_data_endpoint(request: DecryptionRequest):
    # Similar to encrypt, add auth if needed
    try:
        return JSONResponse(content={"decrypted_data": aes_decrypt(request.encrypted_data)})
    except ValueError as ve: # Handles decryption errors like bad padding or key issues
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Decryption failed: {str(ve)}")
    except Exception as e: # Catch any other unexpected errors
        print(f"[{datetime.datetime.now()}] [AES_DECRYPT_ERROR] Unexpected error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during decryption.")
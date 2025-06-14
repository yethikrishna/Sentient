import datetime
import json
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from .models import ManualConnectRequest, OAuthConnectRequest, DisconnectRequest
from ..dependencies import mongo_manager, auth_helper
from ..auth.utils import aes_encrypt
from ..config import (
    INTEGRATIONS_CONFIG, 
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET
)

router = APIRouter(
    prefix="/integrations",
    tags=["Integrations Management"]
)

@router.get("/sources", summary="Get all available integration sources and their status")
async def get_integration_sources(user_id: str = Depends(auth_helper.get_current_user_id)):
    user_profile = await mongo_manager.get_user_profile(user_id)
    user_integrations = user_profile.get("userData", {}).get("integrations", {}) if user_profile else {}

    all_sources = []
    for name, config in INTEGRATIONS_CONFIG.items():
        source_info = config.copy()
        source_info["name"] = name
        user_connection = user_integrations.get(name, {})
        source_info["connected"] = user_connection.get("connected", False)
        
        # Add public config needed by the client for OAuth flow
        if source_info["auth_type"] == "oauth":
            if name.startswith('g'): # Google
                 source_info["client_id"] = GOOGLE_CLIENT_ID
            elif name == 'github':
                 source_info["client_id"] = GITHUB_CLIENT_ID

        all_sources.append(source_info)

    return JSONResponse(content={"integrations": all_sources})


@router.post("/connect/manual", summary="Connect an integration using manual credentials")
async def connect_manual_integration(request: ManualConnectRequest, user_id: str = Depends(auth_helper.get_current_user_id)):
    service_name = request.service_name
    if service_name not in INTEGRATIONS_CONFIG or INTEGRATIONS_CONFIG[service_name]["auth_type"] != "manual":
        raise HTTPException(status_code=400, detail="Invalid service name or auth type is not manual.")

    try:
        encrypted_creds = aes_encrypt(json.dumps(request.credentials))
        update_payload = {
            f"userData.integrations.{service_name}.credentials": encrypted_creds,
            f"userData.integrations.{service_name}.connected": True,
            f"userData.integrations.{service_name}.auth_type": "manual"
        }
        success = await mongo_manager.update_user_profile(user_id, update_payload)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save integration credentials.")

        return JSONResponse(content={"message": f"{service_name} connected successfully."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect/oauth", summary="Finalize OAuth2 connection by exchanging code for token")
async def connect_oauth_integration(request: OAuthConnectRequest, user_id: str = Depends(auth_helper.get_current_user_id)):
    service_name = request.service_name
    if service_name not in INTEGRATIONS_CONFIG or INTEGRATIONS_CONFIG[service_name]["auth_type"] != "oauth":
        raise HTTPException(status_code=400, detail="Invalid service name or auth type is not OAuth.")

    token_url = ""
    token_payload = {}
    request_headers = {}
    creds_to_save = {}

    if service_name.startswith('g'): # Google Services
        token_url = "https://oauth2.googleapis.com/token"
        token_payload = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": request.code,
            "grant_type": "authorization_code",
            "redirect_uri": request.redirect_uri,
        }
    elif service_name == 'github':
        token_url = "https://github.com/login/oauth/access_token"
        token_payload = {
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": request.code,
            "redirect_uri": request.redirect_uri,
        }
        request_headers = {"Accept": "application/json"}
    else:
        raise HTTPException(status_code=400, detail=f"OAuth flow not implemented for {service_name}")

    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=token_payload, headers=request_headers)
            token_response.raise_for_status()
            token_data = token_response.json()
        
        if service_name.startswith('g'):
            creds_to_save = {
                "token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
                "token_uri": token_url,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "scopes": token_data.get("scope", "").split(" "),
            }
        elif service_name == 'github':
             if "access_token" not in token_data:
                raise HTTPException(status_code=400, detail=f"GitHub OAuth error: {token_data.get('error_description', 'No access token in response.')}")
             creds_to_save = {"access_token": token_data["access_token"]}

        encrypted_creds = aes_encrypt(json.dumps(creds_to_save))

        update_payload = {
            f"userData.integrations.{service_name}.credentials": encrypted_creds,
            f"userData.integrations.{service_name}.connected": True,
            f"userData.integrations.{service_name}.auth_type": "oauth"
        }
        success = await mongo_manager.update_user_profile(user_id, update_payload)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save integration credentials.")

        return JSONResponse(content={"message": f"{service_name} connected successfully."})

    except httpx.HTTPStatusError as e:
        error_detail = e.response.json().get("error_description", f"Failed to exchange token with {service_name}.")
        raise HTTPException(status_code=e.response.status_code, detail=error_detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect", summary="Disconnect an integration")
async def disconnect_integration(request: DisconnectRequest, user_id: str = Depends(auth_helper.get_current_user_id)):
    service_name = request.service_name
    if service_name not in INTEGRATIONS_CONFIG:
        raise HTTPException(status_code=400, detail="Invalid service name.")

    try:
        # Unset the specific integration object
        update_payload = {f"userData.integrations.{service_name}": ""}
        result = await mongo_manager.user_profiles_collection.update_one(
            {"user_id": user_id},
            {"$unset": update_payload}
        )

        if result.modified_count == 0:
            # This can happen if the field didn't exist, which is not an error.
            return JSONResponse(content={"message": f"{service_name} was not connected or already disconnected."})

        return JSONResponse(content={"message": f"{service_name} disconnected successfully."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
import datetime
import json
import base64
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from main.integrations.models import ManualConnectRequest, OAuthConnectRequest, DisconnectRequest
from main.dependencies import mongo_manager, auth_helper
from main.auth.utils import aes_encrypt
from main.config import (
    INTEGRATIONS_CONFIG, 
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET,
    SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, NOTION_CLIENT_ID, NOTION_CLIENT_SECRET
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
            # Define a list of Google services to avoid matching 'github' with 'g'
            google_services = ["gmail", "gcalendar", "gdrive", "gdocs", "gslides", "gsheets", "gmaps", "gshopping", "gpeople"]
            if name in google_services:
                 source_info["client_id"] = GOOGLE_CLIENT_ID
            elif name == 'github':
                 source_info["client_id"] = GITHUB_CLIENT_ID
            elif name == 'slack':
                source_info["client_id"] = SLACK_CLIENT_ID
            elif name == 'notion':
                source_info["client_id"] = NOTION_CLIENT_ID

        all_sources.append(source_info)

    return {"integrations": all_sources}


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

    if service_name.startswith('g') and service_name != 'github': # Google Services
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
            "redirect_uri": request.redirect_uri
        }
        request_headers = {"Accept": "application/json"}

        # 🔍 DEBUG: Log the exact payload being sent to GitHub
        print(f"[DEBUG] GitHub OAuth request to {token_url}")
        print(f"[DEBUG] Headers: {request_headers}")
        print(f"[DEBUG] Payload: {token_payload}")
        print(f"[DEBUG] redirect_uri from frontend: {request.redirect_uri}")

    elif service_name == 'slack':
        token_url = "https://slack.com/api/oauth.v2.access"
        token_payload = {
            "client_id": SLACK_CLIENT_ID,
            "client_secret": SLACK_CLIENT_SECRET,
            "code": request.code,
            "redirect_uri": request.redirect_uri,
        }
    elif service_name == 'notion':
        token_url = "https://api.notion.com/v1/oauth/token"
        auth_string = f"{NOTION_CLIENT_ID}:{NOTION_CLIENT_SECRET}"
        auth_bytes = auth_string.encode("ascii")
        base64_string = base64.b64encode(auth_bytes).decode("ascii")
        request_headers = {
            "Authorization": f"Basic {base64_string}",
            "Content-Type": "application/json",
        }
        token_payload = {
            "grant_type": "authorization_code",
            "code": request.code,
            "redirect_uri": request.redirect_uri,
        }
    else:
        raise HTTPException(status_code=400, detail=f"OAuth flow not implemented for {service_name}")

    try:
        async with httpx.AsyncClient() as client:
            if service_name == 'notion':
                token_response = await client.post(token_url, json=token_payload, headers=request_headers)
            else:
                token_response = await client.post(token_url, data=token_payload, headers=request_headers)
            token_response.raise_for_status()
            token_data = token_response.json()
        
        if service_name.startswith('g') and service_name != 'github':
            # Extract granted scopes from the token response
            granted_scopes = token_data.get("scope", "").split(" ")
            # Update the credentials object to include scopes
            creds_to_save = {
                "token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
                "token_uri": token_url,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "scopes": granted_scopes,  # <--- SAVE THE SCOPES HERE
            }
        elif service_name == 'github':
             if "access_token" not in token_data:
                raise HTTPException(status_code=400, detail=f"GitHub OAuth error: {token_data.get('error_description', 'No access token in response.')}")
             creds_to_save = {"access_token": token_data["access_token"]}
        elif service_name == 'slack':
            if not token_data.get("ok"):
                 raise HTTPException(status_code=400, detail=f"Slack OAuth error: {token_data.get('error', 'Unknown error.')}")
            # The user token is nested inside authed_user
            creds_to_save = token_data # Store the whole response for now
        elif service_name == 'notion':
             if "access_token" not in token_data:
                raise HTTPException(status_code=400, detail=f"Notion OAuth error: {token_data.get('error_description', 'No access token in response.')}")
             creds_to_save = token_data # Store the whole object (access_token, workspace_id, etc.)

        encrypted_creds = aes_encrypt(json.dumps(creds_to_save))

        update_payload = {
            f"userData.integrations.{service_name}.credentials": encrypted_creds,
            f"userData.integrations.{service_name}.connected": True,
            f"userData.integrations.{service_name}.auth_type": "oauth"
        }
        success = await mongo_manager.update_user_profile(user_id, update_payload)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save integration credentials.")
        
        # Create the polling state document to enable the poller for this service
        if service_name == 'gmail' or service_name == 'gcalendar':
            await mongo_manager.update_polling_state(
                user_id,
                service_name,
                {
                    "is_enabled": True,
                    "is_currently_polling": False,
                    "next_scheduled_poll_time": datetime.datetime.now(datetime.timezone.utc), # Poll immediately
                    "last_successful_poll_timestamp_unix": None,
                }
            )

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
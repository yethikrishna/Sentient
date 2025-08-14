import os
import datetime
import json
import base64
import asyncio
import time
import uuid
import httpx
import logging
from composio import Composio, types
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from typing import Tuple

from main.integrations.models import ManualConnectRequest, OAuthConnectRequest, DisconnectRequest, ComposioInitiateRequest, ComposioFinalizeRequest
from main.dependencies import mongo_manager, auth_helper
from main.auth.utils import aes_encrypt, PermissionChecker
from main.config import (
    INTEGRATIONS_CONFIG, 
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    TODOIST_CLIENT_ID, TODOIST_CLIENT_SECRET,
    DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET,
    TRELLO_CLIENT_ID, COMPOSIO_API_KEY,
    GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, SLACK_CLIENT_ID,
    SLACK_CLIENT_SECRET, NOTION_CLIENT_ID, NOTION_CLIENT_SECRET,
)
from main.plans import PRO_ONLY_INTEGRATIONS

logger = logging.getLogger(__name__)

# Initialize Composio SDK
composio = Composio(api_key=COMPOSIO_API_KEY)


router = APIRouter(
    prefix="/integrations",
    tags=["Integrations Management"]
)

from mcp_hub.gcal.auth import get_google_creds, authenticate_gcal
from mcp_hub.gcal.utils import _simplify_event

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

        # Add Composio-specific config for the client
        if source_info["auth_type"] == "composio":
            # The client needs the auth_config_id to initiate the connection
            source_info["auth_config_id"] = os.getenv(f"{name.upper()}_AUTH_CONFIG_ID")


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
            elif name == 'trello':
                source_info["client_id"] = TRELLO_CLIENT_ID
            elif name == 'discord':
                source_info["client_id"] = DISCORD_CLIENT_ID
            elif name == 'todoist':
                source_info["client_id"] = TODOIST_CLIENT_ID
            # For Composio, we need the auth_config_id
            elif name == 'gmail':
                source_info["auth_config_id"] = os.getenv("GMAIL_AUTH_CONFIG_ID")
            elif name == 'gdrive':
                source_info["auth_config_id"] = os.getenv("GDRIVE_AUTH_CONFIG_ID")

        all_sources.append(source_info)

    return JSONResponse(content={"integrations": all_sources})


@router.post("/connect/manual", summary="Connect an integration using manual credentials")
async def connect_manual_integration(
    request: ManualConnectRequest,
    user_id_and_plan: Tuple[str, str] = Depends(auth_helper.get_current_user_id_and_plan)
):
    user_id, plan = user_id_and_plan
    service_name = request.service_name
    service_config = INTEGRATIONS_CONFIG.get(service_name)

    if not service_config:
        raise HTTPException(status_code=400, detail="Invalid service name.")

    # --- Check Plan Limit ---
    if service_name in PRO_ONLY_INTEGRATIONS and plan == "free":
        raise HTTPException(
            status_code=403,
            detail=f"The {service_config.get('display_name', service_name)} integration is a Pro feature. Please upgrade your plan."
        )

    # --- Check Plan Limit ---
    if service_name in PRO_ONLY_INTEGRATIONS and plan == "free":
        raise HTTPException(
            status_code=403,
            detail=f"The {service_config.get('display_name', service_name)} integration is a Pro feature. Please upgrade your plan."
        )

    # Allow Trello to use this endpoint despite being 'oauth' type, as its flow provides a token directly.
    if service_config["auth_type"] != "manual" and service_name != "trello":
        raise HTTPException(status_code=400, detail=f"Service '{service_name}' does not support this connection method.")

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


@router.get("/gcalendar/events", summary="Get Google Calendar events for a date range")
async def get_gcalendar_events(
    start_date: str = Query(..., description="Start date in ISO 8601 format"),
    end_date: str = Query(..., description="End date in ISO 8601 format"),
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    user_profile = await mongo_manager.get_user_profile(user_id)
    user_integrations = user_profile.get("userData", {}).get("integrations", {}) if user_profile else {}

    gcal_integration = user_integrations.get("gcalendar", {})
    if not gcal_integration.get("connected"):
        return JSONResponse(content={"events": []})

    try:
        creds = await get_google_creds(user_id)
        service = authenticate_gcal(creds)

        def _fetch_events_sync():
            events_result = service.events().list(
                calendarId="primary",
                timeMin=start_date,
                timeMax=end_date,
                maxResults=250,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            return events_result.get("items", [])

        events = await asyncio.to_thread(_fetch_events_sync)

        simplified_events = [_simplify_event(e) for e in events]

        return JSONResponse(content={"events": simplified_events})

    except Exception as e:
        print(f"Error fetching GCal events for user {user_id}: {e}")
        return JSONResponse(content={"events": []})

@router.post("/connect/oauth", summary="Finalize OAuth2 connection by exchanging code for token")
async def connect_oauth_integration(
    request: OAuthConnectRequest,
    user_id_and_plan: Tuple[str, str] = Depends(auth_helper.get_current_user_id_and_plan)
):
    user_id, plan = user_id_and_plan
    service_name = request.service_name
    if service_name not in INTEGRATIONS_CONFIG or INTEGRATIONS_CONFIG[service_name]["auth_type"] != "oauth":
        raise HTTPException(status_code=400, detail="Invalid service name or auth type is not OAuth.")

    # --- Check Plan Limit ---
    if service_name in PRO_ONLY_INTEGRATIONS and plan == "free":
        raise HTTPException(
            status_code=403,
            detail=f"The {INTEGRATIONS_CONFIG[service_name].get('display_name', service_name)} integration is a Pro feature. Please upgrade your plan."
        )

    # --- Check Plan Limit ---
    if service_name in PRO_ONLY_INTEGRATIONS and plan == "free":
        raise HTTPException(
            status_code=403,
            detail=f"The {INTEGRATIONS_CONFIG[service_name].get('display_name', service_name)} integration is a Pro feature. Please upgrade your plan."
        )

    token_url = ""
    token_payload = {}
    request_headers = {}
    creds_to_save = {}

    if not request.code:
        raise HTTPException(status_code=400, detail="Authorization code is missing.")

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
    elif service_name == 'todoist':
        token_url = "https://todoist.com/oauth/access_token"
        token_payload = {
            "client_id": TODOIST_CLIENT_ID,
            "client_secret": TODOIST_CLIENT_SECRET,
            "code": request.code,
            "redirect_uri": request.redirect_uri
        }
    elif service_name == 'discord':
        token_url = "https://discord.com/api/oauth2/token"
        token_payload = {
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": request.code,
            "redirect_uri": request.redirect_uri
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
        elif service_name == 'todoist':
            if "access_token" not in token_data:
                raise HTTPException(status_code=400, detail=f"Todoist OAuth error: {token_data.get('error', 'No access token in response.')}")
            creds_to_save = token_data
        elif service_name == 'discord':
            if "access_token" not in token_data:
                raise HTTPException(status_code=400, detail=f"Discord OAuth error: {token_data.get('error_description', 'No access token.')}")
            creds_to_save = token_data # This includes access_token, refresh_token, and the 'bot' object with bot token

        encrypted_creds = aes_encrypt(json.dumps(creds_to_save))

        update_payload = {
            f"userData.integrations.{service_name}.credentials": encrypted_creds,
            f"userData.integrations.{service_name}.connected": True,
            f"userData.integrations.{service_name}.auth_type": "oauth"
        }
        success = await mongo_manager.update_user_profile(user_id, update_payload)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save integration credentials.")
        
        if service_name == 'gmail' or service_name == 'gcalendar':
            # Check user's proactivity preference before enabling polling for PROACTIVITY ONLY
            user_profile = await mongo_manager.get_user_profile(user_id)
            is_proactivity_enabled = user_profile.get("userData", {}).get("preferences", {}).get("proactivityEnabled", False)

            # Create a state for the proactivity poller (depends on user setting)
            await mongo_manager.update_polling_state(
                user_id,
                service_name,
                "proactivity",
                {
                    "is_enabled": is_proactivity_enabled,
                    "is_currently_polling": False,
                    "next_scheduled_poll_time": datetime.datetime.now(datetime.timezone.utc), # Poll immediately
                    "last_successful_poll_timestamp_unix": None,
                }
            )
            # Create a state for the triggered workflow poller (ALWAYS enabled on connect)
            await mongo_manager.update_polling_state(
                user_id,
                service_name,
                "triggers",
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
        # Delete tasks that rely on this tool
        deleted_tasks_count = await mongo_manager.delete_tasks_by_tool(user_id, service_name)
        logger.info(f"Deleted {deleted_tasks_count} tasks for user {user_id} associated with disconnected tool '{service_name}'.")

        # Delete polling state for this source
        deleted_polling_states_count = await mongo_manager.delete_polling_state_by_service(user_id, service_name)
        logger.info(f"Deleted {deleted_polling_states_count} polling states for user {user_id} associated with disconnected source '{service_name}'.")

        # Unset the specific integration object from the user profile
        update_payload = {f"userData.integrations.{service_name}": ""}
        result = await mongo_manager.user_profiles_collection.update_one(
            {"user_id": user_id},
            {"$unset": update_payload}
        )

        if result.modified_count == 0 and deleted_tasks_count == 0 and deleted_polling_states_count == 0:
            # This can happen if the field didn't exist, which is not an error.
            return JSONResponse(content={"message": f"{service_name} was not connected or already disconnected."})

        return JSONResponse(content={"message": f"{service_name} disconnected successfully."})
    except Exception as e:
        logger.error(f"Error disconnecting integration {service_name} for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect/composio/initiate", summary="Initiate Composio OAuth flow")
async def initiate_composio_connection(
    request: ComposioInitiateRequest,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    service_name = request.service_name
    service_config = INTEGRATIONS_CONFIG.get(service_name)
    if not service_config or service_config.get("auth_type") != "composio":
        raise HTTPException(status_code=400, detail="Invalid service for Composio connection.")

    auth_config_id = os.getenv(f"{service_name.upper()}_AUTH_CONFIG_ID")
    if not auth_config_id:
        raise HTTPException(status_code=500, detail=f"Auth Config ID for {service_name} is not configured on the server.")

    try:
        logger.info(f"Initiating Composio for {service_name} with auth_config_id={auth_config_id}")
        callback_url = f"{os.getenv('APP_BASE_URL', 'http://localhost:3000')}/integrations"
        connection_request = composio.connected_accounts.initiate(
            user_id=user_id,
            auth_config_id=auth_config_id,
            callback_url=callback_url,
            config={
                "authScheme": "OAUTH2"
            }
        )

        return JSONResponse(content={"redirect_url": connection_request.redirect_url})
    except Exception as e:
        logger.error(f"Error initiating Composio connection for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect/composio/finalize", summary="Finalize Composio OAuth flow")
async def finalize_composio_connection(
    request: ComposioFinalizeRequest,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    service_name = request.service_name
    connected_account_id = request.connectedAccountId

    try:
        timeout = 120  # Wait for up to 2 minutes
        start_time = time.time()
        connected_account = None

        # Manually implement the polling logic to work around the SDK bug in wait_for_connection.
        while time.time() - start_time < timeout:
            # Use asyncio.to_thread to run the synchronous SDK call in a separate thread
            # The .get() method is an alias for .retrieve() and fetches the account by its ID.
            connected_account = await asyncio.to_thread(
                composio.connected_accounts.get, connected_account_id
            )

            if connected_account and connected_account.status == "ACTIVE":
                break  # Success!

            if connected_account and connected_account.status == "FAILED":
                raise HTTPException(status_code=400, detail="Connection failed during authentication with the provider.")

            await asyncio.sleep(2)  # Wait for 2 seconds before polling again
        else:
            # This block runs if the while loop finishes without a `break`
            raise TimeoutError("Connection verification timed out.")

        if not connected_account or connected_account.status != "ACTIVE":
            raise HTTPException(status_code=400, detail="Connection could not be verified or is not active.")

        logger.info(f"Finalized Composio connection for {service_name}: ID {connected_account_id}")

        update_payload = {
            f"userData.integrations.{service_name}.connection_id": connected_account.id,
            f"userData.integrations.{service_name}.connected": True,
            f"userData.integrations.{service_name}.auth_type": "composio"
        }
        await mongo_manager.update_user_profile(user_id, update_payload)

        return JSONResponse(content={"message": f"{service_name} connected successfully via Composio."})
    except Exception as e:
        logger.error(f"Error finalizing Composio connection for {user_id}: {e}", exc_info=True)
        if isinstance(e, TimeoutError) or "timed out" in str(e).lower():
            raise HTTPException(status_code=408, detail="Connection verification timed out. Please try again.")
        raise HTTPException(status_code=500, detail=str(e))

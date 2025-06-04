import os
import requests # Use requests for synchronous JWKS fetching at startup
from typing import List, Tuple, Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Security, WebSocket
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from jose.exceptions import JOSEError # Specific JOSE exception
import datetime 
import traceback

from server.common_lib.utils.config import AUTH0_DOMAIN, AUTH0_AUDIENCE, ALGORITHMS

# Fetch JWKS (JSON Web Key Set) from Auth0 for token validation at module load time
jwks = None
if AUTH0_DOMAIN:
    jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    try:
        print(f"[{datetime.datetime.now()}] [AuthUtils] Fetching JWKS from {jwks_url}...")
        jwks_response = requests.get(jwks_url, timeout=10)
        jwks_response.raise_for_status()
        jwks = jwks_response.json()
        print(f"[{datetime.datetime.now()}] [AuthUtils] JWKS fetched successfully.")
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.datetime.now()}] [AuthUtils FATAL ERROR] Could not fetch JWKS from Auth0: {e}")
        jwks = None
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [AuthUtils FATAL ERROR] Error processing JWKS: {e}")
        jwks = None
else:
    print(f"[{datetime.datetime.now()}] [AuthUtils FATAL ERROR] AUTH0_DOMAIN not set. Cannot fetch JWKS.")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # tokenUrl is a placeholder

class AuthHelper:
    async def _validate_token_and_get_payload(self, token: str) -> dict:
        if not jwks:
            print(f"[{datetime.datetime.now()}] [AuthHelper VALIDATION_ERROR] JWKS not available. Authentication service might be misconfigured or unreachable at startup.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service configuration error (JWKS missing)."
            )

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            unverified_header = jwt.get_unverified_header(token)
            if "kid" not in unverified_header:
                print(f"[{datetime.datetime.now()}] [AuthHelper VALIDATION_ERROR] 'kid' not found in token header.")
                raise credentials_exception
            
            token_kid = unverified_header["kid"]
            rsa_key_data = {}
            if not isinstance(jwks, dict) or "keys" not in jwks or not isinstance(jwks["keys"], list):
                print(f"[{datetime.datetime.now()}] [AuthHelper VALIDATION_ERROR] JWKS structure is invalid or 'keys' array is missing.")
                raise credentials_exception

            found_matching_key = False
            for key_entry in jwks["keys"]:
                if isinstance(key_entry, dict) and key_entry.get("kid") == token_kid:
                    required_rsa_components = ["kty", "kid", "use", "n", "e"]
                    if all(comp in key_entry for comp in required_rsa_components):
                        rsa_key_data = {comp: key_entry[comp] for comp in required_rsa_components}
                        found_matching_key = True
                        break
            
            if not found_matching_key or not rsa_key_data:
                print(f"[{datetime.datetime.now()}] [AuthHelper VALIDATION_ERROR] RSA key not found in JWKS for kid: {token_kid}")
                raise credentials_exception

            payload = jwt.decode(
                token,
                rsa_key_data,
                algorithms=ALGORITHMS,
                audience=AUTH0_AUDIENCE,
                issuer=f"https://{AUTH0_DOMAIN}/"
            )
            return payload
        except JWTError as e:
            print(f"[{datetime.datetime.now()}] [AuthHelper VALIDATION_ERROR] JWT Error: {e}")
            raise credentials_exception
        except JOSEError as e:
            print(f"[{datetime.datetime.now()}] [AuthHelper VALIDATION_ERROR] JOSE Error: {e}")
            raise credentials_exception
        except HTTPException:
            raise
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [AuthHelper VALIDATION_ERROR] Unexpected error during token validation: {e}")
            traceback.print_exc()
            raise credentials_exception

    async def get_current_user_id_and_permissions(self, token: str = Depends(oauth2_scheme)) -> Tuple[str, List[str]]:
        payload = await self._validate_token_and_get_payload(token)
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            print(f"[{datetime.datetime.now()}] [AuthHelper VALIDATION_ERROR] Token payload missing 'sub' (user_id).")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found in token")
        permissions: List[str] = payload.get("permissions", [])
        return user_id, permissions

    async def get_current_user_id(self, token: str = Depends(oauth2_scheme)) -> str:
        user_id, _ = await self.get_current_user_id_and_permissions(token=token)
        return user_id

    async def get_decoded_payload_with_claims(self, token: str = Depends(oauth2_scheme)) -> dict:
        payload = await self._validate_token_and_get_payload(token)
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found in token")
        payload["user_id"] = user_id # Add user_id for convenience
        return payload
    
    async def ws_authenticate(self, websocket: WebSocket) -> Optional[str]:
        """Authenticates a WebSocket connection by expecting an auth token."""
        try:
            auth_message_str = await websocket.receive_text()
            auth_message = json.loads(auth_message_str)
            
            if auth_message.get("type") != "auth" or not auth_message.get("token"):
                print(f"[{datetime.datetime.now()}] [WS_AUTH] Invalid auth message format.")
                await websocket.send_json({"type": "auth_failure", "message": "Invalid auth message format."})
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return None

            token = auth_message["token"]
            payload = await self._validate_token_and_get_payload(token) # Reuses HTTP token validation
            user_id = payload.get("sub")

            if not user_id:
                print(f"[{datetime.datetime.now()}] [WS_AUTH] Auth failed: User ID (sub) not in token.")
                await websocket.send_json({"type": "auth_failure", "message": "User ID not found in token."})
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return None

            print(f"[{datetime.datetime.now()}] [WS_AUTH] WebSocket authenticated for user: {user_id}")
            await websocket.send_json({"type": "auth_success", "user_id": user_id})
            return user_id
            
        except WebSocketDisconnect:
            print(f"[{datetime.datetime.now()}] [WS_AUTH] WebSocket disconnected during auth.")
            return None
        except json.JSONDecodeError:
            print(f"[{datetime.datetime.now()}] [WS_AUTH] Received non-JSON auth message.")
            await websocket.send_json({"type": "auth_failure", "message": "Auth message must be JSON."})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
        except HTTPException as e: # From _validate_token_and_get_payload
            print(f"[{datetime.datetime.now()}] [WS_AUTH] Token validation failed for WebSocket: {e.detail}")
            await websocket.send_json({"type": "auth_failure", "message": f"Token validation failed: {e.detail}"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [WS_AUTH_ERROR] Unexpected error during WebSocket authentication: {e}")
            traceback.print_exc()
            try:
                await websocket.send_json({"type": "auth_failure", "message": "Internal server error during authentication."})
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            except Exception: # Ignore errors during close if connection is already broken
                pass
            return None

class PermissionChecker:
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = set(required_permissions)

    async def __call__(self, auth_helper: AuthHelper = Depends(), token: str = Depends(oauth2_scheme)):
        user_id, token_permissions_list = await auth_helper.get_current_user_id_and_permissions(token=token)
        token_permissions_set = set(token_permissions_list)

        if not self.required_permissions.issubset(token_permissions_set):
            missing_permissions = self.required_permissions - token_permissions_set
            print(f"[{datetime.datetime.now()}] [Auth PERMISSION_DENIED] User {user_id} missing permissions. Required: {self.required_permissions}, Has: {token_permissions_set}, Missing: {missing_permissions}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Missing: {', '.join(missing_permissions)}"
            )
        return user_id # Return user_id if permissions are sufficient
import os
import requests
from typing import List, Tuple, Optional, Dict, Any # Added Dict, Any
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import jwt, JWTError
from jose.exceptions import JOSEError # Specific JOSE exception
from dotenv import load_dotenv
import datetime # For logging timestamps
import traceback # For detailed error logging

# Load .env from the server's root directory (one level up from 'utils')
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=dotenv_path)

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE") # Your Custom API Audience from Auth0
ALGORITHMS = ["RS256"] # Algorithm used by Auth0 for signing tokens

# Fetch JWKS (JSON Web Key Set) from Auth0 for token validation
jwks = None
if AUTH0_DOMAIN:
    jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    try:
        print(f"[{datetime.datetime.now()}] [AuthUtils] Fetching JWKS from {jwks_url}...")
        jwks_response = requests.get(jwks_url, timeout=10) # Added timeout
        jwks_response.raise_for_status() # Raise HTTPError for bad responses (4XX or 5XX)
        jwks = jwks_response.json()
        print(f"[{datetime.datetime.now()}] [AuthUtils] JWKS fetched successfully.")
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.datetime.now()}] [AuthUtils FATAL ERROR] Could not fetch JWKS from Auth0: {e}")
        jwks = None # Ensure jwks is None if fetching fails
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [AuthUtils FATAL ERROR] Error processing JWKS: {e}")
        jwks = None
else:
    print(f"[{datetime.datetime.now()}] [AuthUtils FATAL ERROR] AUTH0_DOMAIN not set. Cannot fetch JWKS.")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # tokenUrl is a placeholder, actual token comes from client

class AuthHelper:
    async def _validate_token_and_get_payload(self, token: str) -> dict:
        if not jwks: # Check if JWKS was successfully fetched
            print(f"[{datetime.datetime.now()}] [AuthHelper VALIDATION_ERROR] JWKS not available. Cannot validate token.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, # Service unavailable if auth config is broken
                detail="Authentication service configuration error (JWKS missing)."
            )

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            unverified_header = jwt.get_unverified_header(token)
            # Ensure 'kid' (Key ID) is present in the token header
            if "kid" not in unverified_header:
                print(f"[{datetime.datetime.now()}] [AuthHelper VALIDATION_ERROR] 'kid' not found in token header.")
                raise credentials_exception
            
            token_kid = unverified_header["kid"]
            
            # Find the RSA key in JWKS that matches the token's 'kid'
            rsa_key_data = {}
            # Ensure jwks and jwks["keys"] are valid before iterating
            if not isinstance(jwks, dict) or "keys" not in jwks or not isinstance(jwks["keys"], list):
                print(f"[{datetime.datetime.now()}] [AuthHelper VALIDATION_ERROR] JWKS structure is invalid or 'keys' array is missing.")
                raise credentials_exception

            found_matching_key = False
            for key_entry in jwks["keys"]:
                if isinstance(key_entry, dict) and key_entry.get("kid") == token_kid:
                    # Check for essential RSA key components
                    required_rsa_components = ["kty", "kid", "use", "n", "e"]
                    if all(comp in key_entry for comp in required_rsa_components):
                        rsa_key_data = {comp: key_entry[comp] for comp in required_rsa_components}
                        found_matching_key = True
                        break
            
            if not found_matching_key or not rsa_key_data:
                print(f"[{datetime.datetime.now()}] [AuthHelper VALIDATION_ERROR] RSA key not found in JWKS for kid: {token_kid}")
                raise credentials_exception

            # Decode and validate the token
            payload = jwt.decode(
                token,
                rsa_key_data,
                algorithms=ALGORITHMS,
                audience=AUTH0_AUDIENCE, # Validate against your API audience
                issuer=f"https://{AUTH0_DOMAIN}/" # Validate the issuer
            )
            return payload
        except JWTError as e: # Specific error for JWT validation issues
            print(f"[{datetime.datetime.now()}] [AuthHelper VALIDATION_ERROR] JWT Error: {e}")
            raise credentials_exception
        except JOSEError as e: # More general JOSE library errors
            print(f"[{datetime.datetime.now()}] [AuthHelper VALIDATION_ERROR] JOSE Error: {e}")
            raise credentials_exception
        except HTTPException: # Re-raise if it's already our specific exception
            raise
        except Exception as e: # Catch any other unexpected errors
            print(f"[{datetime.datetime.now()}] [AuthHelper VALIDATION_ERROR] Unexpected error during token validation: {e}")
            traceback.print_exc() # Log the full traceback for debugging
            raise credentials_exception

    async def get_current_user_id_and_permissions(self, token: str = Depends(oauth2_scheme)) -> Tuple[str, List[str]]:
        payload = await self._validate_token_and_get_payload(token)
        user_id: Optional[str] = payload.get("sub") # 'sub' is the standard claim for user ID
        if user_id is None:
            print(f"[{datetime.datetime.now()}] [AuthHelper VALIDATION_ERROR] Token payload missing 'sub' (user_id).")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found in token")
        
        permissions: List[str] = payload.get("permissions", []) # Get permissions if present
        # print(f"[AuthHelper] Token validated for user {user_id}. Permissions: {permissions}") # Debug log
        return user_id, permissions

    async def get_current_user_id(self, token: str = Depends(oauth2_scheme)) -> str:
        user_id, _ = await self.get_current_user_id_and_permissions(token=token)
        return user_id

    async def get_decoded_payload_with_claims(self, token: str = Depends(oauth2_scheme)) -> dict:
        """Returns the full decoded payload, including the user_id added for convenience."""
        payload = await self._validate_token_and_get_payload(token)
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found in token")
        payload["user_id"] = user_id # Add user_id directly to the payload for easier access
        return payload

# Class for checking permissions based on SecurityScopes
class PermissionChecker:
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = set(required_permissions)

    async def __call__(self, user_details: Tuple[str, List[str]] = Depends(AuthHelper().get_current_user_id_and_permissions)):
        user_id, token_permissions_list = user_details
        token_permissions_set = set(token_permissions_list)

        # Check if all required permissions are present in the token's permissions
        if not self.required_permissions.issubset(token_permissions_set):
            missing_permissions = self.required_permissions - token_permissions_set
            print(f"[{datetime.datetime.now()}] [Auth PERMISSION_DENIED] User {user_id} missing permissions. Required: {self.required_permissions}, Has: {token_permissions_set}, Missing: {missing_permissions}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Missing: {', '.join(missing_permissions)}"
            )
        # print(f"[Auth PERMISSION_GRANTED] User {user_id} has required permissions: {self.required_permissions}") # Debug log
        return user_id # Return user_id if permissions are sufficient

# Global instance for easier dependency injection
auth_helper = AuthHelper()
import os
import requests
from typing import List, Tuple, Optional
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from jose.exceptions import JOSEError
from dotenv import load_dotenv

# Load .env from the root of polling_service, one level up from core
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=dotenv_path)

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
ALGORITHMS = ["RS256"]

jwks = None
if AUTH0_DOMAIN:
    jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    try:
        print(f"[AuthUtils] Fetching JWKS from {jwks_url}...")
        jwks_response = requests.get(jwks_url, timeout=10)
        jwks_response.raise_for_status()
        jwks = jwks_response.json()
        print("[AuthUtils] JWKS fetched successfully.")
    except requests.exceptions.RequestException as e:
        print(f"[AuthUtils FATAL ERROR] Could not fetch JWKS from Auth0: {e}")
        jwks = None
    except Exception as e:
        print(f"[AuthUtils FATAL ERROR] Error processing JWKS: {e}")
        jwks = None
else:
    print("[AuthUtils FATAL ERROR] AUTH0_DOMAIN not set. Cannot fetch JWKS.")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # tokenUrl is placeholder

class AuthHelper: # Renamed class
    async def _validate_token_and_get_payload(self, token: str) -> dict:
        if not jwks:
            print("[AuthHelper VALIDATION_ERROR] JWKS not available.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth service config error (JWKS missing)."
            )
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            unverified_header = jwt.get_unverified_header(token)
            token_kid = unverified_header.get("kid")
            if not token_kid:
                print("[AuthHelper VALIDATION_ERROR] 'kid' missing in token header.")
                raise credentials_exception
            
            rsa_key_data = {}
            for key_entry in jwks.get("keys", []):
                if key_entry.get("kid") == token_kid:
                    rsa_key_data = key_entry
                    break
            
            if not rsa_key_data:
                print(f"[AuthHelper VALIDATION_ERROR] RSA key for kid '{token_kid}' not in JWKS.")
                raise credentials_exception

            payload = jwt.decode(
                token, rsa_key_data, algorithms=ALGORITHMS,
                audience=AUTH0_AUDIENCE, issuer=f"https://{AUTH0_DOMAIN}/"
            )
            return payload
        except JWTError as e:
            print(f"[AuthHelper VALIDATION_ERROR] JWT Error: {e}")
            raise credentials_exception
        except JOSEError as e:
            print(f"[AuthHelper VALIDATION_ERROR] JOSE Error: {e}")
            raise credentials_exception
        except HTTPException:
            raise
        except Exception as e:
            print(f"[AuthHelper VALIDATION_ERROR] Unexpected token validation error: {e}")
            import traceback
            traceback.print_exc()
            raise credentials_exception

    async def get_current_user_id_and_permissions(self, token: str = Depends(oauth2_scheme)) -> Tuple[str, List[str]]:
        payload = await self._validate_token_and_get_payload(token)
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID (sub) not in token")
        permissions: List[str] = payload.get("permissions", [])
        return user_id, permissions

    async def get_current_user_id(self, token: str = Depends(oauth2_scheme)) -> str:
        user_id, _ = await self.get_current_user_id_and_permissions(token=token)
        return user_id

class PermissionChecker:
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = set(required_permissions)

    async def __call__(self, user_details: Tuple[str, List[str]] = Depends(AuthHelper().get_current_user_id_and_permissions)):
        user_id, token_permissions_list = user_details
        token_permissions_set = set(token_permissions_list)
        if not self.required_permissions.issubset(token_permissions_set):
            missing = self.required_permissions - token_permissions_set
            print(f"[Auth PERMISSION_DENIED] User {user_id} missing: {missing}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Missing: {', '.join(missing)}"
            )
        return user_id

auth_helper = AuthHelper() # Global instance
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import base64
import os
import requests # For sync get_management_token
from fastapi import HTTPException, status
import datetime
import platform 
import traceback

from server.common_lib.utils.config import (
    AES_SECRET_KEY, AES_IV,
    AUTH0_DOMAIN, AUTH0_MANAGEMENT_CLIENT_ID, AUTH0_MANAGEMENT_CLIENT_SECRET
)

def aes_encrypt(data: str) -> str:
    if not AES_SECRET_KEY or not AES_IV:
        print(f"[{datetime.datetime.now()}] [AES_ENCRYPT_ERROR] AES keys not configured.")
        raise ValueError("AES encryption keys are not configured.")
    try:
        backend = default_backend()
        cipher = Cipher(algorithms.AES(AES_SECRET_KEY), modes.CBC(AES_IV), backend=backend)
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(data.encode()) + padder.finalize()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(encrypted).decode()
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [AES_ENCRYPT_ERROR] {str(e)}")
        traceback.print_exc()
        raise ValueError(f"Encryption failed: {str(e)}")


def aes_decrypt(encrypted_data: str) -> str:
    if not AES_SECRET_KEY or not AES_IV:
        print(f"[{datetime.datetime.now()}] [AES_DECRYPT_ERROR] AES keys not configured.")
        raise ValueError("AES encryption keys are not configured.")
    try:
        backend = default_backend()
        cipher = Cipher(algorithms.AES(AES_SECRET_KEY), modes.CBC(AES_IV), backend=backend)
        decryptor = cipher.decryptor()
        encrypted_bytes = base64.b64decode(encrypted_data)
        decrypted = decryptor.update(encrypted_bytes) + decryptor.finalize()
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        unpadded_data = unpadder.update(decrypted) + unpadder.finalize()
        return unpadded_data.decode()
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [AES_DECRYPT_ERROR] {str(e)}")
        traceback.print_exc()
        # It's common for decryption to fail with bad data/key, so return more specific error.
        if "padding" in str(e).lower() or "mac" in str(e).lower(): # Common padding/mac errors
             raise ValueError(f"Decryption failed: Invalid padding or key. Data might be corrupted or key/IV mismatch.")
        raise ValueError(f"Decryption failed: {str(e)}")


def get_management_token() -> str:
    if not AUTH0_DOMAIN or not AUTH0_MANAGEMENT_CLIENT_ID or not AUTH0_MANAGEMENT_CLIENT_SECRET:
        print(f"[{datetime.datetime.now()}] [MGMT_TOKEN_ERROR] Auth0 Management API credentials not configured.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth0 Management API configuration error.")
    
    url = f"https://{AUTH0_DOMAIN}/oauth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": AUTH0_MANAGEMENT_CLIENT_ID,
        "client_secret": AUTH0_MANAGEMENT_CLIENT_SECRET,
        "audience": f"https://{AUTH0_DOMAIN}/api/v2/",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        token_data = response.json()
        if "access_token" not in token_data:
            print(f"[{datetime.datetime.now()}] [MGMT_TOKEN_ERROR] 'access_token' not in response from Auth0.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid token response from Auth0.")
        return token_data["access_token"]
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.datetime.now()}] [MGMT_TOKEN_ERROR] Failed to retrieve management token: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Failed to retrieve management token: {e}")
    except (KeyError, Exception) as e: 
        print(f"[{datetime.datetime.now()}] [MGMT_TOKEN_ERROR] Error processing management token response: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error processing management token response.")
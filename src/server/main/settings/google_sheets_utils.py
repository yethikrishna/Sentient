import os
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# --- Configuration from Environment Variables ---
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CLIENT_EMAIL = os.getenv("GOOGLE_CLIENT_EMAIL")
# Private key needs special handling for newline characters when loaded from .env
GOOGLE_PRIVATE_KEY = os.getenv("GOOGLE_PRIVATE_KEY", "").replace('\\n', '\n')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_NAME = "Sheet1" # Assuming the sheet name is static

def _get_sheets_service():
    """Authenticates and returns a Google Sheets service object."""
    if not all([GOOGLE_SHEET_ID, GOOGLE_CLIENT_EMAIL, GOOGLE_PRIVATE_KEY]):
        logger.warning("Google Sheets credentials are not fully configured. Skipping sheet update.")
        return None

    try:
        creds = service_account.Credentials.from_service_account_info(
            {
                "client_email": GOOGLE_CLIENT_EMAIL,
                "private_key": GOOGLE_PRIVATE_KEY,
                "token_uri": "https://oauth2.googleapis.com/token",
                "project_id": os.getenv("GOOGLE_PROJECT_ID") # Optional but good practice
            },
            scopes=SCOPES
        )
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Failed to create Google Sheets service: {e}", exc_info=True)
        return None

async def update_contact_in_sheet(user_email: str, contact_number: str):
    """Finds a user by email in the sheet and updates their contact number."""
    service = _get_sheets_service()
    if not service:
        return

    try:
        # 1. Read the entire email column (C) to find the user's row
        range_to_read = f"{SHEET_NAME}!C:C"
        result = service.spreadsheets().values().get(spreadsheetId=GOOGLE_SHEET_ID, range=range_to_read).execute()
        rows = result.get('values', [])

        # 2. Find the row index (0-based) matching the user's email
        row_index = -1
        for i, row in enumerate(rows):
            if row and row[0] == user_email:
                row_index = i
                break

        if row_index != -1:
            # 3. Update the 'Contact' column (B) for that row
            range_to_update = f"{SHEET_NAME}!B{row_index + 1}" # Sheets are 1-based
            service.spreadsheets().values().update(spreadsheetId=GOOGLE_SHEET_ID, range=range_to_update, valueInputOption='USER_ENTERED', body={'values': [[contact_number]]}).execute()
            logger.info(f"Successfully updated contact for {user_email} in Google Sheet.")
        else:
            logger.warning(f"User with email {user_email} not found in Google Sheet. Could not update contact.")
    except Exception as e:
        logger.error(f"An error occurred while updating Google Sheet for {user_email}: {e}", exc_info=True)
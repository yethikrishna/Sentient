# server/mcp_hub/gcal/generate_google_token.py

import asyncio
import os
import json

import motor.motor_asyncio
from google_auth_oauthlib.flow import InstalledAppFlow

# --- Configuration ---
# This script should be in the same directory as your .env and credentials.json
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
ENV_FILE = os.path.join(os.path.dirname(__file__), '..', '..', '.env')

# This is the scope for full read/write access to Google Calendar.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

if not all([MONGO_URI, MONGO_DB_NAME]):
    print("Error: MONGO_URI and MONGO_DB_NAME must be set in your .env file.")
    exit()

async def main():
    """
    Runs the OAuth 2.0 flow to get a token and saves it to MongoDB.
    """
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"Error: Credentials file not found at '{CREDENTIALS_FILE}'")
        print("Please download it from your Google Cloud Console for a 'Desktop App' and place it here.")
        return

    # Prompt the user for a unique ID.
    user_id = input("Enter a unique User ID for this profile (e.g., 'sarthak', 'user01'): ").strip()
    if not user_id:
        print("User ID cannot be empty.")
        return

    print("\nStarting Google Authentication flow for Google Calendar...")
    print("Your web browser will open for you to log in and grant permissions.")

    # Create the flow using the downloaded credentials file
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    
    # Run the local server flow. This will open the browser.
    creds = flow.run_local_server(port=0)

    print("\nAuthentication successful!")

    # Convert the credentials object to a dictionary for MongoDB storage
    token_info = json.loads(creds.to_json())

    # --- Save the token to MongoDB ---
    print(f"Connecting to MongoDB at {MONGO_URI}...")
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        users_collection = db["users"]
        
        result = await users_collection.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "userId": user_id,
                    "google_token": token_info
                }
            },
            upsert=True
        )

        if result.upserted_id:
            print(f"\nSuccessfully created new user profile with ID: {user_id}")
        else:
            print(f"\nSuccessfully updated token for existing user with ID: {user_id}")

        print("You can now use this User ID in your MCP client.")

    except Exception as e:
        print(f"\nAn error occurred while saving to MongoDB: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
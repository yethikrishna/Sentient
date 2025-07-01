# server/mcp_hub/slack/generate_slack_token.py


# Setup
# Create a Slack App:
# Visit the Slack Apps page: https://api.slack.com/apps
# Click "Create New App"
# Choose "From scratch"
# Name your app and select your workspace
# Configure User Token Scopes: Navigate to "OAuth & Permissions" and add these scopes:
# channels:history - View messages and other content in public channels
# channels:read - View basic channel information
# chat:write - Send messages as yourself
# reactions:write - Add emoji reactions to messages
# users:read - View users and their basic information
# Install App to Workspace:
# Click "Install to Workspace" and authorize the app
# Save the "User OAuth Token" that starts with xoxp-
# Get your Team ID (starts with a T) by following this guidance: https://slack.com/intl/en-in/help/articles/221769328-Locate-your-Slack-URL-or-ID#find-your-workspace-or-org-id

import asyncio
import os

import motor.motor_asyncio
from getpass import getpass

# --- Configuration ---
ENV_FILE = os.path.join(os.path.dirname(__file__), '..', '..', '.env')

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

if not all([MONGO_URI, MONGO_DB_NAME]):
    print("Error: MONGO_URI and MONGO_DB_NAME must be set in your .env file.")
    exit()

async def main():
    """
    Prompts the user for their Slack credentials and saves them to MongoDB.
    """
    print("--- Slack Credential Storage ---")
    print("This script will save your Slack Team ID and User OAuth Token to the database.")

    user_id = input("Enter a unique User ID for this profile (e.g., 'sarthak', 'user01'): ").strip()
    if not user_id:
        print("User ID cannot be empty.")
        return

    team_id = input("Enter your Slack Team ID (starts with 'T'): ").strip()
    # Use getpass to hide the token as the user types it
    user_token = input("Enter your Slack User OAuth Token (starts with 'xoxp-'): ").strip()

    token_info = {"team_id": team_id, "token": user_token}

    print(f"\nConnecting to MongoDB...")
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        users_collection = db["users"]
        
        result = await users_collection.update_one(
            {"_id": user_id},
            {"$set": {"userId": user_id, "slack_token": token_info}},
            upsert=True
        )

        if result.upserted_id:
            print(f"\nSuccessfully created new user profile with ID: {user_id}")
        else:
            print(f"\nSuccessfully updated Slack token for existing user with ID: {user_id}")

        print("You can now use this User ID in your Slack MCP client.")
    except Exception as e:
        print(f"\nAn error occurred while saving to MongoDB: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(main())
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import uvicorn
from helpers import *
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv("../.env") # Load environment variables from .env file

# Initialize FastAPI application
app = FastAPI(
    title="Authentication API",
    description="API for handling Google OAuth2 authentication",
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins - configure this for production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods - configure this for production
    allow_headers=["*"],  # Allows all headers - configure this for production
)


# Pydantic model for request body (currently not used in this file, but defined for potential future use)
class BuildCredentialsRequest(BaseModel):
    """
    Pydantic model for build credentials request body.
    Currently not used in this application but can be used in future for dynamic credential building.
    """

    api_name: str
    api_version: str


# Define the scopes for Google API access.
# These scopes define the permissions that the application requests from the user during OAuth.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive",
    "https://mail.google.com/",
]

# Dictionary to hold the client credentials for OAuth 2.0 flow.
# These credentials should be obtained from the Google Cloud Console for your project.
CREDENTIALS_DICT = {
    "installed": {
        "client_id": os.environ.get("GOOGLE_CLIENT_ID"),  # Your Client ID from Google Cloud Console
        "project_id": os.environ.get("GOOGLE_PROJECT_ID"),  # Your Project ID from Google Cloud Console
        "auth_uri": os.environ.get("GOOGLE_AUTH_URI"),  # OAuth 2.0 Authorize URI from Google Cloud Console
        "token_uri": os.environ.get("GOOGLE_TOKEN_URI"),  # OAuth 2.0 Token URI from Google Cloud Console
        "auth_provider_x509_cert_url": os.environ.get("GOOGLE_AUTH_PROVIDER_x509_CERT_URL"),  # Auth Provider X.509 cert URL from Google Cloud Console
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),  # Your Client Secret from Google Cloud Console
        "redirect_uris": ["http://localhost"],  # Redirect URIs from Google Cloud Console
    }
}

@app.get("/authenticate-google")
async def authenticate_google():
    """
    Endpoint to authenticate with Google using OAuth 2.0.

    This endpoint checks for existing credentials in 'token.pickle'.
    If credentials are found and valid, it indicates successful authentication.
    If credentials are not found or invalid, it initiates the OAuth 2.0 flow,
    prompting the user to authenticate and authorize the application.
    Upon successful authentication, credentials are saved to 'token.pickle' for future use.

    Returns:
        JSONResponse: Returns a JSON response indicating the success or failure of the authentication process.
                      - On success: {"success": True} with HTTP status code 200.
                      - On failure: {"success": False, "error": str(e)} with HTTP status code 500, including the error message.
    """
    try:
        creds = None  # Initialize credentials variable

        # Check if a token.pickle file exists, which contains previously saved credentials.
        if os.path.exists("../token.pickle"):
            with open("../token.pickle", "rb") as token:
                creds = pickle.load(
                    token
                )  # Load credentials from the token.pickle file
                print(f"Loaded credentials")

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            # If credentials are expired but a refresh token is available, refresh the credentials.
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # If no valid credentials, create a flow object to perform OAuth.
                flow = InstalledAppFlow.from_client_config(CREDENTIALS_DICT, SCOPES)
                # Run the local server flow to get credentials by prompting user via browser.
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open("../token.pickle", "wb") as token:
                pickle.dump(creds, token)

        print(f"Authenticated Google")
        return JSONResponse(
            status_code=200, content={"success": True}
        )  # Return success response

    except Exception as e:
        print(f"Error authenticating Google: {e}")
        return JSONResponse(
            status_code=500, content={"success": False, "error": str(e)}
        )  # Return error response with exception details


if __name__ == "__main__":
    uvicorn.run(app, port=5007)  # Start the FastAPI application using Uvicorn server

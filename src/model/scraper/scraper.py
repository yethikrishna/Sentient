import os
import uvicorn
from runnables import *  # Importing runnable classes or functions from runnables.py
from functions import *  # Importing custom functions from functions.py
from helpers import *  # Importing helper functions from helpers.py
from prompts import *  # Importing prompt templates and related utilities from prompts.py
import nest_asyncio  # For running asyncio event loop within another event loop (needed for FastAPI in some environments)
from fastapi import FastAPI  # Importing FastAPI for creating the API application
from pydantic import (
    BaseModel,
)  # Importing BaseModel from Pydantic for request body validation and data modeling
from fastapi.responses import (
    JSONResponse,
)  # Importing JSONResponse for sending JSON responses from API endpoints
from fastapi.middleware.cors import (
    CORSMiddleware,
)  # Importing CORSMiddleware to handle Cross-Origin Resource Sharing
from fastapi import (
    FastAPI,
    HTTPException,
)  # Importing FastAPI and HTTPException for handling HTTP exceptions
from pydantic import BaseModel  # Re-importing BaseModel (likely a typo and redundant)
import os  # Re-importing os (likely a typo and redundant)
from dotenv import load_dotenv

load_dotenv("../.env")  # Load environment variables from .env file

# --- FastAPI Application Initialization ---
app = FastAPI()  # Creating a FastAPI application instance

# --- CORS Middleware Configuration ---
# Configuring CORS to allow requests from any origin.
# This is generally fine for open-source projects or APIs intended for broad use, but be cautious in production environments.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,  # Allows credentials (cookies, authorization headers) to be included in requests
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers to be included in requests
)


# --- Pydantic Models for Request Body Validation ---
class RedditURL(BaseModel):
    """
    Pydantic model for validating Reddit URL requests.
    Requires a 'url' string field.
    """

    url: str  # Reddit profile URL to scrape


class TwitterURL(BaseModel):
    """
    Pydantic model for validating Twitter URL requests.
    Requires a 'url' string field.
    """

    url: str  # Twitter profile URL to scrape


class LinkedInURL(BaseModel):
    """
    Pydantic model for validating LinkedIn URL requests.
    Requires a 'url' string field.
    """

    url: str  # LinkedIn profile URL to scrape


# --- Global Variables for Runnables ---
# These global variables store initialized Langchain Runnable sequences for Reddit and Twitter.
# Initialized in the `/initiate` endpoint.
reddit_runnable = None  # Runnable for Reddit-related tasks (topic extraction)
twitter_runnable = None  # Runnable for Twitter-related tasks (topic extraction)

# --- Apply nest_asyncio ---
# Applying nest_asyncio to allow asyncio event loops to be nested.
nest_asyncio.apply()


# --- API Endpoints ---
@app.get("/")
async def main():
    """
    Root endpoint of the API.
    Returns a simple welcome message.
    """
    return {
        "message": "Hello, I am Sentient, your private, decentralized and interactive AI companion who feels human"
    }


@app.post("/initiate", status_code=200)
async def initiate():
    """
    Endpoint to initialize the AI model and runnables for Reddit and Twitter.
    This endpoint sets up the global runnable variables required for scraping and topic extraction.
    Returns a success message or an error message if initialization fails.
    """
    global reddit_runnable, twitter_runnable

    # Initialize runnables for Reddit and Twitter using functions from runnables.py
    reddit_runnable = get_reddit_runnable()  # Get runnable for Reddit tasks
    twitter_runnable = get_twitter_runnable()  # Get runnable for Twitter tasks
    try:
        return JSONResponse(
            status_code=200, content={"message": "Model initiated successfully"}
        )  # Return success message
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"message": str(e)}
        )  # Return error message if exception occurs


@app.post("/scrape-linkedin", status_code=200)
async def scrape_linkedin(profile: LinkedInURL):
    """
    Endpoint to scrape and return LinkedIn profile information.
    Uses the `scrape_linkedin_profile` function to extract structured data from a LinkedIn profile URL.
    Returns the scraped profile data as a JSON response.
    """
    try:
        linkedin_profile = scrape_linkedin_profile(
            profile.url
        )  # Scrape LinkedIn profile data
        return JSONResponse(
            status_code=200, content={"profile": linkedin_profile}
        )  # Return scraped profile data in JSON response
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"message": str(e)}
        )  # Return error message if exception occurs


@app.post("/scrape-reddit")
async def scrape_reddit(reddit_url: RedditURL):
    """
    Endpoint to extract topics of interest from a Reddit user's profile.
    Leverages the `reddit_scraper` function to fetch subreddit data and then uses a
    `reddit_runnable` (Langchain Runnable) to process this data and extract topics of interest.
    Returns a JSON response containing the extracted topics.
    """
    global reddit_runnable

    try:
        subreddits = reddit_scraper(
            reddit_url.url
        )  # Scrape Reddit user's subreddit data

        response = reddit_runnable.invoke(
            {"subreddits": subreddits}
        )  # Invoke Reddit runnable to extract topics

        try:
            topics = response  # Get topics from the response
            if isinstance(topics, list):
                return JSONResponse(
                    status_code=200, content={"topics": topics}
                )  # Return topics in JSON response
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Invalid response format from the language model.",
                )  # Raise HTTPException for invalid response format
        except Exception as e:
            print(f"Error in scraping-reddit: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error parsing model response: {str(e)}"
            )  # Raise HTTPException for model response parsing error
    except HTTPException as http_exc:
        print(http_exc)
        raise http_exc  # Re-raise HTTPException
    except Exception as e:
        print(f"Error in scraping reddit: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Unexpected error: {str(e)}"
        )  # Raise HTTPException for unexpected errors

@app.post("/scrape-twitter")
async def scrape_twitter(twitter_url: TwitterURL):
    """
    Endpoint to extract topics of interest from a Twitter user's profile.
    Utilizes the `scrape_twitter_data` function to get tweet texts and then employs a
    `twitter_runnable` (Langchain Runnable) to analyze these texts and extract topics of interest.
    Returns a JSON response with the extracted topics.
    """
    global twitter_runnable

    try:
        tweets = scrape_twitter_data(
            twitter_url.url, 20
        )  # Scrape Twitter user's tweet data
        response = twitter_runnable.invoke(
            {"tweets": tweets}
        )  # Invoke Twitter runnable to extract topics
        topics = response  # Get topics from the response
        if isinstance(topics, list):
            return JSONResponse(
                status_code=200, content={"topics": topics}
            )  # Return topics in JSON response
        else:
            raise HTTPException(
                status_code=500,
                detail="Invalid response format from the language model.",
            )  # Raise HTTPException for invalid response format
    except HTTPException as http_exc:
        print(http_exc)
        raise http_exc  # Re-raise HTTPException
    except Exception as e:
        print(f"Error scraping twitter: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Unexpected error: {str(e)}"
        )  # Raise HTTPException for unexpected errors


# --- Main execution block ---
if __name__ == "__main__":
    """
    This block is executed when the script is run directly (not imported as a module).
    It starts the uvicorn server to run the FastAPI application.
    """
    uvicorn.run(app, port=5004)  # Start uvicorn server on port 5004
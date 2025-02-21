import os
from prompts import *  # Importing prompt templates and related utilities from prompts.py
from wrapt_timeout_decorator import *  # Importing timeout decorator for functions from wrapt_timeout_decorator library (not explicitly used in this file)
from helpers import *  # Importing helper functions from helpers.py
from runnables import *  # Importing other runnable classes or functions from runnables.py
import requests  # For making HTTP requests
from formats import *  # Importing format specifications or utilities from formats.py
from prompts import *  # Re-importing prompts, likely redundant
import ast  # For Abstract Syntax Tree manipulation, used for safely evaluating strings as Python literals
import json  # For working with JSON data
from sys import platform  # To get system platform information
from typing import Optional  # For type hints
from dotenv import load_dotenv

load_dotenv("../.env")  # Load environment variables from .env file


class CustomRunnable:
    """
    A custom runnable class to interact with language models via API calls.

    This class encapsulates the logic for building prompts, sending requests to a model API,
    and processing the responses. It supports both standard request-response and streaming modes,
    and can handle different response types including JSON.

    Differs from the stateful version by being stateless; it does not maintain conversation history
    across invocations. Each call starts with a fresh system prompt and user input.

    Attributes:
        model_url (str): URL of the language model API endpoint.
        model_name (str): Name or ID of the language model to be used.
        system_prompt_template (str): Template for the system prompt, setting the model's behavior.
        user_prompt_template (str): Template for the user prompt, containing placeholders for input variables.
        input_variables (list[str]): List of input variable names expected in the user prompt template.
        response_type (str): Expected response type, e.g., "json" or "chat".
        required_format (dict, optional): Expected JSON format for the response, used for structured output. Defaults to None.
        stream (bool): Flag to indicate if streaming response is enabled. Defaults to False.
        messages (list[dict]): List of messages for the current invocation, always starting with system prompt.
        stateful (bool): Always False for this stateless version.
    """

    def __init__(
        self,
        model_url: str,
        model_name: str,
        system_prompt_template: str,
        user_prompt_template: str,
        input_variables: list[str],
        response_type: str,
        required_format: Optional[dict] = None,
        stream: bool = False,
    ):
        """
        Initialize the CustomRunnable instance.

        :param model_url: URL of the model API endpoint.
        :param model_name: Name of the model to use.
        :param system_prompt_template: Template for the system prompt.
        :param user_prompt_template: Template for the user prompt.
        :param input_variables: List of variables required by the prompt.
        :param response_type: Expected response type ("json", "chat", etc.).
        :param required_format: Expected output format for the model response (e.g., JSON schema). Defaults to None.
        :param stream: Whether to use streaming for responses. Defaults to False.
        """
        self.model_url = model_url
        self.model_name = model_name
        self.system_prompt_template = system_prompt_template
        self.user_prompt_template = user_prompt_template
        self.input_variables = input_variables
        self.required_format = required_format
        self.messages = []  # Initialize messages as empty list for stateless behavior
        self.response_type = response_type
        self.stream = stream
        self.stateful = False  # Stateless runnable

    def build_prompt(self, inputs: dict) -> str:
        """
        Build the prompt by substituting input variables into the user prompt template.

        For stateless runnables, this method initializes the messages list with a system message
        and a helper message before formatting the user prompt.

        :param inputs: Dictionary of input variables to replace in the prompt template.
        :return: The constructed user prompt string.
        """
        user_prompt = self.user_prompt_template.format(
            **inputs
        )  # Format user prompt with inputs

        new_messages = [
            {"role": "user", "content": self.system_prompt_template},  # System prompt
            {
                "role": "assistant",
                "content": "Okay, I am ready to help",
            },  # Helper message from assistant
        ]

        self.messages = new_messages  # Reset messages to system and helper messages

        return user_prompt  # Return the formatted user prompt

    def add_to_history(self, chat_history: list[dict]):
        """
        This method is not applicable for stateless runnables and is left empty.

        Stateless runnables do not maintain chat history, so adding to history is not supported.
        :param chat_history: Chat history (not used in stateless runnables).
        :return: None
        """
        pass  # Stateless runnable does not maintain history

    def invoke(self, inputs: dict) -> dict | list | str | None:
        """
        Execute the model call with the constructed prompt and return the processed output.

        Sends a POST request to the model API endpoint with the built prompt and parameters.
        Handles JSON responses, attempts to fix malformed JSON, and parses valid JSON or literal evaluations.

        :param inputs: Dictionary of input values for the prompt.
        :return: Processed output from the model response. Can be a dict, list, str, or None depending on response and parsing.
        :raises ValueError: If the API request fails or if JSON decoding of the response fails and cannot be fixed.
        """
        user_prompt = self.build_prompt(
            inputs
        )  # Build the prompt using provided inputs
        self.messages.append(
            {"role": "user", "content": user_prompt}
        )  # Append user prompt to messages

        payload = {
            "model": self.model_name,  # Specify the model name
            "messages": self.messages,  # Include the message history (system + helper + user)
            "stream": False,  # Disable streaming for standard invoke
        }

        if self.response_type == "json":
            # Add format specification for JSON response if required
            if platform == "win32":
                payload["format"] = (
                    self.required_format
                )  # Format specification for Windows
            else:
                payload["format"] = json.dumps(
                    self.required_format
                )  # Format specification for non-Windows (needs to be JSON string)

        headers = {"Content-Type": "application/json"}  # Set headers for JSON request

        response = requests.post(
            self.model_url, headers=headers, data=json.dumps(payload)
        )  # Send POST request to model API

        if response.status_code == 200:
            # Successful API call
            try:
                data = (
                    response.json().get("message", {}).get("content", "")
                )  # Extract content from JSON response

                try:
                    # Attempt to parse response as JSON, fixing if necessary
                    parsed_data = extract_and_fix_json(data)
                    return parsed_data  # Return parsed JSON data
                except Exception:
                    pass  # If JSON parsing fails, try literal evaluation

                try:
                    # Attempt to parse response as Python literal (fallback for non-JSON structured data)
                    parsed_data = ast.literal_eval(data)
                    return parsed_data  # Return parsed literal data
                except (ValueError, SyntaxError):
                    pass  # If literal evaluation also fails, return raw string

                return data  # Return raw string data if no parsing succeeds

            except json.JSONDecodeError:
                print(f"Failed to decode JSON response: {response.text}")
                raise ValueError(
                    f"Failed to decode JSON response: {response.text}"
                )  # Raise error if initial JSON decode fails
        else:
            raise ValueError(
                f"Request failed with status code {response.status_code}: {response.text}"
            )  # Raise error for non-200 status codes

    def stream_response(self, inputs: dict):
        """Streaming version of invoke.

        Generates a streaming response from the model API, yielding tokens as they are received.
        This method is used for real-time text generation, providing a more interactive user experience.

        :param inputs: Dictionary of input values for the prompt variables.
        :yields: str or None: Tokens from the streaming response. Yields None at the end of the stream.
        """
        user_prompt = self.build_prompt(
            inputs
        )  # Build the prompt using provided inputs
        self.messages.append(
            {"role": "user", "content": user_prompt}
        )  # Append user prompt to messages

        payload = {
            "model": self.model_name,  # Specify the model name
            "messages": self.messages,  # Include the message history (system + helper + user)
            "stream": True,  # Enable streaming for response
        }

        if self.response_type == "json":
            payload["format"] = (
                self.required_format
            )  # Add format specification for JSON response if required

        with requests.post(self.model_url, json=payload, stream=True) as response:
            # Send streaming POST request to model API
            for line in response.iter_lines(
                decode_unicode=True
            ):  # Iterate over response lines
                if line:
                    try:
                        data = json.loads(line)  # Load each line as JSON

                        if data.get("done", False):
                            # Check for 'done' signal to end stream
                            if data.get("done_reason") == "load":
                                continue  # Skip 'load' done reason, continue streaming
                            else:
                                token = None  # Signal end of stream with None token
                                yield token
                                break  # Break out of streaming loop

                        token = data["message"][
                            "content"
                        ]  # Extract content token from data
                        if token:
                            yield token  # Yield the extracted token

                    except json.JSONDecodeError:
                        continue  # Ignore JSON decode errors in stream, continue to next line


def get_reddit_runnable() -> CustomRunnable:
    """
    Creates and configures a stateless CustomRunnable for interacting with Reddit data.

    This runnable is specifically set up for tasks related to Reddit, using Reddit-specific prompts
    and configurations. It is stateless, meaning it does not retain conversation history across calls.

    :return: A configured stateless CustomRunnable instance for Reddit interactions.
    """
    reddit_runnable = CustomRunnable(
        model_url=os.getenv(
            "BASE_MODEL_URL"
        ),  # Get model URL from environment variables
        model_name=os.getenv(
            "BASE_MODEL_REPO_ID"
        ),  # Get model name from environment variables
        system_prompt_template=reddit_system_prompt_template,  # System prompt for Reddit tasks
        user_prompt_template=reddit_user_prompt_template,  # User prompt template for Reddit tasks
        input_variables=[
            "subreddits"
        ],  # Input variables for Reddit prompt (expects subreddits)
        required_format=reddit_required_format,  # Expected JSON format for Reddit response
        response_type="json",  # Response type is JSON
    )

    return reddit_runnable  # Return the configured Reddit runnable


def get_twitter_runnable() -> CustomRunnable:
    """
    Creates and configures a stateless CustomRunnable for interacting with Twitter data.

    This runnable is specifically set up for tasks related to Twitter, using Twitter-specific prompts
    and configurations. Like the Reddit runnable, it is stateless and does not maintain conversation history.

    :return: A configured stateless CustomRunnable instance for Twitter interactions.
    """
    twitter_runnable = CustomRunnable(
        model_url=os.getenv(
            "BASE_MODEL_URL"
        ),  # Get model URL from environment variables
        model_name=os.getenv(
            "BASE_MODEL_REPO_ID"
        ),  # Get model name from environment variables
        system_prompt_template=twitter_system_prompt_template,  # System prompt for Twitter tasks
        user_prompt_template=twitter_user_prompt_template,  # User prompt template for Twitter tasks
        input_variables=[
            "tweets"
        ],  # Input variables for Twitter prompt (expects tweets)
        required_format=twitter_required_format,  # Expected JSON format for Twitter response
        response_type="json",  # Response type is JSON
    )

    return twitter_runnable  # Return the configured Twitter runnable

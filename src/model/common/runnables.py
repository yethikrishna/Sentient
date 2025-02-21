import os
from prompts import *  # Importing prompt templates and related utilities from prompts.py
from wrapt_timeout_decorator import *  # Importing timeout decorator for functions from wrapt_timeout_decorator library
from helpers import *  # Importing helper functions from helpers.py
from runnables import *  # Importing other runnable classes or functions from runnables.py
import requests  # For making HTTP requests
from formats import *  # Importing format specifications or utilities from formats.py
from prompts import *  # Re-importing prompts, likely redundant
import ast  # For Abstract Syntax Tree manipulation, used for safely evaluating strings as Python literals
import json  # For working with JSON data
from sys import platform  # To get system platform information
from dotenv import load_dotenv

load_dotenv("../.env")  # Load environment variables from .env file


class CustomRunnable:
    """
    A custom runnable class to interact with language models via API calls.

    This class encapsulates the logic for building prompts, sending requests to a model API,
    and processing the responses. It supports both standard request-response and streaming modes,
    and can handle different response types including JSON.

    Attributes:
        model_url (str): URL of the language model API endpoint.
        model_name (str): Name or ID of the language model to be used.
        system_prompt_template (str): Template for the system prompt, setting the model's behavior.
        user_prompt_template (str): Template for the user prompt, containing placeholders for input variables.
        input_variables (list[str]): List of input variable names expected in the user prompt template.
        response_type (str): Expected response type, e.g., "json" or "chat".
        required_format (dict, optional): Expected JSON format for the response, used for structured output. Defaults to None.
        stream (bool): Flag to indicate if streaming response is enabled. Defaults to False.
        stateful (bool): Flag to indicate if the runnable should maintain conversation history. Defaults to False.
        messages (list[dict]): List of messages forming the conversation history, initialized with the system prompt.
    """

    def __init__(
        self,
        model_url,
        model_name,
        system_prompt_template,
        user_prompt_template,
        input_variables,
        response_type,
        required_format=None,
        stream=False,
        stateful=False,
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
        :param stateful: Whether to maintain conversation history. Defaults to False.
        """
        self.model_url = model_url
        self.model_name = model_name
        self.system_prompt_template = system_prompt_template
        self.user_prompt_template = user_prompt_template
        self.input_variables = input_variables
        self.required_format = required_format
        self.messages = [
            {"role": "system", "content": self.system_prompt_template}
        ]  # Initialize messages with system prompt
        self.response_type = response_type
        self.stream = stream
        self.stateful = stateful

    def build_prompt(self, inputs):
        """
        Build the prompt by substituting input variables into the user prompt template.

        If `stateful` is True, appends the new user prompt to the existing `messages` list to maintain conversation history.
        If `stateful` is False, resets the `messages` list to just the system prompt before adding the new user prompt, making it stateless.

        :param inputs: Dictionary of input variables to replace in the prompt template.
        """
        if self.stateful:
            # Stateful mode: append new user message to history
            user_prompt = self.user_prompt_template.format(
                **inputs
            )  # Format user prompt with inputs

            new_messages = [
                {"role": "user", "content": user_prompt},  # Create user message
            ]

            for message in new_messages:
                self.messages.append(message)  # Append new message to existing messages
        else:
            # Stateless mode: reset history to system prompt and then add user message
            self.messages = [
                {"role": "system", "content": self.system_prompt_template}
            ]  # Reset messages to only system prompt

            user_prompt = self.user_prompt_template.format(
                **inputs
            )  # Format user prompt
            self.messages.append(
                {"role": "user", "content": user_prompt}
            )  # Append new user message

    def add_to_history(self, chat_history):
        """
        Add provided chat history to the current message history.

        This method is used to incorporate previous conversation turns into the prompt,
        which is essential for maintaining context in stateful conversations.

        :param chat_history: List of chat messages in history format (e.g., [{'role': 'user', 'content': '...'}]).
        """
        for chat in chat_history:
            self.messages.append(
                chat
            )  # Append each message from chat history to current messages

    def invoke(self, inputs):
        """
        Execute the model call with the constructed prompt and return the processed output.

        Sends a POST request to the model API endpoint with the built prompt and parameters.
        Handles JSON responses, attempts to fix malformed JSON, and parses valid JSON or literal evaluations.

        :param inputs: Dictionary of input values for the prompt variables.
        :return: Processed output from the model response. Can be a dict, list, str, or None depending on response and parsing.
        :raises ValueError: If the API request fails or if JSON decoding of the response fails and cannot be fixed.
        """
        self.build_prompt(inputs)  # Build the prompt using provided inputs

        payload = {
            "model": self.model_name,  # Specify the model name
            "messages": self.messages,  # Include the message history
            "stream": False,  # Disable streaming for standard invoke
            "options": {
                "num_ctx": 4096  # Set context window size
            },
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
                raise ValueError(
                    f"Failed to decode JSON response: {response.text}"
                )  # Raise error if initial JSON decode fails
        else:
            raise ValueError(
                f"Request failed with status code {response.status_code}: {response.text}"
            )  # Raise error for non-200 status codes

    def stream_response(self, inputs):
        """Streaming version of invoke.

        Generates a streaming response from the model API, yielding tokens as they are received.
        This method is used for real-time text generation, providing a more interactive user experience.

        :param inputs: Dictionary of input values for the prompt variables.
        :yields: str or None: Tokens from the streaming response. Yields None at the end of the stream.
        """
        self.build_prompt(inputs)  # Build the prompt using provided inputs

        payload = {
            "model": self.model_name,  # Specify the model name
            "messages": self.messages,  # Include the message history
            "stream": True,  # Enable streaming for response
            "options": {
                "num_ctx": 4096  # Set context window size
            },
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


# --- Runnable Initialization Functions ---
# These functions create and configure instances of CustomRunnable for different tasks.
# They encapsulate the specific prompts, model settings, and response formats for each functionality.


def get_orchestrator_runnable(chat_history):
    """
    Creates and configures a CustomRunnable for orchestrating different tasks based on user input.

    This runnable is designed to classify user queries and decide the appropriate course of action,
    such as performing an internet search or providing a direct response. It uses a specific system prompt,
    user prompt template, and required format defined for orchestration tasks.

    :param chat_history: The chat history to maintain context for orchestration decisions.
    :return: A configured CustomRunnable instance for orchestration.
    """
    orchestrator_runnable = CustomRunnable(
        model_url=os.getenv(
            "BASE_MODEL_URL"
        ),  # Get model URL from environment variables
        model_name=os.getenv(
            "BASE_MODEL_REPO_ID"
        ),  # Get model name from environment variables
        system_prompt_template=orchestrator_system_prompt_template,  # System prompt for orchestration
        user_prompt_template=orchestrator_user_prompt_template,  # User prompt template for orchestration
        input_variables=["query"],  # Input variable for the orchestrator prompt
        required_format=orchestrator_required_format,  # Expected JSON format for orchestrator response
        response_type="json",  # Response type is JSON
        stateful=True,  # Stateful to maintain conversation context
    )

    orchestrator_runnable.add_to_history(
        chat_history
    )  # Add chat history to the runnable

    return orchestrator_runnable  # Return the configured orchestrator runnable


def get_context_classification_runnable():
    """
    Creates and configures a CustomRunnable for classifying the context of a user query.

    This runnable is used to determine the general category or intent of a user query,
    which can be used for routing or further processing. It is configured with prompts and settings
    specific to context classification.

    :return: A configured CustomRunnable instance for context classification.
    """
    context_classification_runnable = CustomRunnable(
        model_url=os.getenv(
            "BASE_MODEL_URL"
        ),  # Get model URL from environment variables
        model_name=os.getenv(
            "BASE_MODEL_REPO_ID"
        ),  # Get model name from environment variables
        system_prompt_template=context_classification_system_prompt_template,  # System prompt for context classification
        user_prompt_template=context_classification_user_prompt_template,  # User prompt template for context classification
        input_variables=["query"],  # Input variable for context classification prompt
        required_format=context_classification_required_format,  # Expected JSON format for classification response
        response_type="json",  # Response type is JSON
    )

    return context_classification_runnable  # Return the configured context classification runnable


def get_internet_classification_runnable():
    """
    Creates and configures a CustomRunnable for classifying if a user query requires internet search.

    This runnable decides whether a given query necessitates accessing the internet to provide a relevant response.
    It is set up with prompts and configurations designed for internet search classification tasks.

    :return: A configured CustomRunnable instance for internet classification.
    """
    internet_classification_runnable = CustomRunnable(
        model_url=os.getenv(
            "BASE_MODEL_URL"
        ),  # Get model URL from environment variables
        model_name=os.getenv(
            "BASE_MODEL_REPO_ID"
        ),  # Get model name from environment variables
        system_prompt_template=internet_classification_system_prompt_template,  # System prompt for internet classification
        user_prompt_template=internet_classification_user_prompt_template,  # User prompt template for internet classification
        input_variables=["query"],  # Input variable for internet classification prompt
        required_format=internet_classification_required_format,  # Expected JSON format for internet classification response
        response_type="json",  # Response type is JSON
    )

    return internet_classification_runnable  # Return the configured internet classification runnable


def get_internet_query_reframe_runnable():
    """
    Creates and configures a CustomRunnable for reframing user queries to be more effective for internet searches.

    This runnable takes a user's original query and reformulates it into a query that is optimized for web search engines.
    It utilizes prompts and settings tailored for query reframing.

    :return: A configured CustomRunnable instance for internet query reframing.
    """
    internet_query_reframe_runnable = CustomRunnable(
        model_url=os.getenv(
            "BASE_MODEL_URL"
        ),  # Get model URL from environment variables
        model_name=os.getenv(
            "BASE_MODEL_REPO_ID"
        ),  # Get model name from environment variables
        system_prompt_template=internet_query_reframe_system_prompt_template,  # System prompt for query reframing
        user_prompt_template=internet_query_reframe_user_prompt_template,  # User prompt template for query reframing
        input_variables=["query"],  # Input variable for query reframing prompt
        response_type="chat",  # Response type is chat (text)
    )

    return internet_query_reframe_runnable  # Return the configured internet query reframe runnable


def get_internet_summary_runnable():
    """
    Creates and configures a CustomRunnable for summarizing content retrieved from internet searches.

    This runnable is designed to take web search results and condense them into a concise summary.
    It is configured with prompts and settings optimized for summarization tasks.

    :return: A configured CustomRunnable instance for internet summary generation.
    """
    internet_summary_runnable = CustomRunnable(
        model_url=os.getenv(
            "BASE_MODEL_URL"
        ),  # Get model URL from environment variables
        model_name=os.getenv(
            "BASE_MODEL_REPO_ID"
        ),  # Get model name from environment variables
        system_prompt_template=internet_summary_system_prompt_template,  # System prompt for internet summary
        user_prompt_template=internet_summary_user_prompt_template,  # User prompt template for internet summary
        input_variables=[
            "query"
        ],  # Input variable for summary prompt (expects search results as input)
        response_type="chat",  # Response type is chat (text)
    )

    return internet_summary_runnable  # Return the configured internet summary runnable

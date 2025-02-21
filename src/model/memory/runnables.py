import os
from prompts import *  # Importing prompt templates and related utilities from prompts.py
from wrapt_timeout_decorator import *  # Importing timeout decorator for functions from wrapt_timeout_decorator library
from helpers import *  # Importing helper functions from helpers.py
from constants import *  # Importing constant variables from constants.py
from runnables import *  # Importing other runnable classes or functions from runnables.py
import requests  # For making HTTP requests
from formats import *  # Importing format specifications or utilities from formats.py
from prompts import *  # Re-importing prompts, likely redundant
import ast  # For Abstract Syntax Tree manipulation, used for safely evaluating strings as Python literals
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
        model_url: str,
        model_name: str,
        system_prompt_template: str,
        user_prompt_template: str,
        input_variables: list[str],
        response_type: str,
        required_format: Optional[dict] = None,
        stream: bool = False,
        stateful: bool = False,
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

    def build_prompt(self, inputs: dict):
        """
        Build the prompt by substituting input variables into the user prompt template.

        If `stateful` is True, appends the new user prompt to the existing `messages` list to maintain conversation history.
        If `stateful` is False, resets the `messages` list to just the system prompt before adding the new user prompt, making it stateless.

        :param inputs: Dictionary of input variables to replace in the prompt template.
        :return: None
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

    def add_to_history(self, chat_history: list[dict]):
        """
        Add provided chat history to the current message history.

        This method is used to incorporate previous conversation turns into the prompt,
        which is essential for maintaining context in stateful conversations.

        :param chat_history: List of chat messages in history format (e.g., [{'role': 'user', 'content': '...'}]).
        :return: None
        """
        for chat in chat_history:
            self.messages.append(
                chat
            )  # Append each message from chat history to current messages

    def invoke(self, inputs: dict) -> dict | list | str | None:
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



def get_chat_runnable(chat_history: list[dict]) -> CustomRunnable:
    """
    Creates and configures a CustomRunnable for handling chat interactions.

    This runnable is designed for general chat purposes, utilizing chat-specific prompts and settings.
    It is stateful to maintain conversation history and supports streaming responses for interactive chat experiences.

    :param chat_history: The chat history to be added to the runnable's context.
    :return: A configured CustomRunnable instance for chat interactions.
    """
    chat_runnable = CustomRunnable(
        model_url=os.getenv(
            "BASE_MODEL_URL"
        ),  # Get model URL from environment variables
        model_name=os.getenv(
            "BASE_MODEL_REPO_ID"
        ),  # Get model name from environment variables
        system_prompt_template=chat_system_prompt_template,  # System prompt for chat
        user_prompt_template=chat_user_prompt_template,  # User prompt template for chat
        input_variables=[
            "query",
            "user_context",
            "internet_context",
            "name",
            "personality",
        ],  # Input variables for chat prompt
        response_type="chat",  # Response type is chat (text)
        stream=True,  # Enable streaming for chat response
        stateful=True,  # Stateful to maintain chat history
    )

    chat_runnable.add_to_history(chat_history)  # Add chat history to the runnable
    return chat_runnable  # Return the configured chat runnable


def get_graph_decision_runnable() -> CustomRunnable:
    """
    Creates and configures a CustomRunnable for making decisions about graph operations (CRUD).

    This runnable is responsible for deciding on Create, Read, Update, Delete (CRUD) operations
    based on analysis of graph data. It is configured with prompts and settings specific to graph decision-making.

    :return: A configured CustomRunnable instance for graph decision-making.
    """
    graph_decision_runnable = CustomRunnable(
        model_url=os.getenv(
            "BASE_MODEL_URL"
        ),  # Get model URL from environment variables
        model_name=os.getenv(
            "BASE_MODEL_REPO_ID"
        ),  # Get model name from environment variables
        system_prompt_template=graph_decision_system_prompt_template,  # System prompt for graph decision
        user_prompt_template=graph_decision_user_prompt_template,  # User prompt template for graph decision
        input_variables=[
            "analysis"
        ],  # Input variable for graph decision prompt (expects analysis results)
        required_format=graph_decision_required_format,  # Expected JSON format for graph decision response
        response_type="json",  # Response type is JSON
    )

    return graph_decision_runnable  # Return the configured graph decision runnable


def get_graph_analysis_runnable() -> CustomRunnable:
    """
    Creates and configures a CustomRunnable for analyzing graph data.

    This runnable is designed to analyze and compare graph data, such as identifying differences
    between an existing graph and new information. It is configured with prompts and settings
    optimized for graph analysis tasks.

    :return: A configured CustomRunnable instance for graph analysis.
    """
    graph_analysis_runnable = CustomRunnable(
        model_url=os.getenv(
            "BASE_MODEL_URL"
        ),  # Get model URL from environment variables
        model_name=os.getenv(
            "BASE_MODEL_REPO_ID"
        ),  # Get model name from environment variables
        system_prompt_template=graph_analysis_system_prompt_template,  # System prompt for graph analysis
        user_prompt_template=graph_analysis_user_prompt_template,  # User prompt template for graph analysis
        input_variables=[
            "related_graph",
            "extracted_data",
        ],  # Input variables for graph analysis prompt
        required_format=graph_analysis_required_format,  # Expected JSON format for graph analysis response
        response_type="json",  # Response type is JSON
    )

    return graph_analysis_runnable  # Return the configured graph analysis runnable


def get_text_dissection_runnable() -> CustomRunnable:
    """
    Creates and configures a CustomRunnable for dissecting text into predefined categories.

    This runnable is used to categorize unstructured text into predefined categories, which is useful
    for organizing and processing large volumes of text data. It is configured with prompts and settings
    specific to text dissection tasks.

    :return: A configured CustomRunnable instance for text dissection.
    """
    text_dissection_runnable = CustomRunnable(
        model_url=os.getenv(
            "BASE_MODEL_URL"
        ),  # Get model URL from environment variables
        model_name=os.getenv(
            "BASE_MODEL_REPO_ID"
        ),  # Get model name from environment variables
        system_prompt_template=text_dissection_system_prompt_template,  # System prompt for text dissection
        user_prompt_template=text_dissection_user_prompt_template,  # User prompt template for text dissection
        input_variables=[
            "user_name",
            "text",
        ],  # Input variables for text dissection prompt
        required_format=text_dissection_required_format,  # Expected JSON format for text dissection response
        response_type="json",  # Response type is JSON
    )

    return text_dissection_runnable  # Return the configured text dissection runnable


def get_information_extraction_runnable() -> CustomRunnable:
    """
    Creates and configures a CustomRunnable for extracting structured information (entities and relationships) from text.

    This runnable is designed to identify and extract entities and the relationships between them from unstructured text.
    It is configured with prompts and settings optimized for information extraction tasks, and expects a JSON format response.

    :return: A configured CustomRunnable instance for information extraction.
    """
    information_extraction_runnable = CustomRunnable(
        model_url=os.getenv(
            "BASE_MODEL_URL"
        ),  # Get model URL from environment variables
        model_name=os.getenv(
            "BASE_MODEL_REPO_ID"
        ),  # Get model name from environment variables
        system_prompt_template=information_extraction_system_prompt_template,  # System prompt for information extraction
        user_prompt_template=information_extraction_user_prompt_template,  # User prompt template for information extraction
        input_variables=[
            "category",
            "text",
        ],  # Input variables for information extraction prompt
        required_format=information_extraction_required_format,  # Expected JSON format for information extraction response
        response_type="json",  # Response type is JSON
    )

    return information_extraction_runnable  # Return the configured information extraction runnable


def get_text_conversion_runnable() -> CustomRunnable:
    """
    Creates and configures a CustomRunnable for converting structured graph data into unstructured text.

    This runnable takes graph data as input and transforms it into human-readable, unstructured text.
    It is used for generating textual summaries or descriptions from knowledge graph information and is
    configured with prompts and settings for text conversion.

    :return: A configured CustomRunnable instance for text conversion.
    """
    text_conversion_runnable = CustomRunnable(
        model_url=os.getenv(
            "BASE_MODEL_URL"
        ),  # Get model URL from environment variables
        model_name=os.getenv(
            "BASE_MODEL_REPO_ID"
        ),  # Get model name from environment variables
        system_prompt_template=text_conversion_system_prompt_template,  # System prompt for text conversion
        user_prompt_template=text_conversion_user_prompt_template,  # User prompt template for text conversion
        input_variables=[
            "graph_data"
        ],  # Input variable for text conversion prompt (expects graph data)
        response_type="chat",  # Response type is chat (text)
    )

    return text_conversion_runnable  # Return the configured text conversion runnable


def get_query_classification_runnable() -> CustomRunnable:
    """
    Creates and configures a CustomRunnable for classifying user queries into predefined categories.

    This runnable is used to determine the category or intent of a user query, which is crucial for
    routing queries to the appropriate processing logic. It is configured with prompts and settings
    for query classification tasks and expects a JSON response containing the classification.

    :return: A configured CustomRunnable instance for query classification.
    """
    query_classification_runnable = CustomRunnable(
        model_url=os.getenv(
            "BASE_MODEL_URL"
        ),  # Get model URL from environment variables
        model_name=os.getenv(
            "BASE_MODEL_REPO_ID"
        ),  # Get model name from environment variables
        system_prompt_template=query_classification_system_prompt_template,  # System prompt for query classification
        user_prompt_template=query_classification_user_prompt_template,  # User prompt template for query classification
        input_variables=["query"],  # Input variable for query classification prompt
        required_format=query_classification_required_format,  # Expected JSON format for query classification response
        response_type="json",  # Response type is JSON
    )

    return query_classification_runnable  # Return the configured query classification runnable


def get_fact_extraction_runnable() -> CustomRunnable:
    """
    Creates and configures a CustomRunnable for extracting factual points from a paragraph of text.

    This runnable is designed to identify and extract key factual statements from a given text paragraph.
    It is used for populating the knowledge graph with structured facts and is configured with prompts
    and settings for fact extraction, expecting a JSON format response.

    :return: A configured CustomRunnable instance for fact extraction.
    """
    fact_extraction_runnable = CustomRunnable(
        model_url=os.getenv(
            "BASE_MODEL_URL"
        ),  # Get model URL from environment variables
        model_name=os.getenv(
            "BASE_MODEL_REPO_ID"
        ),  # Get model name from environment variables
        system_prompt_template=fact_extraction_system_prompt_template,  # System prompt for fact extraction
        user_prompt_template=fact_extraction_user_prompt_template,  # User prompt template for fact extraction
        input_variables=[
            "paragraph",
            "username",
        ],  # Input variables for fact extraction prompt
        required_format=fact_extraction_required_format,  # Expected JSON format for fact extraction response
        response_type="json",  # Response type is JSON
    )

    return fact_extraction_runnable  # Return the configured fact extraction runnable


def get_text_summarizer_runnable() -> CustomRunnable:
    """
    Creates and configures a CustomRunnable for summarizing text.

    This runnable is used to generate concise summaries of longer texts. It is configured with prompts
    and settings optimized for text summarization tasks and is expected to return chat-style text output.

    :return: A configured CustomRunnable instance for text summarization.
    """
    text_summarizer_runnable = CustomRunnable(
        model_url=os.getenv(
            "BASE_MODEL_URL"
        ),  # Get model URL from environment variables
        model_name=os.getenv(
            "BASE_MODEL_REPO_ID"
        ),  # Get model name from environment variables
        system_prompt_template=text_summarization_system_prompt_template,  # System prompt for text summarization
        user_prompt_template=text_summarization_user_prompt_template,  # User prompt template for text summarization
        input_variables=[
            "user_name",
            "text",
        ],  # Input variables for text summarization prompt
        response_type="chat",  # Response type is chat (text)
    )

    return text_summarizer_runnable  # Return the configured text summarizer runnable


def get_text_description_runnable() -> CustomRunnable:
    """
    Creates and configures a CustomRunnable for generating descriptive text for entities or queries.

    This runnable is designed to produce human-readable descriptions, often used to provide context or
    elaborate on entities or concepts. It is configured with prompts and settings for text description
    generation and is expected to return chat-style text output.

    :return: A configured CustomRunnable instance for text description generation.
    """
    text_description_runnable = CustomRunnable(
        model_url=os.getenv(
            "BASE_MODEL_URL"
        ),  # Get model URL from environment variables
        model_name=os.getenv(
            "BASE_MODEL_REPO_ID"
        ),  # Get model name from environment variables
        system_prompt_template=text_description_system_prompt_template,  # System prompt for text description
        user_prompt_template=text_description_user_prompt_template,  # User prompt template for text description
        input_variables=["query"],  # Input variable for text description prompt
        response_type="chat",  # Response type is chat (text)
    )

    return text_description_runnable  # Return the configured text description runnable

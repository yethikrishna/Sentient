import re
from constants import *  # Importing constants from constants.py
from prompts import *  # Importing prompt related utilities and variables from prompts.py
import json  # For working with JSON data
from html import unescape  # For unescaping HTML entities
import os  # For interacting with the operating system, e.g., accessing environment variables and file paths
import datetime  # For working with date and time
import platform  # For getting platform information like operating system
from dotenv import load_dotenv

load_dotenv("../.env")  # Load environment variables from .env file

# --- Log File Path Configuration ---
# Determine the log file path based on the operating system.
if platform.system() == "Windows":
    # Log file path for Windows systems, typically under ProgramData
    log_file_path = os.path.join(
        os.getenv("PROGRAMDATA"), "Sentient", "logs", "fastapi-backend.log"
    )
else:
    # Log file path for non-Windows systems (like Linux), typically under /var/log
    log_file_path = os.path.join("/var", "log", "sentient", "fastapi-backend.log")


def clean_key(key: str) -> str:
    """
    Cleans a string key by removing any content within parentheses and stripping whitespace.

    This function is useful for normalizing keys that might contain extra information in parentheses
    that are not needed for processing, such as units or clarifications.

    Args:
        key (str): The key string to be cleaned.

    Returns:
        str: The cleaned key string with parentheses content removed and whitespace stripped.
    """
    return re.sub(
        r"\s*\(.*?\)\s*", "", key
    ).strip()  # Remove parentheses and their contents, then strip whitespace


def clean_description(description: str) -> str:
    """
    Removes HTML tags and unescapes HTML entities from a description string.

    This function processes a description that might contain HTML formatting, removing tags
    to leave only plain text and converting HTML entities (like &) to their corresponding characters.

    Args:
        description (str): The HTML description string to be cleaned.

    Returns:
        str: The cleaned description string with HTML tags removed and entities unescaped.
             Returns an empty string if the input description is None or empty.
    """
    if not description:
        return ""  # Return empty string if description is empty or None
    clean_text = re.sub(r"<.*?>", "", description)  # Remove HTML tags
    clean_text = unescape(clean_text)  # Unescape HTML entities
    return clean_text


class TimeoutException(Exception):
    """
    Custom exception class to represent timeout errors.
    """

    pass


def watchdog(timeout_sec: int):
    """
    Raises a TimeoutError after a specified number of seconds.

    This function is intended to be used with a timeout mechanism (like a decorator) to enforce
    a time limit on operations. If the function is called, it immediately raises a TimeoutError.

    Args:
        timeout_sec (int): The timeout duration in seconds (though the timeout itself is not enforced by this function,
                           it's just used in the error message).

    Raises:
        TimeoutError: Always raised when this function is called, indicating a timeout.
    """
    raise TimeoutError(
        "Query timed out after {} seconds.".format(timeout_sec)
    )  # Raise TimeoutError with a message


def extract_and_fix_json(json_string: str) -> dict | list:
    """
    Extracts and fixes JSON from a possibly malformed string.

    This function attempts to find and parse JSON objects or arrays within a string that might contain
    syntax errors or extraneous content. It tries multiple strategies to recover valid JSON:
    1. Sanitizes invalid characters.
    2. Finds JSON objects or arrays using regex and attempts to parse each match.
    3. Fixes common JSON syntax errors (like unbalanced brackets) and attempts to parse again.

    Args:
        json_string (str): The input string that might contain JSON.

    Returns:
        dict or list: The parsed JSON object or array if successful.

    Raises:
        ValueError: If no JSON object is found or if JSON parsing fails even after fixing.
    """
    try:
        sanitized_string = sanitize_invalid_characters(
            json_string
        )  # Remove invalid characters from the JSON string

        json_matches = re.findall(
            r"(\{.*\}|\[.*\])", sanitized_string, re.DOTALL
        )  # Find all potential JSON objects or arrays using regex
        if not json_matches:
            raise ValueError(
                "No JSON object found in the input string."
            )  # Raise ValueError if no JSON is found

        for match in json_matches:
            try:
                return json.loads(match)  # Attempt to parse each JSON match
            except json.JSONDecodeError as e:
                print(
                    f"Error in fixing JSON: {str(e)}"
                )  # Log JSON decode errors, but continue to try other matches
                continue  # Continue to the next match if parsing fails

        fixed_json_string = fix_json_syntax(
            sanitized_string
        )  # Attempt to fix common JSON syntax errors
        return json.loads(fixed_json_string)  # Try parsing the fixed JSON string

    except Exception as e:
        print(f"Error parsing JSON: {str(e)}")  # Log general JSON parsing errors
        raise ValueError(
            f"Failed to parse JSON: {e}"
        )  # Raise ValueError if parsing fails


def fix_json_syntax(json_string: str) -> str:
    """
    Fixes common JSON syntax issues like missing or extra brackets.

    This function attempts to correct common JSON syntax errors, such as:
    - Unbalanced curly braces '{}' for objects.
    - Unbalanced square brackets '[]' for arrays.
    - Extraneous characters at the beginning or end of the JSON string.

    It does not fix semantic errors within the JSON structure, only syntax related to brackets.

    Args:
        json_string (str): The input JSON string that might have syntax errors.

    Returns:
        str: The fixed JSON string, hopefully syntactically valid.
    """
    json_string = re.sub(
        r"^[^{\[]*", "", json_string
    )  # Remove any characters before the first '{' or '['
    json_string = re.sub(
        r"[^}\]]*$", "", json_string
    )  # Remove any characters after the last '}' or ']'

    open_braces = json_string.count("{")  # Count opening curly braces
    close_braces = json_string.count("}")  # Count closing curly braces
    open_brackets = json_string.count("[")  # Count opening square brackets
    close_brackets = json_string.count("]")  # Count closing square brackets

    if open_braces > close_braces:
        json_string += "}" * (open_braces - close_braces)  # Add missing closing braces
    elif close_braces > open_braces:
        json_string = (
            "{" * (close_braces - open_braces) + json_string
        )  # Add missing opening braces

    if open_brackets > close_brackets:
        json_string += "]" * (
            open_brackets - close_brackets
        )  # Add missing closing brackets
    elif close_brackets > open_brackets:
        json_string = (
            "[" * (close_brackets - open_brackets) + json_string
        )  # Add missing opening brackets

    return json_string  # Return the syntax-fixed JSON string


def sanitize_invalid_characters(json_string: str) -> str:
    """
    Removes invalid control characters from a JSON string.

    JSON strings must not contain control characters (ASCII characters 0-31 and 127) unless they are escaped.
    This function removes these invalid characters to make the string parsable as JSON.

    Args:
        json_string (str): The input JSON string that might contain invalid characters.

    Returns:
        str: The sanitized JSON string with invalid control characters removed.
    """
    invalid_chars_pattern = (
        r"[\x00-\x1F\x7F]"  # Regex pattern for invalid control characters
    )
    return re.sub(
        invalid_chars_pattern, "", json_string
    )  # Replace invalid characters with empty string, effectively removing them


def write_to_log(message: str):
    """
    Writes a message to the log file with a timestamp.

    This function appends a timestamped log message to the configured log file. It also ensures that the
    directory for the log file exists, creating it if necessary, and creates the log file if it doesn't exist.

    Args:
        message (str): The message string to be written to the log file.
    """
    timestamp = datetime.datetime.now().isoformat()  # Generate ISO format timestamp
    log_message = f"{timestamp}: {message}\n"  # Format log message with timestamp

    try:
        os.makedirs(
            os.path.dirname(log_file_path), exist_ok=True
        )  # Ensure log directory exists, create if not

        if not os.path.exists(log_file_path):
            with open(log_file_path, "w") as f:  # Create log file if it doesn't exist
                pass  # Just create the file, no content needed initially

        with open(log_file_path, "a") as log_file:  # Open log file in append mode
            log_file.write(log_message)  # Write the timestamped message to the log file
    except Exception as error:
        print(
            f"Error writing to log file: {error}"
        )  # Print error to console if writing to log file fails

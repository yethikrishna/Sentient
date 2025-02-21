import os
import datetime
import platform

# Determine the log file path based on the operating system.
# On Windows, it will be in the ProgramData directory under Sentient/logs.
# On other systems (like Linux, macOS), it will be in /var/log/sentient/.
if platform.system() == "Windows":
    log_file_path = os.path.join(
        os.getenv("PROGRAMDATA"), "Sentient", "logs", "fastapi-backend.log"
    )
else:
    log_file_path = os.path.join("/var", "log", "sentient", "fastapi-backend.log")


def write_to_log(message: str):
    """
    Writes a message to the log file with a timestamp.

    This function takes a message string, adds a timestamp to it, and then
    writes the timestamped message to the log file specified by `log_file_path`.
    It also handles the creation of the log directory and the log file if they
    do not already exist.

    Args:
        message (str): The message to be written to the log file.
    """
    # Get the current timestamp in ISO format.
    timestamp = datetime.datetime.now().isoformat()
    # Format the log message to include the timestamp and the provided message.
    log_message = f"{timestamp}: {message}\n"

    try:
        # Ensure that the directory for the log file exists.
        # `os.makedirs` creates the directory and any necessary parent directories.
        # `exist_ok=True` prevents an error if the directory already exists.
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

        # Check if the log file exists. If not, create it.
        # This ensures that if the file doesn't exist, it will be created before writing.
        if not os.path.exists(log_file_path):
            with open(log_file_path, "w") as f:
                pass  # 'pass' does nothing, just creates an empty file

        # Open the log file in append mode ('a').
        # This mode ensures that new messages are added to the end of the file,
        # preserving previous log entries.
        with open(log_file_path, "a") as log_file:
            # Write the formatted log message to the log file.
            log_file.write(log_message)
    except Exception as error:
        # If any exception occurs during the process (e.g., file permission issues),
        # print an error message to the console.
        print(f"Error writing to log file: {error}")

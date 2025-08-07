import os
import asyncio
import logging
import time
import base64
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# --- Configuration from Environment ---
BASE_TEMP_DIR = Path(os.getenv("FILE_MANAGEMENT_TEMP_DIR", "/tmp/sentient_files"))
CLEANUP_INTERVAL = int(os.getenv("FILE_CLEANUP_INTERVAL_SECONDS", 3600))
MAX_FILE_AGE = int(os.getenv("FILE_MAX_AGE_SECONDS", 86400))

def get_user_temp_dir(user_id: str) -> Path:
    """Creates and returns the path to the user-specific temporary directory."""
    # Sanitize user_id to prevent path traversal issues
    safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ('-', '_'))
    user_dir = BASE_TEMP_DIR / safe_user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir

def get_safe_filepath(user_id: str, filename: str) -> Path:
    """Constructs a safe file path within the user's temp directory."""
    user_dir = get_user_temp_dir(user_id)
    # Sanitize filename to prevent path traversal (e.g., '../..')
    safe_filename = Path(filename).name
    if not safe_filename:
        raise ValueError("Invalid filename.")
    return user_dir / safe_filename

async def cleanup_old_files():
    """Periodically scans the base temp directory and removes old files."""
    while True:
        logger.info(f"Running scheduled cleanup of temporary files older than {MAX_FILE_AGE} seconds.")
        try:
            now = time.time()
            for user_dir in BASE_TEMP_DIR.iterdir():
                if user_dir.is_dir():
                    for file_path in user_dir.iterdir():
                        if file_path.is_file():
                            try:
                                file_age = now - file_path.stat().st_mtime
                                if file_age > MAX_FILE_AGE:
                                    file_path.unlink()
                                    logger.info(f"Cleaned up old file: {file_path}")
                            except Exception as e:
                                logger.error(f"Error cleaning up file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error during file cleanup loop: {e}")
        
        await asyncio.sleep(CLEANUP_INTERVAL)

def list_files_for_user(user_id: str) -> List[Dict[str, Any]]:
    """Lists all files in a user's temporary directory."""
    user_dir = get_user_temp_dir(user_id)
    files = []
    for file_path in user_dir.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                "filename": file_path.name,
                "size_bytes": stat.st_size,
                "last_modified": stat.st_mtime
            })
    return files

def write_file_for_user(user_id: str, filename: str, content: str, encoding: str = 'utf-8') -> str:
    """Writes content to a file in the user's temp directory."""
    filepath = get_safe_filepath(user_id, filename)
    
    if encoding.lower() == 'base64':
        # Decode base64 content and write as binary
        file_content_bytes = base64.b64decode(content)
        with open(filepath, 'wb') as f:
            f.write(file_content_bytes)
        return f"Successfully wrote {len(file_content_bytes)} bytes to binary file '{filename}'."
    else:
        # Write as text with the specified encoding
        with open(filepath, 'w', encoding=encoding) as f:
            f.write(content)
        return f"Successfully wrote text file '{filename}' with encoding '{encoding}'."

def read_file_for_user(user_id: str, filename: str, read_mode: str = 'text') -> Dict[str, Any]:
    """Reads content from a file in the user's temp directory."""
    filepath = get_safe_filepath(user_id, filename)
    
    if not filepath.exists():
        raise FileNotFoundError(f"File '{filename}' not found.")

    if read_mode.lower() == 'binary':
        with open(filepath, 'rb') as f:
            content_bytes = f.read()
        content_base64 = base64.b64encode(content_bytes).decode('ascii')
        return {
            "filename": filename,
            "encoding": "base64",
            "content": content_base64
        }
    else: # Default to text
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return {
                "filename": filename,
                "encoding": "utf-8",
                "content": content
            }
        except UnicodeDecodeError:
            raise ValueError(f"File '{filename}' is not valid UTF-8 text. Try reading in 'binary' mode.")
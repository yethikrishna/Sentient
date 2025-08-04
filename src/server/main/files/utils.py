import httpx
import logging
import mimetypes
import shutil
from typing import Dict, Any, List, Tuple
from main.config import FILE_MANAGEMENT_TEMP_DIR
from pathlib import Path
from fastapi import UploadFile

logger = logging.getLogger(__name__)

def get_user_temp_dir(user_id: str) -> Path:
    """Creates and returns the path to the user-specific temporary directory."""
    safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ('-', '_'))
    user_dir = Path(FILE_MANAGEMENT_TEMP_DIR) / safe_user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir

def get_safe_filepath(user_id: str, filename: str) -> Path:
    """Constructs a safe file path within the user's temp directory."""
    user_dir = get_user_temp_dir(user_id)
    safe_filename = Path(filename).name
    if not safe_filename:
        raise ValueError("Invalid filename.")
    return user_dir / safe_filename

async def save_user_file(user_id: str, file: UploadFile) -> Path:
    """Saves an uploaded file to the user's temporary directory."""
    if not file.filename:
        raise ValueError("File has no filename.")
    
    filepath = get_safe_filepath(user_id, file.filename)
    
    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Successfully saved uploaded file for user {user_id} to {filepath}")
        return filepath
    finally:
        await file.close()

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

def read_user_file(user_id: str, filename: str) -> Tuple[bytes, str]:
    """Reads a file's binary content and determines its MIME type."""
    filepath = get_safe_filepath(user_id, filename)
    
    if not filepath.exists():
        raise FileNotFoundError(f"File '{filename}' not found.")

    with open(filepath, 'rb') as f:
        content_bytes = f.read()
    
    mime_type, _ = mimetypes.guess_type(filepath)
    return content_bytes, mime_type or "application/octet-stream"
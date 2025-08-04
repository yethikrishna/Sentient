import os
import uuid
import re
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from main.dependencies import auth_helper
from main.config import FILE_MANAGEMENT_TEMP_DIR # Import the base directory constant
from .utils import get_user_temp_dir

router = APIRouter(
    prefix="/api/files",
    tags=["File Management"]
)

def sanitize_filename(filename: str) -> str:
    """Prevents path traversal and removes unsafe characters."""
    # Remove directory separators
    filename = filename.replace("/", "").replace("\\", "")
    # Remove characters that could be used for path traversal
    filename = re.sub(r'\.\.', '', filename)
    # Remove other potentially problematic characters (optional, but good practice)
    filename = re.sub(r'[<>:"|?*]', '', filename)
    return filename

def get_unique_filename(directory: str, filename: str) -> str:
    """Checks if a file exists and appends a number if it does."""
    name, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    while os.path.exists(os.path.join(directory, new_filename)):
        new_filename = f"{name} ({counter}){ext}"
        counter += 1
    return new_filename

@router.post("/upload", summary="Upload a file for AI context")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    # Create a user-specific subdirectory
    safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ('-', '_'))
    user_specific_dir = os.path.join(FILE_MANAGEMENT_TEMP_DIR, safe_user_id)
    os.makedirs(user_specific_dir, exist_ok=True)

    # Sanitize the original filename to prevent security issues
    sanitized_filename = sanitize_filename(file.filename)

    # Ensure the filename is unique within the user's directory
    final_filename = get_unique_filename(user_specific_dir, sanitized_filename)

    file_path = os.path.join(user_specific_dir, final_filename)

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to save file: {e}"})
    
    # Return the relative path including the user's directory
    relative_path = os.path.join(safe_user_id, final_filename)
    return JSONResponse(content={"filename": relative_path})

@router.get("/download/{filepath:path}", summary="Download a file")
async def download_file(
    filepath: str,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    """
    Provides a secure way to download a file from the user's temporary directory.
    """
    try:
        # This is the directory we will check against for security.
        user_specific_dir = get_user_temp_dir(user_id)

        # The 'filepath' from the URL already contains the user's directory.
        # We join it with the BASE temp directory, not the user-specific one.
        full_path = os.path.normpath(os.path.join(FILE_MANAGEMENT_TEMP_DIR, filepath))
        print(f"Safe filepath: {full_path}")

        # Security Check: Ensure the final, resolved path is inside the user's designated directory.
        # This prevents path traversal attacks (e.g., filepath = "../other_user/secret.txt").
        if not os.path.abspath(full_path).startswith(os.path.abspath(user_specific_dir)):
            raise HTTPException(status_code=403, detail="Forbidden: Access denied.")

        if not os.path.isfile(full_path):
            raise HTTPException(status_code=404, detail="File not found.")

        # Use FileResponse to stream the file back to the client.
        # The filename for the download is the base name of the path.
        return FileResponse(path=full_path, filename=os.path.basename(filepath), media_type='application/octet-stream')

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
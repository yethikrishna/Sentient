import datetime
import uuid
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from .models import CreateBlockRequest, UpdateBlockRequest
from ..dependencies import mongo_manager
from ..auth.utils import PermissionChecker
from ...workers.tasks import extract_from_context

router = APIRouter(
    prefix="/journal",
    tags=["Journal"]
)

@router.get("/blocks", status_code=status.HTTP_200_OK)
async def get_journal_blocks(
    date: str, # YYYY-MM-DD format
    user_id: str = Depends(PermissionChecker(required_permissions=["read:journal"]))
):
    """Fetches all journal blocks for a specific date."""
    blocks_cursor = mongo_manager.journal_blocks_collection.find({
        "user_id": user_id,
        "page_date": date
    }).sort("order", 1)
    
    blocks = await blocks_cursor.to_list(length=None)
    for block in blocks:
        block["_id"] = str(block["_id"])
    return {"blocks": blocks}

@router.post("/blocks", status_code=status.HTTP_201_CREATED)
async def create_journal_block(
    request: CreateBlockRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:journal"]))
):
    """Creates a new journal block and optionally sends it for AI processing."""
    now = datetime.datetime.now(datetime.timezone.utc)
    block_id = str(uuid.uuid4())
    block_doc = {
        "block_id": block_id,
        "user_id": user_id,
        "page_date": request.page_date,
        "content": request.content,
        "order": request.order,
        "created_by": "user",
        "created_at": now,
        "updated_at": now,
        "linked_task_id": None,
        "task_status": None,
        "task_progress": [],
        "task_result": None
    }
    await mongo_manager.journal_blocks_collection.insert_one(block_doc)
    
    # Conditionally send to Celery worker for context extraction
    if request.processWithAI:
        event_data = {
            "content": request.content,
            "block_id": block_id
        }
        # Call Celery task asynchronously
        extract_from_context.delay(user_id, "journal_block", block_id, event_data)
        print(f"Dispatched journal block {block_id} to Celery for processing.")
    
    block_doc["_id"] = str(block_doc["_id"])
    return block_doc

@router.put("/blocks/{block_id}", status_code=status.HTTP_200_OK)
async def update_journal_block(
    block_id: str,
    request: UpdateBlockRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:journal"]))
):
    """Updates a journal block's content and re-sends it for processing."""
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Find the original block to check if a plan needs to be deprecated
    original_block = await mongo_manager.journal_blocks_collection.find_one({"user_id": user_id, "block_id": block_id})
    if not original_block:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")
        
    old_task_id_to_deprecate = original_block.get("linked_task_id")
    if old_task_id_to_deprecate:
        await mongo_manager.task_collection.update_one(
            {"task_id": old_task_id_to_deprecate, "user_id": user_id},
            {"$set": {"status": "cancelled", "description": f"[DEPRECATED] {original_block.get('content')}"}}
        )
        print(f"Deprecated old task {old_task_id_to_deprecate} for block {block_id}.")

    # Update the block content and reset task-related fields
    update_data = {
        "content": request.content,
        "updated_at": now,
        "linked_task_id": None,
        "task_status": None,
        "task_progress": [],
        "task_result": None
    }
    result = await mongo_manager.journal_blocks_collection.find_one_and_update(
        {"user_id": user_id, "block_id": block_id},
        {"$set": update_data},
        return_document=True
    )

    # Re-send to Celery for context extraction
    event_data = {
        "content": request.content,
        "block_id": block_id,
        "deprecate_task_id": old_task_id_to_deprecate
    }
    extract_from_context.delay(user_id, "journal_block", block_id, event_data)
    print(f"Dispatched updated journal block {block_id} to Celery for processing.")
    
    result["_id"] = str(result["_id"])
    return result

@router.delete("/blocks/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal_block(
    block_id: str,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:journal"]))
):
    """Deletes a journal block."""
    result = await mongo_manager.journal_blocks_collection.delete_one(
        {"user_id": user_id, "block_id": block_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")
    return
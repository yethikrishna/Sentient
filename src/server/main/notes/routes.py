import datetime
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from main.dependencies import mongo_manager
from main.auth.utils import PermissionChecker
from main.notes.models import NoteCreate, NoteUpdate, NoteInDB
from workers.tasks import extract_from_context

router = APIRouter(
    prefix="/notes",
    tags=["Notes"]
)

@router.post("/")
async def create_note(
    note: NoteCreate,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:notes"]))
):
    now = datetime.datetime.now(datetime.timezone.utc)
    note_doc = {
        "note_id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": note.title,
        "content": note.content,
        "note_date": note.note_date,
        "created_at": now,
        "updated_at": now,
        "linked_task_ids": []
    }
    
    await mongo_manager.notes_collection.insert_one(note_doc)
    
    # Trigger extraction pipeline
    event_data = {"content": note.content, "title": note.title, "note_date": note.note_date}
    extract_from_context.delay(user_id, 'note', note_doc["note_id"], event_data)
    
    return {"note": NoteInDB(**note_doc).dict()}


@router.get("/")
async def get_all_notes(
    user_id: str = Depends(PermissionChecker(required_permissions=["read:notes"])),
    date: Optional[str] = Query(None)
):
    query = {"user_id": user_id}
    if date:
        query["note_date"] = date

    notes_cursor = mongo_manager.notes_collection.find(query).sort("updated_at", -1)
    notes = await notes_cursor.to_list(length=None)
    return {"notes": [NoteInDB(**note).dict() for note in notes]}

@router.get("/{note_id}", response_model=NoteInDB)
async def get_note(
    note_id: str,
    user_id: str = Depends(PermissionChecker(required_permissions=["read:notes"]))
):
    note = await mongo_manager.notes_collection.find_one({"note_id": note_id, "user_id": user_id})
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return NoteInDB(**note)

@router.put("/{note_id}")
async def update_note(
    note_id: str,
    note_update: NoteUpdate,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:notes"]))
):
    update_data = note_update.dict(exclude_unset=True)
    if not update_data:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided.")
    update_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
    
    result = await mongo_manager.notes_collection.update_one(
        {"note_id": note_id, "user_id": user_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    # Re-trigger extraction pipeline on update
    updated_note = await mongo_manager.notes_collection.find_one({"note_id": note_id, "user_id": user_id})
    event_data = {"content": updated_note['content'], "title": updated_note['title'], "note_date": updated_note['note_date']}
    extract_from_context.delay(user_id, 'note', note_id, event_data)

    return {"note": NoteInDB(**updated_note).dict()}

@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:notes"]))
):
    result = await mongo_manager.notes_collection.delete_one({"note_id": note_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return
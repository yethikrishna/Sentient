# src/server/main/projects/routes.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from main.dependencies import mongo_manager, auth_helper
from main.auth.utils import PermissionChecker
from .models import ProjectCreateRequest, ProjectUpdateRequest, MemberInviteRequest, ContextItemCreateRequest

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/projects",
    tags=["Projects"]
)

# --- Project CRUD ---
@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a new project")
async def create_project(
    request: ProjectCreateRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:config"])) # Using config scope for creation
):
    project = await mongo_manager.create_project(request.name, request.description, user_id)
    await mongo_manager.add_project_member(project["project_id"], user_id, "owner")
    return project

@router.get("", summary="List all projects for the current user")
async def list_projects(user_id: str = Depends(auth_helper.get_current_user_id)):
    projects = await mongo_manager.get_projects_for_user(user_id)
    return {"projects": projects}

@router.get("/{project_id}", summary="Get details for a single project")
async def get_project_details(project_id: str, user_id: str = Depends(auth_helper.get_current_user_id)):
    if not await mongo_manager.is_user_in_project(user_id, project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this project.")
    
    project = await mongo_manager.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    
    members = await mongo_manager.get_project_members(project_id)
    context_items = await mongo_manager.get_context_items(project_id)
    
    project["members"] = members
    project["context_items"] = context_items
    return project

@router.put("/{project_id}", summary="Update a project's details (owner only)")
async def update_project(
    project_id: str,
    request: ProjectUpdateRequest,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    if not await mongo_manager.is_project_owner(user_id, project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the project owner can update it.")
    
    update_data = request.dict(exclude_unset=True)
    if not update_data:
        return JSONResponse(content={"message": "No update data provided."})

    success = await mongo_manager.projects_collection.update_one(
        {"project_id": project_id}, {"$set": update_data}
    )
    if not success.modified_count:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found or no changes made.")
    return JSONResponse(content={"message": "Project updated successfully."})

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a project (owner only)")
async def delete_project(project_id: str, user_id: str = Depends(auth_helper.get_current_user_id)):
    if not await mongo_manager.is_project_owner(user_id, project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the project owner can delete it.")
    
    success = await mongo_manager.delete_project_and_members(project_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

# --- Membership Management ---
@router.post("/{project_id}/members", status_code=status.HTTP_201_CREATED, summary="Invite a user to a project (owner only)")
async def invite_member(
    project_id: str,
    request: MemberInviteRequest,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    if not await mongo_manager.is_project_owner(user_id, project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the project owner can invite members.")
    
    # In a real app, you'd check if the user_id_to_add exists.
    success = await mongo_manager.add_project_member(project_id, request.user_id, "member")
    if not success:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a member of this project.")
    return JSONResponse(content={"message": "User added to project successfully."})

@router.delete("/{project_id}/members/{user_id_to_remove}", summary="Remove a member from a project (owner only)")
async def remove_member(
    project_id: str,
    user_id_to_remove: str,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    if not await mongo_manager.is_project_owner(user_id, project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the project owner can remove members.")
    
    project = await mongo_manager.get_project_by_id(project_id)
    if project.get("owner_id") == user_id_to_remove:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove the project owner.")

    success = await mongo_manager.remove_project_member(project_id, user_id_to_remove)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in this project.")
    return JSONResponse(content={"message": "Member removed successfully."})

# --- Project-specific Resources ---
@router.get("/{project_id}/chats", summary="Get all chat sessions for a project")
async def get_project_chats(project_id: str, user_id: str = Depends(auth_helper.get_current_user_id)):
    if not await mongo_manager.is_user_in_project(user_id, project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this project.")
    chats = await mongo_manager.get_chats_for_project(project_id)
    return JSONResponse(content={"chats": chats})

@router.get("/{project_id}/tasks", summary="Get all tasks for a project")
async def get_project_tasks(project_id: str, user_id: str = Depends(auth_helper.get_current_user_id)):
    if not await mongo_manager.is_user_in_project(user_id, project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this project.")
    tasks = await mongo_manager.get_tasks_for_project(project_id)
    return {"tasks": tasks}

# --- Context Item Management ---
@router.get("/{project_id}/context", summary="List context items for a project")
async def list_context_items(project_id: str, user_id: str = Depends(auth_helper.get_current_user_id)):
    if not await mongo_manager.is_user_in_project(user_id, project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this project.")
    items = await mongo_manager.get_context_items(project_id)
    return JSONResponse(content={"context_items": items})

@router.post("/{project_id}/context", status_code=status.HTTP_201_CREATED, summary="Add a context item to a project")
async def add_context_item(
    project_id: str,
    request: ContextItemCreateRequest,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    if not await mongo_manager.is_user_in_project(user_id, project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this project.")
    
    item = await mongo_manager.add_context_item(project_id, user_id, request.type, request.content)
    return JSONResponse(content=item)

@router.delete("/{project_id}/context/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a context item")
async def delete_context_item(
    project_id: str,
    item_id: str,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    if not await mongo_manager.is_user_in_project(user_id, project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this project.")
    
    # Optional: Add owner/creator check for deletion permission
    
    success = await mongo_manager.delete_context_item(item_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Context item not found.")
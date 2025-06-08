import logging
from fastapi import APIRouter, Depends, HTTPException
from ..auth.utils import AuthHelper
from . import models, dependencies as memory_deps
from .utils import run_memory_agent_instruction, trigger_mcp_tool

logger = logging.getLogger(__name__)
auth_helper = AuthHelper()

router = APIRouter(
    prefix="/memory",
    tags=["Memory Management"]
)

# Static categories for the frontend dropdown
MEMORY_CATEGORIES = ["Personal", "Professional", "Social", "Financial", "Health", "Preferences", "Events", "General"]

@router.post("/get-memory-categories")
async def get_memory_categories(user_id: str = Depends(auth_helper.get_current_user_id)):
    return {"categories": MEMORY_CATEGORIES}

@router.post("/get-graph-data")
async def get_graph_data(user_id: str = Depends(auth_helper.get_current_user_id)):
    if not memory_deps.neo4j_manager:
        raise HTTPException(status_code=503, detail="Long-term memory service is unavailable.")
    try:
        graph_data = memory_deps.neo4j_manager.get_graph_data_for_user(user_id)
        return graph_data
    except Exception as e:
        logger.error(f"Failed to get graph data for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve graph data.")

@router.post("/get-short-term-memories")
async def get_short_term_memories(
    request: models.ShortTermMemoryRequest,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    if not memory_deps.mongo_manager_instance:
        raise HTTPException(status_code=503, detail="Short-term memory service is unavailable.")
    try:
        memories = memory_deps.mongo_manager_instance.get_memories(user_id, request.category, request.limit)
        return {"memories": memories}
    except Exception as e:
        logger.error(f"Failed to get short-term memories for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve short-term memories.")

@router.post("/customize-long-term-memories")
async def customize_memories_with_agent(
    request: models.CustomizeMemoryRequest,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    if not request.information:
        raise HTTPException(status_code=400, detail="Information cannot be empty.")
    
    result = await run_memory_agent_instruction(user_id, request.information)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    return {"message": "Memory instruction processed successfully.", "details": result.get("details")}

@router.post("/initiate-long-term-memories")
async def reset_long_term_memories(
    request: models.ResetMemoryRequest,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    if not request.clear_graph:
        return {"message": "No action taken."}
    
    # Directly call the MCP tool for a destructive action
    result = await trigger_mcp_tool(user_id, "clear_all_long_term_memories")
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Failed to reset long-term memory."))
    
    return {"message": "Long-term memories have been reset."}

@router.post("/clear-all-short-term-memories")
async def clear_short_term_memories(user_id: str = Depends(auth_helper.get_current_user_id)):
    result = await trigger_mcp_tool(user_id, "clear_all_short_term_memories")
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Failed to clear short-term memories."))
    
    return {"message": "Short-term memories have been cleared."}

# The following endpoints are placeholders if direct manipulation is ever needed.
# For now, all manipulation is done via the agent.
@router.post("/add-short-term-memory")
async def add_short_term_memory(
    request: models.AddShortTermMemoryRequest,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    params = {
        "content": request.text,
        "category": request.category,
        "ttl_seconds": request.retention_days * 24 * 60 * 60,
    }
    result = await trigger_mcp_tool(user_id, "add_short_term_memory", params)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Failed to add short-term memory"))
    return {"message": "Memory added successfully", "details": result.get("raw_response")}

@router.post("/update-short-term-memory")
async def update_short_term_memory(
    request: models.UpdateShortTermMemoryRequest,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    params = {
        "memory_id": request.id,
        "new_content": request.text,
        "new_ttl_seconds": request.retention_days * 24 * 60 * 60
    }
    result = await trigger_mcp_tool(user_id, "update_short_term_memory", params)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Failed to update short-term memory"))
    return {"message": "Memory updated successfully", "details": result.get("raw_response")}

@router.post("/delete-short-term-memory")
async def delete_short_term_memory(
    request: models.DeleteShortTermMemoryRequest,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    params = { "memory_id": request.memory_id }
    result = await trigger_mcp_tool(user_id, "delete_short_term_memory", params)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Failed to delete short-term memory"))
    return {"message": "Memory deleted successfully", "details": result.get("raw_response")}

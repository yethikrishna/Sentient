import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import List, Dict
import datetime

from main.dependencies import auth_helper
from main.auth.utils import PermissionChecker
from .db import get_db_pool
from . import utils # Import the new utils module

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/memories",
    tags=["Memories"]
)

@router.get("/", summary="Get all memories for a user")
async def get_all_memories(
    user_id: str = Depends(PermissionChecker(required_permissions=["read:profile"])) # Reusing a common permission
):
    """
    Retrieves all facts (memories) for the authenticated user from the PostgreSQL database,
    along with their associated topics.
    """
    pool = None
    try:
        pool = await get_db_pool()
        async with pool.acquire() as connection:
            query = """
                SELECT
                    f.id,
                    f.content,
                    f.source,
                    f.created_at,
                    f.updated_at,
                    COALESCE(ARRAY_AGG(t.name) FILTER (WHERE t.name IS NOT NULL), '{}') as topics
                FROM facts f
                LEFT JOIN fact_topics ft ON f.id = ft.fact_id
                LEFT JOIN topics t ON ft.topic_id = t.id
                WHERE f.user_id = $1
                GROUP BY f.id
                ORDER BY f.created_at DESC;
            """
            records = await connection.fetch(query, user_id)

            memories = [
                {
                    "id": record["id"],
                    "content": record["content"],
                    "source": record["source"],
                    "created_at": record["created_at"].isoformat() if isinstance(record["created_at"], datetime.datetime) else record["created_at"],
                    "updated_at": record["updated_at"].isoformat() if isinstance(record["updated_at"], datetime.datetime) else record["updated_at"],
                    "topics": record["topics"]
                } for record in records
            ]
            return JSONResponse(content={"memories": memories})
    except Exception as e:
        logger.error(f"Error fetching memories for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching memories."
        )
@router.get("/graph", summary="Get memory graph data for a user")
async def get_memory_graph(
    user_id: str = Depends(PermissionChecker(required_permissions=["read:profile"]))
):
    """
    Retrieves all memories for a user and calculates their semantic relationships
    to build a graph structure of nodes and edges.
    """
    try:
        graph_data = await utils.create_memory_graph(user_id)
        return JSONResponse(content=graph_data)
    except Exception as e:
        logger.error(f"Error generating memory graph for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the memory graph."
        )

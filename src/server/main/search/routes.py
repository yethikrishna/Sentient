from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from main.auth.utils import PermissionChecker
from main.search.models import UnifiedSearchRequest
from main.search.utils import perform_unified_search

router = APIRouter(
    prefix="/api/search",
    tags=["Search"]
)

@router.post("/unified", summary="Perform a unified search across all data sources")
async def unified_search_endpoint(
    request: UnifiedSearchRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["read:tasks"])) # Using a common permission
):
    try:
        return StreamingResponse(
            perform_unified_search(request.query, user_id),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Transfer-Encoding": "chunked",
            }
        )
    except Exception as e:
        # This part might not be reached if the error happens inside the generator,
        # but it's good for handling setup errors before the stream starts.
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during search setup: {e}")
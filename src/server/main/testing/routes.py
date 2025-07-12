import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from main.dependencies import auth_helper
from workers.tasks import extract_from_context
from main.config import ENVIRONMENT
from .models import ContextInjectionRequest

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/testing",
    tags=["Testing Utilities"]
)

@router.post("/inject-context", summary="Manually inject a context event for processing")
async def inject_context_event(
    request: ContextInjectionRequest,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    if ENVIRONMENT not in ["dev-local", "selfhost"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development or self-host environments."
        )

    service_name = request.service_name
    event_data = request.event_data

    if not service_name or not event_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="service_name and event_data are required.")

    event_id = f"manual_injection_{uuid.uuid4()}"

    try:
        extract_from_context.delay(user_id, service_name, event_id, event_data)
        logger.info(f"Manually injected event '{event_id}' for user '{user_id}' into the context extraction pipeline.")
        return {"message": "Context event injected successfully.", "event_id": event_id}
    except Exception as e:
        logger.error(f"Failed to queue context injection task for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to queue task.")

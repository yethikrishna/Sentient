import datetime
import uuid
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from kafka import KafkaProducer
from .models import CreateBlockRequest, UpdateBlockRequest
from ..dependencies import mongo_manager
from ..auth.utils import PermissionChecker
from ..config import CONTEXT_EVENTS_TOPIC, KAFKA_BOOTSTRAP_SERVERS

router = APIRouter(
    prefix="/journal",
    tags=["Journal"]
)

try:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
    )
except Exception as e:
    print(f"Failed to initialize Kafka producer for Journal: {e}")
    producer = None

def send_to_kafka(topic: str, value: dict):
    if not producer:
        print("Kafka producer not initialized. Cannot send message.")
        return
    try:
        producer.send(topic, value=value)
    except Exception as e:
        print(f"Failed to send message to Kafka topic {topic}: {e}")

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
    """Creates a new journal block and sends it to the context pipeline."""
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
    
    # Conditionally send to Kafka for context extraction
    if request.processWithAI:
        kafka_payload = {
            "user_id": user_id,
            "service_name": "journal_block",
            "event_type": "new_block",
            "event_id": block_id,
            "data": {"content": request.content, "block_id": block_id},
            "timestamp_utc": now.isoformat()
        }
        # CONTEXT_EVENTS_TOPIC can have multiple topics, we send to the journal one
        journal_topic = next((t for t in CONTEXT_EVENTS_TOPIC if "journal" in t), None)
        if journal_topic:
            send_to_kafka(journal_topic, kafka_payload)
            print(f"Sent journal block {block_id} to Kafka for processing.")
    
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

    # Re-send to Kafka for context extraction
    kafka_payload = {
        "user_id": user_id,
        "service_name": "journal_block",
        "event_type": "updated_block",
        "event_id": block_id,
        "data": {"content": request.content, "block_id": block_id, "deprecate_task_id": old_task_id_to_deprecate},
        "timestamp_utc": now.isoformat()
    }
    journal_topic = next((t for t in CONTEXT_EVENTS_TOPIC if "journal" in t), None)
    if journal_topic:
        send_to_kafka(journal_topic, kafka_payload)
    
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
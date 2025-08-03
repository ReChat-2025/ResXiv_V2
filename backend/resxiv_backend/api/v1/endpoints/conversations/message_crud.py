"""
Message CRUD Operations - L6 Engineering Standards
Split from conversations.py to follow 800-line rule and single responsibility principle.
"""

import uuid
from typing import Dict, Any, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_postgres_session, db_manager
from app.services.message.message_service_integrated import MessageService
from app.core.dependency_injection import get_redis_service
from app.dependencies.conversation_auth import (
    verify_conversation_access,
    verify_conversation_write_access
)
from api.dependencies import get_current_user_required
from app.models.conversation_models import (
    MessageCreate,
    MessageUpdate,
    MessageResponse,
    MessageList,
    MessageSearch
)
from app.core.error_handling import handle_service_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{conversation_id}/messages", response_model=Dict[str, Any])
@handle_service_errors("send message", success_status=201)
async def send_message(
    conversation_id: uuid.UUID = Path(..., description="Conversation ID"),
    message_data: MessageCreate = ...,
    current_user: Dict = Depends(get_current_user_required),
    conversation_access = Depends(verify_conversation_write_access),
    session: AsyncSession = Depends(get_postgres_session),
    redis_service = Depends(get_redis_service)
):
    """Send a new message to conversation"""
    service = MessageService(session, db_manager, redis_service)
    
    result = await service.create_message(
        conversation_id=conversation_id,
        sender_id=current_user["user_id"],
        message_data=message_data,
        sender_name=current_user.get("name") or current_user.get("full_name") or current_user.get("email")
    )
    
    return result


@router.get("/{conversation_id}/messages", response_model=Dict[str, Any])
@handle_service_errors("get messages")
async def get_conversation_messages(
    conversation_id: uuid.UUID = Path(..., description="Conversation ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=200, description="Messages per page"),
    before_message_id: Optional[str] = Query(None, description="Get messages before this ID"),
    after_message_id: Optional[str] = Query(None, description="Get messages after this ID"),
    current_user: Dict = Depends(get_current_user_required),
    conversation_access = Depends(verify_conversation_access),
    session: AsyncSession = Depends(get_postgres_session),
    redis_service = Depends(get_redis_service)
):
    """Get conversation messages with pagination"""
    service = MessageService(session, db_manager, redis_service)
    
    result = await service.get_conversation_messages(
        conversation_id=conversation_id,
        user_id=current_user["user_id"],
        page=page,
        size=size,
        before_message_id=before_message_id,
        after_message_id=after_message_id
    )
    
    return result


@router.post("/{conversation_id}/messages/search", response_model=Dict[str, Any])
@handle_service_errors("search messages")
async def search_messages(
    conversation_id: uuid.UUID = Path(..., description="Conversation ID"),
    search_params: MessageSearch = ...,
    current_user: Dict = Depends(get_current_user_required),
    conversation_access = Depends(verify_conversation_access),
    session: AsyncSession = Depends(get_postgres_session),
    redis_service = Depends(get_redis_service)
):
    """Search messages within conversation"""
    service = MessageService(session, db_manager, redis_service)
    
    result = await service.search_messages(
        conversation_id=conversation_id,
        user_id=current_user["user_id"],
        **search_params.dict()
    )
    
    return result


@router.put("/messages/{message_id}", response_model=Dict[str, Any])
@handle_service_errors("update message")
async def update_message(
    message_id: str = Path(..., description="MongoDB ObjectId of the message to update"),
    updates: MessageUpdate = ...,
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    redis_service = Depends(get_redis_service)
):
    """
    Update an existing message (if user is author).
    
    Args:
        message_id: MongoDB ObjectId string (24-character hex)
        updates: Message update data
        
    Returns:
        Success response with updated message data
        
    Raises:
        400: Invalid message ID format
        403: Not authorized to update this message
        404: Message not found
    """
    # Pre-validate message_id format
    from app.utils.mongodb_utils import is_valid_object_id
    if not is_valid_object_id(message_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": f"Invalid message ID format: '{message_id}'. Expected MongoDB ObjectId (24-character hex string).",
                "example": "Example: 688a1862d03faa1e70f60802"
            }
        )
    
    service = MessageService(session, db_manager, redis_service)
    
    result = await service.update_message(
        message_id=message_id,
        user_id=current_user["user_id"],
        message_data=updates
    )
    
    return result


@router.delete("/messages/{message_id}", response_model=Dict[str, Any])
@handle_service_errors("delete message")
async def delete_message(
    message_id: str = Path(..., description="MongoDB ObjectId of the message to delete"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    redis_service = Depends(get_redis_service)
):
    """
    Delete a message (if user is author or admin).
    
    Args:
        message_id: MongoDB ObjectId string (24-character hex)
        
    Returns:
        Success response with deletion confirmation
        
    Raises:
        400: Invalid message ID format
        403: Not authorized to delete this message 
        404: Message not found
    """
    # Pre-validate message_id format to provide clearer error
    from app.utils.mongodb_utils import is_valid_object_id
    if not is_valid_object_id(message_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": f"Invalid message ID format: '{message_id}'. Expected MongoDB ObjectId (24-character hex string).",
                "example": "Example: 688a1862d03faa1e70f60802"
            }
        )
    
    service = MessageService(session, db_manager, redis_service)
    
    result = await service.delete_message(
        message_id=message_id,
        user_id=current_user["user_id"]
    )
    
    return result 
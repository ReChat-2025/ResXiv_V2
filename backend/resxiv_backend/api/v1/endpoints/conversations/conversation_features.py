"""
Conversation Features - L6 Engineering Standards
Handles reactions, read receipts, and typing indicators.
Split from conversations.py to follow single responsibility principle.
"""

import uuid
from typing import Dict, Any
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_postgres_session, db_manager
from app.services.message.message_service_integrated import MessageService
from app.core.dependency_injection import get_redis_service
from app.dependencies.conversation_auth import verify_conversation_access
from api.dependencies import get_current_user_required
from app.models.conversation_models import (
    MessageReactionCreate,
    TypingIndicator
)
from app.core.error_handling import handle_service_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/messages/{message_id}/reactions", response_model=Dict[str, Any])
@handle_service_errors("add message reaction", success_status=201)
async def add_message_reaction(
    message_id: str = Path(..., description="MongoDB ObjectId of the message"),
    reaction_data: MessageReactionCreate = ...,
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session), 
    redis_service = Depends(get_redis_service)
):
    """Add reaction to a message"""
    # Validate message_id format
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
    
    result = await service.add_message_reaction(
        message_id=message_id,
        user_id=current_user["user_id"],
        reaction=reaction_data.reaction
    )
    
    return result


@router.delete("/messages/{message_id}/reactions", response_model=Dict[str, Any])
@handle_service_errors("remove message reaction")
async def remove_message_reaction(
    message_id: str = Path(..., description="MongoDB ObjectId of the message"),
    reaction: str = Body(..., embed=True, description="Reaction to remove"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session), 
    redis_service = Depends(get_redis_service)
):
    """Remove reaction from a message"""
    # Validate message_id format
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
    
    result = await service.remove_message_reaction(
        message_id=message_id,
        user_id=current_user["user_id"],
        reaction=reaction
    )
    
    return result


@router.post("/messages/{message_id}/read", response_model=Dict[str, Any])
@handle_service_errors("mark message as read")
async def mark_message_as_read(
    message_id: str = Path(..., description="MongoDB ObjectId of the message"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session), 
    redis_service = Depends(get_redis_service)
):
    """Mark a specific message as read"""
    # Validate message_id format
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
    
    result = await service.mark_message_as_read(
        message_id=message_id,
        user_id=current_user["user_id"]
    )
    
    return result


@router.post("/{conversation_id}/read", response_model=Dict[str, Any])
@handle_service_errors("mark conversation as read")
async def mark_conversation_as_read(
    conversation_id: uuid.UUID = Path(..., description="Conversation ID"),
    current_user: Dict = Depends(get_current_user_required),
    conversation_access = Depends(verify_conversation_access),
    session: AsyncSession = Depends(get_postgres_session), redis_service = Depends(get_redis_service)
):
    """Mark all messages in conversation as read"""
    service = MessageService(session, db_manager, redis_service)
    
    result = await service.mark_conversation_as_read(
        conversation_id=conversation_id,
        user_id=current_user["user_id"]
    )
    
    return result


@router.post("/{conversation_id}/typing", response_model=Dict[str, Any])
@handle_service_errors("update typing indicator")
async def update_typing_status(
    conversation_id: uuid.UUID = Path(..., description="Conversation ID"),
    typing_data: TypingIndicator = ...,
    current_user: Dict = Depends(get_current_user_required),
    conversation_access = Depends(verify_conversation_access),
    session: AsyncSession = Depends(get_postgres_session), redis_service = Depends(get_redis_service)
):
    """Update typing indicator for conversation"""
    service = MessageService(session, db_manager, redis_service)
    
    result = await service.update_typing_status(
        conversation_id=conversation_id,
        user_id=current_user["user_id"],
        is_typing=typing_data.is_typing
    )
    
    return result 
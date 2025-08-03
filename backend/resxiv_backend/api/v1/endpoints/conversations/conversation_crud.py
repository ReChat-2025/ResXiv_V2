"""
Conversation CRUD Operations - L6 Engineering Standards
Split from conversations.py to follow 800-line rule and single responsibility principle.
"""

import uuid
from typing import Dict, Any, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_postgres_session
from app.services.conversation.conversation_service_integrated import ConversationService
from app.core.dependency_injection import get_redis_service
from app.dependencies.conversation_auth import (
    verify_conversation_access,
    verify_project_conversation_access
)
from api.dependencies import get_current_user_required
from app.models.conversation_models import (
    ConversationCreate,
    ConversationResponse,
    ConversationList,
    ConversationWithMessages,
    ConversationType
)
from app.core.error_handling import handle_service_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=Dict[str, Any], status_code=201)
@handle_service_errors("create conversation", success_status=201)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    redis_service = Depends(get_redis_service)
):
    """Create a new conversation with error handling"""
    service = ConversationService(session, redis_service)
    
    result = await service.create_conversation(
        user_id=current_user["user_id"],
        **conversation_data.dict()
    )
    
    return result


@router.get("/", response_model=ConversationList)
@handle_service_errors("list conversations")
async def list_user_conversations(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    conversation_type: Optional[ConversationType] = Query(None, description="Filter by type"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    redis_service = Depends(get_redis_service)
):
    """List user conversations with pagination"""
    service = ConversationService(session, redis_service)
    
    result = await service.get_user_conversations(
        user_id=current_user["user_id"],
        page=page,
        limit=size,
        conversation_type=conversation_type
    )
    
    return result


@router.get("/projects/{project_id}", response_model=Dict[str, Any])
@handle_service_errors("list project conversations")
async def list_project_conversations(
    project_id: uuid.UUID = Path(..., description="Project ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    conversation_type: Optional[ConversationType] = Query(None, description="Filter by conversation type (AI, GROUP, PDF, DROP, AGENTIC)"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    redis_service = Depends(get_redis_service)
):
    """
    List conversations for a specific project with pagination and filtering.
    
    Supported conversation types:
    - AI: AI-powered conversations
    - GROUP: Group discussions
    - PDF: Paper-specific discussions
    - DROP: Drop-zone conversations
    - AGENTIC: Agentic AI conversations
    
    By default, returns all conversation types if no filter is specified.
    """
    service = ConversationService(session, redis_service)
    
    result = await service.get_project_conversations(
        project_id=project_id,
        user_id=current_user["user_id"],
        page=page,
        limit=size,
        conversation_type=conversation_type
    )
    
    return result


@router.get("/{conversation_id}", response_model=Dict[str, Any])
@handle_service_errors("get conversation details")
async def get_conversation_details(
    conversation_id: uuid.UUID = Path(..., description="Conversation ID"),
    include_messages: bool = Query(False, description="Include recent messages"),
    message_limit: int = Query(50, ge=1, le=200, description="Max messages to include"),
    current_user: Dict = Depends(get_current_user_required),
    conversation_access = Depends(verify_conversation_access),
    session: AsyncSession = Depends(get_postgres_session),
    redis_service = Depends(get_redis_service)
):
    """Get conversation details with optional message history"""
    service = ConversationService(session, redis_service)
    
    result = await service.get_conversation_details(
        conversation_id=conversation_id,
        user_id=current_user["user_id"],
        include_messages=include_messages,
        message_limit=message_limit
    )
    
    return result


@router.put("/{conversation_id}", response_model=Dict[str, Any])
@handle_service_errors("update conversation")
async def update_conversation(
    conversation_id: uuid.UUID = Path(..., description="Conversation ID"),
    updates: Dict[str, Any] = ...,
    current_user: Dict = Depends(get_current_user_required),
    conversation_access = Depends(verify_conversation_access),
    session: AsyncSession = Depends(get_postgres_session),
    redis_service = Depends(get_redis_service)
):
    """Update conversation details"""
    service = ConversationService(session, redis_service)
    
    result = await service.update_conversation(
        conversation_id=conversation_id,
        user_id=current_user["user_id"],
        updates=updates
    )
    
    return result


@router.delete("/{conversation_id}", response_model=Dict[str, Any])
@handle_service_errors("delete conversation")
async def delete_conversation(
    conversation_id: uuid.UUID = Path(..., description="Conversation ID"),
    current_user: Dict = Depends(get_current_user_required),
    conversation_access = Depends(verify_conversation_access),
    session: AsyncSession = Depends(get_postgres_session),
    redis_service = Depends(get_redis_service)
):
    """Delete a conversation"""
    service = ConversationService(session, redis_service)
    
    result = await service.delete_conversation(
        conversation_id=conversation_id,
        user_id=current_user["user_id"]
    )
    
    return result


@router.get("/projects/{project_id}/conversation", response_model=Dict[str, Any])
@handle_service_errors("get project conversation")
async def get_project_conversation(
    project_id: uuid.UUID = Path(..., description="Project ID"),
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_conversation_access),
    session: AsyncSession = Depends(get_postgres_session),
    redis_service = Depends(get_redis_service)
):
    """Get or create project's main conversation"""
    service = ConversationService(session, redis_service)
    
    result = await service.get_or_create_project_conversation(
        project_id=project_id,
        user_id=current_user["user_id"]
    )
    
    return result 
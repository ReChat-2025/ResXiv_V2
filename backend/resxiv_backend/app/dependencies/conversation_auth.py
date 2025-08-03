"""
Conversation Authentication Dependencies

This module provides authentication and authorization dependencies
specifically for conversation and messaging endpoints.
"""

import uuid
from typing import Dict, Any
from fastapi import Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_postgres_session
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.project_repository import ProjectRepository
from api.dependencies import get_current_user_required


class ConversationAuthorizationError(HTTPException):
    """Custom conversation authorization error"""
    def __init__(self, detail: str = "Access denied to conversation"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class ConversationNotFoundError(HTTPException):
    """Custom conversation not found error"""
    def __init__(self, detail: str = "Conversation not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


async def verify_conversation_access(
    conversation_id: uuid.UUID = Path(..., description="Conversation ID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
) -> Dict[str, Any]:
    """
    Verify that the current user has access to the specified conversation.
    
    This dependency checks:
    1. Conversation exists
    2. User has access based on conversation type and project membership
    
    Args:
        conversation_id: Conversation ID from path parameter
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Dictionary containing conversation access information
        
    Raises:
        ConversationNotFoundError: If conversation doesn't exist
        ConversationAuthorizationError: If user doesn't have access
    """
    user_id = current_user["user_id"]
    
    # Get conversation details
    conversation_repo = ConversationRepository(session)
    conversation = await conversation_repo.get_by_id(conversation_id)
    
    if not conversation:
        raise ConversationNotFoundError(
            f"Conversation {conversation_id} not found"
        )
    
    # Check access based on conversation type
    access_granted = False
    user_role = None
    
    if conversation.type in ["GROUP", "PDF", "DROP", "AGENTIC"] and conversation.entity:
        # For project-associated conversations, check project membership
        project_repo = ProjectRepository(session)
        is_member = await project_repo.is_user_member(conversation.entity, user_id)
        
        if is_member:
            access_granted = True
            user_role = await project_repo.get_user_role(conversation.entity, user_id)
    
    elif conversation.created_by == user_id:
        # User created the conversation
        access_granted = True
        user_role = "owner"
    
    if not access_granted:
        raise ConversationAuthorizationError(
            f"User does not have access to conversation {conversation_id}"
        )
    
    return {
        "conversation_id": conversation_id,
        "conversation": conversation,
        "user_id": user_id,
        "user_role": user_role,
        "can_read": True,
        "can_write": True,  # Most users can write in conversations they have access to
        "can_moderate": user_role in ["admin", "owner"] if user_role else False
    }


async def verify_conversation_write_access(
    conversation_access: Dict[str, Any] = Depends(verify_conversation_access)
) -> Dict[str, Any]:
    """
    Verify that the current user has write access to the conversation.
    
    Args:
        conversation_access: Conversation access from verify_conversation_access
        
    Returns:
        Same conversation access dictionary
        
    Raises:
        ConversationAuthorizationError: If user doesn't have write access
    """
    if not conversation_access.get("can_write", False):
        raise ConversationAuthorizationError(
            "User does not have write access to this conversation"
        )
    
    return conversation_access


async def verify_conversation_moderate_access(
    conversation_access: Dict[str, Any] = Depends(verify_conversation_access)
) -> Dict[str, Any]:
    """
    Verify that the current user has moderation access to the conversation.
    
    Args:
        conversation_access: Conversation access from verify_conversation_access
        
    Returns:
        Same conversation access dictionary
        
    Raises:
        ConversationAuthorizationError: If user doesn't have moderation access
    """
    if not conversation_access.get("can_moderate", False):
        raise ConversationAuthorizationError(
            "User does not have moderation access to this conversation"
        )
    
    return conversation_access


async def verify_project_conversation_access(
    project_id: uuid.UUID = Path(..., description="Project ID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
) -> Dict[str, Any]:
    """
    Verify user access to a project's conversation.
    
    This is used for project-specific conversation endpoints.
    
    Args:
        project_id: Project ID from path parameter
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Dictionary containing project and conversation access information
        
    Raises:
        ConversationAuthorizationError: If user doesn't have access
    """
    user_id = current_user["user_id"]
    
    # Check project membership
    project_repo = ProjectRepository(session)
    is_member = await project_repo.is_user_member(project_id, user_id)
    
    if not is_member:
        raise ConversationAuthorizationError(
            f"User does not have access to project {project_id}"
        )
    
    user_role = await project_repo.get_user_role(project_id, user_id)
    
    # Get or create project conversation
    conversation_repo = ConversationRepository(session)
    conversation = await conversation_repo.get_project_conversation(project_id)
    
    return {
        "project_id": project_id,
        "conversation_id": conversation.id if conversation else None,
        "conversation": conversation,
        "user_id": user_id,
        "user_role": user_role,
        "can_read": True,
        "can_write": True,
        "can_moderate": user_role in ["admin", "owner"] if user_role else False
    } 
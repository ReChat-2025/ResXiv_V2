"""
Conversation CRUD Service - L6 Engineering Standards
Focused on basic conversation operations: create, read, update, delete.
"""

import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.project_repository import ProjectRepository
from app.models.conversation_models import (
    ConversationCreate, ConversationUpdate, ConversationResponse,
    ConversationType
)

logger = logging.getLogger(__name__)


class ConversationCrudService:
    """
    CRUD service for conversation database operations.
    Single Responsibility: Basic conversation CRUD operations.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.conversation_repo = ConversationRepository(session)
        self.project_repo = ProjectRepository(session)
    
    @handle_service_errors("create conversation")
    async def create_conversation(
        self,
        conversation_data: ConversationCreate,
        created_by: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Create a new conversation.
        
        Args:
            conversation_data: Conversation creation data
            created_by: User creating the conversation
            
        Returns:
            Success/error response with conversation data
        """
        try:
            # Validate conversation type and entity
            if conversation_data.conversation_type == ConversationType.GROUP and conversation_data.project_id:
                # For GROUP conversations, verify entity (project) exists and user has access
                project_exists = await self.project_repo.get_project_by_id(conversation_data.project_id)
                if not project_exists:
                    raise ServiceError(
                        "Project not found",
                        ErrorCodes.NOT_FOUND_ERROR
                    )
                
                is_member = await self.project_repo.is_user_member(conversation_data.project_id, created_by)
                if not is_member:
                    raise ServiceError(
                        "User is not a member of the project",
                        ErrorCodes.AUTHORIZATION_ERROR
                    )
                
                # Check if project conversation already exists
                existing_conversation = await self.conversation_repo.get_project_conversation(conversation_data.project_id)
                if existing_conversation:
                    return {
                        "success": False,
                        "error": "Project conversation already exists",
                        "error_code": "CONVERSATION_EXISTS",
                        "conversation_id": existing_conversation.id
                    }
            
            # Create conversation
            conversation = await self.conversation_repo.create(
                type=conversation_data.conversation_type,
                entity=conversation_data.project_id,
                is_group=True,
                created_by=created_by
            )
            
            await self.session.commit()
            
            return {
                "success": True,
                "conversation": ConversationResponse.from_orm(conversation),
                "message": "Conversation created successfully"
            }
            
        except Exception as e:
            await self.session.rollback()
            raise ServiceError(
                f"Failed to create conversation: {str(e)}",
                ErrorCodes.CREATION_ERROR
            )
    
    @handle_service_errors("get conversation")
    async def get_conversation(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        include_messages: bool = False
    ) -> Dict[str, Any]:
        """
        Get conversation by ID with access control.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User requesting the conversation
            include_messages: Whether to include messages
            
        Returns:
            Conversation data or error
        """
        # Get conversation
        conversation = await self.conversation_repo.get_conversation_by_id(conversation_id)
        
        if not conversation:
            raise ServiceError(
                "Conversation not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        # Check access permissions
        has_access = await self._check_conversation_access(conversation_id, user_id)
        if not has_access:
            raise ServiceError(
                "Access denied to conversation",
                ErrorCodes.AUTHORIZATION_ERROR
            )
        
        return {
            "success": True,
            "conversation": ConversationResponse.from_orm(conversation)
        }
    
    @handle_service_errors("get conversation details")
    async def get_conversation_details(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        include_messages: bool = False,
        message_limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get conversation details with optional message history.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User requesting the conversation
            include_messages: Whether to include messages
            message_limit: Maximum number of messages to include
            
        Returns:
            Conversation data with optional messages
        """
        # Get conversation
        conversation = await self.conversation_repo.get_conversation_by_id(conversation_id)
        
        if not conversation:
            raise ServiceError(
                "Conversation not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        # Check access permissions
        has_access = await self._check_conversation_access(conversation_id, user_id)
        if not has_access:
            raise ServiceError(
                "Access denied to conversation",
                ErrorCodes.AUTHORIZATION_ERROR
            )
        
        result = {
            "success": True,
            "conversation": ConversationResponse.from_orm(conversation)
        }
        
        # If messages are requested, get them with the specified limit
        if include_messages:
            try:
                # Import here to avoid circular imports
                from app.services.message.message_core import MessageCoreService
                from app.repositories.message_repository import MessageRepository
                
                message_repo = MessageRepository(self.session)
                message_service = MessageCoreService(self.session, message_repo)
                
                messages_result = await message_service.get_conversation_messages(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    page=1,
                    size=message_limit
                )
                
                result["messages"] = messages_result.get("messages", [])
                result["message_count"] = messages_result.get("total", 0)
            except Exception as e:
                # If message retrieval fails, still return conversation data
                result["messages"] = []
                result["message_count"] = 0
                result["message_error"] = str(e)
        
        return result
    
    @handle_service_errors("update conversation")
    async def update_conversation(
        self,
        conversation_id: uuid.UUID,
        conversation_data: ConversationUpdate,
        updated_by: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Update conversation information.
        
        Args:
            conversation_id: Conversation UUID
            conversation_data: Update data
            updated_by: User performing the update
            
        Returns:
            Updated conversation data
        """
        try:
            # Check if conversation exists and user has access
            conversation = await self.conversation_repo.get_conversation_by_id(conversation_id)
            if not conversation:
                raise ServiceError(
                    "Conversation not found",
                    ErrorCodes.NOT_FOUND_ERROR
                )
            
            # Check permissions
            has_access = await self._check_conversation_access(conversation_id, updated_by)
            if not has_access:
                raise ServiceError(
                    "Access denied to conversation",
                    ErrorCodes.AUTHORIZATION_ERROR
                )
            
            # Update conversation
            updated_conversation = await self.conversation_repo.update_conversation(
                conversation_id=conversation_id,
                **conversation_data.dict(exclude_none=True)
            )
            
            await self.session.commit()
            
            return {
                "success": True,
                "conversation": ConversationResponse.from_orm(updated_conversation),
                "message": "Conversation updated successfully"
            }
            
        except Exception as e:
            await self.session.rollback()
            raise ServiceError(
                f"Failed to update conversation: {str(e)}",
                ErrorCodes.UPDATE_ERROR
            )
    
    @handle_service_errors("delete conversation")
    async def delete_conversation(
        self,
        conversation_id: uuid.UUID,
        deleted_by: uuid.UUID,
        soft_delete: bool = True
    ) -> Dict[str, Any]:
        """
        Delete a conversation.
        
        Args:
            conversation_id: Conversation UUID
            deleted_by: User performing the deletion
            soft_delete: Whether to soft delete (default) or hard delete
            
        Returns:
            Deletion result
        """
        try:
            # Check if conversation exists
            conversation = await self.conversation_repo.get_conversation_by_id(conversation_id)
            if not conversation:
                raise ServiceError(
                    "Conversation not found",
                    ErrorCodes.NOT_FOUND_ERROR
                )
            
            # Check permissions - only owner or admin can delete
            if conversation.created_by != deleted_by:
                # Check if user is project admin for group conversations
                if conversation.type == ConversationType.GROUP.value and conversation.entity:
                    is_admin = await self.project_repo.is_user_admin(conversation.entity, deleted_by)
                    if not is_admin:
                        raise ServiceError(
                            "Insufficient permissions to delete conversation",
                            ErrorCodes.AUTHORIZATION_ERROR
                        )
                else:
                    raise ServiceError(
                        "Only conversation owner can delete this conversation",
                        ErrorCodes.AUTHORIZATION_ERROR
                    )
            
            if soft_delete:
                # Soft delete
                await self.conversation_repo.soft_delete_conversation(conversation_id, deleted_by)
            else:
                # Hard delete
                await self.conversation_repo.delete_conversation(conversation_id)
            
            await self.session.commit()
            
            return {
                "success": True,
                "message": f"Conversation {'soft' if soft_delete else 'hard'} deleted successfully"
            }
            
        except Exception as e:
            await self.session.rollback()
            raise ServiceError(
                f"Failed to delete conversation: {str(e)}",
                ErrorCodes.DELETION_ERROR
            )
    
    @handle_service_errors("get user conversations")
    async def get_user_conversations(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        conversation_type: Optional[ConversationType] = None
    ) -> Dict[str, Any]:
        """
        Get conversations for a user.
        
        Args:
            user_id: User UUID
            page: Page number (1-based)
            limit: Conversations per page
            conversation_type: Optional filter by conversation type
            
        Returns:
            Paginated list of conversations
        """
        offset = (page - 1) * limit
        
        # Get conversations and count separately
        conversations = await self.conversation_repo.get_user_conversations(
            user_id=user_id,
            limit=limit,
            offset=offset,
            conversation_type=conversation_type
        )
        
        total_count = await self.conversation_repo.count_user_conversations(
            user_id=user_id,
            conversation_type=conversation_type
        )
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "success": True,
            "conversations": [ConversationResponse.from_orm(conv) for conv in conversations],
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_conversations": total_count,
                "conversations_per_page": limit,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }
    
    @handle_service_errors("get project conversations")
    async def get_project_conversations(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        conversation_type: Optional[ConversationType] = None
    ) -> Dict[str, Any]:
        """
        Get conversations for a project with pagination and filtering.
        
        Args:
            project_id: Project UUID
            user_id: User requesting the conversations (for access verification)
            page: Page number (1-based)
            limit: Conversations per page
            conversation_type: Optional filter by conversation type
            
        Returns:
            Paginated list of project conversations
        """
        # Verify user has access to the project
        is_member = await self.project_repo.is_user_member(project_id, user_id)
        if not is_member:
            raise ServiceError(
                "User is not a member of this project",
                ErrorCodes.AUTHORIZATION_ERROR
            )
        
        offset = (page - 1) * limit
        
        # Get conversations and count separately
        conversations = await self.conversation_repo.get_project_conversations(
            project_id=project_id,
            conversation_type=conversation_type,
            limit=limit,
            offset=offset
        )
        
        total_count = await self.conversation_repo.count_project_conversations(
            project_id=project_id,
            conversation_type=conversation_type
        )
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "success": True,
            "conversations": [ConversationResponse.from_orm(conv) for conv in conversations],
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_conversations": total_count,
                "conversations_per_page": limit,
                "has_next": has_next,
                "has_prev": has_prev
            },
            "project_id": str(project_id),
            "filters": {
                "conversation_type": conversation_type.value if conversation_type else None
            }
        }
    
    async def _check_conversation_access(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """
        Check if user has access to conversation.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User UUID
            
        Returns:
            True if user has access, False otherwise
        """
        # Get conversation details
        conversation = await self.conversation_repo.get_conversation_by_id(conversation_id)
        if not conversation:
            return False
        
        # Check based on conversation type
        if conversation.type == ConversationType.AI.value:
            # For AI conversations, check if user is a participant
            return await self.conversation_repo.is_user_participant(conversation_id, user_id)
        
        elif conversation.type == ConversationType.GROUP.value:
            if conversation.entity:
                # For project conversations, check project membership
                return await self.project_repo.is_user_member(conversation.entity, user_id)
            else:
                # For general group conversations, check if user is a participant
                return await self.conversation_repo.is_user_participant(conversation_id, user_id)
        
        elif conversation.type in [ConversationType.PDF.value, ConversationType.DROP.value, ConversationType.AGENTIC.value]:
            # For PDF, DROP, and AGENTIC conversations, check project membership
            if conversation.entity:
                return await self.project_repo.is_user_member(conversation.entity, user_id)
            else:
                # Fallback: check if user created the conversation
                return conversation.created_by == user_id
        
        return False
    
    @handle_service_errors("get conversation metadata")
    async def get_conversation_metadata(self, conversation_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get conversation metadata and status.
        
        Args:
            conversation_id: Conversation UUID
            
        Returns:
            Conversation metadata
        """
        conversation = await self.conversation_repo.get_conversation_by_id(conversation_id)
        if not conversation:
            raise ServiceError(
                "Conversation not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        # Get participant count
        participant_count = await self.conversation_repo.get_participant_count(conversation_id)
        
        # Get message count
        message_count = await self.conversation_repo.get_message_count(conversation_id)
        
        # Get last activity
        last_activity = await self.conversation_repo.get_last_activity(conversation_id)
        
        metadata = {
            "basic_info": {
                "id": str(conversation.id),
                "type": conversation.type,
                "title": conversation.title,
                "description": conversation.description,
                "entity": str(conversation.entity) if conversation.entity else None,
                "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None
            },
            "statistics": {
                "participant_count": participant_count,
                "message_count": message_count,
                "last_activity": last_activity.isoformat() if last_activity else None
            },
            "status": {
                "is_active": not conversation.deleted_at,
                "created_by": str(conversation.created_by) if conversation.created_by else None
            }
        }
        
        return {
            "success": True,
            "metadata": metadata
        } 
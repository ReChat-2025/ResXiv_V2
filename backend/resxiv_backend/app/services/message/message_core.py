"""
Message Core Service - L6 Engineering Standards
Focused on core message CRUD operations with clean separation of concerns.
"""

import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.models.conversation_models import MessageCreate, MessageUpdate, MessageResponse

logger = logging.getLogger(__name__)


class MessageCoreService:
    """
    Core message service for basic CRUD operations.
    Single Responsibility: Message lifecycle management.
    """
    
    def __init__(self, session: AsyncSession, message_repo: MessageRepository):
        self.session = session
        self.message_repo = message_repo
        self.conversation_repo = ConversationRepository(session)
    
    @handle_service_errors("create message")
    async def create_message(
        self,
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID,
        message_data: MessageCreate,
        sender_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new message with proper validation.
        
        Args:
            conversation_id: Target conversation
            sender_id: Message sender
            message_data: Message content and metadata
            sender_name: Optional sender display name
            
        Returns:
            Success response with message data
            
        Raises:
            ServiceError: If validation fails or access denied
        """
        # Verify conversation access
        has_access = await self.conversation_repo.can_user_access_conversation(
            conversation_id, sender_id
        )
        if not has_access:
            raise ServiceError(
                "Access denied to conversation",
                ErrorCodes.AUTHORIZATION_ERROR,
                403
            )
        
        # Validate reply_to message if specified
        if message_data.parent_message_id:
            reply_message = await self.message_repo.get_message_by_id(message_data.parent_message_id)
            if not reply_message or reply_message.conversation_id != conversation_id:
                raise ServiceError(
                    "Invalid reply message",
                    ErrorCodes.VALIDATION_ERROR,
                    400
                )
        
        # Create message
        message = await self.message_repo.create_message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            message_data=message_data,
            sender_name=sender_name
        )
        
        # Note: Conversation metadata is updated in MongoDB by message repository
        # No PostgreSQL session commit needed for MongoDB operations
        
        return {
            "success": True,
            "message": message,
            "message_text": "Message sent successfully"
        }
    
    @handle_service_errors("update message")
    async def update_message(
        self,
        message_id: str,
        user_id: uuid.UUID,
        message_data: MessageUpdate
    ) -> Dict[str, Any]:
        """
        Update an existing message.
        
        Args:
            message_id: MongoDB ObjectId string of message to update
            user_id: User attempting update
            message_data: Updated content
            
        Returns:
            Success response with updated message
            
        Raises:
            ServiceError: If message not found, invalid ID format, or access denied
        """
        # Validate message_id format first
        from app.utils.mongodb_utils import validate_object_id
        try:
            validate_object_id(message_id, "Message ID")
        except ServiceError:
            # Re-raise with clearer context for message update
            raise ServiceError(
                f"Invalid message ID format: {message_id}. Expected MongoDB ObjectId (24-character hex string).",
                ErrorCodes.VALIDATION_ERROR,
                400
            )
        
        # Get message and verify ownership
        message = await self.message_repo.get_message_by_id(message_id)
        if not message:
            raise ServiceError(
                f"Message with ID {message_id} not found or has been deleted",
                ErrorCodes.NOT_FOUND,
                404
            )
        
        if message.sender_id != user_id:
            raise ServiceError(
                "Cannot update message from another user",
                ErrorCodes.AUTHORIZATION_ERROR,
                403
            )
        
        # Update message
        updated_message = await self.message_repo.update_message(
            message_id, message_data, user_id
        )
        
        if not updated_message:
            raise ServiceError(
                f"Failed to update message {message_id}",
                ErrorCodes.UPDATE_ERROR,
                500
            )
        
        return {
            "success": True,
            "message": updated_message,
            "message_text": "Message updated successfully"
        }
    
    @handle_service_errors("delete message")
    async def delete_message(
        self,
        message_id: str,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Delete a message (soft delete).
        
        Args:
            message_id: MongoDB ObjectId string of message to delete
            user_id: User attempting deletion
            
        Returns:
            Success response
            
        Raises:
            ServiceError: If message not found, invalid ID format, or access denied
        """
        # Validate message_id format first
        from app.utils.mongodb_utils import validate_object_id
        try:
            validate_object_id(message_id, "Message ID")
        except ServiceError:
            # Re-raise with clearer context for message deletion
            raise ServiceError(
                f"Invalid message ID format: {message_id}. Expected MongoDB ObjectId (24-character hex string).",
                ErrorCodes.VALIDATION_ERROR,
                400
            )
        
        # Get message and verify ownership
        message = await self.message_repo.get_message_by_id(message_id)
        if not message:
            raise ServiceError(
                f"Message with ID {message_id} not found or has been deleted",
                ErrorCodes.NOT_FOUND,
                404
            )
        
        if message.sender_id != user_id:
            raise ServiceError(
                "Cannot delete message from another user",
                ErrorCodes.AUTHORIZATION_ERROR,
                403
            )
        
        # Soft delete message
        deletion_success = await self.message_repo.soft_delete_message(message_id, user_id)
        
        if not deletion_success:
            raise ServiceError(
                f"Failed to delete message {message_id}. It may have already been deleted.",
                ErrorCodes.DELETION_ERROR,
                500
            )
        
        return {
            "success": True,
            "message_text": "Message deleted successfully",
            "message_id": message_id
        }
    
    @handle_service_errors("get messages")
    async def get_conversation_messages(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        page: int = 1,
        size: int = 50,
        before_message_id: Optional[str] = None,
        after_message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get messages for a conversation with pagination.
        
        Args:
            conversation_id: Target conversation
            user_id: Requesting user
            page: Page number (1-based)
            size: Messages per page
            before_message_id: Get messages before this ID (optional)
            after_message_id: Get messages after this ID (optional)
            
        Returns:
            Paginated message list
            
        Raises:
            ServiceError: If access denied
        """
        # Verify conversation access
        has_access = await self.conversation_repo.can_user_access_conversation(
            conversation_id, user_id
        )
        if not has_access:
            raise ServiceError(
                "Access denied to conversation",
                ErrorCodes.AUTHORIZATION_ERROR,
                403
            )
        
        # Get paginated messages
        messages, total = await self.message_repo.get_conversation_messages(
            conversation_id, page, size, before_message_id, after_message_id
        )
        
        return {
            "success": True,
            "messages": messages,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size
            }
        }
    
    @handle_service_errors("search messages")
    async def search_messages(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        **search_params
    ) -> Dict[str, Any]:
        """
        Search messages in a conversation.
        
        Args:
            conversation_id: Target conversation
            user_id: Requesting user
            **search_params: Search parameters
            
        Returns:
            Search results with pagination
            
        Raises:
            ServiceError: If access denied
        """
        # Import here to avoid circular imports
        from app.models.conversation_models import MessageSearch
        
        # Verify conversation access
        has_access = await self.conversation_repo.can_user_access_conversation(
            conversation_id, user_id
        )
        if not has_access:
            raise ServiceError(
                "Access denied to conversation",
                ErrorCodes.AUTHORIZATION_ERROR,
                403
            )
        
        # Create MessageSearch object from params
        search_obj = MessageSearch(**search_params)
        
        # Search messages
        messages, total = await self.message_repo.search_messages(
            conversation_id, search_obj, user_id
        )
        
        return {
            "success": True,
            "messages": messages,
            "pagination": {
                "total": total,
                "limit": search_obj.limit,
                "offset": search_obj.offset
            }
        } 
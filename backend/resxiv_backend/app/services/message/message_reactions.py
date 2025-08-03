"""
Message Reactions Service - L6 Engineering Standards
Focused on message reactions, read receipts, and interaction features.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.message_repository import MessageRepository
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.models.conversation_models import MessageReactionCreate

logger = logging.getLogger(__name__)


class MessageReactionsService:
    """
    Message reactions and interactions service.
    Single Responsibility: Message reactions, read receipts, interactions.
    """
    
    def __init__(self, session: AsyncSession, message_repo: MessageRepository):
        self.session = session
        self.message_repo = message_repo
    
    @handle_service_errors("add reaction")
    async def add_reaction(
        self,
        message_id: str,
        user_id: uuid.UUID,
        reaction_data: MessageReactionCreate
    ) -> Dict[str, Any]:
        """
        Add a reaction to a message.
        
        Args:
            message_id: Target message
            user_id: User adding reaction
            reaction_data: Reaction type and metadata
            
        Returns:
            Success response with reaction data
            
        Raises:
            ServiceError: If message not found or duplicate reaction
        """
        # Verify message exists
        message = await self.message_repo.get_message_by_id(message_id)
        if not message:
            raise ServiceError(
                "Message not found",
                ErrorCodes.NOT_FOUND,
                404
            )
        
        # Check if user already reacted with this emoji
        existing_reaction = await self.message_repo.get_user_reaction(
            message_id, user_id, reaction_data.emoji
        )
        if existing_reaction:
            raise ServiceError(
                "User already reacted with this emoji",
                ErrorCodes.DUPLICATE_RESOURCE,
                409
            )
        
        # Add reaction
        reaction = await self.message_repo.add_reaction(
            message_id=message_id,
            user_id=user_id,
            emoji=reaction_data.emoji,
            created_at=datetime.utcnow()
        )
        
        return {
            "success": True,
            "reaction": reaction,
            "message_text": "Reaction added successfully"
        }
    
    @handle_service_errors("remove reaction")
    async def remove_reaction(
        self,
        message_id: str,
        user_id: uuid.UUID,
        emoji: str
    ) -> Dict[str, Any]:
        """
        Remove a reaction from a message.
        
        Args:
            message_id: Target message
            user_id: User removing reaction
            emoji: Reaction emoji to remove
            
        Returns:
            Success response
            
        Raises:
            ServiceError: If reaction not found
        """
        # Verify reaction exists
        reaction = await self.message_repo.get_user_reaction(
            message_id, user_id, emoji
        )
        if not reaction:
            raise ServiceError(
                "Reaction not found",
                ErrorCodes.NOT_FOUND,
                404
            )
        
        # Remove reaction
        await self.message_repo.remove_reaction(message_id, user_id, emoji)
        
        return {
            "success": True,
            "message_text": "Reaction removed successfully"
        }
    
    @handle_service_errors("get message reactions")
    async def get_message_reactions(
        self,
        message_id: str
    ) -> Dict[str, Any]:
        """
        Get all reactions for a message.
        
        Args:
            message_id: Target message
            
        Returns:
            Grouped reactions by emoji
            
        Raises:
            ServiceError: If message not found
        """
        # Verify message exists
        message = await self.message_repo.get_message_by_id(message_id)
        if not message:
            raise ServiceError(
                "Message not found",
                ErrorCodes.NOT_FOUND,
                404
            )
        
        # Get reactions grouped by emoji
        reactions = await self.message_repo.get_message_reactions(message_id)
        
        # Group reactions by emoji
        grouped_reactions = {}
        for reaction in reactions:
            emoji = reaction.emoji
            if emoji not in grouped_reactions:
                grouped_reactions[emoji] = {
                    "emoji": emoji,
                    "count": 0,
                    "users": []
                }
            grouped_reactions[emoji]["count"] += 1
            grouped_reactions[emoji]["users"].append({
                "user_id": str(reaction.user_id),
                "created_at": reaction.created_at.isoformat()
            })
        
        return {
            "success": True,
            "message_id": str(message_id),
            "reactions": list(grouped_reactions.values()),
            "total_reactions": len(reactions)
        }
    
    @handle_service_errors("add read receipt")
    async def add_read_receipt(
        self,
        message_id: str,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Add read receipt for a message.
        
        Args:
            message_id: Message being read
            user_id: User reading the message
            
        Returns:
            Success response
        """
        # Add read receipt
        await self.message_repo.add_read_receipt(
            message_id=message_id,
            user_id=user_id,
            read_at=datetime.utcnow()
        )
        
        return {
            "success": True,
            "message_text": "Read receipt added"
        }
    
    @handle_service_errors("get read receipts")
    async def get_read_receipts(
        self,
        message_id: str
    ) -> Dict[str, Any]:
        """
        Get read receipts for a message.
        
        Args:
            message_id: Target message
            
        Returns:
            List of read receipts
            
        Raises:
            ServiceError: If message not found
        """
        # Verify message exists
        message = await self.message_repo.get_message_by_id(message_id)
        if not message:
            raise ServiceError(
                "Message not found",
                ErrorCodes.NOT_FOUND,
                404
            )
        
        # Get read receipts
        receipts = await self.message_repo.get_read_receipts(message_id)
        
        return {
            "success": True,
            "message_id": str(message_id),
            "read_receipts": [
                {
                    "user_id": str(receipt.user_id),
                    "read_at": receipt.read_at.isoformat()
                }
                for receipt in receipts
            ],
            "read_count": len(receipts)
        } 
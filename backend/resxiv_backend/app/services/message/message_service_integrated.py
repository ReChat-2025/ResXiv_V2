"""
Integrated Message Service - L6 Engineering Standards
Orchestrates core, real-time, and reactions services for unified message handling.
"""

import uuid
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import DatabaseManager
from app.services.redis_service import RedisService
from app.repositories.message_repository import MessageRepository
from app.services.message.message_core import MessageCoreService
from app.services.message.message_realtime import MessageRealtimeService
from app.services.message.message_reactions import MessageReactionsService
from app.core.error_handling import handle_service_errors
from app.models.conversation_models import (
    MessageCreate, MessageUpdate, MessageReactionCreate
)

logger = logging.getLogger(__name__)


class MessageService:
    """
    Integrated message service orchestrating specialized sub-services.
    
    Follows Composition over Inheritance principle with clean separation:
    - Core service: CRUD operations
    - Realtime service: WebSocket/Redis operations  
    - Reactions service: Interactions and reactions
    
    Single point of access for all message operations while maintaining
    focused, testable components.
    """
    
    def __init__(
        self, 
        session: AsyncSession, 
        db_manager: DatabaseManager, 
        redis_service: RedisService
    ):
        self.session = session
        self.db_manager = db_manager
        self.redis_service = redis_service
        
        # Initialize repositories
        self.message_repo = MessageRepository(db_manager)
        
        # Initialize specialized services
        self.core_service = MessageCoreService(session, self.message_repo)
        self.realtime_service = MessageRealtimeService(redis_service)
        self.reactions_service = MessageReactionsService(session, self.message_repo)
    
    # ================================
    # UNIFIED MESSAGE OPERATIONS
    # ================================
    
    @handle_service_errors("create message with real-time")
    async def create_message(
        self,
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID,
        message_data: MessageCreate,
        sender_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create message with real-time publishing.
        Orchestrates core creation + real-time delivery.
        """
        # Create message via core service
        result = await self.core_service.create_message(
            conversation_id, sender_id, message_data, sender_name
        )
        
        if result["success"]:
            # Publish to real-time subscribers
            await self.realtime_service.publish_message(
                conversation_id, result["message"]
            )
            
            # Update unread counts
            await self.realtime_service.update_unread_counts(
                conversation_id, sender_id
            )
        
        return result
    
    # ================================
    # DELEGATED OPERATIONS
    # ================================
    
    # Core operations
    async def update_message(self, message_id: str, user_id: uuid.UUID, message_data: MessageUpdate):
        return await self.core_service.update_message(message_id, user_id, message_data)
    
    async def delete_message(self, message_id: str, user_id: uuid.UUID):
        return await self.core_service.delete_message(message_id, user_id)
    
    async def get_conversation_messages(
        self, 
        conversation_id: uuid.UUID, 
        user_id: uuid.UUID, 
        page: int = 1, 
        size: int = 50,
        before_message_id: Optional[str] = None,
        after_message_id: Optional[str] = None
    ):
        return await self.core_service.get_conversation_messages(
            conversation_id, user_id, page, size, before_message_id, after_message_id
        )
    
    async def search_messages(self, conversation_id: uuid.UUID, user_id: uuid.UUID, **search_params):
        return await self.core_service.search_messages(conversation_id, user_id, **search_params)
    
    # Real-time operations
    async def update_typing_status(self, conversation_id: uuid.UUID, user_id: uuid.UUID, is_typing: bool):
        return await self.realtime_service.update_typing_status(conversation_id, user_id, is_typing)
    
    async def update_online_status(self, user_id: uuid.UUID, is_online: bool):
        return await self.realtime_service.update_online_status(user_id, is_online)
    
    async def mark_messages_read(self, conversation_id: uuid.UUID, user_id: uuid.UUID, message_ids: Optional[List[str]] = None):
        return await self.realtime_service.mark_messages_read(conversation_id, user_id, message_ids)
    
    async def get_conversation_status(self, conversation_id: uuid.UUID):
        return await self.realtime_service.get_conversation_status(conversation_id)
    
    # Reaction operations
    async def add_reaction(self, message_id: str, user_id: uuid.UUID, reaction_data: MessageReactionCreate):
        return await self.reactions_service.add_reaction(message_id, user_id, reaction_data)
    
    async def remove_reaction(self, message_id: str, user_id: uuid.UUID, emoji: str):
        return await self.reactions_service.remove_reaction(message_id, user_id, emoji)
    
    async def get_message_reactions(self, message_id: str):
        return await self.reactions_service.get_message_reactions(message_id)
    
    async def add_read_receipt(self, message_id: str, user_id: uuid.UUID):
        return await self.reactions_service.add_read_receipt(message_id, user_id)
    
    # Convenience methods for endpoint compatibility
    async def add_message_reaction(self, message_id: str, user_id: uuid.UUID, reaction_data: MessageReactionCreate):
        return await self.add_reaction(message_id, user_id, reaction_data)
    
    async def remove_message_reaction(self, message_id: str, user_id: uuid.UUID, emoji: str):
        return await self.remove_reaction(message_id, user_id, emoji)
    
    async def mark_message_as_read(self, message_id: str, user_id: uuid.UUID):
        return await self.mark_messages_read(None, user_id, [message_id])
    
    async def mark_conversation_as_read(self, conversation_id: uuid.UUID, user_id: uuid.UUID):
        return await self.mark_messages_read(conversation_id, user_id, None)
    
    async def get_read_receipts(self, message_id: str):
        return await self.reactions_service.get_read_receipts(message_id) 
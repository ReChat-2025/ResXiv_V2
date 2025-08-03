"""
Message Real-time Service - L6 Engineering Standards
Focused on real-time messaging features: WebSocket, Redis pub/sub, typing indicators.
"""

import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from app.services.redis_service import RedisService
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.models.conversation_models import (
    MessageResponse, TypingIndicator, OnlineStatus, WebSocketMessage
)

logger = logging.getLogger(__name__)


class MessageRealtimeService:
    """
    Real-time messaging service for WebSocket and Redis operations.
    Single Responsibility: Real-time message delivery and status updates.
    """
    
    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service
    
    @handle_service_errors("publish message")
    async def publish_message(
        self,
        conversation_id: uuid.UUID,
        message: MessageResponse
    ) -> Dict[str, Any]:
        """
        Publish message to real-time subscribers.
        
        Args:
            conversation_id: Target conversation
            message: Message to publish
            
        Returns:
            Success response
        """
        await self.redis_service.publish_message(conversation_id, message)
        await self._cache_recent_messages(conversation_id)
        
        return {
            "success": True,
            "message_text": "Message published successfully"
        }
    
    @handle_service_errors("update typing status")
    async def update_typing_status(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        is_typing: bool
    ) -> Dict[str, Any]:
        """
        Update user typing status in conversation.
        
        Args:
            conversation_id: Target conversation
            user_id: User changing typing status
            is_typing: Whether user is typing
            
        Returns:
            Success response
        """
        typing_indicator = TypingIndicator(
            conversation_id=conversation_id,
            user_id=user_id,
            is_typing=is_typing,
            timestamp=datetime.utcnow()
        )
        
        await self.redis_service.set_typing_status(typing_indicator)
        
        return {
            "success": True,
            "message_text": f"Typing status updated: {is_typing}"
        }
    
    @handle_service_errors("update online status")
    async def update_online_status(
        self,
        user_id: uuid.UUID,
        is_online: bool
    ) -> Dict[str, Any]:
        """
        Update user online status.
        
        Args:
            user_id: User to update
            is_online: Whether user is online
            
        Returns:
            Success response
        """
        status = OnlineStatus(
            user_id=user_id,
            is_online=is_online,
            last_seen=datetime.utcnow()
        )
        
        await self.redis_service.set_user_online_status(status)
        
        return {
            "success": True,
            "message_text": f"Online status updated: {is_online}"
        }
    
    @handle_service_errors("update unread counts")
    async def update_unread_counts(
        self,
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Update unread message counts for conversation participants.
        
        Args:
            conversation_id: Target conversation
            sender_id: Message sender (excluded from count)
            
        Returns:
            Success response
        """
        # Get conversation participants
        participants = await self.redis_service.get_conversation_participants(
            conversation_id
        )
        
        # Update unread counts for all except sender
        for participant_id in participants:
            if participant_id != sender_id:
                await self.redis_service.increment_unread_count(
                    conversation_id, participant_id
                )
        
        return {
            "success": True,
            "message_text": "Unread counts updated"
        }
    
    @handle_service_errors("mark messages read")
    async def mark_messages_read(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        message_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Mark messages as read for a user.
        
        Args:
            conversation_id: Target conversation
            user_id: User marking messages as read
            message_ids: Specific messages to mark (optional)
            
        Returns:
            Success response
        """
        if message_ids:
            # Mark specific messages as read
            for message_id in message_ids:
                await self.redis_service.mark_message_read(
                    conversation_id, user_id, message_id
                )
        else:
            # Mark all messages in conversation as read
            await self.redis_service.clear_unread_count(conversation_id, user_id)
        
        return {
            "success": True,
            "message_text": "Messages marked as read"
        }
    
    @handle_service_errors("get conversation status")
    async def get_conversation_status(
        self,
        conversation_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get real-time status for conversation (typing, online users).
        
        Args:
            conversation_id: Target conversation
            
        Returns:
            Conversation status data
        """
        # Get typing indicators
        typing_users = await self.redis_service.get_typing_users(conversation_id)
        
        # Get online participants
        participants = await self.redis_service.get_conversation_participants(
            conversation_id
        )
        online_users = []
        for user_id in participants:
            is_online = await self.redis_service.is_user_online(user_id)
            if is_online:
                online_users.append(user_id)
        
        return {
            "success": True,
            "conversation_id": str(conversation_id),
            "typing_users": [str(uid) for uid in typing_users],
            "online_users": [str(uid) for uid in online_users],
            "total_participants": len(participants)
        }
    
    async def _cache_recent_messages(
        self,
        conversation_id: uuid.UUID,
        limit: int = 50
    ) -> None:
        """Cache recent messages for faster retrieval."""
        # This would typically get messages from the message repository
        # and cache them in Redis for quick access
        await self.redis_service.cache_recent_messages(conversation_id, limit) 
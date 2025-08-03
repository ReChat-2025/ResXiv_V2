"""
Redis Service for Real-time Messaging

This service handles Redis operations for real-time chat features including:
- Message caching and pub/sub
- WebSocket connection management  
- User online status tracking
- Typing indicators
- Message read receipts
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
import redis.asyncio as redis
import logging

from app.database.connection import DatabaseManager
from app.models.conversation_models import (
    TypingIndicator, 
    OnlineStatus, 
    WebSocketMessage,
    MessageResponse
)

logger = logging.getLogger(__name__)


class RedisService:
    """
    Redis service for real-time chat operations.
    
    Provides methods for:
    - Publishing/subscribing to real-time events
    - Managing user online status
    - Caching conversation data
    - WebSocket connection tracking
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.redis_client = db_manager.redis_client
        
        # Redis key prefixes
        self.CONVERSATION_PREFIX = "conversation:"
        self.USER_ONLINE_PREFIX = "user:online:"
        self.TYPING_PREFIX = "typing:"
        self.WEBSOCKET_PREFIX = "ws:connections:"
        self.MESSAGE_CACHE_PREFIX = "messages:"
        self.UNREAD_COUNT_PREFIX = "unread:"
        
        # Default expiration times
        self.USER_ONLINE_TTL = 300  # 5 minutes
        self.TYPING_TTL = 10  # 10 seconds
        self.MESSAGE_CACHE_TTL = 3600  # 1 hour
    
    # ================================
    # REAL-TIME MESSAGING
    # ================================
    
    async def publish_message(self, conversation_id: uuid.UUID, message: MessageResponse) -> None:
        """
        Publish new message to conversation subscribers.
        
        Args:
            conversation_id: Conversation UUID
            message: Message data to publish
        """
        try:
            channel = f"{self.CONVERSATION_PREFIX}{conversation_id}"
            message_data = {
                "type": "message",
                "data": message.dict(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.redis_client.publish(channel, json.dumps(message_data, default=str))
            logger.debug(f"Published message to channel {channel}")
            
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
    
    async def subscribe_to_conversation(self, conversation_id: uuid.UUID):
        """
        Subscribe to conversation updates.
        
        Args:
            conversation_id: Conversation UUID
            
        Returns:
            Redis pubsub object for listening to messages
        """
        try:
            pubsub = self.redis_client.pubsub()
            channel = f"{self.CONVERSATION_PREFIX}{conversation_id}"
            await pubsub.subscribe(channel)
            return pubsub
            
        except Exception as e:
            logger.error(f"Error subscribing to conversation {conversation_id}: {e}")
            return None
    
    async def publish_typing_indicator(self, typing_data: TypingIndicator) -> None:
        """
        Publish typing indicator to conversation.
        
        Args:
            typing_data: Typing indicator data
        """
        try:
            channel = f"{self.CONVERSATION_PREFIX}{typing_data.conversation_id}"
            message_data = {
                "type": "typing",
                "data": typing_data.dict(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.redis_client.publish(channel, json.dumps(message_data, default=str))
            
            # Cache typing status temporarily
            typing_key = f"{self.TYPING_PREFIX}{typing_data.conversation_id}:{typing_data.user_id}"
            if typing_data.is_typing:
                await self.redis_client.setex(typing_key, self.TYPING_TTL, "1")
            else:
                await self.redis_client.delete(typing_key)
                
        except Exception as e:
            logger.error(f"Error publishing typing indicator: {e}")
    
    async def publish_reaction(self, conversation_id: uuid.UUID, message_id: str, reaction_data: Dict[str, Any]) -> None:
        """
        Publish message reaction to conversation.
        
        Args:
            conversation_id: Conversation UUID
            message_id: Message ID
            reaction_data: Reaction data
        """
        try:
            channel = f"{self.CONVERSATION_PREFIX}{conversation_id}"
            message_data = {
                "type": "reaction",
                "data": {
                    "message_id": message_id,
                    "reaction": reaction_data
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.redis_client.publish(channel, json.dumps(message_data, default=str))
            
        except Exception as e:
            logger.error(f"Error publishing reaction: {e}")
    
    # ================================
    # USER ONLINE STATUS
    # ================================
    
    async def set_user_online(self, user_id: uuid.UUID, username: str) -> None:
        """
        Mark user as online.
        
        Args:
            user_id: User UUID
            username: Username for display
        """
        try:
            key = f"{self.USER_ONLINE_PREFIX}{user_id}"
            user_data = {
                "user_id": str(user_id),
                "username": username,
                "last_seen": datetime.utcnow().isoformat(),
                "is_online": True
            }
            
            await self.redis_client.setex(key, self.USER_ONLINE_TTL, json.dumps(user_data, default=str))
            
        except Exception as e:
            logger.error(f"Error setting user online status: {e}")
    
    async def set_user_offline(self, user_id: uuid.UUID) -> None:
        """
        Mark user as offline.
        
        Args:
            user_id: User UUID
        """
        try:
            key = f"{self.USER_ONLINE_PREFIX}{user_id}"
            await self.redis_client.delete(key)
            
        except Exception as e:
            logger.error(f"Error setting user offline: {e}")
    
    async def get_user_online_status(self, user_id: uuid.UUID) -> Optional[OnlineStatus]:
        """
        Get user online status.
        
        Args:
            user_id: User UUID
            
        Returns:
            OnlineStatus object or None
        """
        try:
            key = f"{self.USER_ONLINE_PREFIX}{user_id}"
            user_data = await self.redis_client.get(key)
            
            if user_data:
                data = json.loads(user_data)
                return OnlineStatus(
                    user_id=user_id,
                    is_online=True,
                    last_seen=datetime.fromisoformat(data["last_seen"])
                )
            else:
                return OnlineStatus(
                    user_id=user_id,
                    is_online=False,
                    last_seen=None
                )
                
        except Exception as e:
            logger.error(f"Error getting user online status: {e}")
            return None
    
    async def get_online_users_in_conversation(self, conversation_id: uuid.UUID, user_ids: List[uuid.UUID]) -> List[OnlineStatus]:
        """
        Get online status for multiple users in a conversation.
        
        Args:
            conversation_id: Conversation UUID
            user_ids: List of user UUIDs
            
        Returns:
            List of OnlineStatus objects
        """
        try:
            statuses = []
            for user_id in user_ids:
                status = await self.get_user_online_status(user_id)
                if status:
                    statuses.append(status)
            
            return statuses
            
        except Exception as e:
            logger.error(f"Error getting online users: {e}")
            return []
    
    # ================================
    # WEBSOCKET CONNECTION MANAGEMENT
    # ================================
    
    async def add_websocket_connection(self, user_id: uuid.UUID, conversation_id: uuid.UUID, connection_id: str) -> None:
        """
        Track WebSocket connection for user.
        
        Args:
            user_id: User UUID
            conversation_id: Conversation UUID
            connection_id: Unique connection identifier
        """
        try:
            # Track user connections
            user_key = f"{self.WEBSOCKET_PREFIX}user:{user_id}"
            await self.redis_client.sadd(user_key, connection_id)
            await self.redis_client.expire(user_key, self.USER_ONLINE_TTL)
            
            # Track conversation connections
            conv_key = f"{self.WEBSOCKET_PREFIX}conversation:{conversation_id}"
            connection_data = {
                "user_id": str(user_id),
                "connection_id": connection_id,
                "connected_at": datetime.utcnow().isoformat()
            }
            await self.redis_client.sadd(conv_key, json.dumps(connection_data, default=str))
            await self.redis_client.expire(conv_key, self.USER_ONLINE_TTL)
            
        except Exception as e:
            logger.error(f"Error adding WebSocket connection: {e}")
    
    async def remove_websocket_connection(self, user_id: uuid.UUID, conversation_id: uuid.UUID, connection_id: str) -> None:
        """
        Remove WebSocket connection tracking.
        
        Args:
            user_id: User UUID
            conversation_id: Conversation UUID
            connection_id: Connection identifier
        """
        try:
            # Remove from user connections
            user_key = f"{self.WEBSOCKET_PREFIX}user:{user_id}"
            await self.redis_client.srem(user_key, connection_id)
            
            # Remove from conversation connections
            conv_key = f"{self.WEBSOCKET_PREFIX}conversation:{conversation_id}"
            # Get all connections and remove the matching one
            connections = await self.redis_client.smembers(conv_key)
            for conn_data in connections:
                try:
                    conn_info = json.loads(conn_data)
                    if conn_info["connection_id"] == connection_id:
                        await self.redis_client.srem(conv_key, conn_data)
                        break
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            logger.error(f"Error removing WebSocket connection: {e}")
    
    # ================================
    # MESSAGE CACHING
    # ================================
    
    async def cache_recent_messages(self, conversation_id: uuid.UUID, messages: List[MessageResponse], limit: int = 50) -> None:
        """
        Cache recent messages for faster loading.
        
        Args:
            conversation_id: Conversation UUID
            messages: List of messages to cache
            limit: Maximum number of messages to cache
        """
        try:
            key = f"{self.MESSAGE_CACHE_PREFIX}{conversation_id}"
            
            # Store as sorted set with timestamp as score
            pipe = self.redis_client.pipeline()
            
            for message in messages[-limit:]:  # Keep only recent messages
                score = message.timestamp.timestamp()
                value = json.dumps(message.dict(), default=str)
                pipe.zadd(key, {value: score})
            
            pipe.expire(key, self.MESSAGE_CACHE_TTL)
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Error caching messages: {e}")
    
    async def get_cached_messages(self, conversation_id: uuid.UUID, limit: int = 50) -> List[MessageResponse]:
        """
        Get cached recent messages.
        
        Args:
            conversation_id: Conversation UUID
            limit: Maximum number of messages to return
            
        Returns:
            List of cached messages
        """
        try:
            key = f"{self.MESSAGE_CACHE_PREFIX}{conversation_id}"
            
            # Get recent messages (highest scores = most recent)
            cached_data = await self.redis_client.zrevrange(key, 0, limit - 1)
            
            messages = []
            for data in cached_data:
                try:
                    message_dict = json.loads(data)
                    message = MessageResponse(**message_dict)
                    messages.append(message)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Error parsing cached message: {e}")
                    continue
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting cached messages: {e}")
            return []
    
    # ================================
    # UNREAD COUNTS
    # ================================
    
    async def increment_unread_count(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        Increment unread message count for user.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User UUID
        """
        try:
            key = f"{self.UNREAD_COUNT_PREFIX}{user_id}:{conversation_id}"
            await self.redis_client.incr(key)
            await self.redis_client.expire(key, 86400)  # 24 hours
            
        except Exception as e:
            logger.error(f"Error incrementing unread count: {e}")
    
    async def reset_unread_count(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        Reset unread message count for user.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User UUID
        """
        try:
            key = f"{self.UNREAD_COUNT_PREFIX}{user_id}:{conversation_id}"
            await self.redis_client.delete(key)
            
        except Exception as e:
            logger.error(f"Error resetting unread count: {e}")
    
    async def get_unread_count(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> int:
        """
        Get unread message count for user.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User UUID
            
        Returns:
            Number of unread messages
        """
        try:
            key = f"{self.UNREAD_COUNT_PREFIX}{user_id}:{conversation_id}"
            count = await self.redis_client.get(key)
            return int(count) if count else 0
            
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")

    # ================================
    # PARTICIPANTS (Fallback placeholder)
    # ================================

    async def get_conversation_participants(self, conversation_id: uuid.UUID) -> List[str]:
        """Return participant user IDs for a conversation.

        NOTE: Proper implementation should query a set in Redis populated elsewhere. For now,
        return an empty list so that higher-level services do not fail.
        """
        try:
            key = f"{self.CONVERSATION_PREFIX}{conversation_id}:participants"
            if await self.redis_client.exists(key):
                members = await self.redis_client.smembers(key)
                return [m.decode() if isinstance(m, bytes) else str(m) for m in members]
            return []
        except Exception as e:
            logger.error(f"Error getting conversation participants: {e}")
            return [] 
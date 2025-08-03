"""
Message Repository

This module handles all MongoDB operations for messages and conversation metadata.
Provides CRUD operations, search functionality, and message analytics.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import logging
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
import pymongo

from app.database.connection import DatabaseManager
from app.models.conversation_models import (
    MessageResponse,
    MessageCreate,
    MessageUpdate,
    MessageSearch,
    MessageType,
    MessageReaction,
    MessageReadStatus,
    MessageMetadata
)

logger = logging.getLogger(__name__)


class MessageRepository:
    """
    Repository for message operations in MongoDB.
    
    Handles:
    - Message CRUD operations
    - Message search and filtering
    - Conversation metadata management
    - Message analytics and aggregations
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.db: AsyncIOMotorDatabase = db_manager.mongodb_database
        self.messages: AsyncIOMotorCollection = self.db.messages
        self.conversation_metadata: AsyncIOMotorCollection = self.db.conversation_metadata
    
    # ================================
    # MESSAGE CRUD OPERATIONS
    # ================================
    
    async def create_message(
        self,
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID,
        message_data: MessageCreate,
        sender_name: Optional[str] = None
    ) -> MessageResponse:
        """
        Create a new message in the conversation.
        
        Args:
            conversation_id: Conversation UUID
            sender_id: Sender user UUID
            message_data: Message creation data
            sender_name: Sender's display name
            
        Returns:
            Created message response
        """
        now = datetime.utcnow()
        
        # Prepare message document
        message_doc = {
            "conversation_id": str(conversation_id),
            "sender_id": str(sender_id),
            "message": message_data.content,
            "message_type": message_data.message_type.value,
            "reply_to": ObjectId(message_data.parent_message_id) if message_data.parent_message_id else None,
            "edited_at": None,
            "deleted_by": [],
            "read_by": [],
            "reactions": [],
            "metadata": message_data.metadata.dict() if message_data.metadata else {},
            "timestamp": now,
            "created_at": now,
            "updated_at": now
        }
        
        # Insert message
        result = await self.messages.insert_one(message_doc)
        
        # Update conversation metadata
        await self._update_conversation_metadata(conversation_id, message_data.content, sender_id, now)
        
        # Return response
        return MessageResponse(
            id=str(result.inserted_id),
            conversation_id=conversation_id,
            sender_id=sender_id,
            sender_name=sender_name,
            message=message_data.content,
            message_type=message_data.message_type,
            reply_to=message_data.parent_message_id,
            metadata=message_data.metadata,
            timestamp=now,
            created_at=now,
            updated_at=now
        )
    
    async def get_message_by_id(self, message_id: str) -> Optional[MessageResponse]:
        """
        Get message by MongoDB ObjectId.
        
        Args:
            message_id: Message ObjectId as string
            
        Returns:
            Message response or None if not found
        """
        try:
            message_doc = await self.messages.find_one({"_id": ObjectId(message_id)})
            if message_doc:
                return self._doc_to_message_response(message_doc)
            return None
        except Exception as e:
            logger.error(f"Error getting message by ID: {e}")
            return None
    
    async def update_message(
        self,
        message_id: str,
        update_data: MessageUpdate,
        updated_by: uuid.UUID
    ) -> Optional[MessageResponse]:
        """
        Update an existing message.
        
        Args:
            message_id: Message ObjectId as string
            update_data: Update data
            updated_by: User performing the update
            
        Returns:
            Updated message response or None if not found
        """
        try:
            update_fields = {}
            
            if update_data.message is not None:
                update_fields["message"] = update_data.message
                update_fields["edited_at"] = datetime.utcnow()
            
            if update_data.metadata is not None:
                update_fields["metadata"] = update_data.metadata.dict()
            
            update_fields["updated_at"] = datetime.utcnow()
            
            result = await self.messages.update_one(
                {"_id": ObjectId(message_id)},
                {"$set": update_fields}
            )
            
            if result.modified_count > 0:
                return await self.get_message_by_id(message_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating message: {e}")
            return None
    
    async def soft_delete_message(self, message_id: str, deleted_by: uuid.UUID) -> bool:
        """
        Soft delete a message by adding user to deleted_by list.
        
        Args:
            message_id: Message ObjectId as string
            deleted_by: User who deleted the message
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.messages.update_one(
                {"_id": ObjectId(message_id)},
                {
                    "$addToSet": {"deleted_by": str(deleted_by)},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error soft deleting message: {e}")
            return False
    
    async def hard_delete_message(self, message_id: str) -> bool:
        """
        Permanently delete a message.
        
        Args:
            message_id: Message ObjectId as string
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.messages.delete_one({"_id": ObjectId(message_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error hard deleting message: {e}")
            return False
    
    # ================================
    # MESSAGE QUERIES
    # ================================
    
    async def get_conversation_messages(
        self,
        conversation_id: uuid.UUID,
        page: int = 1,
        size: int = 50,
        before_message_id: Optional[str] = None,
        after_message_id: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> Tuple[List[MessageResponse], int]:
        """
        Get messages from a conversation with pagination.
        
        Args:
            conversation_id: Conversation UUID
            page: Page number (1-based)
            size: Maximum number of messages per page
            before_message_id: Get messages before this message ID (for pagination)
            after_message_id: Get messages after this message ID (for pagination)
            user_id: Filter out messages deleted by this user
            
        Returns:
            Tuple of (List of message responses, total count)
        """
        try:
            # Build query
            query = {"conversation_id": str(conversation_id)}
            
            # Exclude messages deleted by the requesting user
            if user_id:
                query["deleted_by"] = {"$ne": str(user_id)}
            
            # Add pagination filters
            if before_message_id:
                query["_id"] = {"$lt": ObjectId(str(before_message_id))}
            
            if after_message_id:
                query["_id"] = {"$gt": ObjectId(str(after_message_id))}
            
            # Get total count
            total_count = await self.messages.count_documents(query)
            
            # Calculate pagination
            skip = (page - 1) * size
            
            # Execute query with sorting, skip, and limit
            cursor = self.messages.find(query).sort("_id", -1).skip(skip).limit(size)
            messages = await cursor.to_list(length=size)
            
            # Convert to response objects
            message_responses = []
            for message_doc in messages:
                response = self._doc_to_message_response(message_doc)
                if response:
                    message_responses.append(response)
            
            # Return in chronological order (oldest first)
            return list(reversed(message_responses)), total_count
            
        except Exception as e:
            logger.error(f"Error getting conversation messages: {e}")
            return [], 0
    
    async def search_messages(
        self,
        conversation_id: uuid.UUID,
        search_params: MessageSearch,
        user_id: Optional[uuid.UUID] = None
    ) -> Tuple[List[MessageResponse], int]:
        """
        Search messages in a conversation.
        
        Args:
            conversation_id: Conversation UUID
            search_params: Search parameters
            user_id: Filter out messages deleted by this user
            
        Returns:
            Tuple of (messages, total_count)
        """
        try:
            # Build query
            query = {"conversation_id": str(conversation_id)}
            
            # Exclude messages deleted by the requesting user
            if user_id:
                query["deleted_by"] = {"$ne": str(user_id)}
            
            # Add search filters
            if search_params.query:
                query["message"] = {"$regex": search_params.query, "$options": "i"}
            
            if search_params.message_type:
                query["message_type"] = search_params.message_type.value
            
            if search_params.sender_id:
                query["sender_id"] = str(search_params.sender_id)
            
            if search_params.start_date or search_params.end_date:
                date_filter = {}
                if search_params.start_date:
                    date_filter["$gte"] = search_params.start_date
                if search_params.end_date:
                    date_filter["$lte"] = search_params.end_date
                query["timestamp"] = date_filter
            
            # Get total count
            total_count = await self.messages.count_documents(query)
            
            # Execute search with pagination
            cursor = (
                self.messages
                .find(query)
                .sort("timestamp", -1)
                .skip(search_params.offset)
                .limit(search_params.limit)
            )
            
            messages = await cursor.to_list(length=search_params.limit)
            
            # Convert to response objects
            message_responses = []
            for message_doc in messages:
                response = self._doc_to_message_response(message_doc)
                if response:
                    message_responses.append(response)
            
            return message_responses, total_count
            
        except Exception as e:
            logger.error(f"Error searching messages: {e}")
            return [], 0
    
    # ================================
    # MESSAGE REACTIONS
    # ================================
    
    async def add_reaction(
        self,
        message_id: str,
        user_id: uuid.UUID,
        emoji: str
    ) -> bool:
        """
        Add or update a reaction to a message.
        
        Args:
            message_id: Message ObjectId as string
            user_id: User adding the reaction
            emoji: Emoji string
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove existing reaction from this user first
            await self.messages.update_one(
                {"_id": ObjectId(message_id)},
                {"$pull": {"reactions": {"user_id": str(user_id)}}}
            )
            
            # Add new reaction
            reaction = {
                "user_id": str(user_id),
                "emoji": emoji,
                "created_at": datetime.utcnow()
            }
            
            result = await self.messages.update_one(
                {"_id": ObjectId(message_id)},
                {
                    "$push": {"reactions": reaction},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error adding reaction: {e}")
            return False
    
    async def remove_reaction(self, message_id: str, user_id: uuid.UUID) -> bool:
        """
        Remove a user's reaction from a message.
        
        Args:
            message_id: Message ObjectId as string
            user_id: User removing the reaction
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = await self.messages.update_one(
                {"_id": ObjectId(message_id)},
                {
                    "$pull": {"reactions": {"user_id": str(user_id)}},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error removing reaction: {e}")
            return False
    
    # ================================
    # READ RECEIPTS
    # ================================
    
    async def mark_message_read(self, message_id: str, user_id: uuid.UUID) -> bool:
        """
        Mark a message as read by a user.
        
        Args:
            message_id: Message ObjectId as string
            user_id: User marking as read
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove existing read status for this user
            await self.messages.update_one(
                {"_id": ObjectId(message_id)},
                {"$pull": {"read_by": {"user_id": str(user_id)}}}
            )
            
            # Add new read status
            read_status = {
                "user_id": str(user_id),
                "read_at": datetime.utcnow()
            }
            
            result = await self.messages.update_one(
                {"_id": ObjectId(message_id)},
                {
                    "$push": {"read_by": read_status},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error marking message as read: {e}")
            return False
    
    async def mark_conversation_read(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        up_to_message_id: Optional[str] = None
    ) -> int:
        """
        Mark all messages in conversation as read by user.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User marking as read
            up_to_message_id: Mark messages up to this ID (optional)
            
        Returns:
            Number of messages marked as read
        """
        try:
            # Build query
            query = {
                "conversation_id": str(conversation_id),
                "sender_id": {"$ne": str(user_id)},  # Don't mark own messages as read
                "read_by.user_id": {"$ne": str(user_id)}  # Only unread messages
            }
            
            if up_to_message_id:
                query["_id"] = {"$lte": ObjectId(up_to_message_id)}
            
            # Get all unread messages
            unread_messages = await self.messages.find(query, {"_id": 1}).to_list(length=None)
            
            if not unread_messages:
                return 0
            
            # Mark all as read
            read_status = {
                "user_id": str(user_id),
                "read_at": datetime.utcnow()
            }
            
            message_ids = [msg["_id"] for msg in unread_messages]
            
            result = await self.messages.update_many(
                {"_id": {"$in": message_ids}},
                {
                    "$push": {"read_by": read_status},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Error marking conversation as read: {e}")
            return 0
    
    # ================================
    # CONVERSATION METADATA
    # ================================
    
    async def _update_conversation_metadata(
        self,
        conversation_id: uuid.UUID,
        last_message: str,
        sender_id: uuid.UUID,
        timestamp: datetime
    ) -> None:
        """
        Update conversation metadata after new message.
        
        Args:
            conversation_id: Conversation UUID
            last_message: Last message text
            sender_id: Message sender UUID
            timestamp: Message timestamp
        """
        try:
            metadata_doc = {
                "_id": str(conversation_id),
                "last_message": {
                    "text": last_message[:100],  # Truncate for storage
                    "sender_id": str(sender_id),
                    "timestamp": timestamp
                },
                "updated_at": timestamp
            }
            
            await self.conversation_metadata.update_one(
                {"_id": str(conversation_id)},
                {
                    "$set": metadata_doc,
                    "$inc": {"message_count": 1}
                },
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Error updating conversation metadata: {e}")
    
    async def get_conversation_metadata(self, conversation_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get conversation metadata.
        
        Args:
            conversation_id: Conversation UUID
            
        Returns:
            Metadata dictionary or None
        """
        try:
            return await self.conversation_metadata.find_one({"_id": str(conversation_id)})
        except Exception as e:
            logger.error(f"Error getting conversation metadata: {e}")
            return None
    
    # ================================
    # ANALYTICS
    # ================================
    
    async def get_message_count(
        self,
        conversation_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Get message count for a conversation within date range.
        
        Args:
            conversation_id: Conversation UUID
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            
        Returns:
            Number of messages
        """
        try:
            query = {"conversation_id": str(conversation_id)}
            
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter["$gte"] = start_date
                if end_date:
                    date_filter["$lte"] = end_date
                query["timestamp"] = date_filter
            
            return await self.messages.count_documents(query)
            
        except Exception as e:
            logger.error(f"Error getting message count: {e}")
            return 0
    
    async def get_user_message_count(
        self,
        user_id: uuid.UUID,
        conversation_id: Optional[uuid.UUID] = None,
        days: int = 30
    ) -> int:
        """
        Get message count for a user within specified days.
        
        Args:
            user_id: User UUID
            conversation_id: Specific conversation (optional)
            days: Number of days to look back
            
        Returns:
            Number of messages sent by user
        """
        try:
            query = {
                "sender_id": str(user_id),
                "timestamp": {"$gte": datetime.utcnow() - timedelta(days=days)}
            }
            
            if conversation_id:
                query["conversation_id"] = str(conversation_id)
            
            return await self.messages.count_documents(query)
            
        except Exception as e:
            logger.error(f"Error getting user message count: {e}")
            return 0
    
    # ================================
    # HELPER METHODS
    # ================================
    
    def _doc_to_message_response(self, message_doc: Dict[str, Any]) -> Optional[MessageResponse]:
        """
        Convert MongoDB document to MessageResponse.
        
        Args:
            message_doc: MongoDB message document
            
        Returns:
            MessageResponse object or None if conversion fails
        """
        try:
            # Check required fields
            if not message_doc.get("sender_id"):
                logger.warning(f"Message document missing sender_id: {message_doc.get('_id')}")
                return None
            
            if not message_doc.get("conversation_id"):
                logger.warning(f"Message document missing conversation_id: {message_doc.get('_id')}")
                return None
            
            # Convert reactions
            reactions = []
            for reaction in message_doc.get("reactions", []):
                try:
                    reactions.append(MessageReaction(
                        user_id=uuid.UUID(reaction["user_id"]),
                        emoji=reaction["emoji"],
                        created_at=reaction["created_at"]
                    ))
                except (KeyError, ValueError) as e:
                    logger.warning(f"Invalid reaction data: {e}")
                    continue
            
            # Convert read receipts
            read_by = []
            for read_receipt in message_doc.get("read_by", []):
                try:
                    read_by.append(MessageReadStatus(
                        user_id=uuid.UUID(read_receipt["user_id"]),
                        read_at=read_receipt["read_at"]
                    ))
                except (KeyError, ValueError) as e:
                    logger.warning(f"Invalid read receipt data: {e}")
                    continue
            
            # Convert metadata
            metadata = None
            if message_doc.get("metadata"):
                try:
                    metadata = MessageMetadata(**message_doc["metadata"])
                except (TypeError, ValueError) as e:
                    logger.warning(f"Invalid metadata: {e}")
            
            return MessageResponse(
                id=str(message_doc["_id"]),
                conversation_id=uuid.UUID(message_doc["conversation_id"]),
                sender_id=uuid.UUID(message_doc["sender_id"]),
                message=message_doc.get("message", ""),
                message_type=MessageType(message_doc.get("message_type", "text")),
                reply_to=str(message_doc["reply_to"]) if message_doc.get("reply_to") else None,
                edited_at=message_doc.get("edited_at"),
                reactions=reactions,
                read_by=read_by,
                metadata=metadata,
                timestamp=message_doc.get("timestamp"),
                created_at=message_doc.get("created_at"),
                updated_at=message_doc.get("updated_at")
            )
            
        except Exception as e:
            logger.error(f"Error converting message document: {e}")
            return None 
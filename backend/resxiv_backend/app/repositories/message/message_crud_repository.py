"""
Message CRUD Repository - L6 Engineering Standards
Focused on basic message database operations: create, read, update, delete.
"""

import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
import pymongo

from app.database.connection import DatabaseManager
from app.models.conversation_models import (
    MessageResponse, MessageCreate, MessageUpdate, MessageType
)

logger = logging.getLogger(__name__)


class MessageCrudRepository:
    """
    CRUD repository for message database operations.
    Single Responsibility: Basic message CRUD operations.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.db: AsyncIOMotorDatabase = db_manager.mongodb_database
        self.messages: AsyncIOMotorCollection = self.db.messages
    
    async def create_message(
        self,
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        metadata: Optional[Dict[str, Any]] = None,
        reply_to: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new message.
        
        Args:
            conversation_id: Conversation UUID
            sender_id: Sender user UUID
            content: Message content
            message_type: Type of message
            metadata: Optional metadata
            reply_to: Optional message ID this is replying to
            thread_id: Optional thread ID
            
        Returns:
            Created message document
        """
        message_doc = {
            "conversation_id": str(conversation_id),
            "sender_id": str(sender_id),
            "content": content,
            "type": message_type.value,
            "metadata": metadata or {},
            "reply_to": reply_to,
            "thread_id": thread_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "deleted_at": None,
            "reactions": [],
            "read_by": [],
            "edited": False,
            "edit_history": []
        }
        
        result = await self.messages.insert_one(message_doc)
        message_doc["_id"] = result.inserted_id
        
        return message_doc
    
    async def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get message by ID.
        
        Args:
            message_id: Message ObjectId string
            
        Returns:
            Message document or None
        """
        try:
            object_id = ObjectId(message_id)
            return await self.messages.find_one({"_id": object_id, "deleted_at": None})
        except Exception as e:
            logger.error(f"Error getting message {message_id}: {e}")
            return None
    
    async def update_message(
        self,
        message_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update message content and metadata.
        
        Args:
            message_id: Message ObjectId string
            content: New content (optional)
            metadata: New metadata (optional)
            
        Returns:
            Success status
        """
        try:
            object_id = ObjectId(message_id)
            update_doc = {
                "updated_at": datetime.utcnow()
            }
            
            # Store edit history if content is being changed
            if content is not None:
                # Get current message to store in history
                current_message = await self.messages.find_one({"_id": object_id})
                if current_message:
                    edit_entry = {
                        "content": current_message.get("content"),
                        "edited_at": current_message.get("updated_at"),
                        "edit_number": len(current_message.get("edit_history", [])) + 1
                    }
                    
                    update_doc.update({
                        "content": content,
                        "edited": True,
                        "$push": {"edit_history": edit_entry}
                    })
            
            if metadata is not None:
                update_doc["metadata"] = metadata
            
            result = await self.messages.update_one(
                {"_id": object_id, "deleted_at": None},
                {"$set": update_doc}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating message {message_id}: {e}")
            return False
    
    async def delete_message(
        self,
        message_id: str,
        soft_delete: bool = True
    ) -> bool:
        """
        Delete a message.
        
        Args:
            message_id: Message ObjectId string
            soft_delete: Whether to soft delete (default) or hard delete
            
        Returns:
            Success status
        """
        try:
            object_id = ObjectId(message_id)
            
            if soft_delete:
                # Soft delete
                result = await self.messages.update_one(
                    {"_id": object_id, "deleted_at": None},
                    {"$set": {"deleted_at": datetime.utcnow()}}
                )
                return result.modified_count > 0
            else:
                # Hard delete
                result = await self.messages.delete_one({"_id": object_id})
                return result.deleted_count > 0
                
        except Exception as e:
            logger.error(f"Error deleting message {message_id}: {e}")
            return False
    
    async def get_conversation_messages(
        self,
        conversation_id: uuid.UUID,
        limit: int = 50,
        before: Optional[str] = None,
        after: Optional[str] = None,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get messages for a conversation with pagination.
        
        Args:
            conversation_id: Conversation UUID
            limit: Maximum number of messages
            before: Get messages before this message ID
            after: Get messages after this message ID
            include_deleted: Whether to include soft-deleted messages
            
        Returns:
            List of message documents
        """
        try:
            # Build query
            query = {"conversation_id": str(conversation_id)}
            
            if not include_deleted:
                query["deleted_at"] = None
            
            # Handle pagination
            if before:
                try:
                    before_id = ObjectId(before)
                    query["_id"] = {"$lt": before_id}
                except Exception:
                    pass
            
            if after:
                try:
                    after_id = ObjectId(after)
                    query["_id"] = {"$gt": after_id}
                except Exception:
                    pass
            
            # Execute query with sorting
            cursor = self.messages.find(query).sort("_id", -1).limit(limit)
            messages = await cursor.to_list(length=limit)
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting conversation messages: {e}")
            return []
    
    async def get_message_count(
        self,
        conversation_id: uuid.UUID,
        include_deleted: bool = False
    ) -> int:
        """
        Get total message count for a conversation.
        
        Args:
            conversation_id: Conversation UUID
            include_deleted: Whether to include soft-deleted messages
            
        Returns:
            Message count
        """
        try:
            query = {"conversation_id": str(conversation_id)}
            
            if not include_deleted:
                query["deleted_at"] = None
            
            return await self.messages.count_documents(query)
            
        except Exception as e:
            logger.error(f"Error counting messages: {e}")
            return 0
    
    async def mark_messages_as_read(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        up_to_message_id: Optional[str] = None
    ) -> int:
        """
        Mark messages as read by a user.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User UUID
            up_to_message_id: Mark as read up to this message (optional)
            
        Returns:
            Number of messages updated
        """
        try:
            query = {
                "conversation_id": str(conversation_id),
                "deleted_at": None,
                "read_by": {"$ne": str(user_id)}
            }
            
            if up_to_message_id:
                try:
                    up_to_id = ObjectId(up_to_message_id)
                    query["_id"] = {"$lte": up_to_id}
                except Exception:
                    pass
            
            # Add user to read_by array with timestamp
            read_entry = {
                "user_id": str(user_id),
                "read_at": datetime.utcnow()
            }
            
            result = await self.messages.update_many(
                query,
                {"$push": {"read_by": read_entry}}
            )
            
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Error marking messages as read: {e}")
            return 0
    
    async def get_unread_count(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> int:
        """
        Get unread message count for a user in a conversation.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User UUID
            
        Returns:
            Unread message count
        """
        try:
            query = {
                "conversation_id": str(conversation_id),
                "deleted_at": None,
                "sender_id": {"$ne": str(user_id)},  # Exclude own messages
                "read_by.user_id": {"$ne": str(user_id)}
            }
            
            return await self.messages.count_documents(query)
            
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0
    
    async def get_user_messages(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get messages sent by a user.
        
        Args:
            user_id: User UUID
            limit: Maximum number of messages
            offset: Number of messages to skip
            
        Returns:
            List of message documents
        """
        try:
            query = {
                "sender_id": str(user_id),
                "deleted_at": None
            }
            
            cursor = self.messages.find(query).sort("_id", -1).skip(offset).limit(limit)
            messages = await cursor.to_list(length=limit)
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting user messages: {e}")
            return []
    
    async def bulk_delete_messages(
        self,
        message_ids: List[str],
        soft_delete: bool = True
    ) -> int:
        """
        Bulk delete multiple messages.
        
        Args:
            message_ids: List of message ObjectId strings
            soft_delete: Whether to soft delete (default) or hard delete
            
        Returns:
            Number of messages deleted
        """
        try:
            # Convert to ObjectIds
            object_ids = []
            for msg_id in message_ids:
                try:
                    object_ids.append(ObjectId(msg_id))
                except Exception:
                    continue
            
            if not object_ids:
                return 0
            
            query = {"_id": {"$in": object_ids}}
            
            if soft_delete:
                query["deleted_at"] = None  # Only update non-deleted messages
                result = await self.messages.update_many(
                    query,
                    {"$set": {"deleted_at": datetime.utcnow()}}
                )
                return result.modified_count
            else:
                result = await self.messages.delete_many(query)
                return result.deleted_count
                
        except Exception as e:
            logger.error(f"Error bulk deleting messages: {e}")
            return 0 
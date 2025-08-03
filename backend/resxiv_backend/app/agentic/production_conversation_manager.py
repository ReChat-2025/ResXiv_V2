"""
Production-Grade Conversation Manager

Clean, efficient conversation management following SOLID principles.
Replaces the bloated 1,049-line conversation manager.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from uuid import UUID, uuid4
from abc import ABC, abstractmethod

from motor.motor_asyncio import AsyncIOMotorClient
from app.database.connection import get_mongodb_database, db_manager

logger = logging.getLogger(__name__)


class ConversationStore(ABC):
    """
    Abstract interface for conversation storage.
    
    Follows Dependency Inversion Principle.
    """
    
    @abstractmethod
    async def save_message(self, conversation_id: str, message: Dict[str, Any]) -> bool:
        """Save a message to storage"""
        pass
    
    @abstractmethod
    async def get_messages(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages from storage"""
        pass
    
    @abstractmethod
    async def create_conversation(self, conversation_id: str, metadata: Dict[str, Any]) -> bool:
        """Create a new conversation"""
        pass


class MongoConversationStore(ConversationStore):
    """MongoDB implementation of conversation storage"""
    
    def __init__(self):
        self.db = None
        # Separate collections for metadata vs chat messages
        self.conversation_collection = None  # Stores high-level conversation metadata
        self.message_collection = None       # Stores individual chat messages
    
    async def initialize(self) -> None:
        """Initialize MongoDB connection"""
        try:
            self.db = await get_mongodb_database()

            # High-level conversation metadata (one document per conversation/session)
            self.conversation_collection = self.db.conversations

            # Chat messages (many documents per conversation)
            self.message_collection = self.db.messages

            await self._ensure_indexes()
            logger.info("MongoDB conversation store initialized")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB store: {e}")
            raise
    
    async def _ensure_indexes(self) -> None:
        """Ensure required indexes exist"""
        try:
            # Indexes for messages collection
            await self.message_collection.create_index([("conversation_id", 1), ("timestamp", -1)])
            await self.message_collection.create_index([("sender_id", 1), ("timestamp", -1)])
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")
    
    async def save_message(self, conversation_id: str, message: Dict[str, Any]) -> bool:
        """Save message to MongoDB with proper UUID handling"""
        try:
            # Convert UUID objects to strings for MongoDB compatibility
            serialized_message = self._serialize_uuids(message)
            
            message_doc = {
                "conversation_id": conversation_id,
                "message_id": str(uuid4()),
                "timestamp": datetime.utcnow(),
                **serialized_message
            }
            
            result = await self.message_collection.insert_one(message_doc)
            return bool(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            return False
    
    def _serialize_uuids(self, data: Any) -> Any:
        """Recursively convert UUID objects to strings for MongoDB"""
        if isinstance(data, UUID):
            return str(data)
        elif isinstance(data, dict):
            return {key: self._serialize_uuids(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._serialize_uuids(item) for item in data]
        # Handle Pydantic/BaseModel or dataclass objects by converting to dict first
        elif hasattr(data, "model_dump"):
            # Pydantic v2 BaseModel
            return self._serialize_uuids(data.model_dump())
        elif hasattr(data, "dict"):
            # Pydantic v1 BaseModel
            return self._serialize_uuids(data.dict())
        else:
            return data
    
    async def get_messages(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages from MongoDB with schema transformation"""
        try:
            cursor = self.message_collection.find(
                {"conversation_id": conversation_id}
            ).sort("timestamp", -1).limit(limit)
            
            messages = []
            async for doc in cursor:
                # Remove MongoDB _id for clean response
                doc.pop("_id", None)
                
                # Transform message to match ConversationHistoryResponse schema
                transformed_message = self._transform_message_schema(doc)
                messages.append(transformed_message)
            
            # Return in chronological order
            return list(reversed(messages))
            
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []
    
    def _transform_message_schema(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Transform MongoDB message document to ConversationHistoryResponse schema"""
        # Determine sender_type from metadata or message_type
        is_ai_response = doc.get("metadata", {}).get("ai_response", False)
        sender_type = "agent" if is_ai_response else "user"
        
        # Generate message_id if not present (for legacy messages)
        message_id = doc.get("message_id", f"msg_{doc.get('conversation_id', 'unknown')}_{doc.get('timestamp', 'unknown')}")
        
        # Transform to expected schema
        transformed = {
            "message_id": message_id,
            "content": doc.get("message", doc.get("content", "")),  # Handle both field names
            "timestamp": doc.get("timestamp", doc.get("created_at")),
            "sender_type": sender_type,
            "sender_id": doc.get("sender_id"),
            "conversation_id": doc.get("conversation_id"),
            "metadata": doc.get("metadata", {})
        }
        
        # Add any additional fields that might be useful
        if "message_type" in doc:
            transformed["message_type"] = doc["message_type"]
        if "created_at" in doc:
            transformed["created_at"] = doc["created_at"]
        if "updated_at" in doc:
            transformed["updated_at"] = doc["updated_at"]
            
        return transformed
    
    async def create_conversation(self, conversation_id: str, metadata: Dict[str, Any]) -> bool:
        """Create conversation metadata document"""
        try:
            conversation_doc = {
                "conversation_id": conversation_id,
                "created_at": datetime.utcnow(),
                "type": "conversation_metadata",
                **metadata
            }
            
            result = await self.conversation_collection.insert_one(conversation_doc)
            return bool(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            return False


class MessageValidator:
    """Validates and sanitizes messages"""
    
    @staticmethod
    def validate_message(message: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean message data"""
        required_fields = ["user_id", "content", "message_type"]
        
        for field in required_fields:
            if field not in message:
                raise ValueError(f"Missing required field: {field}")
        
        # Sanitize content
        content = str(message["content"]).strip()
        if not content:
            raise ValueError("Message content cannot be empty")
        
        # Validate message type
        valid_types = ["user", "assistant", "system"]
        if message["message_type"] not in valid_types:
            raise ValueError(f"Invalid message type: {message['message_type']}")
        
        return {
            "user_id": str(message["user_id"]),
            "content": content,
            "message_type": message["message_type"],
            "metadata": message.get("metadata", {})
        }


class ProductionConversationManager:
    """
    Production-grade conversation manager with focused responsibilities.
    
    Single Responsibility: Conversation management only
    Open/Closed: Easy to extend with new stores
    Liskov Substitution: Can replace original manager
    Interface Segregation: Clean, focused interface  
    Dependency Inversion: Depends on storage abstraction
    """
    
    def __init__(self, store: Optional[ConversationStore] = None):
        self.store = store or MongoConversationStore()
        self.validator = MessageValidator()
        self._initialized = False
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def initialize(self) -> None:
        """Initialize the conversation manager"""
        if self._initialized:
            self.logger.warning("ConversationManager already initialized")
            return
        
        try:
            if hasattr(self.store, 'initialize'):
                await self.store.initialize()
            
            self._initialized = True
            self.logger.info("Production conversation manager initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize conversation manager: {e}")
            raise
    
    async def add_message(
        self,
        conversation_id: str,
        user_id: str,
        message: str,
        message_type: str = "user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: ID of the conversation
            user_id: ID of the user sending the message
            message: Message content
            message_type: Type of message (user, assistant, system)
            metadata: Optional metadata
            
        Returns:
            True if message was saved successfully
        """
        if not self._initialized:
            raise RuntimeError("ConversationManager not initialized")
        
        try:
            # Validate message
            message_data = self.validator.validate_message({
                "user_id": user_id,
                "content": message,
                "message_type": message_type,
                "metadata": metadata or {}
            })
            
            # Save to store
            success = await self.store.save_message(conversation_id, message_data)
            
            if success:
                self.logger.debug(f"Message added to conversation {conversation_id}")
            else:
                self.logger.warning(f"Failed to save message to conversation {conversation_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to add message: {e}")
            return False
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history.
        
        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages to return
            
        Returns:
            List of messages in chronological order
        """
        if not self._initialized:
            raise RuntimeError("ConversationManager not initialized")
        
        try:
            messages = await self.store.get_messages(conversation_id, limit)
            self.logger.debug(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
            return messages
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation history: {e}")
            return []
    
    async def create_conversation(
        self,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        conversation_type: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new conversation.
        
        Args:
            conversation_id: Optional specific conversation ID
            user_id: ID of the user creating the conversation
            project_id: Optional project context
            conversation_type: Type of conversation
            metadata: Additional metadata
            
        Returns:
            The conversation ID
        """
        if not self._initialized:
            raise RuntimeError("ConversationManager not initialized")
        
        try:
            # Generate ID if not provided
            conv_id = conversation_id or str(uuid4())
            
            # Prepare metadata
            conv_metadata = {
                "user_id": user_id,
                "project_id": project_id,
                "conversation_type": conversation_type,
                "status": "active",
                **(metadata or {})
            }
            
            # Create conversation
            success = await self.store.create_conversation(conv_id, conv_metadata)
            
            if success:
                self.logger.info(f"Created conversation {conv_id}")
                return conv_id
            else:
                raise RuntimeError("Failed to create conversation in store")
                
        except Exception as e:
            self.logger.error(f"Failed to create conversation: {e}")
            raise
    
    async def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get a summary of the conversation"""
        if not self._initialized:
            raise RuntimeError("ConversationManager not initialized")
        
        try:
            messages = await self.get_conversation_history(conversation_id, limit=100)
            
            if not messages:
                return {
                    "conversation_id": conversation_id,
                    "message_count": 0,
                    "last_activity": None,
                    "participants": []
                }
            
            # Calculate summary stats
            participants = set(msg.get("user_id") for msg in messages if msg.get("user_id"))
            message_count = len(messages)
            last_activity = messages[-1].get("timestamp") if messages else None
            
            return {
                "conversation_id": conversation_id,
                "message_count": message_count,
                "last_activity": last_activity,
                "participants": list(participants),
                "first_message": messages[0].get("timestamp") if messages else None,
                "summary_generated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation summary: {e}")
            return {
                "conversation_id": conversation_id,
                "error": str(e)
            }
    
    def is_initialized(self) -> bool:
        """Check if manager is initialized"""
        return self._initialized
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        health = {
            "service": "ProductionConversationManager",
            "initialized": self._initialized,
            "store_type": type(self.store).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if self._initialized:
            try:
                # Test store connection
                test_conv_id = f"health_check_{uuid4()}"
                test_success = await self.store.save_message(test_conv_id, {
                    "user_id": "health_check",
                    "content": "Health check message",
                    "message_type": "system",
                    "metadata": {"test": True}
                })
                health["store_connection"] = "healthy" if test_success else "unhealthy"
            except Exception as e:
                health["store_connection"] = f"error: {str(e)}"
        else:
            health["store_connection"] = "not_initialized"
        
        return health 
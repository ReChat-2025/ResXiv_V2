"""
Conversation Pydantic Models

This module contains all Pydantic models for conversation and message operations.
Includes request/response models for API validation and serialization.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, validator
from pydantic.types import constr, conlist


class ConversationType(str, Enum):
    """Conversation type enumeration matching database ENUM"""
    AI = "AI"
    GROUP = "GROUP"
    PDF = "PDF"
    DROP = "DROP"
    AGENTIC = "AGENTIC"


class MessageType(str, Enum):
    """Message type enumeration matching database ENUM"""
    TEXT = "text"
    FILE = "file"
    IMAGE = "image"
    SYSTEM = "system"


class MessageReaction(BaseModel):
    """Message reaction model"""
    user_id: UUID
    emoji: str = Field(..., max_length=10)
    created_at: datetime


class MessageReadStatus(BaseModel):
    """Message read status model"""
    user_id: UUID
    read_at: datetime


class MessageMetadata(BaseModel):
    """Flexible message metadata model"""
    file_id: Optional[UUID] = None
    ai_context: Optional[Dict[str, Any]] = None
    latex_commit: Optional[str] = None
    paper_id: Optional[UUID] = None
    mention_users: Optional[List[UUID]] = None


# ================================
# REQUEST MODELS
# ================================

class ConversationCreate(BaseModel):
    """Create conversation request model"""
    title: constr(min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    conversation_type: ConversationType = ConversationType.GROUP
    is_public: bool = False
    project_id: Optional[UUID] = None
    
    @validator('title')
    def title_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()


class ConversationUpdate(BaseModel):
    """Update conversation request model"""
    title: Optional[constr(min_length=1, max_length=255)] = None
    description: Optional[str] = Field(None, max_length=1000)
    is_public: Optional[bool] = None
    
    @validator('title')
    def title_must_not_be_empty(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Title cannot be empty')
        return v.strip() if v else v


class MessageCreate(BaseModel):
    """Create message request model"""
    content: constr(min_length=1, max_length=10000)
    message_type: MessageType = MessageType.TEXT
    parent_message_id: Optional[UUID] = None
    metadata: Optional[MessageMetadata] = None
    
    @validator('content')
    def content_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()


class MessageUpdate(BaseModel):
    """Update message request model"""
    message: Optional[constr(min_length=1, max_length=10000)] = None
    metadata: Optional[MessageMetadata] = None


class MessageReactionCreate(BaseModel):
    """Add reaction to message request model"""
    emoji: constr(min_length=1, max_length=10)


class ConversationMemberAdd(BaseModel):
    """Add member to conversation request model"""
    user_id: UUID


class MessageSearch(BaseModel):
    """Message search parameters"""
    query: Optional[str] = None
    message_type: Optional[MessageType] = None
    sender_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


# ================================
# RESPONSE MODELS
# ================================

class ConversationResponse(BaseModel):
    """Conversation response model"""
    id: UUID
    type: ConversationType
    entity: Optional[UUID]
    is_group: bool
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    participant_count: Optional[int] = None
    unread_count: Optional[int] = None
    last_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Message response model"""
    id: str  # MongoDB ObjectId as string
    conversation_id: UUID
    sender_id: UUID
    sender_name: Optional[str] = None
    message: str
    message_type: MessageType
    reply_to: Optional[str] = None
    edited_at: Optional[datetime] = None
    reactions: List[MessageReaction] = []
    read_by: List[MessageReadStatus] = []
    metadata: Optional[MessageMetadata] = None
    timestamp: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConversationWithMessages(ConversationResponse):
    """Conversation with recent messages"""
    messages: List[MessageResponse] = []
    has_more: bool = False


class ConversationList(BaseModel):
    """Paginated conversation list response"""
    conversations: List[ConversationResponse]
    total: int
    page: int = Field(ge=1)
    limit: int = Field(ge=1, le=100)
    has_next: bool
    has_prev: bool


class MessageList(BaseModel):
    """Paginated message list response"""
    messages: List[MessageResponse]
    total: int
    page: int = Field(ge=1)
    limit: int = Field(ge=1, le=100)
    has_next: bool
    has_prev: bool


class TypingIndicator(BaseModel):
    """Typing indicator model for WebSocket"""
    conversation_id: UUID
    user_id: UUID
    username: str
    is_typing: bool
    timestamp: datetime


class OnlineStatus(BaseModel):
    """User online status model"""
    user_id: UUID
    is_online: bool
    last_seen: Optional[datetime] = None


class WebSocketMessage(BaseModel):
    """WebSocket message wrapper"""
    type: str  # 'message', 'typing', 'reaction', 'read_receipt', etc.
    data: Union[MessageResponse, TypingIndicator, MessageReaction, Dict[str, Any]]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ================================
# ANALYTICS MODELS
# ================================

class ConversationStats(BaseModel):
    """Conversation statistics"""
    conversation_id: UUID
    total_messages: int
    total_participants: int
    messages_today: int
    most_active_user: Optional[UUID] = None
    avg_response_time: Optional[float] = None  # in minutes


class UserChatActivity(BaseModel):
    """User chat activity summary"""
    user_id: UUID
    total_messages_sent: int
    total_conversations: int
    favorite_emoji: Optional[str] = None
    avg_messages_per_day: float
    most_active_conversation: Optional[UUID] = None


# ================================
# ERROR MODELS
# ================================

class ConversationError(BaseModel):
    """Conversation error response"""
    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = None


class ValidationError(BaseModel):
    """Validation error response"""
    field: str
    message: str
    value: Any 
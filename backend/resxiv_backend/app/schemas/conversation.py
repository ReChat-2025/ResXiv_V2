"""conversation.py

Complete SQLAlchemy models for conversations table with all fields
from the database schema. Handles conversation management for the chat system.
"""

import uuid
from sqlalchemy import Column, DateTime, String, Boolean, UUID as SQLAlchemyUUID, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database.connection import Base


# PostgreSQL ENUM types (these should already exist in database)
conversation_type_enum = ENUM(
    'AI', 'GROUP', 'PDF', 'DROP', 'AGENTIC',
    name='conversation_type',
    create_type=False  # Don't create, use existing
)


class Conversation(Base):
    """
    Conversation model representing chat conversations.
    
    Supports different types of conversations:
    - GROUP: Project group chats
    - AI: AI assistant conversations
    - PDF: Paper-specific discussions
    - DROP: File drop conversations
    - AGENTIC: Agent-based conversations
    """

    __tablename__ = "conversations"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Conversation type from ENUM
    type = Column(conversation_type_enum, nullable=False)
    
    # Entity reference (project_id, paper_id, etc.)
    entity = Column(UUID(as_uuid=True), nullable=True)
    
    # Group conversation flag
    is_group = Column(Boolean, default=False, nullable=False)
    
    # Creator reference
    created_by = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Encrypted group key for security (JSONB for flexibility)
    group_key_encrypted = Column(JSONB, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, type={self.type}, is_group={self.is_group})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "type": self.type,
            "entity": self.entity,
            "is_group": self.is_group,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        } 
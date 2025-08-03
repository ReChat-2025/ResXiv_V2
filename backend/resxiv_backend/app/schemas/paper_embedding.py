"""
Paper Embeddings Schema

SQLAlchemy models for the paper_embeddings table.
Supports AI-powered semantic search with vector embeddings.
"""

from sqlalchemy import Column, UUID, Text, TIMESTAMP, CheckConstraint, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class PaperEmbedding(Base):
    """
    Paper Embeddings model for semantic search functionality.
    
    Stores AI-generated embeddings from diagnostic text using all-mini-lmv6 model
    for enabling semantic paper search and similarity matching.
    """
    __tablename__ = 'paper_embeddings'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('papers.id', ondelete='CASCADE'), 
        unique=True,
        nullable=False,
        comment="Reference to the paper this embedding belongs to"
    )
    # Note: embedding column handled via raw SQL due to vector type complexity
    # embedding vector(384) - 384-dimensional vector embedding from all-mini-lmv6 model
    source_text = Column(
        Text, 
        nullable=False,
        comment="Concatenated diagnostic text used to generate the embedding"
    )
    model_name = Column(
        Text, 
        nullable=False, 
        default='all-mini-lmv6',
        comment="Name of the model used for embedding generation"
    )
    model_version = Column(
        Text, 
        nullable=True,
        comment="Version of the embedding model"
    )
    embedding_metadata = Column(
        JSONB, 
        nullable=True,
        comment="Additional metadata about embedding generation process"
    )
    processing_status = Column(
        Text, 
        nullable=True, 
        default='pending',
        comment="Status of embedding processing pipeline"
    )
    error_message = Column(
        Text, 
        nullable=True,
        comment="Error details if embedding processing fails"
    )
    created_at = Column(
        TIMESTAMP(timezone=True), 
        nullable=False, 
        server_default=func.now(),
        comment="Timestamp when embedding record was created"
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), 
        nullable=False, 
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when embedding record was last updated"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'completed', 'failed')",
            name='valid_processing_status'
        ),
        CheckConstraint(
            "length(trim(source_text)) > 0",
            name='source_text_not_empty'
        ),
        # Performance indexes
        Index('idx_paper_embeddings_paper_id', 'paper_id'),
        Index('idx_paper_embeddings_status', 'processing_status'),
        Index('idx_paper_embeddings_model', 'model_name'),
        Index('idx_paper_embeddings_created_at', 'created_at'),
        # Note: Vector similarity search index created via raw SQL
        # CREATE INDEX idx_paper_embeddings_vector ON paper_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    )
    
    def __repr__(self):
        return f"<PaperEmbedding(id={self.id}, paper_id={self.paper_id}, status={self.processing_status})>"


# Pydantic models for API responses

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class PaperEmbeddingBase(BaseModel):
    """Base paper embedding model"""
    paper_id: uuid.UUID = Field(..., description="ID of the paper")
    source_text: str = Field(..., description="Source text used for embedding")
    model_name: str = Field(default="all-mini-lmv6", description="Embedding model name")
    model_version: Optional[str] = Field(None, description="Model version")
    embedding_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    processing_status: str = Field(default="pending", description="Processing status")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")


class PaperEmbeddingCreate(PaperEmbeddingBase):
    """Model for creating paper embeddings"""
    pass


class PaperEmbeddingUpdate(BaseModel):
    """Model for updating paper embeddings"""
    embedding: Optional[List[float]] = Field(None, description="384-dimensional embedding vector")
    model_version: Optional[str] = Field(None, description="Model version")
    embedding_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    processing_status: Optional[str] = Field(None, description="Processing status")
    error_message: Optional[str] = Field(None, description="Error message")


class PaperEmbeddingResponse(PaperEmbeddingBase):
    """Model for paper embedding API responses"""
    id: uuid.UUID = Field(..., description="Embedding ID")
    embedding: Optional[List[float]] = Field(None, description="384-dimensional embedding vector")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class PaperEmbeddingSearchRequest(BaseModel):
    """Model for semantic search requests"""
    query: str = Field(..., description="Search query text")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")
    include_metadata: bool = Field(default=False, description="Include embedding metadata in response")


class PaperEmbeddingSearchResult(BaseModel):
    """Model for semantic search results"""
    paper_id: uuid.UUID = Field(..., description="Paper ID")
    similarity_score: float = Field(..., description="Cosine similarity score")
    source_text: str = Field(..., description="Source text that was embedded")
    embedding_metadata: Optional[Dict[str, Any]] = Field(None, description="Embedding metadata")


class PaperEmbeddingSearchResponse(BaseModel):
    """Model for semantic search response"""
    query: str = Field(..., description="Original search query")
    results: List[PaperEmbeddingSearchResult] = Field(..., description="Search results")
    total_found: int = Field(..., description="Total number of results found")
    processing_time_ms: float = Field(..., description="Search processing time in milliseconds") 
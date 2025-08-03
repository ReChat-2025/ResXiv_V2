"""
Paper SQLAlchemy Models

Database schemas for paper management, diagnostics, and related tables.
Based on the comprehensive database schema from db_details.txt.
"""

from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer, BigInteger,
    ForeignKey, UniqueConstraint, CheckConstraint, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database.connection import Base


class Paper(Base):
    """Paper model - main papers table"""
    __tablename__ = "papers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    date_added = Column(DateTime(timezone=True), server_default=func.now())
    last_modified = Column(DateTime(timezone=True), server_default=func.now())
    pdf_path = Column(Text, nullable=True)
    bib_path = Column(Text, nullable=True)
    xml_path = Column(Text, nullable=True)  # For GROBID XML output
    file_size = Column(BigInteger, nullable=True)
    mime_type = Column(Text, nullable=True)
    checksum = Column(Text, nullable=True)
    private_uploaded = Column(Boolean, default=False)
    authors = Column(ARRAY(Text), default=list)
    keywords = Column(ARRAY(Text), default=list)
    arxiv_id = Column(Text, nullable=True)  # For ArXiv papers
    doi = Column(Text, nullable=True)
    abstract = Column(Text, nullable=True)  # Store abstract directly for quick access
    safe_title = Column(Text, nullable=True)  # For file storage naming
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    diagnostics = relationship(
        "Diagnostic", 
        back_populates="paper",
        cascade="all, delete-orphan",
        uselist=False  # One-to-one relationship
    )
    
    project_papers = relationship(
        "ProjectPaper",
        back_populates="paper",
        cascade="all, delete-orphan"
    )
    
    highlights = relationship(
        "Highlight",
        back_populates="paper",
        cascade="all, delete-orphan"
    )
    
    notes = relationship(
        "Note",
        back_populates="paper", 
        cascade="all, delete-orphan"
    )


class Diagnostic(Base):
    """Diagnostic model - one-to-one with papers"""
    __tablename__ = "diagnostics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), unique=True)
    abstract = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    method = Column(Text, nullable=True)
    dataset = Column(Text, nullable=True)
    highlights = Column(Text, nullable=True)
    weakness = Column(Text, nullable=True)
    future_scope = Column(Text, nullable=True)
    strengths = Column(Text, nullable=True)  # Additional field for completeness
    contributions = Column(Text, nullable=True)  # Main contributions
    limitations = Column(Text, nullable=True)  # Limitations
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    paper = relationship("Paper", back_populates="diagnostics")


class ProjectPaper(Base):
    """Project-Paper many-to-many relationship"""
    __tablename__ = "project_papers"
    
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    uploaded = Column(Boolean, default=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    paper = relationship("Paper", back_populates="project_papers")


class Highlight(Base):
    """Highlights model for paper annotations"""
    __tablename__ = "highlights"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    name = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    start_pos = Column(ARRAY(Integer), nullable=True)  # [page, offset]
    end_pos = Column(ARRAY(Integer), nullable=True)    # [page, offset]
    content = Column(Text, nullable=True)  # The highlighted text
    color = Column(Text, default="#ffff00")  # Highlight color
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    paper = relationship("Paper", back_populates="highlights")


class Note(Base):
    """Notes model for paper annotations"""
    __tablename__ = "notes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    name = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    text = Column(Text, nullable=False)
    position = Column(ARRAY(Integer), nullable=True)  # [page, offset] where note is anchored
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    paper = relationship("Paper", back_populates="notes") 
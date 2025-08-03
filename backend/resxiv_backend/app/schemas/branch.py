"""
Branch SQLAlchemy Models

Database schemas for Git-like branch management in collaborative LaTeX editor.
Supports branch creation, permissions, file management, and CRDT states.

Tables covered:
- branches: Git-like branches for projects
- branch_permissions: User permissions per branch
- latex_files: Files within branches
- document_sessions: CRDT state management
- git_repositories: Git repository metadata
- autosave_queue: Automated Git commit queue
"""

from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer, BIGINT,
    ForeignKey, UniqueConstraint, CheckConstraint, JSON, text
)
from sqlalchemy.dialects.postgresql import UUID, ENUM as PGEnum, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.database.connection import Base


class BranchStatus(str, enum.Enum):
    """Branch status enumeration"""
    active = "active"
    merged = "merged"
    archived = "archived"
    deleted = "deleted"


class CRDTStateType(str, enum.Enum):
    """CRDT state type enumeration"""
    yjs = "yjs"
    automerge = "automerge"
    json = "json"


class Branch(Base):
    """Git-like branches for projects"""
    __tablename__ = "branches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    source_branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    head_commit_hash = Column(Text, nullable=True)
    status = Column(PGEnum(BranchStatus, name="branch_status"), default=BranchStatus.active)
    is_default = Column(Boolean, default=False)
    is_protected = Column(Boolean, default=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    merged_at = Column(DateTime(timezone=True), nullable=True)
    merged_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        UniqueConstraint('project_id', 'name', name='unique_project_branch_name'),
        CheckConstraint('id != source_branch_id', name='no_self_source'),
    )
    
    # Relationships
    source_branch = relationship("Branch", remote_side=[id], backref="child_branches")
    permissions = relationship("BranchPermission", back_populates="branch", cascade="all, delete-orphan")
    files = relationship("LaTeXFile", back_populates="branch", cascade="all, delete-orphan")


class BranchPermission(Base):
    """User permissions for branches"""
    __tablename__ = "branch_permissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    can_read = Column(Boolean, default=True)
    can_write = Column(Boolean, default=False)
    can_admin = Column(Boolean, default=False)
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('branch_id', 'user_id', name='unique_branch_user_permission'),
    )
    
    # Relationships
    branch = relationship("Branch", back_populates="permissions")


class LaTeXFile(Base):
    """File metadata for Git-stored files"""
    __tablename__ = "latex_files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(Text, nullable=False)
    file_name = Column(Text, nullable=False)
    file_type = Column(Text, default='tex')
    # NO CONTENT COLUMN - files stored in Git repository
    file_size = Column(BIGINT, default=0)
    encoding = Column(Text, default='utf-8')
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        UniqueConstraint('branch_id', 'file_path', name='unique_branch_file_path'),
    )
    
    # Relationships
    branch = relationship("Branch", back_populates="files")
    sessions = relationship("DocumentSession", back_populates="file", cascade="all, delete-orphan")


class DocumentSession(Base):
    """CRDT state management for real-time collaboration"""
    __tablename__ = "document_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("latex_files.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(Text, nullable=False, unique=True)
    crdt_state = Column(JSONB, nullable=True)
    crdt_type = Column(PGEnum(CRDTStateType, name="crdt_state_type"), default=CRDTStateType.yjs)
    active_users = Column(JSONB, default=lambda: [])
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    autosave_pending = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), server_default=text("now() + INTERVAL '24 hours'"))
    
    # Relationships
    file = relationship("LaTeXFile", back_populates="sessions")


class GitRepository(Base):
    """Git repository metadata for projects"""
    __tablename__ = "git_repositories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    repo_path = Column(Text, nullable=False)
    repo_url = Column(Text, nullable=True)
    default_branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    last_commit_hash = Column(Text, nullable=True)
    initialized = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AutosaveQueue(Base):
    """Queue for automated Git commits"""
    __tablename__ = "autosave_queue"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("latex_files.id", ondelete="CASCADE"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    change_summary = Column(Text, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content_snapshot = Column(Text, nullable=True)
    priority = Column(Integer, default=0)
    status = Column(Text, default='pending')
    scheduled_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name='valid_status'),
    ) 
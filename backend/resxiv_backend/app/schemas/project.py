"""
Project SQLAlchemy Models

Database schemas for project management, access control, and collaboration.
Based on the comprehensive database schema from db_details.txt.

Tables covered:
- projects: Main project information
- project_members: User roles in projects (owner, admin, writer, reader)
- project_collaborators: Alternative permission model (read, write, admin)
- project_invitations: External email invitations with tokens
- invitation_reminders: Tracking reminder emails sent
"""

from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer,
    ForeignKey, UniqueConstraint, CheckConstraint, ARRAY, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from typing import Optional
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
import enum

from app.database.connection import Base


class ProjectRoleEnum(str, enum.Enum):
    """Python representation of project_role ENUM."""
    owner = "owner"
    admin = "admin"
    writer = "writer"
    reader = "reader"


# PermissionType for permission-based access (read, write, admin)
class PermissionType(str, enum.Enum):
    read = "read"
    write = "write"
    admin = "admin"

# Access control model enum (role based vs permission based)
class AccessControlModel(str, enum.Enum):
    role_based = "role_based"
    permission_based = "permission_based"


class Project(Base):
    """Main projects table"""
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    slug = Column(Text, nullable=True)  # URL-friendly identifier - removed unique=True
    description = Column(Text, nullable=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    repo_url = Column(Text, nullable=True)  # Git repository URL
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    access_model = Column(
        PGEnum(AccessControlModel, name="access_control_model", create_type=False),
        nullable=False,
        default=AccessControlModel.role_based,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
    
    @property
    def is_private(self) -> bool:
        """Placeholder property for project privacy (DB column missing)"""
        return True

    @property
    def current_user_role(self) -> Optional[str]:
        """Placeholder for current user's role in this project"""
        return None

    @property
    def current_user_permission(self) -> Optional[str]:
        """Placeholder for current user's permission in this project"""
        return None
    
    # Table args with partial unique index for active projects only
    __table_args__ = (
        Index(
            'ix_projects_slug_unique_active',
            'slug',
            unique=True,
            postgresql_where=(Column('deleted_at').is_(None))
        ),
        # Other existing indexes
        Index('ix_projects_created_by', 'created_by'),
        Index('ix_projects_deleted_at', 'deleted_at'),
        Index('ix_projects_created_at', 'created_at'),
    )
    
    # Relationships
    members = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    collaborators = relationship(
        "ProjectCollaborator",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    invitations = relationship(
        "ProjectInvitation",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    # Creator relationship
    creator = relationship("User", foreign_keys=[created_by])


class ProjectMember(Base):
    """Project members with role-based access (owner, admin, writer, reader)"""
    __tablename__ = "project_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    role = Column(
        PGEnum(ProjectRoleEnum, name="project_role", create_type=False),
        nullable=False,
        default=ProjectRoleEnum.reader
    )  # uses existing PostgreSQL ENUM
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    # Placeholder permission column for compatibility with MemberResponse (always NULL for role-based)
    permission = None  # type: ignore
    
    # Unique constraint: one role per user per project
    __table_args__ = (
        UniqueConstraint('user_id', 'project_id', name='unique_user_project'),
        CheckConstraint("role IN ('owner', 'admin', 'writer', 'reader')", name='valid_project_role')
    )
    
    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User")


class ProjectCollaborator(Base):
    """Project collaborators with permission-based access (read, write, admin)"""
    __tablename__ = "project_collaborators"
    
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    permission = Column(
        PGEnum(PermissionType, name="permission_type", create_type=False),
        nullable=False
    )
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("permission IN ('read', 'write', 'admin')", name='valid_permission_type'),
    )
    
    # Relationships
    project = relationship("Project", back_populates="collaborators")
    user = relationship("User")


class ProjectInvitation(Base):
    """External email invitations to join projects"""
    __tablename__ = "project_invitations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    email = Column(Text, nullable=False)
    role = Column(
        PGEnum(ProjectRoleEnum, name="project_role", create_type=False),
        nullable=False,
        default=ProjectRoleEnum.reader
    )  # project_role enum
    permission = Column(
        PGEnum(PermissionType, name="permission_type", create_type=False),
        nullable=True
    )  # permission_type enum (optional)
    invitation_token = Column(Text, nullable=False, unique=True)
    message = Column(Text, nullable=True)  # Personal message from inviter
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Default 7 days from creation
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    accepted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    declined_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Constraint: only one of accepted/declined/cancelled can be set
    __table_args__ = (
        CheckConstraint("role IN ('owner', 'admin', 'write', 'read')", name='valid_invitation_role'),
        CheckConstraint("permission IS NULL OR permission IN ('read', 'write', 'admin')", name='valid_invitation_permission'),
        CheckConstraint("""
            (accepted_at IS NULL AND declined_at IS NULL AND cancelled_at IS NULL) OR
            (accepted_at IS NOT NULL AND declined_at IS NULL AND cancelled_at IS NULL) OR
            (accepted_at IS NULL AND declined_at IS NOT NULL AND cancelled_at IS NULL) OR
            (accepted_at IS NULL AND declined_at IS NULL AND cancelled_at IS NOT NULL)
        """, name='check_invitation_state')
    )
    
    # Relationships
    project = relationship("Project", back_populates="invitations")
    inviter = relationship("User", foreign_keys=[invited_by])
    accepter = relationship("User", foreign_keys=[accepted_by])
    canceller = relationship("User", foreign_keys=[cancelled_by])
    
    # Invitation reminders
    reminders = relationship(
        "InvitationReminder",
        back_populates="invitation",
        cascade="all, delete-orphan"
    )


class InvitationReminder(Base):
    """Track reminder emails sent for invitations"""
    __tablename__ = "invitation_reminders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invitation_id = Column(UUID(as_uuid=True), ForeignKey("project_invitations.id", ondelete="CASCADE"), nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    reminder_count = Column(Integer, default=1)  # 1st reminder, 2nd reminder, etc.
    
    # Relationships
    invitation = relationship("ProjectInvitation", back_populates="reminders") 
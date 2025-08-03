"""
User SQLAlchemy Models

Database schemas for user management, authentication, and related tables.
Based on the comprehensive database schema from db_details.txt.
"""

from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer, 
    ForeignKey, UniqueConstraint, CheckConstraint, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from typing import Optional, Dict, Any

from app.database.connection import Base


class User(Base):
    """User model - main user table"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    email = Column(Text, unique=True, nullable=False)
    password = Column(Text, nullable=False)  # Store hashed password
    public_key = Column(Text, nullable=True)
    email_verified = Column(Boolean, default=False)
    accepted_terms = Column(Boolean, default=False)
    interests = Column(ARRAY(Text), default=list)
    intro = Column(Text, default="Fill in your information")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Email validation constraint
    __table_args__ = (
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name="valid_email_format"
        ),
    )
    
    # Relationships
    email_verification_tokens = relationship(
        "EmailVerificationToken", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    password_reset_tokens = relationship(
        "PasswordResetToken", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    user_sessions = relationship(
        "UserSession", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    created_projects = relationship(
        "Project", 
        back_populates="creator",
        foreign_keys="Project.created_by"
    )
    project_memberships = relationship(
        "ProjectMember", 
        back_populates="user"
    )
    
    @property
    def is_active(self) -> bool:
        """Check if user account is active (not soft deleted)"""
        return self.deleted_at is None
    
    @property
    def role(self) -> str:
        """User role (default: user). Placeholder until roles column added."""
        return getattr(self, "_role", "user")  # legacy support

    @property
    def profile_picture_url(self) -> Optional[str]:
        """User profile picture URL (not stored yet)"""
        return None

    @property
    def bio(self) -> Optional[str]:
        """User biography"""
        return None

    @property
    def organization(self) -> Optional[str]:
        """User organization"""
        return None

    @property
    def location(self) -> Optional[str]:
        """User location"""
        return None

    @property
    def website(self) -> Optional[str]:
        """User personal website"""
        return None

    @property
    def social_links(self) -> Dict[str, str]:
        """User social media links"""
        return {}

    @property
    def privacy_settings(self) -> Dict[str, Any]:
        """User privacy settings"""
        return {}

    @property
    def notification_settings(self) -> Dict[str, Any]:
        """User notification settings"""
        return {}
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"


class EmailVerificationToken(Base):
    """Email verification token model"""
    __tablename__ = "email_verification_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    email = Column(Text, nullable=False)
    token = Column(Text, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="email_verification_tokens")
    
    def __repr__(self):
        return f"<EmailVerificationToken(id={self.id}, user_id={self.user_id}, email={self.email})>"


class PasswordResetToken(Base):
    """Password reset token model"""
    __tablename__ = "password_reset_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(Text, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="password_reset_tokens")
    
    def __repr__(self):
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id}, used={self.used})>"

    @property
    def is_expired(self) -> bool:
        """Return True if token is expired or already used."""
        from datetime import datetime, timezone
        return self.used or (self.expires_at <= datetime.now(timezone.utc))


class UserSession(Base):
    """User session model for tracking active sessions"""
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(Text, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), server_default=func.now())
    user_agent = Column(Text, nullable=True)
    ip_address = Column(INET, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="user_sessions")
   
    @property
    def is_expired(self) -> bool:
        """Return True if the session (refresh token) is expired."""
        from datetime import datetime, timezone
        return self.expires_at <= datetime.now(timezone.utc)
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"


# Import other related models to ensure they're available
# These will be created in separate files to maintain the 800-line limit

try:
    from app.schemas.project import Project, ProjectMember
except ImportError:
    # Project models not yet created, create placeholder classes
    class Project(Base):
        __tablename__ = "projects"
        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
        
        # Relationships
        creator = relationship("User", back_populates="created_projects")
    
    class ProjectMember(Base):
        __tablename__ = "project_members"
        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
        
        # Relationships
        user = relationship("User", back_populates="project_memberships") 
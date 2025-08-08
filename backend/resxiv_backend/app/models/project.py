"""
Project Pydantic Models

All Pydantic models for project management API requests and responses.
Handles validation, serialization, and type safety for:

Request Models:
- ProjectCreate: Create new project
- ProjectUpdate: Update project information  
- MemberAdd: Add member to project
- MemberUpdate: Update member role
- InvitationCreate: Send project invitation
- InvitationResponse: Accept/decline invitation

Response Models:
- ProjectResponse: Project details with members/collaborators
- ProjectListResponse: Paginated project list
- MemberResponse: Project member information
- InvitationResponse: Invitation details
- ProjectStatsResponse: Project statistics

Enums:
- ProjectRole: owner, admin, writer, reader
- PermissionType: read, write, admin
- InvitationStatus: pending, accepted, declined, cancelled, expired
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
import enum
from pydantic import BaseModel, Field, validator, EmailStr, field_validator
import uuid
from enum import Enum


# ================================
# ENUMS
# ================================

class ProjectRole(str, Enum):
    """Unified access-control levels with backward compatibility."""
    OWNER = "owner"
    ADMIN = "admin"
    WRITER = "writer"
    READ = "reader"
    
    @classmethod
    def normalize(cls, value: str) -> "ProjectRole":
        """Normalize input values for backward compatibility."""
        # Handle backward compatibility mapping
        compatibility_map = {
            "write": cls.WRITER,  # old -> new
            "read": cls.READ,     # old -> new
            "writer": cls.WRITER, # new (passthrough)
            "reader": cls.READ,   # new (passthrough)
            "owner": cls.OWNER,   # unchanged
            "admin": cls.ADMIN,   # unchanged
        }
        
        normalized = compatibility_map.get(value.lower())
        if normalized:
            return normalized
        
        # Fallback to standard enum validation
        return cls(value)
    



class PermissionType(str, Enum):
    """Permission type enumeration (permission-based access)"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class InvitationStatus(str, Enum):
    """Invitation status enumeration"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class AccessControlModel(str, Enum):
    """Access control model type"""
    ROLE_BASED = "role_based"      # Uses ProjectRole (owner, admin, write, read)
    PERMISSION_BASED = "permission_based"  # Uses PermissionType (read, write, admin)


# ================================
# BASE PROJECT MODELS
# ================================

class ProjectCreate(BaseModel):
    """Project creation request model"""
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    slug: Optional[str] = Field(None, min_length=3, max_length=50, description="URL-friendly identifier")
    description: Optional[str] = Field(None, max_length=2000, description="Project description")
    repo_url: Optional[str] = Field(None, description="Git repository URL")
    access_model: AccessControlModel = Field(AccessControlModel.ROLE_BASED, description="Access control model")
    is_private: bool = Field(True, description="Whether project is private")
    
    @validator("slug")
    def validate_slug(cls, v):
        if v:
            import re
            if not re.match(r'^[a-z0-9-]+$', v):
                raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
            if v.startswith('-') or v.endswith('-'):
                raise ValueError("Slug cannot start or end with hyphen")
        return v
    
    @validator("repo_url")
    def validate_repo_url(cls, v):
        if v:
            import re
            # Basic URL validation for git repositories
            if not re.match(r'^https?://', v):
                raise ValueError("Repository URL must start with http:// or https://")
        return v


class ProjectUpdate(BaseModel):
    """Project update request model"""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Updated project name")
    slug: Optional[str] = Field(None, min_length=3, max_length=50, description="Updated slug")
    description: Optional[str] = Field(None, max_length=2000, description="Updated description")
    repo_url: Optional[str] = Field(None, description="Updated repository URL")
    is_private: Optional[bool] = Field(None, description="Update privacy setting")
    
    @validator("slug")
    def validate_slug(cls, v):
        if v:
            import re
            if not re.match(r'^[a-z0-9-]+$', v):
                raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v


# ================================
# MEMBER MANAGEMENT MODELS
# ================================

class MemberAdd(BaseModel):
    """Add member to project request model"""
    user_id: Optional[uuid.UUID] = Field(None, description="User ID (for existing users)")
    email: Optional[EmailStr] = Field(None, description="Email (for invitations)")
    role: ProjectRole = Field(ProjectRole.READ, description="Project role")
    permission: Optional[PermissionType] = Field(None, description="Permission (for permission-based model)")
    send_invitation: bool = Field(True, description="Whether to send invitation email")
    message: Optional[str] = Field(None, max_length=500, description="Personal invitation message")
    
    @validator('role', pre=True)
    def normalize_role(cls, v):
        """Normalize role for backward compatibility."""
        if isinstance(v, str):
            return ProjectRole.normalize(v)
        return v
    
    @validator("user_id")
    def validate_user_or_email(cls, v, values):
        email = values.get('email')
        if not v and not email:
            raise ValueError("Either user_id or email must be provided")
        if v and email:
            raise ValueError("Provide either user_id or email, not both")
        return v


class MemberUpdate(BaseModel):
    """Update member role/permission request model"""
    role: Optional[ProjectRole] = Field(None, description="Updated role")
    permission: Optional[PermissionType] = Field(None, description="Updated permission")
    
    @validator("permission")
    def validate_role_or_permission(cls, v, values):
        role = values.get('role')
        if not role and not v:
            raise ValueError("Either role or permission must be provided")
        return v


class MemberRemove(BaseModel):
    """Remove member from project request model"""
    user_id: uuid.UUID = Field(..., description="User ID to remove")
    transfer_ownership: Optional[uuid.UUID] = Field(None, description="Transfer ownership to this user (if removing owner)")


# ================================
# INVITATION MODELS
# ================================

class InvitationCreate(BaseModel):
    """Project invitation creation request model"""
    email: EmailStr = Field(..., description="Email address to invite")
    role: ProjectRole = Field(ProjectRole.READ, description="Role for invitee")
    permission: Optional[PermissionType] = Field(None, description="Permission for invitee")
    message: Optional[str] = Field(None, max_length=500, description="Personal invitation message")
    expires_in_days: int = Field(7, ge=1, le=30, description="Invitation expiry (1-30 days)")
    
    @validator('role', pre=True)
    def normalize_role(cls, v):
        """Normalize role for backward compatibility."""
        if isinstance(v, str):
            return ProjectRole.normalize(v)
        return v


class InvitationRespond(BaseModel):
    """Respond to project invitation request model"""
    invitation_token: str = Field(..., description="Invitation token")
    accept: bool = Field(..., description="True to accept, False to decline")


class InvitationManage(BaseModel):
    """Manage invitation request model (cancel, resend, etc.)"""
    action: str = Field(..., description="Action to perform")
    
    @validator("action")
    def validate_action(cls, v):
        valid_actions = ["cancel", "resend", "extend"]
        if v not in valid_actions:
            raise ValueError(f"Action must be one of {valid_actions}")
        return v


# ================================
# RESPONSE MODELS
# ================================

class UserBasicInfo(BaseModel):
    """Basic user information for responses"""
    id: uuid.UUID
    name: str
    email: str
    
    class Config:
        from_attributes = True


class MemberResponse(BaseModel):
    """Project member response model"""
    id: uuid.UUID
    user: UserBasicInfo
    role: ProjectRole
    permission: Optional[PermissionType]
    added_at: datetime
    is_owner: bool = False
    can_manage_members: bool = False

    @validator('role', pre=True, always=True)
    def _coerce_role_enum(cls, v):
        if isinstance(v, enum.Enum):
            return v.value
        if hasattr(v, 'value'):  # Handle any enum-like object
            return v.value
        return v

    @validator('permission', pre=True, always=True)
    def _coerce_permission_enum(cls, v):
        if isinstance(v, enum.Enum):
            return v.value
        if hasattr(v, 'value'):  # Handle any enum-like object
            return v.value
        return v
    
    class Config:
        from_attributes = True
        use_enum_values = True  # Automatically use enum values for serialization


class InvitationResponse(BaseModel):
    """Project invitation response model"""
    id: uuid.UUID
    email: str
    role: ProjectRole
    permission: Optional[PermissionType]
    status: InvitationStatus
    message: Optional[str]
    invited_by: Optional[UserBasicInfo]
    expires_at: datetime
    created_at: datetime
    accepted_at: Optional[datetime]
    declined_at: Optional[datetime]
    cancelled_at: Optional[datetime]

    @validator('role', 'permission', pre=True)
    def _coerce_invitation_enum(cls, v):
        if isinstance(v, enum.Enum):
            return v.value
        return v

    @validator('status', pre=True)
    def _coerce_status_enum(cls, v):
        if isinstance(v, enum.Enum):
            return v.value
        return v
    
    class Config:
        from_attributes = True
        use_enum_values = True  # Automatically use enum values for serialization


class ProjectResponse(BaseModel):
    """Complete project response model"""
    id: uuid.UUID
    name: str
    slug: Optional[str]
    description: Optional[str]
    repo_url: Optional[str]
    is_private: bool = True
    access_model: AccessControlModel
    created_by: uuid.UUID
    creator: UserBasicInfo
    created_at: datetime
    updated_at: datetime
    
    # Members and access control
    members: List[MemberResponse] = []
    pending_invitations: List[InvitationResponse] = []
    
    # Current user's access level
    current_user_role: Optional[ProjectRole] = None
    current_user_permission: Optional[PermissionType] = None
    current_user_can_read: bool = False
    current_user_can_write: bool = False
    current_user_can_admin: bool = False
    current_user_is_owner: bool = False
    
    # Statistics
    member_count: int = 0
    paper_count: int = 0
    task_count: int = 0
    
    class Config:
        from_attributes = True
        use_enum_values = True  # Automatically use enum values for serialization

    @validator('access_model', pre=True)
    def _coerce_access_model_enum(cls, v):
        if isinstance(v, enum.Enum):
            return v.value
        return v

    @validator('current_user_role', pre=True)
    def _coerce_current_user_role_enum(cls, v):
        if isinstance(v, enum.Enum):
            return v.value
        return v

    @validator('current_user_permission', pre=True)
    def _coerce_current_user_permission_enum(cls, v):
        if isinstance(v, enum.Enum):
            return v.value
        return v


class ProjectListItem(BaseModel):
    """Simplified project model for lists"""
    id: uuid.UUID
    name: str
    slug: Optional[str]
    description: Optional[str]
    is_private: bool
    created_by: uuid.UUID
    creator: UserBasicInfo
    created_at: datetime
    updated_at: datetime
    
    # Current user's role
    current_user_role: Optional[ProjectRole]
    current_user_permission: Optional[PermissionType]
    
    # Basic stats
    member_count: int = 0
    paper_count: int = 0
    task_count: int = 0
    
    class Config:
        from_attributes = True
        use_enum_values = True  # Automatically use enum values for serialization

    @validator('current_user_role', 'current_user_permission', pre=True)
    def _coerce_listitem_enum(cls, v):
        if isinstance(v, enum.Enum):
            return v.value
        return v


class ProjectListResponse(BaseModel):
    """Paginated project list response model"""
    projects: List[ProjectListItem]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool


class ProjectStatsResponse(BaseModel):
    """Project statistics response model"""
    project_id: uuid.UUID
    member_count: int
    collaborator_count: int
    pending_invitation_count: int
    paper_count: int
    task_count: int
    
    # Activity stats
    recent_activity_count: int  # Last 30 days
    
    # Access breakdown
    owner_count: int
    admin_count: int
    write_count: int  # TODO: Implement role breakdown
    read_count: int
    
    class Config:
        from_attributes = True


# ================================
# BULK OPERATIONS
# ================================

class BulkMemberOperation(BaseModel):
    """Bulk member operations request model"""
    user_ids: List[uuid.UUID] = Field(..., description="List of user IDs")
    operation: str = Field(..., description="Operation to perform")
    role: Optional[ProjectRole] = Field(None, description="Role for add/update operations")
    permission: Optional[PermissionType] = Field(None, description="Permission for add/update operations")
    
    @validator("operation")
    def validate_operation(cls, v):
        valid_operations = ["add", "remove", "update_role", "update_permission"]
        if v not in valid_operations:
            raise ValueError(f"operation must be one of {valid_operations}")
        return v


class BulkInvitationOperation(BaseModel):
    """Bulk invitation operations request model"""
    emails: List[EmailStr] = Field(..., description="List of email addresses")
    role: ProjectRole = Field(ProjectRole.READ, description="Role for invitees")
    permission: Optional[PermissionType] = Field(None, description="Permission for invitees")
    message: Optional[str] = Field(None, max_length=500, description="Personal message")
    expires_in_days: int = Field(7, ge=1, le=30, description="Invitation expiry")


class BulkOperationResponse(BaseModel):
    """Bulk operation response model"""
    success: bool
    message: str
    total_requested: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]


# ================================
# SEARCH AND FILTER MODELS
# ================================

class ProjectSearchRequest(BaseModel):
    """Project search request model"""
    query: Optional[str] = Field(None, description="Search query")
    role: Optional[ProjectRole] = Field(None, description="Filter by user's role")
    is_private: Optional[bool] = Field(None, description="Filter by privacy")
    created_by_me: Optional[bool] = Field(None, description="Filter projects created by current user")
    has_repo: Optional[bool] = Field(None, description="Filter projects with repository")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date")
    created_before: Optional[datetime] = Field(None, description="Filter by creation date")


class MemberSearchRequest(BaseModel):
    """Member search request model"""
    query: Optional[str] = Field(None, description="Search by name or email")
    role: Optional[ProjectRole] = Field(None, description="Filter by role")
    permission: Optional[PermissionType] = Field(None, description="Filter by permission")
    added_after: Optional[datetime] = Field(None, description="Filter by join date")


# ================================
# PROJECT SETTINGS MODELS
# ================================

class ProjectSettings(BaseModel):
    """Project settings model (for future features)"""
    # TODO: Add project-specific settings
    # Examples: default_role, auto_approve_members, require_invitation_approval, etc.
    pass


class ProjectAccessSummary(BaseModel):
    """Summary of user's access to project"""
    project_id: uuid.UUID
    user_id: uuid.UUID
    role: Optional[ProjectRole]
    permission: Optional[PermissionType]
    can_read: bool
    can_write: bool
    can_admin: bool
    is_owner: bool
    access_source: str  # "member", "collaborator", "owner" 
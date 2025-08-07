"""
Journal System Models

Pydantic models for journal functionality including journals, collaborators,
versions, and tags with proper validation and typing.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, validator


class JournalStatus(str, Enum):
    """Journal status enumeration"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PermissionType(str, Enum):
    """Permission types for journal collaborators"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


# ================================
# Base Models
# ================================

class JournalBase(BaseModel):
    """Base journal model with common fields"""
    title: str = Field(..., min_length=1, max_length=500, description="Journal title")
    content: str = Field(default="", description="Journal content")
    is_public: bool = Field(default=False, description="Whether journal is public")
    status: JournalStatus = Field(default=JournalStatus.DRAFT, description="Journal status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @validator('title')
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()


class JournalCreate(JournalBase):
    """Model for creating a new journal"""
    project_id: Optional[uuid.UUID] = Field(None, description="Project ID (will be set from URL path)")
    tags: Optional[List[str]] = Field(default=None, description="Initial tags")

    @validator('tags')
    def validate_tags(cls, v):
        if v is not None:
            # Remove duplicates and empty tags
            cleaned_tags = list(set(tag.strip() for tag in v if tag and tag.strip()))
            # Validate tag length
            for tag in cleaned_tags:
                if len(tag) > 50:
                    raise ValueError(f'Tag "{tag}" is too long (max 50 characters)')
            return cleaned_tags
        return v


class JournalUpdate(BaseModel):
    """Model for updating an existing journal"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None)
    is_public: Optional[bool] = Field(None)
    status: Optional[JournalStatus] = Field(None)
    metadata: Optional[Dict[str, Any]] = Field(None)

    @validator('title')
    def validate_title(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Title cannot be empty')
        return v.strip() if v else v


class JournalResponse(JournalBase):
    """Model for journal responses"""
    id: uuid.UUID
    project_id: uuid.UUID
    created_by: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JournalDetailResponse(JournalResponse):
    """Detailed journal response with additional information"""
    creator_name: Optional[str] = None
    project_name: Optional[str] = None
    collaborator_count: int = 0
    version_count: int = 0
    can_edit: bool = False
    can_admin: bool = False
    tags: List[str] = Field(default_factory=list)


# ================================
# Collaborator Models
# ================================

class JournalCollaboratorBase(BaseModel):
    """Base collaborator model"""
    permission: PermissionType = Field(default=PermissionType.READ, description="Permission level")


class JournalCollaboratorCreate(JournalCollaboratorBase):
    """Model for adding a collaborator"""
    user_id: uuid.UUID = Field(..., description="User ID to add as collaborator")


class JournalCollaboratorUpdate(BaseModel):
    """Model for updating collaborator permissions"""
    permission: PermissionType = Field(..., description="New permission level")


class JournalCollaboratorResponse(JournalCollaboratorBase):
    """Model for collaborator responses"""
    id: uuid.UUID
    journal_id: uuid.UUID
    user_id: uuid.UUID
    added_by: Optional[uuid.UUID] = None
    added_at: datetime
    
    # Additional fields from joins
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    added_by_name: Optional[str] = None

    class Config:
        from_attributes = True


# ================================
# Version Models
# ================================

class JournalVersionResponse(BaseModel):
    """Model for journal version responses"""
    id: uuid.UUID
    journal_id: uuid.UUID
    version_number: int
    title: str
    content: str
    changed_by: Optional[uuid.UUID] = None
    change_summary: Optional[str] = None
    created_at: datetime
    
    # Additional fields
    changed_by_name: Optional[str] = None

    class Config:
        from_attributes = True


class JournalVersionCompare(BaseModel):
    """Model for comparing journal versions"""
    from_version: int = Field(..., description="Source version number")
    to_version: int = Field(..., description="Target version number")


# ================================
# Tag Models
# ================================

class JournalTagCreate(BaseModel):
    """Model for creating journal tags"""
    tag_name: str = Field(..., min_length=1, max_length=50, description="Tag name")

    @validator('tag_name')
    def validate_tag_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Tag name cannot be empty')
        return v.strip()


class JournalTagResponse(BaseModel):
    """Model for journal tag responses"""
    id: uuid.UUID
    journal_id: uuid.UUID
    tag_name: str
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    
    # Additional fields
    created_by_name: Optional[str] = None

    class Config:
        from_attributes = True


# ================================
# Search and Filter Models
# ================================

class JournalSearchFilters(BaseModel):
    """Model for journal search and filtering"""
    query: Optional[str] = Field(None, description="Text search query")
    status: Optional[JournalStatus] = Field(None, description="Filter by status")
    is_public: Optional[bool] = Field(None, description="Filter by public/private")
    created_by: Optional[uuid.UUID] = Field(None, description="Filter by creator")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date")
    created_before: Optional[datetime] = Field(None, description="Filter by creation date")


class JournalListResponse(BaseModel):
    """Model for paginated journal list responses"""
    journals: List[JournalDetailResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# ================================
# Bulk Operation Models
# ================================

class BulkJournalOperation(BaseModel):
    """Model for bulk journal operations"""
    operation: str = Field(..., description="Operation type: 'delete', 'archive', 'publish'")
    journal_ids: List[uuid.UUID] = Field(..., min_items=1, description="List of journal IDs")

    @validator('operation')
    def validate_operation(cls, v):
        valid_operations = ['delete', 'archive', 'publish', 'make_private', 'make_public']
        if v not in valid_operations:
            raise ValueError(f'Invalid operation. Must be one of: {valid_operations}')
        return v


class BulkOperationResult(BaseModel):
    """Model for bulk operation results"""
    operation: str
    total_requested: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]


# ================================
# Permission Check Models
# ================================

class JournalPermissionCheck(BaseModel):
    """Model for checking journal permissions"""
    can_read: bool = False
    can_write: bool = False
    can_admin: bool = False
    is_owner: bool = False
    permission_level: Optional[PermissionType] = None 
"""
Branch Pydantic Models

All Pydantic models for collaborative LaTeX editor API requests and responses.
Handles validation, serialization, and type safety for Git-like branch operations.

Request Models:
- BranchCreate: Create new branch
- BranchUpdate: Update branch information
- BranchPermissionUpdate: Update user permissions
- FileCreate: Create new file in branch
- FileUpdate: Update file content

Response Models:
- BranchResponse: Branch details with permissions
- BranchListResponse: Paginated branch list
- FileResponse: File details with metadata
- DocumentSessionResponse: Active collaboration session
- GitStatusResponse: Git repository status

Enums:
- BranchStatus: active, merged, archived, deleted
- CRDTStateType: yjs, automerge, json
- FileType: tex, bib, sty, cls, pdf, png, jpg
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
import uuid
from enum import Enum


# ================================
# ENUMS
# ================================

class BranchStatus(str, Enum):
    """Branch status enumeration"""
    ACTIVE = "active"
    MERGED = "merged"
    ARCHIVED = "archived"
    DELETED = "deleted"


class CRDTStateType(str, Enum):
    """CRDT state type enumeration"""
    YJS = "yjs"
    AUTOMERGE = "automerge"
    JSON = "json"


class FileType(str, Enum):
    """Supported file types in LaTeX projects"""
    TEX = "tex"
    BIB = "bib"
    STY = "sty"
    CLS = "cls"
    PDF = "pdf"
    PNG = "png"
    JPG = "jpg"
    TXT = "txt"
    MD = "md"


class AutosaveStatus(str, Enum):
    """Autosave queue status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ================================
# BRANCH MODELS
# ================================

class BranchCreate(BaseModel):
    """Branch creation request model"""
    name: str = Field(..., min_length=1, max_length=100, description="Branch name")
    description: Optional[str] = Field(None, max_length=500, description="Branch description")
    source_branch_id: Optional[uuid.UUID] = Field(None, description="Source branch to create from")
    is_protected: bool = Field(False, description="Whether branch is protected from direct commits")
    
    @validator("name")
    def validate_branch_name(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Branch name must contain only letters, numbers, underscores, and hyphens")
        if v in ['HEAD', 'master', 'origin']:
            raise ValueError("Branch name cannot be a reserved Git keyword")
        return v


class BranchUpdate(BaseModel):
    """Branch update request model"""
    description: Optional[str] = Field(None, max_length=500, description="Branch description")
    is_protected: Optional[bool] = Field(None, description="Whether branch is protected")
    status: Optional[BranchStatus] = Field(None, description="Branch status")


class BranchPermissionUpdate(BaseModel):
    """Branch permission update model"""
    user_id: uuid.UUID = Field(..., description="User ID")
    can_read: bool = Field(True, description="Read permission")
    can_write: bool = Field(False, description="Write permission")
    can_admin: bool = Field(False, description="Admin permission")


class UserBasicInfo(BaseModel):
    """Basic user information for responses"""
    id: uuid.UUID
    name: str
    email: str


class BranchPermissionResponse(BaseModel):
    """Branch permission response model"""
    id: uuid.UUID
    user: UserBasicInfo
    can_read: bool
    can_write: bool
    can_admin: bool
    granted_by: UserBasicInfo
    granted_at: datetime


class BranchResponse(BaseModel):
    """Branch details response model"""
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: Optional[str]
    source_branch_id: Optional[uuid.UUID]
    head_commit_hash: Optional[str]
    status: BranchStatus
    is_default: bool
    is_protected: bool
    created_by: UserBasicInfo
    created_at: datetime
    updated_at: datetime
    merged_at: Optional[datetime]
    merged_by: Optional[UserBasicInfo]
    
    # Optional detailed information
    permissions: Optional[List[BranchPermissionResponse]] = None
    file_count: Optional[int] = None
    commits_ahead: Optional[int] = None
    commits_behind: Optional[int] = None
    last_activity: Optional[datetime] = None


class BranchListItem(BaseModel):
    """Simplified branch info for listing"""
    id: uuid.UUID
    name: str
    description: Optional[str]
    status: BranchStatus
    is_default: bool
    is_protected: bool
    created_by: UserBasicInfo
    created_at: datetime
    updated_at: datetime
    file_count: int
    user_permissions: Dict[str, bool]  # {"can_read": True, "can_write": False, "can_admin": False}


class BranchListResponse(BaseModel):
    """Paginated branch list response"""
    branches: List[BranchListItem]
    total_count: int
    page: int
    size: int
    has_next: bool
    has_previous: bool


# ================================
# FILE MODELS
# ================================

class FileCreate(BaseModel):
    """File creation request model"""
    file_name: str = Field(..., min_length=1, max_length=255, description="File name")
    file_path: Optional[str] = Field(None, description="File path (defaults to root)")
    file_type: FileType = Field(FileType.TEX, description="File type")
    content: str = Field("", description="Initial file content")
    encoding: str = Field("utf-8", description="File encoding")
    
    @validator("file_name")
    def validate_file_name(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError("File name must contain only letters, numbers, underscores, periods, and hyphens")
        # Allow dotfiles like .gitkeep, .gitignore but not files ending with period
        if v.endswith('.'):
            raise ValueError("File name cannot end with a period")
        # Don't allow just a period or double periods
        if v in ['.', '..'] or '..' in v:
            raise ValueError("File name cannot be '.' or '..' or contain '..'")
        return v


class FileUpdate(BaseModel):
    """File update request model"""
    content: Optional[str] = Field(None, description="File content")
    file_name: Optional[str] = Field(None, min_length=1, max_length=255, description="New file name")
    file_path: Optional[str] = Field(None, description="New file path")
    
    @validator("file_name")
    def validate_file_name(cls, v):
        if v is not None:
            import re
            if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
                raise ValueError("File name must contain only letters, numbers, underscores, periods, and hyphens")
        return v


class FileResponse(BaseModel):
    """File details response model"""
    id: uuid.UUID
    project_id: uuid.UUID
    branch_id: uuid.UUID
    file_path: str
    file_name: str
    file_type: FileType
    content: Optional[str]
    file_size: int
    encoding: str
    created_by: UserBasicInfo
    created_at: datetime
    updated_at: datetime
    last_modified_by: Optional[UserBasicInfo]
    
    # Optional collaboration info
    active_session: Optional["DocumentSessionResponse"] = None
    active_users: Optional[List[UserBasicInfo]] = None


class FileListItem(BaseModel):
    """Simplified file info for listing"""
    id: uuid.UUID
    file_path: str
    file_name: str
    file_type: FileType
    file_size: int
    created_by: UserBasicInfo
    updated_at: datetime
    last_modified_by: Optional[UserBasicInfo]
    has_active_session: bool


class FileListResponse(BaseModel):
    """File list response for branch"""
    files: List[FileListItem]
    total_count: int
    branch_id: uuid.UUID
    branch_name: str


# ================================
# COLLABORATION MODELS
# ================================

class DocumentSessionResponse(BaseModel):
    """Document session response model"""
    id: uuid.UUID
    file_id: uuid.UUID
    session_token: str
    crdt_type: CRDTStateType
    active_users: List[UserBasicInfo]
    last_activity: datetime
    autosave_pending: bool
    created_at: datetime
    expires_at: datetime


class DocumentSessionCreate(BaseModel):
    """Document session creation request"""
    file_id: uuid.UUID = Field(..., description="File ID to collaborate on")
    crdt_type: CRDTStateType = Field(CRDTStateType.YJS, description="CRDT implementation type")


class CRDTOperation(BaseModel):
    """CRDT operation for real-time collaboration"""
    operation_type: str = Field(..., description="Type of CRDT operation")
    operation_data: Dict[str, Any] = Field(..., description="Operation payload")
    user_id: uuid.UUID = Field(..., description="User who performed operation")
    timestamp: datetime = Field(..., description="Operation timestamp")


# ================================
# GIT MODELS
# ================================

class GitStatusResponse(BaseModel):
    """Git repository status response"""
    branch_id: uuid.UUID
    branch_name: str
    head_commit_hash: Optional[str]
    commits_ahead: int
    commits_behind: int
    modified_files: List[str]
    untracked_files: List[str]
    staged_files: List[str]
    is_clean: bool
    last_commit: Optional[Dict[str, Any]]


class MergeRequest(BaseModel):
    """Branch merge request model"""
    source_branch_id: uuid.UUID = Field(..., description="Source branch to merge from")
    target_branch_id: uuid.UUID = Field(..., description="Target branch to merge into")
    merge_message: Optional[str] = Field(None, description="Custom merge commit message")
    delete_source_branch: bool = Field(False, description="Delete source branch after merge")


class MergeResponse(BaseModel):
    """Merge operation response"""
    success: bool
    merge_commit_hash: Optional[str]
    conflicts: Optional[List[Dict[str, Any]]]
    message: str


class AutosaveQueueItem(BaseModel):
    """Autosave queue item response"""
    id: uuid.UUID
    file_id: uuid.UUID
    branch_id: uuid.UUID
    change_summary: Optional[str]
    user_id: uuid.UUID
    status: AutosaveStatus
    scheduled_at: datetime
    processed_at: Optional[datetime]


# ================================
# SEARCH AND FILTER MODELS
# ================================

class BranchSearchRequest(BaseModel):
    """Branch search and filter request"""
    search_query: Optional[str] = Field(None, description="Search in branch names and descriptions")
    status_filter: Optional[BranchStatus] = Field(None, description="Filter by branch status")
    created_by_filter: Optional[uuid.UUID] = Field(None, description="Filter by creator")
    date_from: Optional[datetime] = Field(None, description="Filter branches created after date")
    date_to: Optional[datetime] = Field(None, description="Filter branches created before date")
    include_permissions: bool = Field(False, description="Include permission details")
    sort_by: str = Field("updated_at", description="Sort field")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")


# Forward reference resolution
FileResponse.model_rebuild() 
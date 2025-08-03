"""
Branch Repository

Repository layer for branch management and Git-like operations.
Handles database interactions for branches, permissions, files, and collaboration sessions.

Responsibilities:
- Branch CRUD operations
- Permission management
- File operations within branches
- Document session management
- Git repository metadata
- Autosave queue operations
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload, joinedload

from app.schemas.branch import (
    Branch, BranchPermission, LaTeXFile, DocumentSession, 
    GitRepository, AutosaveQueue, BranchStatus, CRDTStateType
)
from app.models.branch import (
    BranchCreate, BranchUpdate, BranchPermissionUpdate,
    FileCreate, FileUpdate, DocumentSessionCreate
)

logger = logging.getLogger(__name__)


class BranchRepository:
    """Repository for branch-related database operations"""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the repository
        
        Args:
            session: Database session
        """
        self.session = session
    
    # ================================
    # BRANCH OPERATIONS
    # ================================
    
    async def create_branch(
        self, 
        project_id: uuid.UUID,
        branch_data: BranchCreate, 
        user_id: uuid.UUID
    ) -> Branch:
        """
        Create a new branch
        
        Args:
            project_id: Project ID
            branch_data: Branch creation data
            user_id: User creating the branch
            
        Returns:
            Created branch
        """
        branch = Branch(
            project_id=project_id,
            name=branch_data.name,
            description=branch_data.description,
            source_branch_id=branch_data.source_branch_id,
            is_protected=branch_data.is_protected,
            created_by=user_id,
            status=BranchStatus.active
        )
        
        self.session.add(branch)
        await self.session.flush()  # Get the ID
        
        # Grant full permissions to creator
        await self.add_branch_permission(
            branch_id=branch.id,
            user_id=user_id,
            can_read=True,
            can_write=True,
            can_admin=True,
            granted_by=user_id
        )
        
        return branch
    
    async def get_branch_by_id(
        self, 
        branch_id: uuid.UUID,
        include_permissions: bool = False,
        include_files: bool = False
    ) -> Optional[Branch]:
        """
        Get branch by ID with optional related data
        
        Args:
            branch_id: Branch ID
            include_permissions: Include permission details
            include_files: Include file list
            
        Returns:
            Branch or None
        """
        query = select(Branch).where(Branch.id == branch_id)
        
        if include_permissions:
            query = query.options(selectinload(Branch.permissions))
        if include_files:
            query = query.options(selectinload(Branch.files))
            
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_project_branches(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        status_filter: Optional[BranchStatus] = None,
        include_permissions: bool = False,
        page: int = 1,
        size: int = 20
    ) -> Tuple[List[Branch], int]:
        """
        Get branches for a project that user has access to
        
        Args:
            project_id: Project ID
            user_id: User ID for permission checking
            status_filter: Optional status filter
            include_permissions: Include permission details
            page: Page number
            size: Page size
            
        Returns:
            Tuple of (branches, total_count)
        """
        # Base query with user permission check
        query = (
            select(Branch)
            .join(BranchPermission, Branch.id == BranchPermission.branch_id)
            .where(
                and_(
                    Branch.project_id == project_id,
                    BranchPermission.user_id == user_id,
                    BranchPermission.can_read == True
                )
            )
        )
        
        if status_filter:
            query = query.where(Branch.status == status_filter)
            
        if include_permissions:
            query = query.options(selectinload(Branch.permissions))
        
        # Count query
        count_query = select(func.count()).select_from(query.subquery())
        total_count = await self.session.scalar(count_query)
        
        # Apply pagination
        query = query.order_by(desc(Branch.updated_at))
        query = query.offset((page - 1) * size).limit(size)
        
        result = await self.session.execute(query)
        branches = result.scalars().all()
        
        return list(branches), total_count
    
    async def update_branch(
        self, 
        branch_id: uuid.UUID, 
        branch_data: BranchUpdate
    ) -> Optional[Branch]:
        """
        Update branch information
        
        Args:
            branch_id: Branch ID
            branch_data: Update data
            
        Returns:
            Updated branch or None
        """
        branch = await self.get_branch_by_id(branch_id)
        if not branch:
            return None
        
        update_data = branch_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(branch, field, value)
        
        return branch
    
    async def delete_branch(self, branch_id: uuid.UUID) -> bool:
        """
        Soft delete a branch
        
        Args:
            branch_id: Branch ID
            
        Returns:
            True if deleted, False if not found
        """
        branch = await self.get_branch_by_id(branch_id)
        if not branch:
            return False
        
        branch.status = BranchStatus.deleted
        branch.deleted_at = datetime.utcnow()
        return True
    
    # ================================
    # PERMISSION OPERATIONS
    # ================================
    
    async def add_branch_permission(
        self,
        branch_id: uuid.UUID,
        user_id: uuid.UUID,
        can_read: bool = True,
        can_write: bool = False,
        can_admin: bool = False,
        granted_by: uuid.UUID = None
    ) -> BranchPermission:
        """
        Add or update branch permission for user
        
        Args:
            branch_id: Branch ID
            user_id: User ID
            can_read: Read permission
            can_write: Write permission  
            can_admin: Admin permission
            granted_by: User granting permission
            
        Returns:
            Branch permission
        """
        # Check if permission already exists
        existing = await self.session.execute(
            select(BranchPermission).where(
                and_(
                    BranchPermission.branch_id == branch_id,
                    BranchPermission.user_id == user_id
                )
            )
        )
        permission = existing.scalar_one_or_none()
        
        if permission:
            # Update existing permission
            permission.can_read = can_read
            permission.can_write = can_write
            permission.can_admin = can_admin
            permission.granted_by = granted_by or permission.granted_by
        else:
            # Create new permission
            permission = BranchPermission(
                branch_id=branch_id,
                user_id=user_id,
                can_read=can_read,
                can_write=can_write,
                can_admin=can_admin,
                granted_by=granted_by or user_id
            )
            self.session.add(permission)
        
        return permission
    
    async def get_user_branch_permission(
        self,
        branch_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[BranchPermission]:
        """
        Get user's permission for a branch
        
        Args:
            branch_id: Branch ID
            user_id: User ID
            
        Returns:
            Branch permission or None
        """
        result = await self.session.execute(
            select(BranchPermission).where(
                and_(
                    BranchPermission.branch_id == branch_id,
                    BranchPermission.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def remove_branch_permission(
        self,
        branch_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """
        Remove user's permission for a branch
        
        Args:
            branch_id: Branch ID
            user_id: User ID
            
        Returns:
            True if removed, False if not found
        """
        permission = await self.get_user_branch_permission(branch_id, user_id)
        if permission:
            await self.session.delete(permission)
            return True
        return False
    
    async def update_branch_permission(
        self,
        branch_id: uuid.UUID,
        user_id: uuid.UUID,
        can_read: bool,
        can_write: bool,
        can_admin: bool,
        granted_by: uuid.UUID
    ) -> bool:
        """
        Update or create branch permission for a user.
        
        Args:
            branch_id: Branch ID
            user_id: User ID
            can_read: Read permission
            can_write: Write permission
            can_admin: Admin permission
            granted_by: User granting permission
            
        Returns:
            True if successful
        """
        try:
            # Check if permission exists
            existing = await self.session.execute(
                select(BranchPermission).where(
                    and_(
                        BranchPermission.branch_id == branch_id,
                        BranchPermission.user_id == user_id
                    )
                )
            )
            permission = existing.scalar_one_or_none()
            
            if permission:
                # Update existing permission
                permission.can_read = can_read
                permission.can_write = can_write
                permission.can_admin = can_admin
                permission.granted_by = granted_by
                permission.granted_at = datetime.utcnow()
            else:
                # Create new permission
                permission = BranchPermission(
                    branch_id=branch_id,
                    user_id=user_id,
                    can_read=can_read,
                    can_write=can_write,
                    can_admin=can_admin,
                    granted_by=granted_by
                )
                self.session.add(permission)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating branch permission: {str(e)}")
            return False
    
    # ================================
    # FILE OPERATIONS
    # ================================
    
    async def create_file_metadata(
        self,
        project_id: uuid.UUID,
        branch_id: uuid.UUID,
        file_path: str,
        file_name: str,
        file_type: str,
        file_size: int,
        encoding: str,
        created_by: uuid.UUID
    ) -> LaTeXFile:
        """
        Create file metadata record (NO CONTENT STORAGE).
        Content is stored in Git repository.
        
        Args:
            project_id: Project ID
            branch_id: Branch ID  
            file_path: Full file path
            file_name: File name
            file_type: File type
            file_size: File size in bytes
            encoding: File encoding
            created_by: User creating the file
            
        Returns:
            Created file metadata
        """
        file = LaTeXFile(
            project_id=project_id,
            branch_id=branch_id,
            file_path=file_path,
            file_name=file_name,
            file_type=file_type,
            # NO CONTENT PARAMETER - content stored in Git repository
            file_size=file_size,
            encoding=encoding,
            created_by=created_by,
            last_modified_by=created_by
        )
        
        self.session.add(file)
        await self.session.flush()  # Get ID
        return file
    
    async def get_file_by_id(self, file_id: uuid.UUID) -> Optional[LaTeXFile]:
        """
        Get file by ID
        
        Args:
            file_id: File ID
            
        Returns:
            File or None
        """
        result = await self.session.execute(
            select(LaTeXFile).where(LaTeXFile.id == file_id)
        )
        return result.scalar_one_or_none()
    
    async def get_branch_files(
        self,
        branch_id: uuid.UUID,
        include_deleted: bool = False
    ) -> List[LaTeXFile]:
        """
        Get all files in a branch
        
        Args:
            branch_id: Branch ID
            include_deleted: Include soft-deleted files
            
        Returns:
            List of files
        """
        query = select(LaTeXFile).where(LaTeXFile.branch_id == branch_id)
        
        if not include_deleted:
            query = query.where(LaTeXFile.deleted_at.is_(None))
        
        query = query.order_by(LaTeXFile.file_path)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_file(
        self,
        file_id: uuid.UUID,
        file_data: FileUpdate,
        user_id: uuid.UUID
    ) -> Optional[LaTeXFile]:
        """
        Update file content or metadata
        
        Args:
            file_id: File ID
            file_data: Update data
            user_id: User updating the file
            
        Returns:
            Updated file or None
        """
        file = await self.get_file_by_id(file_id)
        if not file:
            return None
        
        update_data = file_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == "content":
                file.content = value
                file.file_size = len(value.encode('utf-8'))
            else:
                setattr(file, field, value)
        
        file.last_modified_by = user_id
        return file
    
    async def delete_file(self, file_id: uuid.UUID) -> bool:
        """
        Soft delete a file
        
        Args:
            file_id: File ID
            
        Returns:
            True if deleted, False if not found
        """
        file = await self.get_file_by_id(file_id)
        if not file:
            return False
        
        file.deleted_at = datetime.utcnow()
        return True
    
    # ================================
    # DOCUMENT SESSION OPERATIONS
    # ================================
    
    async def create_document_session(
        self,
        session_data: DocumentSessionCreate,
        user_id: uuid.UUID
    ) -> DocumentSession:
        """
        Create a new document collaboration session
        
        Args:
            session_data: Session creation data
            user_id: User creating the session
            
        Returns:
            Created session
        """
        import secrets
        session_token = secrets.token_urlsafe(32)
        
        session = DocumentSession(
            file_id=session_data.file_id,
            session_token=session_token,
            crdt_type=session_data.crdt_type,
            active_users=[str(user_id)]
        )
        
        self.session.add(session)
        return session
    
    async def get_document_session(
        self, 
        session_token: str
    ) -> Optional[DocumentSession]:
        """
        Get document session by token
        
        Args:
            session_token: Session token
            
        Returns:
            Session or None
        """
        result = await self.session.execute(
            select(DocumentSession).where(
                DocumentSession.session_token == session_token
            )
        )
        return result.scalar_one_or_none()
    
    async def get_file_active_session(
        self, 
        file_id: uuid.UUID
    ) -> Optional[DocumentSession]:
        """
        Get active session for a file
        
        Args:
            file_id: File ID
            
        Returns:
            Active session or None
        """
        result = await self.session.execute(
            select(DocumentSession).where(
                and_(
                    DocumentSession.file_id == file_id,
                    DocumentSession.expires_at > datetime.utcnow()
                )
            ).order_by(desc(DocumentSession.last_activity))
        )
        return result.scalar_one_or_none()
    
    # ================================
    # GIT REPOSITORY OPERATIONS
    # ================================
    
    async def get_project_git_repository(
        self, 
        project_id: uuid.UUID
    ) -> Optional[GitRepository]:
        """
        Get Git repository for project
        
        Args:
            project_id: Project ID
            
        Returns:
            Git repository or None
        """
        result = await self.session.execute(
            select(GitRepository).where(
                GitRepository.project_id == project_id
            )
        )
        return result.scalar_one_or_none()
    
    async def create_git_repository(
        self,
        project_id: uuid.UUID,
        repo_path: str,
        repo_url: Optional[str] = None
    ) -> GitRepository:
        """
        Create Git repository metadata
        
        Args:
            project_id: Project ID
            repo_path: Local repository path
            repo_url: Optional remote URL
            
        Returns:
            Created repository
        """
        repository = GitRepository(
            project_id=project_id,
            repo_path=repo_path,
            repo_url=repo_url,
            initialized=False
        )
        
        self.session.add(repository)
        return repository 
"""
Branch Service - L6 Engineering Standards

Production-grade Git-based branch management and collaborative LaTeX editing.
Single Responsibility: Branch operations with proper Git version control.

Key Features:
- Real Git repositories on filesystem 
- Proper version control with Git branches
- File operations through Git commits
- Database only stores metadata
"""

import uuid
import logging
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.branch_repository import BranchRepository
from app.repositories.project_repository import ProjectRepository
from app.services.git.git_repository_service import GitRepositoryService
from app.models.branch import (
    BranchCreate, BranchUpdate, BranchPermissionUpdate,
    FileCreate, FileUpdate, BranchResponse, BranchListResponse, FileResponse, BranchListItem
)
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.utils.todo_resolver import TODOResolverFactory
from app.models.branch import BranchStatus

logger = logging.getLogger(__name__)


class BranchService:
    """Production-grade Git-based branch management service"""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the service with Git-based operations
        
        Args:
            session: Database session
        """
        self.session = session
        self.repository = BranchRepository(session)
        self.project_repository = ProjectRepository(session)
        self.git_service = GitRepositoryService(session)
    
    # ================================
    # REPOSITORY INITIALIZATION
    # ================================
    
    @handle_service_errors("initialize project repository")
    async def initialize_project_repository(
        self,
        project_id: uuid.UUID,
        project_name: str,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Initialize Git repository for project.
        
        Args:
            project_id: Project UUID
            project_name: Project name
            user_id: User initializing repository
            
        Returns:
            Initialization result
        """
        return await self.git_service.initialize_project_repository(
            project_id=project_id,
            project_name=project_name,
            created_by=user_id
        )
    
    # ================================
    # BRANCH OPERATIONS
    # ================================
    
    @handle_service_errors("create branch")
    async def create_branch(
        self,
        project_id: uuid.UUID,
        branch_data: BranchCreate,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Create a new Git branch.
        
        Args:
            project_id: Project ID
            branch_data: Branch creation data
            user_id: User creating the branch
            
        Returns:
            Creation result
        """
        try:
            # Verify user has project access
            user_role = await self.project_repository.get_user_role(project_id, user_id)
            if not user_role or user_role not in ["writer", "admin", "owner"]:
                return {
                    "success": False,
                    "error": "Insufficient permissions to create branch"
                }
            
            # Check for duplicate branch name
            existing_branches, _ = await self.repository.get_project_branches(
                project_id=project_id,
                user_id=user_id,
                page=1,
                size=1000
            )
            
            if any(b.name == branch_data.name for b in existing_branches):
                return {
                    "success": False,
                    "error": f"Branch '{branch_data.name}' already exists"
                }
            
            # Create Git branch
            git_result = await self.git_service.create_git_branch(
                project_id=project_id,
                branch_name=branch_data.name,
                source_branch_name=getattr(branch_data, 'source_branch_name', None),
                created_by=user_id
            )
            
            if not git_result["success"]:
                return git_result
            
            # Create database record
            branch = await self.repository.create_branch(
                project_id=project_id,
                branch_data=branch_data,
                user_id=user_id
            )
            
            # Update with Git commit hash
            branch.head_commit_hash = git_result.get("commit_hash")
            
            await self.session.commit()
            
            return {
                "success": True,
                "message": "Branch created successfully",
                "branch_id": str(branch.id),
                "commit_hash": git_result.get("commit_hash")
            }
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating branch: {str(e)}")
            return {
                "success": False,
                "error": f"Branch creation failed: {str(e)}"
            }
    
    @handle_service_errors("get project branches")
    async def get_project_branches(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        page: int = 1,
        size: int = 20,
        include_permissions: bool = False
    ) -> BranchListResponse:
        """
        Get branches for a project with proper Git metadata.
        
        Args:
            project_id: Project ID
            user_id: User requesting branches
            page: Page number
            size: Page size
            include_permissions: Include permission details
            
        Returns:
            Paginated branch list with Git metadata
        """
        try:
            # Get branches from database
            branches, total_count = await self.repository.get_project_branches(
                project_id=project_id,
                user_id=user_id,
                page=page,
                size=size,
                include_permissions=include_permissions
            )
            
            # Enhance with user information
            from app.utils.todo_resolver import TODOResolverFactory
            user_lookup = TODOResolverFactory.get_user_lookup_service(self.session)
            created_by_info = await user_lookup.get_user_info(str(branches[0].created_by)) if branches else None
            
            # Build response
            branch_responses = []
            for branch in branches:
                if created_by_info:
                    # Get file count for this branch
                    branch_files = await self.repository.get_branch_files(branch.id)
                    file_count = len(branch_files)
                    
                    # Get user permissions for this branch
                    permission = await self.repository.get_user_branch_permission(
                        branch_id=branch.id,
                        user_id=user_id
                    )
                    
                    user_permissions = {
                        "can_read": permission.can_read if permission else False,
                        "can_write": permission.can_write if permission else False,
                        "can_admin": permission.can_admin if permission else False
                    }
                    
                    branch_data = BranchListItem(
                        id=branch.id,
                        name=branch.name,
                        description=branch.description,
                        status=branch.status if branch.status else BranchStatus.ACTIVE,
                        is_default=branch.is_default,
                        is_protected=branch.is_protected,
                        created_by={
                            "id": created_by_info["id"],
                            "name": created_by_info["name"],
                            "email": created_by_info["email"]
                        },
                        created_at=branch.created_at,
                        updated_at=branch.updated_at,
                        file_count=file_count,
                        user_permissions=user_permissions
                    )
                    branch_responses.append(branch_data)
            
            return BranchListResponse(
                branches=branch_responses,
                total_count=total_count,
                page=page,
                size=size,
                has_next=(page * size) < total_count,
                has_previous=page > 1
            )
            
        except Exception as e:
            logger.error(f"Error getting project branches: {str(e)}")
            raise ServiceError(
                f"Failed to get branches: {str(e)}",
                ErrorCodes.NOT_FOUND_ERROR
            )
    
    # ================================
    # FILE OPERATIONS - GIT BASED
    # ================================
    
    @handle_service_errors("create file")
    async def create_file(
        self,
        project_id: uuid.UUID,
        branch_id: uuid.UUID,
        file_data: FileCreate,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Create file in Git repository and database metadata.
        
        Args:
            project_id: Project ID
            branch_id: Branch ID
            file_data: File creation data
            user_id: User creating the file
            
        Returns:
            Creation result
        """
        try:
            # Check write permissions
            permission = await self.repository.get_user_branch_permission(
                branch_id=branch_id,
                user_id=user_id
            )
            
            if not permission or not permission.can_write:
                return {
                    "success": False,
                    "error": "Write permission required to create files"
                }
            
            # Get branch info
            branch = await self.repository.get_branch_by_id(branch_id)
            if not branch:
                return {
                    "success": False,
                    "error": "Branch not found"
                }
            
            # Get user info for Git commit
            user_lookup = TODOResolverFactory.get_user_lookup_service(self.session)
            user_info = await user_lookup.get_user_info(str(user_id))
            author_name = user_info.get("name", "ResXiv User") if user_info else "ResXiv User"
            author_email = user_info.get("email", "user@resxiv.com") if user_info else "user@resxiv.com"
            
            # Construct file path
            # Normalize directory path (no leading slash)
            dir_path = (file_data.file_path or "").lstrip("/")
            if dir_path and not dir_path.endswith("/"):
                dir_path += "/"
            full_file_path = dir_path + file_data.file_name
            
            # Write file to Git repository
            git_result = await self.git_service.write_file_to_repository(
                project_id=project_id,
                branch_name=branch.name,
                file_path=full_file_path,
                content=file_data.content,
                commit_message=f"Create {full_file_path}",
                author_name=author_name,
                author_email=author_email
            )
            
            if not git_result["success"]:
                return git_result
            
            # Create database metadata record (NO CONTENT STORAGE)
            file_metadata = await self.repository.create_file_metadata(
                project_id=project_id,
                branch_id=branch_id,
                file_path=full_file_path,
                file_name=file_data.file_name,
                file_type=file_data.file_type,
                file_size=len(file_data.content.encode('utf-8')),
                encoding=file_data.encoding,
                created_by=user_id
            )
            
            # Update branch commit hash
            branch.head_commit_hash = git_result["commit_hash"]
            
            await self.session.commit()
            
            return {
                "success": True,
                "message": "File created successfully",
                "file_id": str(file_metadata.id),
                "commit_hash": git_result["commit_hash"]
            }
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating file: {str(e)}")
            return {
                "success": False,
                "error": f"File creation failed: {str(e)}"
            }
    
    @handle_service_errors("get branch files")
    async def get_branch_files(
        self,
        branch_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get files from Git repository with database metadata.
        
        Args:
            branch_id: Branch ID
            user_id: User requesting files
            
        Returns:
            Files from Git repository
        """
        try:
            # Check permissions
            permission = await self.repository.get_user_branch_permission(
                branch_id=branch_id,
                user_id=user_id
            )
            
            if not permission or not permission.can_read:
                return {
                    "success": False,
                    "error": "Read permission required"
                }
            
            # Get branch info
            branch = await self.repository.get_branch_by_id(branch_id)
            if not branch:
                return {
                    "success": False,
                    "error": "Branch not found"
                }
            
            # Initialize repository if it doesn't exist
            from app.repositories.project_repository import ProjectRepository
            project_repo = ProjectRepository(self.session)
            project = await project_repo.get_project_by_id(branch.project_id)
            
            if project:
                # Check if repository exists, if not initialize it
                existing_repo = await self.repository.get_project_git_repository(branch.project_id)
                if not existing_repo:
                    logger.info(f"Initializing Git repository for project {branch.project_id}")
                    init_result = await self.initialize_project_repository(
                        project_id=branch.project_id,
                        project_name=project.name,
                        user_id=user_id
                    )
                    if not init_result["success"]:
                        return {
                            "success": False,
                            "error": f"Failed to initialize repository: {init_result.get('error', 'Unknown error')}"
                        }
            
            # Get files from Git repository
            git_result = await self.git_service.list_repository_files(
                project_id=branch.project_id,
                branch_name=branch.name
            )
            
            if not git_result["success"]:
                return git_result
            
            # Enhance with user metadata
            user_lookup = TODOResolverFactory.get_user_lookup_service(self.session)
            
            # Get database metadata for files
            db_files = await self.repository.get_branch_files(branch_id)
            
            # Combine Git data with database metadata
            files = []
            for git_file in git_result["files"]:
                # Find matching database record
                db_file = next((f for f in db_files if f.file_path == git_file["file_path"]), None)
                
                if db_file:
                    created_by_info = await user_lookup.get_user_info(str(db_file.created_by))
                    last_modified_by_info = None
                    if db_file.last_modified_by:
                        last_modified_by_info = await user_lookup.get_user_info(str(db_file.last_modified_by))
                    
                    file_response = {
                        "id": str(db_file.id),
                        "file_path": git_file["file_path"],
                        "file_name": git_file["file_name"],
                        "file_type": db_file.file_type,
                        "file_size": git_file["file_size"],
                        "created_by": {
                            "id": created_by_info["id"],
                            "name": created_by_info["name"],
                            "email": created_by_info["email"],
                            "created_at": created_by_info.get("created_at"),
                            "is_active": created_by_info.get("is_active", True)
                        } if created_by_info else None,
                        "updated_at": git_file["last_modified"],
                        "last_modified_by": {
                            "id": last_modified_by_info["id"],
                            "name": last_modified_by_info["name"],
                            "email": last_modified_by_info["email"],
                            "created_at": last_modified_by_info.get("created_at"),
                            "is_active": last_modified_by_info.get("is_active", True)
                        } if last_modified_by_info else None,
                        "has_active_session": False  # TODO: Check for active collaboration sessions
                    }
                    files.append(file_response)
                else:
                    # File exists in Git but not in database (created outside ResXiv)
                    # Create a basic response without user info
                    files.append({
                        "id": None,
                        "file_path": git_file["file_path"],
                        "file_name": git_file["file_name"],
                        "file_type": "tex",  # Default type
                        "file_size": git_file["file_size"],
                        "created_by": None,
                        "updated_at": git_file["last_modified"],
                        "last_modified_by": None,
                        "has_active_session": False
                    })
            
            return {
                "success": True,
                "files": files,
                "total_count": len(files),
                "branch_id": str(branch_id),
                "branch_name": branch.name
            }
            
        except Exception as e:
            logger.error(f"Error getting branch files: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get files: {str(e)}"
            }
    
    @handle_service_errors("get file content")
    async def get_file_content(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get file content from Git repository.
        
        Args:
            file_id: File ID
            user_id: User requesting content
            
        Returns:
            File content from Git
        """
        try:
            # Get file metadata
            file_metadata = await self.repository.get_file_by_id(file_id)
            if not file_metadata:
                return {
                    "success": False,
                    "error": "File not found"
                }
            
            # Check permissions
            permission = await self.repository.get_user_branch_permission(
                branch_id=file_metadata.branch_id,
                user_id=user_id
            )
            
            if not permission or not permission.can_read:
                return {
                    "success": False,
                    "error": "Read permission required"
                }
            
            # Get branch info
            branch = await self.repository.get_branch_by_id(file_metadata.branch_id)
            
            # Initialize repository if it doesn't exist
            from app.repositories.project_repository import ProjectRepository
            project_repo = ProjectRepository(self.session)
            project = await project_repo.get_project_by_id(file_metadata.project_id)
            
            if project:
                # Check if repository exists, if not initialize it
                existing_repo = await self.repository.get_project_git_repository(file_metadata.project_id)
                if not existing_repo:
                    logger.info(f"Initializing Git repository for project {file_metadata.project_id}")
                    init_result = await self.initialize_project_repository(
                        project_id=file_metadata.project_id,
                        project_name=project.name,
                        user_id=user_id
                    )
                    if not init_result["success"]:
                        return {
                            "success": False,
                            "error": f"Failed to initialize repository: {init_result.get('error', 'Unknown error')}"
                        }
            
            # Read from Git repository
            git_result = await self.git_service.read_file_from_repository(
                project_id=file_metadata.project_id,
                branch_name=branch.name,
                file_path=file_metadata.file_path
            )
            
            return git_result
            
        except Exception as e:
            logger.error(f"Error getting file content: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get file content: {str(e)}"
            }
    
    @handle_service_errors("update file content")
    async def update_file_content(
        self,
        file_id: uuid.UUID,
        content: str,
        user_id: uuid.UUID,
        commit_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update file content in Git repository.
        
        Args:
            file_id: File ID
            content: New file content
            user_id: User updating file
            commit_message: Commit message
            
        Returns:
            Update result
        """
        try:
            # Get file metadata
            file_metadata = await self.repository.get_file_by_id(file_id)
            if not file_metadata:
                return {
                    "success": False,
                    "error": "File not found"
                }
            
            # Check permissions
            permission = await self.repository.get_user_branch_permission(
                branch_id=file_metadata.branch_id,
                user_id=user_id
            )
            
            if not permission or not permission.can_write:
                return {
                    "success": False,
                    "error": "Write permission required"
                }
            
            # Get branch and user info
            branch = await self.repository.get_branch_by_id(file_metadata.branch_id)
            
            # Initialize repository if it doesn't exist
            from app.repositories.project_repository import ProjectRepository
            project_repo = ProjectRepository(self.session)
            project = await project_repo.get_project_by_id(file_metadata.project_id)
            
            if project:
                # Check if repository exists, if not initialize it
                existing_repo = await self.repository.get_project_git_repository(file_metadata.project_id)
                if not existing_repo:
                    logger.info(f"Initializing Git repository for project {file_metadata.project_id}")
                    init_result = await self.initialize_project_repository(
                        project_id=file_metadata.project_id,
                        project_name=project.name,
                        user_id=user_id
                    )
                    if not init_result["success"]:
                        return {
                            "success": False,
                            "error": f"Failed to initialize repository: {init_result.get('error', 'Unknown error')}"
                        }
            
            user_lookup = TODOResolverFactory.get_user_lookup_service(self.session)
            user_info = await user_lookup.get_user_info(str(user_id))
            
            author_name = user_info.get("name", "ResXiv User") if user_info else "ResXiv User"
            author_email = user_info.get("email", "user@resxiv.com") if user_info else "user@resxiv.com"
            
            # Write to Git repository
            git_result = await self.git_service.write_file_to_repository(
                project_id=file_metadata.project_id,
                branch_name=branch.name,
                file_path=file_metadata.file_path,
                content=content,
                commit_message=commit_message or f"Update {file_metadata.file_path}",
                author_name=author_name,
                author_email=author_email
            )
            
            if not git_result["success"]:
                return git_result
            
            # Update metadata
            file_metadata.file_size = len(content.encode('utf-8'))
            file_metadata.last_modified_by = user_id
            branch.head_commit_hash = git_result["commit_hash"]
            
            await self.session.commit()
            
            return {
                "success": True,
                "message": "File updated successfully",
                "commit_hash": git_result["commit_hash"]
            }
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating file: {str(e)}")
            return {
                "success": False,
                "error": f"File update failed: {str(e)}"
            }
    
    # ================================
    # PERMISSION OPERATIONS (unchanged)
    # ================================
    
    async def update_branch_permissions(
        self,
        branch_id: uuid.UUID,
        permission_updates: List[BranchPermissionUpdate],
        admin_user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Update branch permissions (unchanged from original)"""
        try:
            updated_count = 0
            errors = []
            
            for update in permission_updates:
                try:
                    success = await self.repository.update_branch_permission(
                        branch_id=branch_id,
                        user_id=update.user_id,
                        can_read=update.can_read,
                        can_write=update.can_write,
                        can_admin=update.can_admin,
                        granted_by=admin_user_id
                    )
                    
                    if success:
                        updated_count += 1
                    else:
                        errors.append(f"Failed to update permissions for user {update.user_id}")
                        
                except Exception as e:
                    errors.append(f"Error updating user {update.user_id}: {str(e)}")
            
            await self.session.commit()
            
            return {
                "success": True,
                "updated_count": updated_count,
                "errors": errors,
                "message": f"Updated permissions for {updated_count} users"
            }
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating branch permissions: {str(e)}")
            return {
                "success": False,
                "error": f"Permission update failed: {str(e)}"
            } 
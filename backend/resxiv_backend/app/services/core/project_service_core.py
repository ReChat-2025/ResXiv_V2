"""
Production-Grade Project Core Service
L6 Engineering Standards Implementation

Single Responsibility: Core project CRUD operations only
- Project creation, reading, updating, deletion
- Member management 
- Basic access control validation

Separated from:
- Statistics (ProjectStatsService)
- Advanced features (ProjectExtendedService)
- Email operations (EmailService)
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.service_factory import BaseService
from app.repositories.project_repository import ProjectRepository
from app.models.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectListItem,
    ProjectSearchRequest,
    MemberAdd,
    MemberUpdate,
)
from app.core.error_handler import ProductionErrorHandler, ErrorCategories

logger = logging.getLogger(__name__)

class ProjectCoreService(BaseService):
    """
    Core project service focused on essential CRUD operations.
    Follows single responsibility principle - no business logic bloat.
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.repository = ProjectRepository(session)
    
    async def health_check(self) -> bool:
        """Service health check"""
        try:
            # Simple repository health check
            return await self.repository.health_check()
        except Exception as e:
            self.logger.error(f"Project service health check failed: {e}")
            return False
    
    # ================================
    # CORE PROJECT OPERATIONS
    # ================================
    
    async def create_project(
        self,
        project_data: ProjectCreate,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Create project with user as owner and initialize Git repository.
        L6 Engineering Standards: Proper version control from day one.
        """
        try:
            self.logger.info(f"Creating project: {project_data.name} by user {user_id}")
            
            # Validate slug uniqueness
            if project_data.slug:
                if await self.repository.get_project_by_slug(project_data.slug):
                    return {
                        "success": False,
                        "error": f"Project with slug '{project_data.slug}' already exists"
                    }
            
            # Generate unique slug if not provided
            if not project_data.slug:
                base_slug = self._generate_unique_slug(project_data.name)
                project_data.slug = await self._ensure_slug_unique(base_slug)
            
            # Create project and eagerly load relationships
            project = await self.repository.create_project(project_data, user_id)
            
            # NEW: Initialize Git repository immediately for L6 standards
            try:
                from app.services.branch_service import BranchService
                branch_service = BranchService(self.session)
                
                self.logger.info(f"Initializing Git repository for project {project.id}")
                git_result = await branch_service.initialize_project_repository(
                    project_id=project.id,
                    project_name=project.name,
                    user_id=user_id
                )
                
                if not git_result["success"]:
                    # Rollback project creation if Git initialization fails
                    await self.session.rollback()
                    return {
                        "success": False,
                        "error": f"Project created but Git initialization failed: {git_result.get('error', 'Unknown error')}"
                    }
                    
                self.logger.info(f"✅ Git repository initialized for project {project.id} at {git_result['repo_path']}")
                
            except Exception as git_error:
                # Rollback project creation if Git initialization fails
                await self.session.rollback()
                self.logger.error(f"Git initialization failed for project {project.id}: {git_error}")
                return {
                    "success": False,
                    "error": f"Project created but Git initialization failed: {str(git_error)}"
                }
            
            # Commit everything if Git initialization succeeded
            await self.session.commit()
            
            # Load full project details
            project_obj = await self.repository.get_project_by_id(
                project.id, include_members=True, include_invitations=True
            )
            
            return {
                "success": True,
                "project": ProjectResponse.from_orm(project_obj),
                "git_initialized": True,
                "git_repo_path": git_result["repo_path"],
                "main_branch_id": git_result["main_branch_id"]
            }
            
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Failed to create project: {e}")
            return {
                "success": False,
                "error": "Failed to create project"
            }
    
    async def get_project(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[ProjectResponse]:
        """Get project details"""
        try:
            # Load project with members and pending invitations
            project_obj = await self.repository.get_project_by_id(
                project_id, include_members=True, include_invitations=True
            )
            if not project_obj:
                return None

            # Build Pydantic response
            project_response = ProjectResponse.from_orm(project_obj)

            # Set current user's access info
            user_role = await self.repository.get_user_role(project_id, user_id) or "reader"
            project_response.current_user_role = user_role
            project_response.current_user_can_read = True
            project_response.current_user_can_write = user_role in ["write", "admin", "owner"]
            project_response.current_user_can_admin = user_role in ["admin", "owner"]
            project_response.current_user_is_owner = user_role == "owner"

            # Populate basic stats
            project_response.member_count = await self.repository.get_project_member_count(project_id)

            return project_response
        except Exception as e:
            self.logger.error(f"Failed to get project {project_id}: {e}")
            return None
    
    async def update_project(
        self,
        project_id: uuid.UUID,
        project_data: ProjectUpdate,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Update project and return success status"""
        try:
            updated = await self.repository.update_project(
                project_id=project_id,
                project_data=project_data
            )
            if not updated:
                return {"success": False, "error": "Project not found or no changes applied"}
            return {"success": True}
        except Exception as e:
            self.logger.error(f"Failed to update project {project_id}: {e}")
            return {"success": False, "error": "Failed to update project"}
    
    async def delete_project(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Delete project if user is owner"""
        try:
            # Soft delete project
            deleted = await self.repository.soft_delete_project(project_id)
            if not deleted:
                return {"success": False, "error": "Project not found or already deleted"}
            return {"success": True}
            
        except Exception as e:
            self.logger.error(f"Failed to delete project {project_id}: {e}")
            return {
                "success": False,
                "error": "Failed to delete project"
            }
    
    # ================================
    # MEMBER MANAGEMENT
    # ================================
    
    async def add_member(
        self,
        project_id: uuid.UUID,
        member_data: MemberAdd,
        admin_user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Add member if admin has permission"""
        try:
            # Verify admin access
            if not await self.repository.user_has_admin_access(project_id, admin_user_id):
                return {"success": False, "error": "Insufficient permissions"}

            # Gather context for e-mails once (project + inviter)
            project_obj = await self.repository.get_project_by_id(project_id)
            if not project_obj:
                return {"success": False, "error": "Project not found"}

            try:
                inviter_user = await self.repository.get_user_by_id(admin_user_id)  # type: ignore[attr-defined]
                inviter_name = inviter_user.name if inviter_user else str(admin_user_id)
            except Exception:
                inviter_name = str(admin_user_id)
            project_name_val = project_obj.name

            from app.models.project import (
                MemberResponse, InvitationCreate, InvitationResponse
            )
            from app.services.notification_service import (
                send_project_invitation_notification,
            )

            # Case 1 – existing user by ID  ➜ add as member
            if member_data.user_id:
                member_obj = await self.repository.add_member(
                    project_id,
                    member_data.user_id,
                    member_data.role.value,
                )

                # Optional e-mail
                if member_data.send_invitation:
                    await send_project_invitation_notification(
                        self.session,
                        inviter_name=inviter_name,
                        project_name=project_name_val,
                        invitation_token=None,
                        user_id=member_data.user_id,
                    )

                return {"success": True, "member": MemberResponse.from_orm(member_obj)}

            # Case 2 – invite via e-mail ✅
            invitation_data = InvitationCreate(
                email=member_data.email,  # type: ignore
                role=member_data.role,
                permission=member_data.permission,
                message=member_data.message,
                expires_in_days=7,
            )
            invitation = await self.repository.create_invitation(
                invitation_data, project_id, admin_user_id
            )

            # send email if requested
            if member_data.send_invitation:
                await send_project_invitation_notification(
                    self.session,
                    inviter_name=inviter_name,
                    project_name=project_name_val,
                    invitation_token=invitation.invitation_token,
                    email=invitation.email,
                )

            invitation_resp = InvitationResponse.from_orm(invitation)
            return {"success": True, "invitation": invitation_resp}
        except Exception as e:
            self.logger.error(f"Failed to add member to project {project_id}: {e}")
            return {"success": False, "error": "Failed to add member"}
    
    async def remove_member(
        self,
        project_id: uuid.UUID,
        member_id: uuid.UUID,
        admin_user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Remove member if admin has permission"""
        try:
            # Verify admin access
            if not await self.repository.user_has_admin_access(project_id, admin_user_id):
                return {
                    "success": False,
                    "error": "Insufficient permissions"
                }
            
            # Prevent removing last owner
            if await self.repository.is_last_owner(project_id, member_id):
                return {
                    "success": False,
                    "error": "Cannot remove the last owner"
                }
            
            await self.repository.remove_member(project_id, member_id)
            
            return {"success": True}
            
        except Exception as e:
            self.logger.error(f"Failed to remove member from project {project_id}: {e}")
            return {
                "success": False,
                "error": "Failed to remove member"
            }
    
    # Wrapper methods for endpoints
    async def add_project_member(
        self,
        project_id: uuid.UUID,
        member_data: MemberAdd,
        added_by: uuid.UUID
    ) -> Dict[str, Any]:
        """Endpoint wrapper to add a project member"""
        return await self.add_member(project_id, member_data, added_by)

    async def get_project_members(
        self,
        project_id: uuid.UUID,
        requesting_user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Endpoint wrapper to list project members"""
        project_obj = await self.repository.get_project_by_id(
            project_id, include_members=True
        )
        if not project_obj:
            return {"success": False, "error": "Project not found"}
        # Convert to Pydantic models
        from app.models.project import MemberResponse
        members = [MemberResponse.from_orm(m) for m in project_obj.members]
        return {"success": True, "data": members}

    async def update_project_member(
        self,
        project_id: uuid.UUID,
        member_user_id: uuid.UUID,
        member_data: MemberUpdate,
        updated_by: uuid.UUID
    ) -> Dict[str, Any]:
        """Endpoint wrapper to update a project member.

        The path param is documented as *member user UUID* but many clients pass
        the ProjectMember.id instead.  We transparently resolve that case so we
        always operate with a real `user_id`.
        """

        user_id_to_use = member_user_id
        # Does this ID correspond to a user record?
        if not await self.repository.get_user_by_id(member_user_id):  # type: ignore[attr-defined]
            member_obj = await self.repository.get_project_member_by_id(member_user_id)
            if not member_obj:
                return {"success": False, "error": "Member not found"}
            user_id_to_use = member_obj.user_id

        # Apply role update
        if member_data.role:
            await self.repository.update_member_role(
                project_id, user_id_to_use, member_data.role.value
            )
        # Apply permission update
        if member_data.permission:
            await self.repository.add_collaborator(
                project_id, user_id_to_use, member_data.permission.value
            )

        return {"success": True}

    async def remove_project_member(
        self,
        project_id: uuid.UUID,
        member_user_id: uuid.UUID,
        removed_by: uuid.UUID
    ) -> Dict[str, Any]:
        """Endpoint wrapper to remove a project member"""
        # Resolve to actual user_id if a ProjectMember.id is provided
        user_id_to_use = member_user_id
        if not await self.repository.get_user_by_id(member_user_id):  # type: ignore[attr-defined]
            member_obj = await self.repository.get_project_member_by_id(member_user_id)
            if not member_obj:
                return {"success": False, "error": "Member not found"}
            user_id_to_use = member_obj.user_id

        return await self.remove_member(project_id, user_id_to_use, removed_by)
    
    async def get_project_invitations(
        self,
        project_id: uuid.UUID,
        requesting_user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get all pending invitations for a project.
        
        Args:
            project_id: Project UUID
            requesting_user_id: User requesting the invitations (must be admin)
            
        Returns:
            Dict containing success status and list of invitations
        """
        try:
            # Verify user has admin access to the project
            user_access = await self.get_user_project_access(requesting_user_id, project_id)
            if not user_access["success"] or user_access["role"] != "admin":
                return {
                    "success": False,
                    "error": "Insufficient permissions to view project invitations"
                }
            
            # Get pending invitations from repository
            invitations = await self.repository.get_pending_invitations(project_id)
            
            # Convert to response format
            from app.models.project import InvitationResponse
            invitation_responses = [
                InvitationResponse.from_orm(invitation) for invitation in invitations
            ]
            
            return {
                "success": True,
                "invitations": invitation_responses,
                "total_count": len(invitation_responses)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get invitations for project {project_id}: {e}")
            return {
                "success": False,
                "error": "Failed to retrieve project invitations"
            }
    
    async def get_user_projects(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        size: int = 20,
        search_query: Optional[str] = None,
        role_filter: Optional[str] = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc"
    ) -> ProjectListResponse:
        """Get projects for user with pagination and optional filtering"""
        try:
            # Fetch paginated projects and total count
            projects_list, total = await self.repository.get_user_projects(
                user_id=user_id,
                page=page,
                size=size,
                search_query=search_query,
                role_filter=role_filter,
                sort_by=sort_by,
                sort_order=sort_order
            )
            # Compute navigation
            has_next = page * size < total
            has_prev = page > 1
            return ProjectListResponse(
                projects=projects_list,
                total=total,
                page=page,
                size=size,
                has_next=has_next,
                has_prev=has_prev
            )
        except Exception as e:
            self.logger.error(f"Failed to get projects for user {user_id}: {e}")
            return ProjectListResponse(
                projects=[],
                total=0,
                page=page,
                size=size,
                has_next=False,
                has_prev=False
            )
    
    async def search_projects(
        self,
        search_request: ProjectSearchRequest,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Search projects for a user based on provided filters.
        """
        try:
            role_filter = search_request.role.value if search_request.role else None
            # Count total matching
            _, total = await self.repository.get_user_projects(
                user_id=user_id,
                page=1,
                size=1,
                search_query=search_request.query,
                role_filter=role_filter
            )
            # Fetch all matches
            projects, _ = await self.repository.get_user_projects(
                user_id=user_id,
                page=1,
                size=total,
                search_query=search_request.query,
                role_filter=role_filter
            )
            # Build items
            items = []
            for proj in projects:
                item = ProjectListItem.from_orm(proj)
                user_role = await self.repository.get_user_role(proj.id, user_id) or "reader"
                item.current_user_role = user_role
                item.member_count = await self.repository.get_project_member_count(proj.id)
                items.append(item)
            return {
                "success": True,
                "data": ProjectListResponse(
                    projects=items,
                    total=total,
                    page=1,
                    size=total,
                    has_next=False,
                    has_prev=False
                )
            }
        except Exception as e:
            self.logger.error(f"Failed to search projects: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_user_project_access(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Return the caller's access details for a project (role/permission flags)."""
        try:
            project = await self.repository.get_project_by_id(project_id)
            if not project:
                return {"success": False, "error": "Project not found"}

            role = await self.repository.get_user_role(project_id, user_id)
            permission = await self.repository.get_user_permission(project_id, user_id)

            can_read = True  # membership verified by dependency
            can_write = role in ("write", "admin", "owner") or permission in ("write", "admin")
            can_admin = role in ("admin", "owner") or permission == "admin"
            is_owner = role == "owner"

            from app.models.project import ProjectAccessSummary
            summary = ProjectAccessSummary(
                project_id=project_id,
                user_id=user_id,
                role=role,
                permission=permission,
                can_read=can_read,
                can_write=can_write,
                can_admin=can_admin,
                is_owner=is_owner,
                access_source="member" if role else "collaborator" if permission else "guest",
            )
            return {"success": True, "data": summary}
        except Exception as exc:
            self.logger.error(
                "Failed to compute access for project %s user %s: %s", project_id, user_id, exc
            )
            return {"success": False, "error": "Failed to get access info"}
    
    # ================================
    # UTILITY METHODS
    # ================================
    
    def _generate_unique_slug(self, name: str) -> str:
        """Generate URL-friendly slug from project name"""
        import re
        
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', name.lower())
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')
        
        # Truncate if too long
        return slug[:50]
    
    async def _ensure_slug_unique(self, base_slug: str) -> str:
        """Ensure slug is unique by adding counter if needed"""
        slug = base_slug
        counter = 1
        
        while await self.repository.get_project_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug 
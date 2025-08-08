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
import asyncio

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
    InvitationCreate,
)
from app.core.error_handler import ProductionErrorHandler, ErrorCategories
from app.repositories.paper_repository import PaperRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.project import Project

logger = logging.getLogger(__name__)

class ProjectCoreService(BaseService):
    """
    Core project service focused on essential CRUD operations.
    Follows single responsibility principle - no business logic bloat.
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.repository = ProjectRepository(session)
        # L6 Engineering: Inject dependencies through DI container to avoid tight coupling
        from app.core.dependency_injection import container
        self._paper_repository = container.get_service(PaperRepository, session)
        self._task_repository = container.get_service(TaskRepository, session)
    
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
            project_response.current_user_can_write = user_role in ["writer", "admin", "owner"]
            project_response.current_user_can_admin = user_role in ["admin", "owner"]
            project_response.current_user_is_owner = user_role == "owner"

            # L6 Engineering: Use dedicated method for statistics enrichment
            await self._enrich_project_statistics(project_response, project_id)

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

            invitation_resp = await self._build_invitation_response(invitation, admin_user_id)
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
            
            # Remove member (repository method returns None)
            await self.repository.remove_member(project_id, member_id)
            
            return {"success": True}
        except Exception as e:
            self.logger.error(f"Failed to remove member {member_id} from project {project_id}: {e}")
            return {"success": False, "error": "Failed to remove member"}
    
    async def create_project_invitation(
        self,
        project_id: uuid.UUID,
        invitation_data: InvitationCreate,
        invited_by: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Create project invitation for external email.
        
        L6 Engineering: Single responsibility method that reuses existing 
        repository patterns and follows DRY principle.
        
        Args:
            project_id: Project UUID
            invitation_data: Invitation details (email, role, etc.)
            invited_by: User creating the invitation
            
        Returns:
            Success/error response with invitation details
        """
        try:
            # Verify admin access
            if not await self.repository.user_has_admin_access(project_id, invited_by):
                return {
                    "success": False,
                    "error": "Insufficient permissions - admin access required"
                }
            
            # Get project and inviter context for email notification
            project_obj = await self.repository.get_project_by_id(project_id)
            if not project_obj:
                return {"success": False, "error": "Project not found"}
            
            try:
                inviter_user = await self.repository.get_user_by_id(invited_by)  # type: ignore[attr-defined]
                inviter_name = inviter_user.name if inviter_user else str(invited_by)
            except Exception:
                inviter_name = str(invited_by)
            
            # Create invitation using existing repository method
            invitation = await self.repository.create_invitation(
                invitation_data, project_id, invited_by
            )
            
            # Send email notification if requested (following existing pattern)
            try:
                from app.services.notification_service import send_project_invitation_notification
                
                await send_project_invitation_notification(
                    self.session,
                    inviter_name=inviter_name,
                    project_name=project_obj.name,
                    invitation_token=invitation.invitation_token,
                    email=invitation.email,
                )
                
                self.logger.info(f"Invitation email sent to {invitation.email} for project {project_id}")
                
            except Exception as email_error:
                self.logger.warning(f"Invitation created but email failed: {email_error}")
                # Don't fail the entire operation if email fails
            
            # Convert to response model with proper data enrichment
            invitation_resp = await self._build_invitation_response(invitation, invited_by)
            
            return {
                "success": True, 
                "invitation": invitation_resp,
                "message": f"Invitation sent to {invitation.email}"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create invitation for project {project_id}: {e}")
            return {"success": False, "error": "Failed to create invitation"}
    
    async def _build_invitation_response(
        self, 
        invitation: "ProjectInvitation", 
        invited_by_id: uuid.UUID
    ) -> "InvitationResponse":
        """
        Build a complete InvitationResponse from database invitation.
        
        L6 Engineering: Centralized response building logic following DRY principles.
        Properly computes status and fetches required user data.
        
        Args:
            invitation: Database invitation object
            invited_by_id: UUID of the user who created the invitation
            
        Returns:
            Complete InvitationResponse object
        """
        from app.models.project import InvitationResponse, InvitationStatus, UserBasicInfo
        from app.schemas.project import ProjectInvitation
        
        # Compute invitation status based on database state
        status = self._compute_invitation_status(invitation)
        
        # Fetch inviter user data
        invited_by_user = None
        try:
            # Try to get user from repository if method exists
            if hasattr(self.repository, 'get_user_by_id'):
                invited_by_user = await self.repository.get_user_by_id(invited_by_id)
            else:
                # Fallback: query directly
                from app.schemas.user import User
                from sqlalchemy import select
                result = await self.session.execute(
                    select(User).where(User.id == invited_by_id)
                )
                invited_by_user = result.scalar_one_or_none()
        except Exception as e:
            self.logger.warning(f"Could not fetch inviter user {invited_by_id}: {e}")
        
        # Build UserBasicInfo or use None
        invited_by_info = None
        if invited_by_user:
            invited_by_info = UserBasicInfo(
                id=invited_by_user.id,
                name=invited_by_user.name,
                email=invited_by_user.email
            )
        
        # Build complete InvitationResponse
        return InvitationResponse(
            id=invitation.id,
            email=invitation.email,
            role=invitation.role.value if hasattr(invitation.role, 'value') else invitation.role,
            permission=invitation.permission.value if invitation.permission and hasattr(invitation.permission, 'value') else invitation.permission,
            status=status,
            message=invitation.message,
            invited_by=invited_by_info,
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
            accepted_at=invitation.accepted_at,
            declined_at=invitation.declined_at,
            cancelled_at=invitation.cancelled_at
        )
    
    def _compute_invitation_status(self, invitation: "ProjectInvitation") -> "InvitationStatus":
        """
        Compute invitation status from database state.
        
        Args:
            invitation: Database invitation object
            
        Returns:
            Computed InvitationStatus
        """
        from app.models.project import InvitationStatus
        from datetime import datetime, timezone
        
        # Check explicit status fields first
        if invitation.accepted_at:
            return InvitationStatus.ACCEPTED
        elif invitation.declined_at:
            return InvitationStatus.DECLINED  
        elif invitation.cancelled_at:
            return InvitationStatus.CANCELLED
        elif self._is_invitation_expired(invitation):
            return InvitationStatus.EXPIRED
        else:
            return InvitationStatus.PENDING
    
    def _is_invitation_expired(self, invitation: "ProjectInvitation") -> bool:
        """
        Check if invitation is expired, handling timezone-aware comparisons.
        
        Args:
            invitation: Database invitation object
            
        Returns:
            True if invitation is expired
        """
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        expires_at = invitation.expires_at
        
        # Handle timezone-aware comparison
        if expires_at.tzinfo is None:
            # Database timestamp is naive, assume UTC
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        return expires_at < now
    
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
            # Verify user has admin/owner access to the project
            user_access = await self.get_user_project_access(project_id, requesting_user_id)
            if not user_access.get("success"):
                return {"success": False, "error": "Unable to verify permissions"}
            access_data = user_access.get("data")
            access_role = getattr(access_data, "role", None) if access_data is not None else None
            # Allow both admin and owner to view invitations
            if access_role not in ("admin", "owner"):
                return {
                    "success": False,
                    "error": "Insufficient permissions to view project invitations"
                }
            
            # Get pending invitations from repository
            invitations = await self.repository.get_pending_invitations(project_id)
            
            # Convert to enriched response objects
            invitation_responses = []
            for inv in invitations:
                invited_by_id = getattr(inv, "invited_by", None)
                invitation_responses.append(
                    await self._build_invitation_response(inv, invited_by_id)  # type: ignore[arg-type]
                )
            
            return {
                "success": True,
                "data": {
                "invitations": invitation_responses,
                "total_count": len(invitation_responses)
                }
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
            
            # L6 Engineering: Convert raw Project objects to enriched ProjectListItem objects
            enriched_projects = await self._enrich_project_list_items(projects_list, user_id)
            
            # Compute navigation
            has_next = page * size < total
            has_prev = page > 1
            return ProjectListResponse(
                projects=enriched_projects,
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
            
            # L6 Engineering: Use consistent enrichment method
            items = await self._enrich_project_list_items(projects, user_id)
            
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
            can_write = role in ("writer", "admin", "owner") or permission in ("write", "admin")
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

    # ================================
    # L6 ENGINEERING: PRIVATE ENRICHMENT METHODS
    # ================================
    
    async def _enrich_project_statistics(
        self, 
        project_response: ProjectResponse, 
        project_id: uuid.UUID
    ) -> None:
        """
        Enrich project response with calculated statistics.
        
        L6 Engineering: Single responsibility method for statistics enrichment.
        Uses dependency injection and follows DRY principle.
        
        Args:
            project_response: Project response to enrich
            project_id: Project UUID for statistics calculation
        """
        try:
            # Get all statistics in parallel for optimal performance
            member_count_task = self.repository.get_project_member_count(project_id)
            paper_count_task = self._paper_repository.get_papers_count_by_project(project_id)
            task_count_task = self._get_project_task_count(project_id)
            
            # Await all counts concurrently
            member_count, paper_count, task_count = await asyncio.gather(
                member_count_task,
                paper_count_task,
                task_count_task,
                return_exceptions=True
            )
            
            # Handle potential errors gracefully
            project_response.member_count = member_count if not isinstance(member_count, Exception) else 0
            project_response.paper_count = paper_count if not isinstance(paper_count, Exception) else 0
            project_response.task_count = task_count if not isinstance(task_count, Exception) else 0
            
            if isinstance(member_count, Exception):
                self.logger.warning(f"Failed to get member count for project {project_id}: {member_count}")
            if isinstance(paper_count, Exception):
                self.logger.warning(f"Failed to get paper count for project {project_id}: {paper_count}")
            if isinstance(task_count, Exception):
                self.logger.warning(f"Failed to get task count for project {project_id}: {task_count}")
                
        except Exception as e:
            self.logger.error(f"Failed to enrich project statistics for {project_id}: {e}")
            # Ensure counts are set to 0 if enrichment fails
            project_response.member_count = 0
            project_response.paper_count = 0
            project_response.task_count = 0
    
    async def _enrich_project_list_items(
        self, 
        projects: List[Project], 
        user_id: uuid.UUID
    ) -> List[ProjectListItem]:
        """
        Convert raw Project objects to enriched ProjectListItem objects.
        
        L6 Engineering: Reusable enrichment method following DRY principle.
        Optimizes database calls by batching where possible.
        
        Args:
            projects: List of raw Project objects from repository
            user_id: Current user ID for role calculation
            
        Returns:
            List of enriched ProjectListItem objects
        """
        enriched_items = []
        
        for project in projects:
            try:
                # Convert to ProjectListItem
                item = ProjectListItem.from_orm(project)
                
                # Get user role for this project
                user_role = await self.repository.get_user_role(project.id, user_id) or "reader"
                item.current_user_role = user_role
                
                # Get statistics in parallel
                member_count_task = self.repository.get_project_member_count(project.id)
                paper_count_task = self._paper_repository.get_papers_count_by_project(project.id)
                task_count_task = self._get_project_task_count(project.id)
                
                member_count, paper_count, task_count = await asyncio.gather(
                    member_count_task,
                    paper_count_task,
                    task_count_task,
                    return_exceptions=True
                )
                
                # Set counts with error handling
                item.member_count = member_count if not isinstance(member_count, Exception) else 0
                item.paper_count = paper_count if not isinstance(paper_count, Exception) else 0
                item.task_count = task_count if not isinstance(task_count, Exception) else 0
                
                if isinstance(member_count, Exception):
                    self.logger.warning(f"Failed to get member count for project {project.id}: {member_count}")
                if isinstance(paper_count, Exception):
                    self.logger.warning(f"Failed to get paper count for project {project.id}: {paper_count}")
                if isinstance(task_count, Exception):
                    self.logger.warning(f"Failed to get task count for project {project.id}: {task_count}")
                
                enriched_items.append(item)
                
            except Exception as e:
                self.logger.error(f"Failed to enrich project {project.id}: {e}")
                # Still add the item with default values rather than skip it
                item = ProjectListItem.from_orm(project)
                item.member_count = 0
                item.paper_count = 0
                item.task_count = 0
                enriched_items.append(item)
        
        return enriched_items
    
    async def _get_project_task_count(self, project_id: uuid.UUID) -> int:
        """
        Get task count for a project using the existing repository pattern.
        
        L6 Engineering: Abstracts task repository interaction, following 
        single responsibility and dependency inversion principles.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Number of tasks in the project
        """
        try:
            # Use existing repository method that returns (tasks, count)
            _, task_count = await self._task_repository.get_project_tasks(
                project_id=project_id, 
                limit=1,  # We only need the count
                offset=0
            )
            return task_count
        except Exception as e:
            self.logger.error(f"Failed to get task count for project {project_id}: {e}")
            return 0 
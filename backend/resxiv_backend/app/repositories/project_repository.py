"""project_repository.py

Repository layer for project membership & permission queries.

This file contains only the boiler-plate – real SQLAlchemy queries will be
filled in later.  All methods are asynchronous to support the async engine.

Design notes
------------
• Keeps database access logic out of service / dependency layers
• Easy to unit-test by injecting an async session and mocking queries
• Will ultimately expose many helpers (list members, add, remove, etc.)
"""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import select, insert, func, desc, asc, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.schemas.project import (
    Project, ProjectMember, ProjectRoleEnum, ProjectCollaborator, ProjectInvitation
)
from app.schemas.user import User
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
import secrets


class ProjectRepository:
    """Data-access helper for `projects` & related tables."""

    def __init__(self, session: AsyncSession):
        self._session: AsyncSession = session

    # ---------------------------------------------------------------------
    # Membership checks
    # ---------------------------------------------------------------------

    async def is_user_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Return True if the user is a member of the project."""
        stmt = (
            select(ProjectMember.id)
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_user_role(self, project_id: uuid.UUID, user_id: uuid.UUID) -> Optional[str]:
        """Return the user's role in the project, or None if not a member."""
        stmt = (
            select(ProjectMember.role)
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def is_project_owner(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Return True if user is owner of project."""
        stmt = select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id, ProjectMember.role == ProjectRoleEnum.owner)
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none() is not None
    
    async def user_has_admin_access(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Return True if user has admin or owner role in project."""
        role = await self.get_user_role(project_id, user_id)
        if role is None:
            return False
        # role may be enum or string
        role_str = role.value if hasattr(role, 'value') else str(role)
        return role_str in ('admin', 'owner')
    
    async def is_last_owner(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Return True if the given user is the only owner of the project"""
        # Count total owners
        stmt = select(func.count(ProjectMember.id))
        stmt = stmt.where(
            ProjectMember.project_id == project_id,
            ProjectMember.role == ProjectRoleEnum.owner
        )
        result = await self._session.execute(stmt)
        total = result.scalar() or 0
        if total != 1:
            return False
        # Verify the single owner is the given user
        return await self.is_project_owner(project_id, user_id)

    # ---------------------------------------------------------------------
    # CRUD helpers required by ProjectCoreService
    # ---------------------------------------------------------------------

    async def get_project_by_slug(self, slug: str) -> Optional[Project]:
        """Fetch a project by *slug* or return None."""
        stmt = (
            select(Project)
            .where(Project.slug == slug, Project.deleted_at.is_(None))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_project(self, project_data: "ProjectCreate", user_id: uuid.UUID) -> Project:  # type: ignore
        """Insert a new project and add the creator as *owner* member."""
        # Deferred import to avoid circular dependency of typing
        from app.models.project import ProjectCreate

        if not isinstance(project_data, ProjectCreate):
            raise ValueError("project_data must be ProjectCreate")

        project = Project(
            name=project_data.name,
            slug=project_data.slug,
            description=project_data.description,
            repo_url=project_data.repo_url,
            created_by=user_id,
        )
        self._session.add(project)
        await self._session.flush()  # project.id available

        owner_member = ProjectMember(
            user_id=user_id,
            project_id=project.id,
            role=ProjectRoleEnum.owner,
        )
        self._session.add(owner_member)
        await self._session.flush()

        await self._session.refresh(project)
        return project

    async def soft_delete_project(self, project_id: uuid.UUID) -> bool:
        """Soft-delete project (sets deleted_at). Returns True if a row was updated."""
        stmt = (
            update(Project)
            .where(Project.id == project_id, Project.deleted_at.is_(None))
            .values(deleted_at=datetime.utcnow())
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def update_project(self, project_id: uuid.UUID, project_data: "ProjectUpdate") -> Optional[Project]:
        """Update project fields and return updated project."""
        # Prepare values excluding unset fields
        data = project_data.dict(exclude_unset=True)
        if not data:
            return await self.get_project_by_id(project_id)
        stmt = (
            update(Project)
            .where(Project.id == project_id, Project.deleted_at.is_(None))
            .values(**data)
            .returning(Project)
        )
        result = await self._session.execute(stmt)
        project = result.scalar_one_or_none()
        if project:
            await self._session.refresh(project)
        return project

    # ---------------------------------------------------------------------
    # Additional helper stubs (placeholders)
    # ---------------------------------------------------------------------

    async def add_member(self, project_id: uuid.UUID, user_id: uuid.UUID, role: str) -> ProjectMember:
        """Add a user to a project with specified role."""
        from app.schemas.project import ProjectMember, ProjectRoleEnum
        # Ensure role is valid
        if isinstance(role, str):
            role_enum = ProjectRoleEnum(role)
        else:
            role_enum = role
        # Check if member already exists
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        ).limit(1)
        res = await self._session.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            await self.update_member_role(project_id, user_id, role_enum.value)
            # Eager-load user
            res2 = await self._session.execute(
                select(ProjectMember)
                .options(selectinload(ProjectMember.user))
                .where(ProjectMember.id == existing.id)
                .limit(1)
            )
            return res2.scalar_one()
        # Create new member
        member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            role=role_enum
        )
        self._session.add(member)
        await self._session.flush()
        # Eager-load user
        res3 = await self._session.execute(
            select(ProjectMember)
            .options(selectinload(ProjectMember.user))
            .where(ProjectMember.id == member.id)
            .limit(1)
        )
        return res3.scalar_one()

    async def update_member_role(self, project_id: uuid.UUID, user_id: uuid.UUID, role: str) -> None:
        """Update member role."""
        from app.schemas.project import ProjectMember, ProjectRoleEnum
        
        # Ensure role is valid
        if isinstance(role, str):
            role_enum = ProjectRoleEnum(role)
        else:
            role_enum = role
            
        stmt = (
            update(ProjectMember)
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id
            )
            .values(role=role_enum)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def remove_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Remove user from project."""
        from app.schemas.project import ProjectMember
        
        stmt = delete(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def add_collaborator(self, project_id: uuid.UUID, user_id: uuid.UUID, permission) -> None:
        """Insert a row into project_collaborators (idempotent)."""
        from app.schemas.project import ProjectCollaborator, PermissionType

        # Ensure we pass PermissionType enum for proper binding
        if isinstance(permission, str):
            permission_enum = PermissionType(permission)
        else:
            permission_enum = permission

        collab = ProjectCollaborator(project_id=project_id, user_id=user_id, permission=permission_enum)
        self._session.add(collab)
        await self._session.flush()

    async def get_user_permission(self, project_id: uuid.UUID, user_id: uuid.UUID) -> Optional[str]:
        """Return the user's permission in the collaborator table or None if not a collaborator."""
        stmt = (
            select(ProjectCollaborator.permission)
            .where(
                ProjectCollaborator.project_id == project_id,
                ProjectCollaborator.user_id == user_id
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_projects(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        size: int = 20,
        search_query: Optional[str] = None,
        role_filter: Optional[str] = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> tuple[list[Project], int]:
        """Return paginated list of projects the user belongs to."""
        stmt = (
            select(Project)
            .join(ProjectMember)
            .where(ProjectMember.user_id == user_id, Project.deleted_at.is_(None))
            .options(selectinload(Project.creator))
        )

        if role_filter:
            stmt = stmt.where(ProjectMember.role == role_filter)

        if search_query:
            from sqlalchemy import or_
            stmt = stmt.where(
                or_(Project.name.ilike(f"%{search_query}%"), Project.description.ilike(f"%{search_query}%"))
            )

        sort_column = getattr(Project, sort_by, Project.updated_at)
        stmt = stmt.order_by(desc(sort_column) if sort_order.lower() == "desc" else asc(sort_column))

        # total count
        total_result = await self._session.execute(select(func.count()).select_from(stmt.subquery()))
        total = total_result.scalar() or 0

        # pagination
        offset = (page - 1) * size
        stmt = stmt.offset(offset).limit(size)

        result = await self._session.execute(stmt)
        projects = result.scalars().all()

        return list(projects), total

    async def get_user_projects_count(self, user_id: uuid.UUID) -> int:
        """Return total number of projects for a user (no filters) using default pagination"""
        # Reuse get_user_projects default page and size
        _, total = await self.get_user_projects(user_id)
        return total

    async def get_project_member_count(self, project_id: uuid.UUID) -> int:
        """Return count of members in project."""
        stmt = select(func.count(ProjectMember.id)).where(ProjectMember.project_id == project_id)
        result = await self._session.execute(stmt)
        return int(result.scalar() or 0)

    async def add_project_member(self, project_id: uuid.UUID, user_id: uuid.UUID, role: str) -> ProjectMember:
        """Insert a row into project_members and return the created member."""
        # Check if already member
        stmt_check = (
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
            .limit(1)
        )
        res = await self._session.execute(stmt_check)
        existing = res.scalar_one_or_none()
        if existing:
            return existing  # idempotent
        
        member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            role=ProjectRoleEnum(role)
        )
        self._session.add(member)
        await self._session.flush()
        # Re-select with eager load so `.user` is ready for Pydantic
        res_member = await self._session.execute(
            select(ProjectMember)
            .options(selectinload(ProjectMember.user))
            .where(ProjectMember.id == member.id)
        )
        return res_member.scalar_one()

    async def create_invitation(
        self,
        invitation_data: "InvitationCreate",
        project_id: uuid.UUID,
        invited_by: uuid.UUID
    ) -> ProjectInvitation:
        """Create a new invitation and return it.

        If an active invitation already exists for the same email (or user),
        we cancel the previous one before inserting a fresh record so that
        only one pending invitation per (project,email) remains.
        """
        from app.models.project import InvitationCreate  # deferred import
        if not isinstance(invitation_data, InvitationCreate):
            raise ValueError("invitation_data must be InvitationCreate")

        # Cancel existing active invitations for same email
        await self._session.execute(
            update(ProjectInvitation)
            .where(
                ProjectInvitation.project_id == project_id,
                ProjectInvitation.email == invitation_data.email,
                ProjectInvitation.accepted_at.is_(None),
                ProjectInvitation.declined_at.is_(None),
                ProjectInvitation.cancelled_at.is_(None),
                ProjectInvitation.expires_at > datetime.utcnow(),
            )
            .values(cancelled_at=datetime.utcnow(), cancelled_by=invited_by)
        )

        # Generate secure token & expiry
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=invitation_data.expires_in_days)

        invitation = ProjectInvitation(
            project_id=project_id,
            invited_by=invited_by,
            email=invitation_data.email,
            role=invitation_data.role,
            permission=invitation_data.permission,
            invitation_token=token,
            message=invitation_data.message,
            expires_at=expires_at,
        )
        self._session.add(invitation)
        await self._session.flush()
        await self._session.refresh(invitation)
        return invitation

    async def get_pending_invitations(self, project_id: uuid.UUID):
        """Return list of pending invitations for a project."""
        stmt = (
            select(ProjectInvitation)
            .where(
                ProjectInvitation.project_id == project_id,
                ProjectInvitation.accepted_at.is_(None),
                ProjectInvitation.declined_at.is_(None),
                ProjectInvitation.cancelled_at.is_(None),
                ProjectInvitation.expires_at > datetime.utcnow()
            )
        )
        res = await self._session.execute(stmt)
        return res.scalars().all()

    async def get_invitation_by_token(self, token: str) -> Optional[ProjectInvitation]:
        """Fetch invitation by token."""
        res = await self._session.execute(
            select(ProjectInvitation).where(ProjectInvitation.invitation_token == token)
        )
        return res.scalar_one_or_none()

    async def update_invitation_status(
        self,
        invitation_id: uuid.UUID,
        accept: bool,
        user_id: uuid.UUID,
    ) -> bool:
        """Set accepted_at or declined_at on invitation."""
        fields = {
            "accepted_at": datetime.utcnow(),
            "accepted_by": user_id,
        } if accept else {"declined_at": datetime.utcnow()}

        res = await self._session.execute(
            update(ProjectInvitation)
            .where(ProjectInvitation.id == invitation_id)
            .values(**fields)
        )
        return res.rowcount > 0

    async def accept_invitation(self, invitation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        # Fetch invitation details
        inv: ProjectInvitation | None = await self.get_invitation_by_id(invitation_id)
        if inv is None:
            return False

        # Validate email matches user
        user = await self.get_user_by_id(user_id)
        if user is None or user.email.lower() != inv.email.lower():
            # email mismatch – reject
            return False

        # Mark invitation accepted
        ok = await self.update_invitation_status(invitation_id, True, user_id)
        if not ok:
            return False

        # Add member if not already
        await self.add_project_member(inv.project_id, user_id, inv.role.value)

        # Add collaborator if permission present
        if inv.permission:
            await self.add_collaborator(inv.project_id, user_id, inv.permission.value)

        return True

    async def decline_invitation(self, invitation_id: uuid.UUID) -> bool:
        return await self.update_invitation_status(invitation_id, False, uuid.uuid4())

    # ---------------------------------------------------------------------
    # Fetch helpers
    # ---------------------------------------------------------------------

    async def get_project_by_id(
        self,
        project_id: uuid.UUID,
        include_members: bool = False,
        include_invitations: bool = False,
    ) -> Optional[Project]:
        """Return a project by ID with optional eager-loaded relationships."""
        # Always eager-load the creator to avoid lazy-load in Pydantic
        options_list = [selectinload(Project.creator)]
        if include_members:
            options_list.append(selectinload(Project.members).selectinload(ProjectMember.user))
        if include_invitations:
            options_list.append(selectinload(Project.invitations))

        stmt = select(Project).where(Project.id == project_id, Project.deleted_at.is_(None))
        if options_list:
            stmt = stmt.options(*options_list)

        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Fetch a user basic record by ID."""
        res = await self._session.execute(select(User).where(User.id == user_id))
        return res.scalar_one_or_none()

    async def get_invitation_by_id(self, invitation_id: uuid.UUID) -> Optional[ProjectInvitation]:
        res = await self._session.execute(select(ProjectInvitation).where(ProjectInvitation.id == invitation_id))
        return res.scalar_one_or_none()

    async def get_project_member_by_id(self, member_id: uuid.UUID) -> Optional[ProjectMember]:
        """Return ProjectMember by member row ID, eagerly loading user."""
        res = await self._session.execute(
            select(ProjectMember).options(selectinload(ProjectMember.user)).where(ProjectMember.id == member_id)
        )
        return res.scalar_one_or_none()

    # More methods (invitations, stats, etc.) will be added as needed. 
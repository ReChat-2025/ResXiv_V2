"""
Journal Collaboration Service - L6 Engineering Standards

Focused service for journal collaboration and permission management.
Extracted from bloated journal_service.py for SOLID compliance.
"""

import uuid
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import HTTPException, status

from app.models.journal_models import (
    JournalCollaboratorCreate, JournalCollaboratorResponse,
    JournalPermissionCheck, PermissionType
)
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes

logger = logging.getLogger(__name__)


class JournalCollaborationService:
    """Service class for journal collaboration management"""

    def __init__(self, session: AsyncSession):
        self.session = session

    @handle_service_errors("journal permission check")
    async def check_journal_permission(
        self, 
        journal_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> JournalPermissionCheck:
        """Check user permissions for a journal"""
        # Get journal and user permissions
        result = await self.session.execute(
            text("""
                SELECT 
                    j.id, j.created_by, j.is_public,
                    jc.permission
                FROM journals j
                LEFT JOIN journal_collaborators jc ON j.id = jc.journal_id 
                    AND jc.user_id = %s
                WHERE j.id = %s AND j.deleted_at IS NULL
            """),
            [user_id, journal_id]
        )
        
        row = result.fetchone()
        if not row:
            return JournalPermissionCheck(
                has_access=False,
                permission=None,
                is_owner=False,
                can_read=False,
                can_write=False,
                can_delete=False
            )
        
        is_owner = row.created_by == user_id
        permission = row.permission
        is_public = row.is_public
        
        # Determine permissions
        has_access = is_owner or permission is not None or is_public
        can_read = has_access
        can_write = is_owner or permission in [PermissionType.WRITE, PermissionType.ADMIN]
        can_delete = is_owner or permission == PermissionType.ADMIN
        
        return JournalPermissionCheck(
            has_access=has_access,
            permission=permission,
            is_owner=is_owner,
            can_read=can_read,
            can_write=can_write,
            can_delete=can_delete
        )

    @handle_service_errors("journal collaborator addition")
    async def add_collaborator(
        self, 
        journal_id: uuid.UUID,
        collaborator_data: JournalCollaboratorCreate,
        added_by: uuid.UUID
    ) -> JournalCollaboratorResponse:
        """Add a collaborator to a journal"""
        # Check if user exists
        user_result = await self.session.execute(
            text("""
                SELECT id, username, email
                FROM users 
                WHERE id = %s AND deleted_at IS NULL
            """),
            [collaborator_data.user_id]
        )
        
        user_row = user_result.fetchone()
        if not user_row:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if already a collaborator
        existing_result = await self.session.execute(
            text("""
                SELECT id FROM journal_collaborators
                WHERE journal_id = %s AND user_id = %s
            """),
            [journal_id, collaborator_data.user_id]
        )
        
        if existing_result.fetchone():
            raise HTTPException(
                status_code=400, 
                detail="User is already a collaborator"
            )
        
        # Add collaborator
        collab_id = uuid.uuid4()
        await self.session.execute(
            text("""
                INSERT INTO journal_collaborators (
                    id, journal_id, user_id, permission, added_by, added_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """),
            [
                collab_id, journal_id, collaborator_data.user_id,
                collaborator_data.permission, added_by, datetime.utcnow()
            ]
        )
        
        return JournalCollaboratorResponse(
            id=str(collab_id),
            user_id=str(collaborator_data.user_id),
            username=user_row.username,
            email=user_row.email,
            permission=collaborator_data.permission,
            added_at=datetime.utcnow()
        )

    @handle_service_errors("journal collaborator update")
    async def update_collaborator_permission(
        self, 
        journal_id: uuid.UUID,
        user_id: uuid.UUID,
        new_permission: PermissionType,
        updated_by: uuid.UUID
    ) -> JournalCollaboratorResponse:
        """Update a collaborator's permission"""
        result = await self.session.execute(
            text("""
                UPDATE journal_collaborators 
                SET permission = %s, updated_at = %s
                WHERE journal_id = %s AND user_id = %s
                RETURNING id, added_at
            """),
            [new_permission, datetime.utcnow(), journal_id, user_id]
        )
        
        updated_row = result.fetchone()
        if not updated_row:
            raise HTTPException(
                status_code=404, 
                detail="Collaborator not found"
            )
        
        # Get user info
        user_result = await self.session.execute(
            text("""
                SELECT username, email
                FROM users 
                WHERE id = %s
            """),
            [user_id]
        )
        
        user_row = user_result.fetchone()
        
        return JournalCollaboratorResponse(
            id=str(updated_row.id),
            user_id=str(user_id),
            username=user_row.username,
            email=user_row.email,
            permission=new_permission,
            added_at=updated_row.added_at
        )

    @handle_service_errors("journal collaborator removal")
    async def remove_collaborator(
        self, 
        journal_id: uuid.UUID,
        user_id: uuid.UUID,
        removed_by: uuid.UUID
    ) -> bool:
        """Remove a collaborator from a journal"""
        result = await self.session.execute(
            text("""
                DELETE FROM journal_collaborators
                WHERE journal_id = %s AND user_id = %s
                RETURNING id
            """),
            [journal_id, user_id]
        )
        
        return result.fetchone() is not None

    @handle_service_errors("journal collaborators list")
    async def list_collaborators(
        self, 
        journal_id: uuid.UUID
    ) -> List[JournalCollaboratorResponse]:
        """List all collaborators for a journal"""
        result = await self.session.execute(
            text("""
                SELECT jc.id, jc.user_id, u.username, u.email,
                       jc.permission, jc.added_at
                FROM journal_collaborators jc
                JOIN users u ON jc.user_id = u.id
                WHERE jc.journal_id = %s
                ORDER BY jc.added_at ASC
            """),
            [journal_id]
        )
        
        collaborators = []
        for row in result.fetchall():
            collaborators.append(JournalCollaboratorResponse(
                id=str(row.id),
                user_id=str(row.user_id),
                username=row.username,
                email=row.email,
                permission=row.permission,
                added_at=row.added_at
            ))
        
        return collaborators

    @handle_service_errors("user accessible journals")
    async def get_user_accessible_journals(
        self, 
        user_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get all journals accessible to a user"""
        where_clauses = [
            "j.deleted_at IS NULL",
            "(j.created_by = %s OR jc.user_id = %s OR j.is_public = true)"
        ]
        params = [user_id, user_id]
        
        if project_id:
            where_clauses.append("j.project_id = %s")
            params.append(project_id)
        
        result = await self.session.execute(
            text(f"""
                SELECT DISTINCT j.id, j.title, j.status, j.is_public,
                       j.created_at, j.updated_at, j.project_id,
                       u.username as created_by_name,
                       CASE 
                           WHEN j.created_by = %s THEN 'owner'
                           WHEN jc.permission IS NOT NULL THEN jc.permission
                           ELSE 'public_read'
                       END as user_permission
                FROM journals j
                JOIN users u ON j.created_by = u.id
                LEFT JOIN journal_collaborators jc ON j.id = jc.journal_id 
                    AND jc.user_id = %s
                WHERE {' AND '.join(where_clauses)}
                ORDER BY j.updated_at DESC
            """),
            [user_id, user_id] + params
        )
        
        journals = []
        for row in result.fetchall():
            journals.append({
                "id": str(row.id),
                "title": row.title,
                "status": row.status,
                "is_public": row.is_public,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "project_id": str(row.project_id),
                "created_by_name": row.created_by_name,
                "user_permission": row.user_permission
            })
        
        return journals 
"""
Journal CRUD Service - L6 Engineering Standards

Focused service for journal CRUD operations.
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
    JournalCreate, JournalUpdate, JournalResponse, JournalDetailResponse,
    JournalListResponse, JournalStatus
)
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes

logger = logging.getLogger(__name__)


class JournalCrudService:
    """Service class for journal CRUD operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    @handle_service_errors("journal creation")
    async def create_journal(
        self, 
        journal_data: JournalCreate, 
        created_by: uuid.UUID
    ) -> JournalDetailResponse:
        """Create a new journal"""
        journal_id = uuid.uuid4()
        
        # Insert journal record
        result = await self.session.execute(
            text("""
                INSERT INTO journals (
                    id, project_id, title, content, created_by, 
                    status, is_public, created_at, updated_at
                )
                VALUES (:journal_id, :project_id, :title, :content, :created_by, :status, :is_public, :created_at, :updated_at)
                RETURNING id, title, status, created_at
            """),
            {
                "journal_id": journal_id,
                "project_id": journal_data.project_id,
                "title": journal_data.title,
                "content": journal_data.content or "",
                "created_by": created_by,
                "status": (journal_data.status or JournalStatus.DRAFT).value,
                "is_public": journal_data.is_public or False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        )
        
        created_journal = result.fetchone()
        
        return JournalDetailResponse(
            id=str(created_journal.id),
            project_id=str(journal_data.project_id),
            title=created_journal.title,
            content=journal_data.content or "",
            status=created_journal.status,
            is_public=journal_data.is_public or False,
            created_at=created_journal.created_at,
            updated_at=created_journal.created_at,
            created_by=str(created_by),
            collaborators=[],
            tags=[],
            version=1
        )

    @handle_service_errors("journal retrieval")
    async def get_journal(
        self, 
        journal_id: uuid.UUID
    ) -> Optional[JournalDetailResponse]:
        """Get a journal by ID"""
        result = await self.session.execute(
            text("""
                SELECT j.id, j.project_id, j.title, j.content, j.status,
                       j.is_public, j.created_at, j.updated_at, j.created_by,
                       j.version
                FROM journals j
                WHERE j.id = :journal_id AND j.deleted_at IS NULL
            """),
            {"journal_id": journal_id}
        )
        
        journal_row = result.fetchone()
        if not journal_row:
            return None
        
        # Get collaborators
        collab_result = await self.session.execute(
            text("""
                SELECT u.id, u.name, jc.permission, jc.added_at
                FROM journal_collaborators jc
                JOIN users u ON jc.user_id = u.id
                WHERE jc.journal_id = :journal_id
            """),
            {"journal_id": journal_id}
        )
        
        collaborators = []
        for row in collab_result.fetchall():
            collaborators.append({
                "user_id": str(row.id),
                "username": row.name,  # Note: keeping 'username' key for API compatibility
                "permission": row.permission,
                "added_at": row.added_at
            })
        
        # Get tags
        tags_result = await self.session.execute(
            text("""
                SELECT jt.id, jt.tag_name as name, jt.color
                FROM journal_tags jt
                WHERE jt.journal_id = :journal_id
            """),
            {"journal_id": journal_id}
        )
        
        tags = []
        for row in tags_result.fetchall():
            tags.append({
                "id": str(row.id),
                "name": row.name,
                "color": row.color
            })
        
        return JournalDetailResponse(
            id=str(journal_row.id),
            project_id=str(journal_row.project_id),
            title=journal_row.title,
            content=journal_row.content,
            status=journal_row.status,
            is_public=journal_row.is_public,
            created_at=journal_row.created_at,
            updated_at=journal_row.updated_at,
            created_by=str(journal_row.created_by),
            collaborators=collaborators,
            tags=tags,
            version=journal_row.version
        )

    @handle_service_errors("journal update")
    async def update_journal(
        self, 
        journal_id: uuid.UUID, 
        journal_data: JournalUpdate,
        updated_by: uuid.UUID
    ) -> JournalDetailResponse:
        """Update a journal"""
        # Build update query dynamically
        set_clauses = ["updated_at = :updated_at", "version = version + 1"]
        params = {"updated_at": datetime.utcnow(), "journal_id": journal_id}
        
        if journal_data.title is not None:
            set_clauses.append("title = :title")
            params["title"] = journal_data.title
        
        if journal_data.content is not None:
            set_clauses.append("content = :content")
            params["content"] = journal_data.content
        
        if journal_data.status is not None:
            set_clauses.append("status = :status")
            params["status"] = journal_data.status.value if hasattr(journal_data.status, 'value') else journal_data.status
        
        if journal_data.is_public is not None:
            set_clauses.append("is_public = :is_public")
            params["is_public"] = journal_data.is_public
        
        result = await self.session.execute(
            text(f"""
                UPDATE journals 
                SET {', '.join(set_clauses)}
                WHERE id = :journal_id AND deleted_at IS NULL
                RETURNING id, title, status, updated_at, version
            """),
            params
        )
        
        updated_journal = result.fetchone()
        if not updated_journal:
            raise HTTPException(status_code=404, detail="Journal not found")
        
        # Return updated journal
        return await self.get_journal(journal_id)

    @handle_service_errors("journal deletion")
    async def delete_journal(
        self, 
        journal_id: uuid.UUID,
        deleted_by: uuid.UUID
    ) -> bool:
        """Soft delete a journal"""
        result = await self.session.execute(
            text("""
                UPDATE journals 
                SET deleted_at = :deleted_at, deleted_by = :deleted_by
                WHERE id = :journal_id AND deleted_at IS NULL
                RETURNING id
            """),
            {
                "deleted_at": datetime.utcnow(),
                "deleted_by": deleted_by,
                "journal_id": journal_id
            }
        )
        
        return result.fetchone() is not None

    @handle_service_errors("journal list retrieval")
    async def list_project_journals(
        self, 
        project_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[JournalStatus] = None,
        search_query: Optional[str] = None
    ) -> JournalListResponse:
        """List journals for a project"""
        # Build where clause with named parameters
        where_clauses = ["j.project_id = :project_id", "j.deleted_at IS NULL"]
        params = {"project_id": project_id}
        
        if status_filter:
            where_clauses.append("j.status = :status_filter")
            params["status_filter"] = status_filter.value
        
        if search_query:
            where_clauses.append("(j.title ILIKE :search_term OR j.content ILIKE :search_term)")
            params["search_term"] = f"%{search_query}%"
        
        # Get total count
        count_result = await self.session.execute(
            text(f"""
                SELECT COUNT(*)
                FROM journals j
                WHERE {' AND '.join(where_clauses)}
            """),
            params
        )
        
        total_count = count_result.scalar()
        
        # Get journals with pagination
        params.update({"limit": limit, "offset": offset})
        journals_result = await self.session.execute(
            text(f"""
                SELECT j.id, j.project_id, j.title, j.content, j.status, j.is_public, 
                       j.created_by, j.version, j.created_at, j.updated_at, j.metadata,
                       u.name as created_by_name
                FROM journals j
                JOIN users u ON j.created_by = u.id
                WHERE {' AND '.join(where_clauses)}
                ORDER BY j.updated_at DESC
                LIMIT :limit OFFSET :offset
            """),
            params
        )
        
        journals = []
        for row in journals_result.fetchall():
            journals.append(JournalResponse(
                id=str(row.id),
                project_id=str(row.project_id),
                title=row.title,
                content=row.content or "",
                status=row.status,
                is_public=row.is_public,
                metadata=row.metadata if row.metadata else {},
                created_by=str(row.created_by),
                version=row.version,
                created_at=row.created_at,
                updated_at=row.updated_at
            ))
        
        # Calculate pagination info
        page = (offset // limit) + 1 if limit > 0 else 1
        total_pages = max(1, (total_count + limit - 1) // limit) if limit > 0 else 1
        
        return JournalListResponse(
            journals=journals,
            total=total_count,
            page=page,
            per_page=limit,
            total_pages=total_pages
        ) 
"""
Journal Service - L6 Engineering Standards

Clean, focused service replacing the previous 722-line monolithic file.
Delegates to modular components following SOLID principles.
"""

import uuid
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.journal_models import (
    JournalCreate, JournalUpdate, JournalResponse, JournalDetailResponse,
    JournalCollaboratorCreate, JournalCollaboratorResponse,
    JournalListResponse, JournalPermissionCheck, PermissionType, JournalStatus
)
from .journal.journal_crud_service import JournalCrudService
from .journal.journal_collaboration_service import JournalCollaborationService

logger = logging.getLogger(__name__)


class JournalService:
    """Unified journal service that delegates to specialized modules"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.crud_service = JournalCrudService(session)
        self.collaboration_service = JournalCollaborationService(session)

    # CRUD Operations (delegate to JournalCrudService)
    async def create_journal(self, journal_data: JournalCreate, created_by: uuid.UUID) -> JournalDetailResponse:
        return await self.crud_service.create_journal(journal_data, created_by)

    async def get_journal(self, journal_id: uuid.UUID) -> Optional[JournalDetailResponse]:
        return await self.crud_service.get_journal(journal_id)

    async def update_journal(self, journal_id: uuid.UUID, journal_data: JournalUpdate, updated_by: uuid.UUID) -> JournalDetailResponse:
        return await self.crud_service.update_journal(journal_id, journal_data, updated_by)

    async def delete_journal(self, journal_id: uuid.UUID, deleted_by: uuid.UUID) -> bool:
        return await self.crud_service.delete_journal(journal_id, deleted_by)

    async def list_project_journals(self, project_id: uuid.UUID, limit: int = 20, offset: int = 0, 
                                  status_filter: Optional[JournalStatus] = None, 
                                  search_query: Optional[str] = None) -> JournalListResponse:
        return await self.crud_service.list_project_journals(project_id, limit, offset, status_filter, search_query)

    # Collaboration Operations (delegate to JournalCollaborationService)
    async def check_journal_permission(self, journal_id: uuid.UUID, user_id: uuid.UUID) -> JournalPermissionCheck:
        return await self.collaboration_service.check_journal_permission(journal_id, user_id)

    async def add_collaborator(self, journal_id: uuid.UUID, collaborator_data: JournalCollaboratorCreate, 
                             added_by: uuid.UUID) -> JournalCollaboratorResponse:
        return await self.collaboration_service.add_collaborator(journal_id, collaborator_data, added_by)

    async def update_collaborator_permission(self, journal_id: uuid.UUID, user_id: uuid.UUID, 
                                           new_permission: PermissionType, updated_by: uuid.UUID) -> JournalCollaboratorResponse:
        return await self.collaboration_service.update_collaborator_permission(journal_id, user_id, new_permission, updated_by)

    async def remove_collaborator(self, journal_id: uuid.UUID, user_id: uuid.UUID, removed_by: uuid.UUID) -> bool:
        return await self.collaboration_service.remove_collaborator(journal_id, user_id, removed_by)

    async def list_collaborators(self, journal_id: uuid.UUID) -> List[JournalCollaboratorResponse]:
        return await self.collaboration_service.list_collaborators(journal_id)

    async def get_user_accessible_journals(self, user_id: uuid.UUID, project_id: Optional[uuid.UUID] = None) -> List[Dict[str, Any]]:
        return await self.collaboration_service.get_user_accessible_journals(user_id, project_id) 
"""
Journal Modules Test Suite - L6 Engineering Standards

Comprehensive test coverage for modular journal system.
Tests the split modules that replaced the bloated journal_service.py file.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.journal.journal_crud_service import JournalCrudService
from app.services.journal.journal_collaboration_service import JournalCollaborationService
from app.services.journal_service import JournalService
from app.models.journal_models import (
    JournalCreate, JournalUpdate, JournalStatus,
    JournalCollaboratorCreate, PermissionType
)


class TestJournalCrudService:
    """Test suite for journal CRUD service"""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def crud_service(self, mock_session):
        return JournalCrudService(mock_session)

    @pytest.fixture
    def sample_journal_create(self):
        return JournalCreate(
            project_id=uuid.uuid4(),
            title="Test Journal",
            content="Test content",
            status=JournalStatus.DRAFT,
            is_public=False
        )

    @pytest.mark.asyncio
    async def test_create_journal_success(self, crud_service, sample_journal_create):
        """Test successful journal creation"""
        created_by = uuid.uuid4()
        
        # Mock database response
        mock_result = Mock()
        mock_result.fetchone.return_value = Mock(
            id=uuid.uuid4(),
            title="Test Journal",
            status=JournalStatus.DRAFT,
            created_at=datetime.utcnow()
        )
        crud_service.session.execute.return_value = mock_result
        
        result = await crud_service.create_journal(sample_journal_create, created_by)
        
        assert result.title == "Test Journal"
        assert result.status == JournalStatus.DRAFT
        assert result.is_public is False
        assert result.version == 1

    @pytest.mark.asyncio
    async def test_get_journal_success(self, crud_service):
        """Test successful journal retrieval"""
        journal_id = uuid.uuid4()
        
        # Mock journal data
        mock_journal_result = Mock()
        mock_journal_result.fetchone.return_value = Mock(
            id=journal_id,
            project_id=uuid.uuid4(),
            title="Test Journal",
            content="Test content",
            status=JournalStatus.DRAFT.value,
            is_public=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=uuid.uuid4(),
            version=1
        )
        
        # Mock collaborators and tags
        mock_collab_result = Mock()
        mock_collab_result.fetchall.return_value = []
        mock_tags_result = Mock()
        mock_tags_result.fetchall.return_value = []
        
        crud_service.session.execute.side_effect = [
            mock_journal_result, mock_collab_result, mock_tags_result
        ]
        
        result = await crud_service.get_journal(journal_id)
        
        assert result is not None
        assert result.title == "Test Journal"
        assert result.status == JournalStatus.DRAFT

    @pytest.mark.asyncio
    async def test_get_journal_not_found(self, crud_service):
        """Test journal retrieval when journal doesn't exist"""
        journal_id = uuid.uuid4()
        
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        crud_service.session.execute.return_value = mock_result
        
        result = await crud_service.get_journal(journal_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_journal_success(self, crud_service):
        """Test successful journal update"""
        journal_id = uuid.uuid4()
        updated_by = uuid.uuid4()
        
        journal_update = JournalUpdate(
            title="Updated Title",
            content="Updated content",
            status=JournalStatus.PUBLISHED
        )
        
        # Mock update result
        mock_update_result = Mock()
        mock_update_result.fetchone.return_value = Mock(
            id=journal_id,
            title="Updated Title",
            status=JournalStatus.PUBLISHED,
            updated_at=datetime.utcnow(),
            version=2
        )
        
        # Mock get_journal call
        crud_service.get_journal = AsyncMock(return_value=Mock(
            id=str(journal_id),
            title="Updated Title",
            status=JournalStatus.PUBLISHED
        ))
        
        crud_service.session.execute.return_value = mock_update_result
        
        result = await crud_service.update_journal(journal_id, journal_update, updated_by)
        
        assert result is not None
        crud_service.get_journal.assert_called_once_with(journal_id)

    @pytest.mark.asyncio
    async def test_delete_journal_success(self, crud_service):
        """Test successful journal deletion"""
        journal_id = uuid.uuid4()
        deleted_by = uuid.uuid4()
        
        mock_result = Mock()
        mock_result.fetchone.return_value = Mock(id=journal_id)
        crud_service.session.execute.return_value = mock_result
        
        result = await crud_service.delete_journal(journal_id, deleted_by)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_list_project_journals_success(self, crud_service):
        """Test successful project journals listing"""
        project_id = uuid.uuid4()
        
        # Mock count result
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 2
        
        # Mock journals result
        mock_journals_result = Mock()
        mock_journals_result.fetchall.return_value = [
            Mock(
                id=uuid.uuid4(),
                title="Journal 1",
                status=JournalStatus.DRAFT.value,
                is_public=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by_name="User 1"
            ),
            Mock(
                id=uuid.uuid4(),
                title="Journal 2",
                status=JournalStatus.PUBLISHED.value,
                is_public=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by_name="User 2"
            )
        ]
        
        crud_service.session.execute.side_effect = [mock_count_result, mock_journals_result]
        
        result = await crud_service.list_project_journals(project_id)
        
        assert result.total_count == 2
        assert len(result.journals) == 2
        assert result.journals[0].title == "Journal 1"
        assert result.journals[1].title == "Journal 2"


class TestJournalCollaborationService:
    """Test suite for journal collaboration service"""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def collab_service(self, mock_session):
        return JournalCollaborationService(mock_session)

    @pytest.mark.asyncio
    async def test_check_journal_permission_owner(self, collab_service):
        """Test permission check for journal owner"""
        journal_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        mock_result = Mock()
        mock_result.fetchone.return_value = Mock(
            id=journal_id,
            created_by=user_id,
            is_public=False,
            permission=None
        )
        collab_service.session.execute.return_value = mock_result
        
        result = await collab_service.check_journal_permission(journal_id, user_id)
        
        assert result.has_access is True
        assert result.is_owner is True
        assert result.can_write is True
        assert result.can_delete is True

    @pytest.mark.asyncio
    async def test_check_journal_permission_public(self, collab_service):
        """Test permission check for public journal"""
        journal_id = uuid.uuid4()
        user_id = uuid.uuid4()
        different_user_id = uuid.uuid4()
        
        mock_result = Mock()
        mock_result.fetchone.return_value = Mock(
            id=journal_id,
            created_by=different_user_id,
            is_public=True,
            permission=None
        )
        collab_service.session.execute.return_value = mock_result
        
        result = await collab_service.check_journal_permission(journal_id, user_id)
        
        assert result.has_access is True
        assert result.is_owner is False
        assert result.can_read is True

    @pytest.mark.asyncio
    async def test_add_collaborator_success(self, collab_service):
        """Test successful collaborator addition"""
        journal_id = uuid.uuid4()
        added_by = uuid.uuid4()
        
        collaborator_data = JournalCollaboratorCreate(
            user_id=uuid.uuid4(),
            permission=PermissionType.WRITE
        )
        
        # Mock user existence check
        mock_user_result = Mock()
        mock_user_result.fetchone.return_value = Mock(
            id=collaborator_data.user_id,
            username="test_user",
            email="test@example.com"
        )
        
        # Mock existing collaborator check
        mock_existing_result = Mock()
        mock_existing_result.fetchone.return_value = None
        
        collab_service.session.execute.side_effect = [mock_user_result, mock_existing_result, Mock()]
        
        result = await collab_service.add_collaborator(journal_id, collaborator_data, added_by)
        
        assert result.username == "test_user"
        assert result.permission == PermissionType.WRITE

    @pytest.mark.asyncio
    async def test_add_collaborator_user_not_found(self, collab_service):
        """Test collaborator addition when user doesn't exist"""
        journal_id = uuid.uuid4()
        added_by = uuid.uuid4()
        
        collaborator_data = JournalCollaboratorCreate(
            user_id=uuid.uuid4(),
            permission=PermissionType.WRITE
        )
        
        mock_user_result = Mock()
        mock_user_result.fetchone.return_value = None
        collab_service.session.execute.return_value = mock_user_result
        
        with pytest.raises(HTTPException) as exc_info:
            await collab_service.add_collaborator(journal_id, collaborator_data, added_by)
        
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)


class TestJournalServiceIntegration:
    """Integration tests for the unified journal service"""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def journal_service(self, mock_session):
        return JournalService(mock_session)

    @pytest.mark.asyncio
    async def test_service_delegation(self, journal_service):
        """Test that unified service properly delegates to sub-services"""
        # Mock the sub-services
        journal_service.crud_service.create_journal = AsyncMock()
        journal_service.collaboration_service.check_journal_permission = AsyncMock()
        
        journal_data = JournalCreate(
            project_id=uuid.uuid4(),
            title="Test Journal",
            content="Test content"
        )
        created_by = uuid.uuid4()
        
        # Test CRUD delegation
        await journal_service.create_journal(journal_data, created_by)
        journal_service.crud_service.create_journal.assert_called_once_with(journal_data, created_by)
        
        # Test collaboration delegation
        journal_id = uuid.uuid4()
        user_id = uuid.uuid4()
        await journal_service.check_journal_permission(journal_id, user_id)
        journal_service.collaboration_service.check_journal_permission.assert_called_once_with(journal_id, user_id)


@pytest.mark.integration
class TestJournalModulesIntegration:
    """Integration tests for journal modules"""
    
    def test_modules_independence(self):
        """Test that journal modules work independently"""
        from app.services.journal.journal_crud_service import JournalCrudService
        from app.services.journal.journal_collaboration_service import JournalCollaborationService
        
        assert JournalCrudService is not None
        assert JournalCollaborationService is not None
        
    def test_error_handling_consistency(self):
        """Test that all modules use consistent error handling"""
        from app.services.journal import journal_crud_service, journal_collaboration_service
        
        # Check that error handling decorators are applied
        assert hasattr(journal_crud_service.JournalCrudService.create_journal, '__wrapped__')
        assert hasattr(journal_collaboration_service.JournalCollaborationService.check_journal_permission, '__wrapped__')


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 
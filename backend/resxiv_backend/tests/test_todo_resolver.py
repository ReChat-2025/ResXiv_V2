"""
Tests for TODO Resolver Factory
L6 Engineering Standards - Production Feature Implementations
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.utils.todo_resolver import (
    TODOResolverFactory,
    ProductionUserLookupService,
    ProductionAdminChecker
)


class TestProductionUserLookupService:
    """Test cases for ProductionUserLookupService"""
    
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def user_lookup_service(self, mock_session):
        return ProductionUserLookupService(mock_session)
    
    @pytest.mark.asyncio
    async def test_get_user_info_success(self, user_lookup_service, mock_session):
        # Mock successful database response
        mock_row = MagicMock()
        mock_row.id = "user123"
        mock_row.name = "John Doe"
        mock_row.email = "john@example.com"
        mock_row.created_at = None
        mock_row.is_active = True
        
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result
        
        user_info = await user_lookup_service.get_user_info("user123")
        
        assert user_info is not None
        assert user_info["id"] == "user123"
        assert user_info["name"] == "John Doe"
        assert user_info["email"] == "john@example.com"
        assert user_info["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_get_user_info_not_found(self, user_lookup_service, mock_session):
        # Mock user not found
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result
        
        user_info = await user_lookup_service.get_user_info("nonexistent")
        
        assert user_info is None
    
    @pytest.mark.asyncio
    async def test_get_user_info_exception(self, user_lookup_service, mock_session):
        # Mock database exception
        mock_session.execute.side_effect = Exception("Database error")
        
        user_info = await user_lookup_service.get_user_info("user123")
        
        assert user_info is None
    
    @pytest.mark.asyncio
    async def test_get_users_info_success(self, user_lookup_service, mock_session):
        # Mock multiple users response
        mock_row1 = MagicMock()
        mock_row1.id = "user1"
        mock_row1.name = "User One"
        mock_row1.email = "user1@example.com"
        mock_row1.created_at = None
        mock_row1.is_active = True
        
        mock_row2 = MagicMock()
        mock_row2.id = "user2"
        mock_row2.name = "User Two"
        mock_row2.email = "user2@example.com"
        mock_row2.created_at = None
        mock_row2.is_active = False
        
        mock_result = AsyncMock()
        mock_result.fetchall.return_value = [mock_row1, mock_row2]
        mock_session.execute.return_value = mock_result
        
        users_info = await user_lookup_service.get_users_info(["user1", "user2"])
        
        assert len(users_info) == 2
        assert users_info["user1"]["name"] == "User One"
        assert users_info["user2"]["name"] == "User Two"
    
    @pytest.mark.asyncio
    async def test_get_users_info_empty_list(self, user_lookup_service, mock_session):
        users_info = await user_lookup_service.get_users_info([])
        
        assert users_info == {}
        mock_session.execute.assert_not_called()


class TestProductionAdminChecker:
    """Test cases for ProductionAdminChecker"""
    
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def admin_checker(self, mock_session):
        return ProductionAdminChecker(mock_session)
    
    @pytest.mark.asyncio
    async def test_is_admin_true(self, admin_checker, mock_session):
        # Mock admin user
        mock_result = AsyncMock()
        mock_result.scalar.return_value = True
        mock_session.execute.return_value = mock_result
        
        is_admin = await admin_checker.is_admin("admin_user")
        
        assert is_admin is True
    
    @pytest.mark.asyncio
    async def test_is_admin_false(self, admin_checker, mock_session):
        # Mock non-admin user
        mock_result = AsyncMock()
        mock_result.scalar.return_value = False
        mock_session.execute.return_value = mock_result
        
        is_admin = await admin_checker.is_admin("regular_user")
        
        assert is_admin is False
    
    @pytest.mark.asyncio
    async def test_is_admin_exception(self, admin_checker, mock_session):
        # Mock database exception
        mock_session.execute.side_effect = Exception("Database error")
        
        is_admin = await admin_checker.is_admin("user123")
        
        assert is_admin is False
    
    @pytest.mark.asyncio
    async def test_has_permission_admin_user(self, admin_checker, mock_session):
        # Mock admin user - should have all permissions
        with patch.object(admin_checker, 'is_admin', return_value=True):
            has_perm = await admin_checker.has_permission("admin_user", "some_permission")
            
            assert has_perm is True
    
    @pytest.mark.asyncio
    async def test_has_permission_specific_permission(self, admin_checker, mock_session):
        # Mock non-admin user with specific permission
        with patch.object(admin_checker, 'is_admin', return_value=False):
            mock_result = AsyncMock()
            mock_result.scalar.return_value = True
            mock_session.execute.return_value = mock_result
            
            has_perm = await admin_checker.has_permission("user123", "read_data")
            
            assert has_perm is True
    
    @pytest.mark.asyncio
    async def test_has_permission_no_permission(self, admin_checker, mock_session):
        # Mock non-admin user without permission
        with patch.object(admin_checker, 'is_admin', return_value=False):
            mock_result = AsyncMock()
            mock_result.scalar.return_value = False
            mock_session.execute.return_value = mock_result
            
            has_perm = await admin_checker.has_permission("user123", "admin_access")
            
            assert has_perm is False


class TestTODOResolverFactory:
    """Test cases for TODOResolverFactory"""
    
    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)
    
    def test_get_user_lookup_service(self, mock_session):
        service = TODOResolverFactory.get_user_lookup_service(mock_session)
        
        assert isinstance(service, ProductionUserLookupService)
        assert service.session == mock_session
    
    def test_get_admin_checker(self, mock_session):
        checker = TODOResolverFactory.get_admin_checker(mock_session)
        
        assert isinstance(checker, ProductionAdminChecker)
        assert checker.session == mock_session
    
    @pytest.mark.asyncio
    async def test_get_real_user_info_success(self, mock_session):
        # Mock successful user lookup
        with patch.object(TODOResolverFactory, 'get_user_lookup_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_user_info.return_value = {
                "id": "user123",
                "name": "John Doe",
                "email": "john@example.com",
                "created_at": None,
                "is_active": True
            }
            mock_get_service.return_value = mock_service
            
            user_info = await TODOResolverFactory.get_real_user_info(mock_session, "user123")
            
            assert user_info["name"] == "John Doe"
            assert user_info["email"] == "john@example.com"
    
    @pytest.mark.asyncio
    async def test_get_real_user_info_not_found(self, mock_session):
        # Mock user not found - should return safe default
        with patch.object(TODOResolverFactory, 'get_user_lookup_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_user_info.return_value = None
            mock_get_service.return_value = mock_service
            
            user_info = await TODOResolverFactory.get_real_user_info(mock_session, "nonexistent")
            
            assert user_info["id"] == "nonexistent"
            assert user_info["name"] == "Unknown User"
            assert user_info["email"] == "unknown@example.com"
            assert user_info["is_active"] is False
    
    @pytest.mark.asyncio
    async def test_check_admin_access(self, mock_session):
        # Mock admin check
        with patch.object(TODOResolverFactory, 'get_admin_checker') as mock_get_checker:
            mock_checker = AsyncMock()
            mock_checker.is_admin.return_value = True
            mock_get_checker.return_value = mock_checker
            
            is_admin = await TODOResolverFactory.check_admin_access(mock_session, "admin_user")
            
            assert is_admin is True
            mock_checker.is_admin.assert_called_once_with("admin_user") 
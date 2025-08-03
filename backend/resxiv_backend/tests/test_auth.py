"""
Authentication Module Tests
L6 Engineering Standards Implementation

Comprehensive tests for authentication functionality including:
- JWT token creation and validation
- Password hashing and verification
- User authentication flows
- Admin role checking
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    AuthService, PasswordService, AuthenticationError, AuthorizationError,
    get_current_user_optional, get_current_user_required, get_admin_user
)
from app.config.settings import get_settings


class TestAuthService:
    """Test AuthService functionality."""
    
    def test_create_access_token(self):
        """Test JWT access token creation."""
        data = {"user_id": "123", "email": "test@example.com"}
        token = AuthService.create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_access_token_with_expiration(self):
        """Test JWT access token creation with custom expiration."""
        data = {"user_id": "123", "email": "test@example.com"}
        expires_delta = timedelta(minutes=15)
        token = AuthService.create_access_token(data, expires_delta)
        
        assert token is not None
        assert isinstance(token, str)
    
    def test_create_refresh_token(self):
        """Test JWT refresh token creation."""
        data = {"user_id": "123", "email": "test@example.com"}
        token = AuthService.create_refresh_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_token_valid(self):
        """Test decoding a valid JWT token."""
        data = {"user_id": "123", "email": "test@example.com"}
        token = AuthService.create_access_token(data)
        
        decoded = AuthService.decode_token(token)
        
        assert decoded is not None
        assert decoded["user_id"] == "123"
        assert decoded["email"] == "test@example.com"
        assert "exp" in decoded
        assert "iat" in decoded
        assert decoded["type"] == "access"
    
    def test_decode_token_invalid(self):
        """Test decoding an invalid JWT token."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(Exception):
            AuthService.decode_token(invalid_token)
    
    def test_verify_token_valid(self):
        """Test verifying a valid JWT token."""
        data = {"user_id": "123", "email": "test@example.com"}
        token = AuthService.create_access_token(data)
        
        user_data = AuthService.verify_token(token)
        
        assert user_data is not None
        assert user_data["user_id"] == "123"
        assert user_data["email"] == "test@example.com"
    
    def test_verify_token_invalid(self):
        """Test verifying an invalid JWT token."""
        invalid_token = "invalid.token.here"
        
        user_data = AuthService.verify_token(invalid_token)
        assert user_data is None
    
    def test_verify_token_expired(self):
        """Test verifying an expired JWT token."""
        data = {"user_id": "123", "email": "test@example.com"}
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        token = AuthService.create_access_token(data, expires_delta)
        
        user_data = AuthService.verify_token(token)
        assert user_data is None
    
    def test_create_user_tokens(self):
        """Test creating user token pair."""
        user_id = str(uuid.uuid4())
        username = "testuser"
        email = "test@example.com"
        
        tokens = AuthService.create_user_tokens(user_id, username, email)
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert tokens["token_type"] == "bearer"
        
        # Verify access token
        access_data = AuthService.verify_token(tokens["access_token"])
        assert access_data["user_id"] == user_id
        assert access_data["username"] == username
        assert access_data["email"] == email


class TestPasswordService:
    """Test PasswordService functionality."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = PasswordService.hash_password(password)
        
        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are typically 60 chars
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "TestPassword123!"
        hashed = PasswordService.hash_password(password)
        
        is_valid = PasswordService.verify_password(password, hashed)
        assert is_valid is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword456!"
        hashed = PasswordService.hash_password(password)
        
        is_valid = PasswordService.verify_password(wrong_password, hashed)
        assert is_valid is False
    
    def test_validate_password_strength_valid(self):
        """Test password strength validation with valid passwords."""
        valid_passwords = [
            "TestPassword123!",
            "MyStr0ng@Password",
            "Complex#Pass123",
            "Valid!Password456"
        ]
        
        for password in valid_passwords:
            is_valid = PasswordService.validate_password_strength(password)
            assert is_valid is True, f"Password '{password}' should be valid"
    
    def test_validate_password_strength_invalid(self):
        """Test password strength validation with invalid passwords."""
        invalid_passwords = [
            "short",
            "lowercase",
            "UPPERCASE",
            "NoSpecialChars123",
            "NoNumbers!",
            "no-uppercase123!"
        ]
        
        for password in invalid_passwords:
            is_valid = PasswordService.validate_password_strength(password)
            assert is_valid is False, f"Password '{password}' should be invalid"


class TestAuthenticationEndpoints:
    """Test authentication endpoint dependencies."""
    
    @pytest.mark.asyncio
    async def test_get_current_user_optional_valid_token(self, valid_jwt_token):
        """Test get_current_user_optional with valid token."""
        from fastapi.security import HTTPAuthorizationCredentials
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=valid_jwt_token
        )
        
        user = await get_current_user_optional(credentials)
        
        assert user is not None
        assert "user_id" in user
        assert "email" in user
    
    @pytest.mark.asyncio
    async def test_get_current_user_optional_invalid_token(self):
        """Test get_current_user_optional with invalid token."""
        from fastapi.security import HTTPAuthorizationCredentials
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token.here"
        )
        
        user = await get_current_user_optional(credentials)
        assert user is None
    
    @pytest.mark.asyncio
    async def test_get_current_user_optional_no_credentials(self):
        """Test get_current_user_optional with no credentials."""
        user = await get_current_user_optional(None)
        assert user is None
    
    @pytest.mark.asyncio
    async def test_get_current_user_required_valid_token(self, valid_jwt_token):
        """Test get_current_user_required with valid token."""
        from fastapi.security import HTTPAuthorizationCredentials
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=valid_jwt_token
        )
        
        user = await get_current_user_required(credentials)
        
        assert user is not None
        assert "user_id" in user
        assert "email" in user
    
    @pytest.mark.asyncio
    async def test_get_current_user_required_invalid_token(self):
        """Test get_current_user_required with invalid token."""
        from fastapi.security import HTTPAuthorizationCredentials
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token.here"
        )
        
        with pytest.raises(AuthenticationError):
            await get_current_user_required(credentials)
    
    @pytest.mark.asyncio
    async def test_get_current_user_required_no_credentials(self):
        """Test get_current_user_required with no credentials."""
        with pytest.raises(AuthenticationError):
            await get_current_user_required(None)
    
    @pytest.mark.asyncio
    async def test_get_admin_user_valid_admin(self, admin_user_data, admin_jwt_token, mock_session):
        """Test get_admin_user with valid admin user."""
        # Mock get_current_user_required to return user data
        with patch('app.core.auth.get_current_user_required') as mock_get_user:
            mock_get_user.return_value = admin_user_data
            
            # Mock the admin checker to return True
            with patch('app.utils.todo_resolver.TODOResolverFactory.get_admin_checker') as mock_checker:
                mock_admin_service = AsyncMock()
                mock_admin_service.is_system_admin = AsyncMock(return_value=True)
                mock_checker.return_value = mock_admin_service
                
                admin_user = await get_admin_user(admin_user_data, mock_session)
                
                assert admin_user is not None
                assert admin_user == admin_user_data
    
    @pytest.mark.asyncio
    async def test_get_admin_user_non_admin(self, sample_user_data, valid_jwt_token, mock_session):
        """Test get_admin_user with non-admin user."""
        # Mock get_current_user_required to return user data
        with patch('app.core.auth.get_current_user_required') as mock_get_user:
            mock_get_user.return_value = sample_user_data
            
            # Mock the admin checker to return False
            with patch('app.utils.todo_resolver.TODOResolverFactory.get_admin_checker') as mock_checker:
                mock_admin_service = AsyncMock()
                mock_admin_service.is_system_admin = AsyncMock(return_value=False)
                mock_checker.return_value = mock_admin_service
                
                with pytest.raises(AuthorizationError):
                    await get_admin_user(sample_user_data, mock_session)


class TestAuthenticationExceptions:
    """Test custom authentication exceptions."""
    
    def test_authentication_error_default(self):
        """Test AuthenticationError with default message."""
        error = AuthenticationError()
        
        assert error.status_code == 401
        assert error.detail == "Authentication failed"
        assert error.headers == {"WWW-Authenticate": "Bearer"}
    
    def test_authentication_error_custom_message(self):
        """Test AuthenticationError with custom message."""
        custom_message = "Custom auth error"
        error = AuthenticationError(custom_message)
        
        assert error.status_code == 401
        assert error.detail == custom_message
        assert error.headers == {"WWW-Authenticate": "Bearer"}
    
    def test_authorization_error_default(self):
        """Test AuthorizationError with default message."""
        error = AuthorizationError()
        
        assert error.status_code == 403
        assert error.detail == "Access denied"
    
    def test_authorization_error_custom_message(self):
        """Test AuthorizationError with custom message."""
        custom_message = "Custom access denied"
        error = AuthorizationError(custom_message)
        
        assert error.status_code == 403
        assert error.detail == custom_message


class TestTokenEdgeCases:
    """Test edge cases and security scenarios."""
    
    def test_token_with_none_data(self):
        """Test token creation with None data."""
        with pytest.raises(Exception):
            AuthService.create_access_token(None)
    
    def test_token_with_empty_data(self):
        """Test token creation with empty data."""
        token = AuthService.create_access_token({})
        
        assert token is not None
        decoded = AuthService.decode_token(token)
        assert "exp" in decoded
        assert "iat" in decoded
        assert decoded["type"] == "access"
    
    def test_token_with_large_payload(self):
        """Test token creation with large payload."""
        large_data = {
            "user_id": "123",
            "email": "test@example.com",
            "large_field": "x" * 1000,  # Large string
            "array_field": list(range(100))  # Large array
        }
        
        token = AuthService.create_access_token(large_data)
        assert token is not None
        
        decoded = AuthService.decode_token(token)
        assert decoded["user_id"] == "123"
        assert decoded["large_field"] == "x" * 1000
    
    def test_malformed_token_variations(self):
        """Test various malformed token formats."""
        malformed_tokens = [
            "",
            "not.a.token",
            "header.payload",  # Missing signature
            "too.many.parts.here.invalid",
            "invalid-base64!@#",
        ]
        
        for token in malformed_tokens:
            user_data = AuthService.verify_token(token)
            assert user_data is None, f"Token '{token}' should be invalid" 
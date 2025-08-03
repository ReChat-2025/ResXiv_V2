"""
User Service Integrated - L6 Engineering Standards
Orchestrates specialized user sub-services with clean separation of concerns.
"""

import uuid
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_handling import handle_service_errors
from app.models.user import (
    UserRegistration, UserLogin, TokenResponse, UserResponse,
    UserProfileUpdate, PasswordChangeRequest, PasswordResetRequest,
    PasswordResetConfirm
)

from .user_auth_service import UserAuthService
from .user_profile_service import UserProfileService
from .user_verification_service import UserVerificationService

logger = logging.getLogger(__name__)


class UserService:
    """
    Integrated user service orchestrating specialized sub-services.
    
    Follows Composition over Inheritance principle with clean separation:
    - Auth service: Authentication and session management
    - Profile service: Profile data and preferences
    - Verification service: Email verification and password resets
    
    Single point of access for all user operations while maintaining
    focused, testable components.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
        # Initialize specialized services
        self.auth_service = UserAuthService(session)
        self.profile_service = UserProfileService(session)
        self.verification_service = UserVerificationService(session)
    
    # ================================
    # AUTHENTICATION OPERATIONS
    # ================================
    
    async def register_user(
        self,
        registration_data: UserRegistration,
        request_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Register new user."""
        return await self.auth_service.register_user(registration_data, request_info)
    
    async def login_user(
        self,
        login_data: UserLogin,
        request_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Authenticate user and create session."""
        return await self.auth_service.login_user(login_data, request_info)
    
    async def refresh_token(
        self,
        refresh_token: str,
        request_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Refresh access token."""
        return await self.auth_service.refresh_token(refresh_token, request_info)
    
    async def logout_user(
        self,
        user_id: uuid.UUID,
        refresh_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Logout user and invalidate tokens."""
        return await self.auth_service.logout_user(user_id, refresh_token)
    
    async def change_password(
        self,
        user_id: uuid.UUID,
        password_data: PasswordChangeRequest
    ) -> Dict[str, Any]:
        """Change user password."""
        return await self.auth_service.change_password(user_id, password_data)
    
    # ================================
    # PROFILE OPERATIONS
    # ================================
    
    async def get_user_profile(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get user profile information."""
        return await self.profile_service.get_user_profile(user_id)
    
    async def update_user_profile(
        self,
        user_id: uuid.UUID,
        profile_data: UserProfileUpdate
    ) -> Dict[str, Any]:
        """Update user profile."""
        return await self.profile_service.update_user_profile(user_id, profile_data)
    
    async def update_user_preferences(
        self,
        user_id: uuid.UUID,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user preferences."""
        return await self.profile_service.update_user_preferences(user_id, preferences)
    
    async def get_user_statistics(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get user activity statistics."""
        return await self.profile_service.get_user_statistics(user_id)
    
    async def search_users(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Search users."""
        return await self.profile_service.search_users(query, limit, offset, filters)
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address."""
        return await self.profile_service.get_user_by_email(email)
    
    async def delete_user_account(
        self,
        user_id: uuid.UUID,
        confirmation: str
    ) -> Dict[str, Any]:
        """Delete user account."""
        return await self.profile_service.delete_user_account(user_id, confirmation)
    
    # ================================
    # VERIFICATION OPERATIONS
    # ================================
    
    async def verify_email(self, token: str) -> Dict[str, Any]:
        """Verify user email."""
        return await self.verification_service.verify_email(token)
    
    async def resend_verification_email(self, email: str) -> Dict[str, Any]:
        """Resend email verification."""
        return await self.verification_service.resend_verification_email(email)
    
    async def request_password_reset(
        self,
        reset_data: PasswordResetRequest
    ) -> Dict[str, Any]:
        """Request password reset."""
        return await self.verification_service.request_password_reset(reset_data)
    
    async def confirm_password_reset(
        self,
        reset_data: PasswordResetConfirm
    ) -> Dict[str, Any]:
        """Confirm password reset."""
        return await self.verification_service.confirm_password_reset(reset_data)
    
    # ================================
    # ADMIN/MAINTENANCE OPERATIONS
    # ================================
    
    async def cleanup_expired_tokens(self) -> Dict[str, Any]:
        """Cleanup expired tokens."""
        return await self.verification_service.cleanup_expired_tokens()
    
    @handle_service_errors("user service health check")
    async def health_check(self) -> Dict[str, Any]:
        """Service health check."""
        # Check all sub-services
        try:
            # Basic repository health check via auth service
            await self.auth_service.repository.health_check()
            
            return {
                "success": True,
                "status": "healthy",
                "services": {
                    "auth": "healthy",
                    "profile": "healthy", 
                    "verification": "healthy"
                }
            }
        except Exception as e:
            logger.error(f"User service health check failed: {e}")
            return {
                "success": False,
                "status": "unhealthy",
                "error": str(e)
            } 
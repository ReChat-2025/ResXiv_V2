"""
User Authentication Service - L6 Engineering Standards
Focused on authentication operations with clean separation of concerns.
"""

import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging

from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailService, get_email_service
from app.core.auth import AuthService, PasswordService
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.models.user import (
    UserRegistration, UserLogin, TokenResponse,
    PasswordChangeRequest, PasswordResetRequest, PasswordResetConfirm
)
from app.config.settings import get_settings

settings_cfg = get_settings()
logger = logging.getLogger(__name__)


class UserAuthService:
    """
    Authentication service for user login/logout/registration.
    Single Responsibility: User authentication and session management.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = UserRepository(session)
        self.email_service = get_email_service()
    
    @handle_service_errors("user registration")
    async def register_user(
        self,
        registration_data: UserRegistration,
        request_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Register a new user with email verification.
        
        Handles re-registration for unverified accounts by cleaning up
        previous incomplete registrations.
        
        Args:
            registration_data: User registration data
            request_info: Request information (IP, user agent, etc.)
            
        Returns:
            Success response with user data
        """
        # Check if email already exists for a verified user
        if await self.repository.email_exists(registration_data.email):
            raise ServiceError(
                "An account with this email already exists",
                ErrorCodes.VALIDATION_ERROR
            )
        
        # Check for unverified user with same email
        unverified_user = await self.repository.get_unverified_user_by_email(registration_data.email)
        if unverified_user:
            logger.info(f"Cleaning up unverified account for re-registration: {registration_data.email}")
            
            # Check if the unverified account is recent (within 24 hours)
            # If it's very recent, we might want to just resend verification instead
            from datetime import datetime, timezone, timedelta
            
            account_age = datetime.now(timezone.utc) - unverified_user.created_at
            if account_age < timedelta(minutes=5):
                # Account is very recent, suggest resending verification instead
                logger.warning(f"Recent unverified account found for {registration_data.email}, suggesting resend verification")
                raise ServiceError(
                    "An unverified account with this email was recently created. Please check your email for the verification link or use the 'Resend Verification' option.",
                    ErrorCodes.VALIDATION_ERROR
                )
            
            # Clean up the old unverified account
            deleted = await self.repository.delete_unverified_user(unverified_user.id)
            if not deleted:
                logger.error(f"Failed to delete unverified user {unverified_user.id} for re-registration")
                raise ServiceError(
                    "Unable to process registration. Please contact support.",
                    ErrorCodes.INTERNAL_ERROR
                )
            
            logger.info(f"Successfully cleaned up unverified account {unverified_user.id} for re-registration")
        
        # Validate password strength
        if not PasswordService.validate_password_strength(registration_data.password):
            raise ServiceError(
                "Password does not meet security requirements",
                ErrorCodes.VALIDATION_ERROR
            )
        
        # Create user
        user = await self.repository.create_user(
            name=registration_data.name,
            email=registration_data.email,
            password=registration_data.password,
            interests=registration_data.interests,
            accepted_terms=registration_data.accepted_terms
        )
        
        # Create email verification token
        verification_token = await self.repository.create_email_verification_token(
            user_id=user.id,
            email=user.email
        )
        
        # Send verification email
        email_sent = await self.email_service.send_email_verification(
            to_email=user.email,
            name=user.name,
            verification_token=verification_token.token
        )
        
        if not email_sent:
            logger.warning(f"Failed to send verification email to {user.email}")
        
        return {
            "success": True,
            "message": "Registration successful. Please check your email for verification.",
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "email_verified": user.email_verified
            },
            "requires_verification": True
        }
    
    @handle_service_errors("user login")
    async def login_user(
        self,
        login_data: UserLogin,
        request_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Authenticate user and create session.
        
        Args:
            login_data: Login credentials
            request_info: Request metadata
            
        Returns:
            Success response with tokens
        """
        # Authenticate user
        user = await self.repository.authenticate_user(
            email=login_data.email,
            password=login_data.password
        )
        
        if not user:
            raise ServiceError(
                "Invalid email or password",
                ErrorCodes.AUTHENTICATION_ERROR
            )
        
        # Check if user is active
        if not user.is_active:
            raise ServiceError(
                "Account is disabled",
                ErrorCodes.AUTHORIZATION_ERROR
            )
        
        # Generate tokens
        access_token = AuthService.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        refresh_token = AuthService.create_refresh_token(
            data={"sub": str(user.id)}
        )
        
        # Store refresh token
        await self.repository.store_refresh_token(
            user_id=user.id,
            token=refresh_token,
            request_info=request_info
        )
        
        # Update last login
        await self.repository.update_last_login(user.id)
        
        return {
            "success": True,
            "tokens": TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=int(get_settings().jwt.access_token_expire_minutes) * 60
            ),
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "email_verified": user.email_verified,
                "role": user.role
            }
        }
    
    @handle_service_errors("token refresh")
    async def refresh_token(
        self,
        refresh_token: str,
        request_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            request_info: Request metadata
            
        Returns:
            New token pair
        """
        # Validate refresh token
        token_data = AuthService.verify_refresh_token(refresh_token)
        if not token_data:
            raise ServiceError(
                "Invalid refresh token",
                ErrorCodes.AUTHENTICATION_ERROR
            )
        
        user_id = uuid.UUID(token_data["sub"])
        
        # Verify token exists in database
        stored_token = await self.repository.get_refresh_token(user_id, refresh_token)
        if not stored_token or stored_token.is_expired:
            raise ServiceError(
                "Refresh token expired or invalid",
                ErrorCodes.AUTHENTICATION_ERROR
            )
        
        # Get user
        user = await self.repository.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise ServiceError(
                "User not found or inactive",
                ErrorCodes.AUTHORIZATION_ERROR
            )
        
        # Generate new tokens
        new_access_token = AuthService.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
 
        # Optionally update session last_used timestamp
        await self.repository.update_session_last_used(stored_token.id)
 
        return {
            "success": True,
            "tokens": TokenResponse(
                access_token=new_access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=int(get_settings().jwt.access_token_expire_minutes) * 60
            )
        }
    
    @handle_service_errors("user logout")
    async def logout_user(
        self,
        user_id: uuid.UUID,
        refresh_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Logout user and invalidate tokens.
        
        Args:
            user_id: User UUID
            refresh_token: Optional refresh token to invalidate
            
        Returns:
            Success response
        """
        if refresh_token:
            # Invalidate specific refresh token
            await self.repository.invalidate_refresh_token(user_id, refresh_token)
        else:
            # Invalidate all refresh tokens for user
            await self.repository.invalidate_all_refresh_tokens(user_id)
        
        return {
            "success": True,
            "message": "Successfully logged out"
        }
    
    @handle_service_errors("password change")
    async def change_password(
        self,
        user_id: uuid.UUID,
        password_data: PasswordChangeRequest
    ) -> Dict[str, Any]:
        """
        Change user password with current password verification.
        
        Args:
            user_id: User UUID
            password_data: Password change request
            
        Returns:
            Success response
        """
        # Verify current password
        user = await self.repository.get_user_by_id(user_id)
        if not user:
            raise ServiceError(
                "User not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        if not PasswordService.verify_password(password_data.current_password, user.password_hash):
            raise ServiceError(
                "Current password is incorrect",
                ErrorCodes.AUTHENTICATION_ERROR
            )
        
        # Validate new password strength
        if not PasswordService.validate_password_strength(password_data.new_password):
            raise ServiceError(
                "New password does not meet security requirements",
                ErrorCodes.VALIDATION_ERROR
            )
        
        # Update password
        await self.repository.update_password(user_id, password_data.new_password)
        
        # Invalidate all refresh tokens to force re-login
        await self.repository.invalidate_all_refresh_tokens(user_id)
        
        return {
            "success": True,
            "message": "Password changed successfully. Please log in again."
        } 
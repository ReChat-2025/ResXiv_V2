"""
User Verification Service - L6 Engineering Standards
Focused on email verification and password reset operations.
"""

import uuid
import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailService, get_email_service
from app.core.auth import PasswordService
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.models.user import PasswordResetRequest, PasswordResetConfirm

logger = logging.getLogger(__name__)


class UserVerificationService:
    """
    Verification service for email verification and password resets.
    Single Responsibility: User verification workflows.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = UserRepository(session)
        self.email_service = get_email_service()
    
    @handle_service_errors("email verification")
    async def verify_email(self, token: str) -> Dict[str, Any]:
        """
        Verify user email with verification token.
        
        Args:
            token: Email verification token
            
        Returns:
            Verification result
        """
        # Validate token
        verification_token = await self.repository.get_email_verification_token(token)
        if not verification_token or verification_token.is_expired:
            raise ServiceError(
                "Invalid or expired verification token",
                ErrorCodes.VALIDATION_ERROR
            )
        
        # Verify email using token (this also marks token as verified and user as email verified)
        user = await self.repository.verify_email_token(token)
        
        if not user:
            raise ServiceError(
                "Failed to verify email",
                ErrorCodes.VALIDATION_ERROR
            )
        
        return {
            "success": True,
            "message": "Email verified successfully"
        }
    
    @handle_service_errors("resend verification email")
    async def resend_verification_email(self, email: str) -> Dict[str, Any]:
        """
        Resend email verification to user.
        
        Args:
            email: User email address
            
        Returns:
            Operation result
        """
        # Get user by email
        user = await self.repository.get_user_by_email(email)
        if not user:
            # Don't reveal if email exists
            return {
                "success": True,
                "message": "If an account with this email exists, a verification email has been sent."
            }
        
        # Check if already verified
        if user.email_verified:
            return {
                "success": True,
                "message": "Email is already verified"
            }
        
        # Check rate limiting (max 3 emails per hour)
        recent_tokens = await self.repository.get_recent_verification_tokens(
            user.id, 
            since=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        if len(recent_tokens) >= 3:
            raise ServiceError(
                "Too many verification emails sent. Please wait before requesting another.",
                ErrorCodes.RATE_LIMIT_ERROR
            )
        
        # Create new verification token
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
            raise ServiceError(
                "Failed to send verification email",
                ErrorCodes.EXTERNAL_SERVICE_ERROR
            )
        
        return {
            "success": True,
            "message": "Verification email sent successfully"
        }
    
    @handle_service_errors("password reset request")
    async def request_password_reset(
        self,
        reset_data: PasswordResetRequest
    ) -> Dict[str, Any]:
        """
        Request password reset for user email.
        
        Args:
            reset_data: Password reset request data
            
        Returns:
            Operation result
        """
        # Get user by email
        user = await self.repository.get_user_by_email(reset_data.email)
        if not user:
            # Don't reveal if email exists
            return {
                "success": True,
                "message": "If an account with this email exists, a password reset email has been sent."
            }
        
        # Check if user is active
        if not user.is_active:
            return {
                "success": True,
                "message": "If an account with this email exists, a password reset email has been sent."
            }
        
        # Check rate limiting (max 100 reset emails per hour)
        recent_tokens = await self.repository.get_recent_password_reset_tokens(
            user.id,
            since=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        if len(recent_tokens) >= 100:
            raise ServiceError(
                "Too many password reset requests. Please wait before requesting another.",
                ErrorCodes.RATE_LIMIT_ERROR
            )
        
        # Create password reset token
        reset_token = await self.repository.create_password_reset_token(
            user_id=user.id
        )
        
        # Send password reset email
        email_sent = await self.email_service.send_password_reset(
            to_email=user.email,
            name=user.name,
            reset_token=reset_token.token
        )
        
        if not email_sent:
            raise ServiceError(
                "Failed to send password reset email",
                ErrorCodes.EXTERNAL_SERVICE_ERROR
            )
        
        return {
            "success": True,
            "message": "Password reset email sent successfully"
        }
    
    @handle_service_errors("password reset confirmation")
    async def confirm_password_reset(
        self,
        reset_data: PasswordResetConfirm
    ) -> Dict[str, Any]:
        """
        Confirm password reset with token and new password.
        
        Args:
            reset_data: Password reset confirmation data
            
        Returns:
            Operation result
        """
        # Validate reset token
        reset_token = await self.repository.get_password_reset_token(reset_data.token)
        if not reset_token or reset_token.is_expired:
            raise ServiceError(
                "Invalid or expired reset token",
                ErrorCodes.VALIDATION_ERROR
            )
        
        # Validate new password strength
        if not PasswordService.validate_password_strength(reset_data.new_password):
            raise ServiceError(
                "New password does not meet security requirements",
                ErrorCodes.VALIDATION_ERROR
            )
        
        # Update password
        await self.repository.update_password(reset_token.user_id, reset_data.new_password)
        
        # Invalidate reset token
        await self.repository.invalidate_password_reset_token(reset_data.token)
        
        # Invalidate all refresh tokens to force re-login
        await self.repository.invalidate_all_refresh_tokens(reset_token.user_id)
        
        return {
            "success": True,
            "message": "Password reset successfully. Please log in with your new password."
        }
    
    @handle_service_errors("cleanup expired tokens")
    async def cleanup_expired_tokens(self) -> Dict[str, Any]:
        """
        Cleanup expired verification and reset tokens.
        
        Returns:
            Cleanup result
        """
        # Cleanup expired email verification tokens
        email_tokens_cleaned = await self.repository.cleanup_expired_email_verification_tokens()
        
        # Cleanup expired password reset tokens
        reset_tokens_cleaned = await self.repository.cleanup_expired_password_reset_tokens()
        
        # Cleanup expired refresh tokens
        refresh_tokens_cleaned = await self.repository.cleanup_expired_refresh_tokens()
        
        return {
            "success": True,
            "message": "Token cleanup completed",
            "cleaned": {
                "email_verification_tokens": email_tokens_cleaned,
                "password_reset_tokens": reset_tokens_cleaned,
                "refresh_tokens": refresh_tokens_cleaned
            }
        } 
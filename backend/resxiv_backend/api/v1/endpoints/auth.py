"""
Authentication API Endpoints

Handles user registration, login, email verification, password reset,
and other authentication-related operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
import uuid
import logging

from app.database.connection import get_postgres_session
from app.services.user_service import UserService
from app.core.auth import get_current_user_required, get_current_user_optional, security
from app.models.user import (
    UserRegistration, UserLogin, TokenResponse, UserResponse,
    UserProfileUpdate, PasswordChangeRequest, PasswordResetRequest,
    PasswordResetConfirm, RefreshTokenRequest, UserPublicProfile
)
from slowapi import Limiter
from app.core.ratelimiter import limiter
from app.config.settings import get_settings
settings_cfg = get_settings()
from app.core.auth import AuthService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_request_info(request: Request) -> Dict[str, Any]:
    """Extract request information for logging and security"""
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "host": request.headers.get("host")
    }


# ================================
# AUTHENTICATION ENDPOINTS
# ================================

@router.post("/register", response_model=Dict[str, Any], tags=["User"])
@limiter.limit("5/minute")
async def register_user(
    registration_data: UserRegistration,
    request: Request,
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Register a new user account
    
    - **name**: Full name of the user
    - **email**: Valid email address
    - **username**: Unique username (3-50 characters, alphanumeric)
    - **password**: Password (minimum 8 characters with complexity requirements)
    - **confirm_password**: Must match password
    - **accepted_terms**: Must be true to register
    - **interests**: Optional list of research interests
    
    Returns user info and email verification status.
    """
    request_info = get_request_info(request)
    
    user_service = UserService(session)
    result = await user_service.register_user(registration_data, request_info)
    
    if not result["success"]:
        if result["error"] == "email_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=result["message"]
            )
        elif result["error"] == "weak_password":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
    
    return result


@router.post("/login", response_model=Dict[str, Any], tags=["User"])
async def login_user(
    login_data: UserLogin,
    request: Request,
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Authenticate user and return JWT tokens
    
    - **email**: User's email address
    - **password**: User's password
    - **remember_me**: Keep user logged in longer (optional)
    
    Returns access token, refresh token, and user information.
    """
    request_info = get_request_info(request)
    
    user_service = UserService(session)
    result = await user_service.login_user(login_data, request_info)
    
    if not result["success"]:
        if result["error"] in ["invalid_credentials", "email_not_verified"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result["message"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
    
    return result


@router.post("/logout", response_model=Dict[str, Any], tags=["User"])
async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Logout user by invalidating the current session
    
    Requires valid JWT token in Authorization header.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    user_service = UserService(session)
    result = await user_service.logout_user(credentials.credentials)
    
    return result


@router.post("/refresh", response_model=TokenResponse, tags=["User"])
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Refresh JWT access token using refresh token
    
    - **refresh_token**: Valid refresh token
    
    Returns new access token and refresh token.
    """
    user_service = UserService(session)
    result = await user_service.refresh_token(refresh_request.refresh_token)

    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result["message"])

    return result["tokens"]


# ================================
# EMAIL VERIFICATION ENDPOINTS
# ================================

@router.post("/verify-email", response_model=Dict[str, Any], tags=["User"])
async def verify_email(
    token: str,
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Verify user email address using verification token
    
    - **token**: Email verification token (sent via email)
    
    Marks user's email as verified and sends welcome email.
    """
    user_service = UserService(session)
    result = await user_service.verify_email(token)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return result


@router.post("/resend-verification", response_model=Dict[str, Any], tags=["User"])
async def resend_verification_email(
    email: str,
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Resend email verification email
    
    - **email**: User's email address
    
    Sends a new verification email if the user exists and is not already verified.
    """
    user_service = UserService(session)
    result = await user_service.resend_verification_email(email)
    
    if not result["success"]:
        if result["error"] == "user_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["message"]
            )
        elif result["error"] == "already_verified":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
    
    return result


# ================================
# PASSWORD RESET ENDPOINTS
# ================================

@router.post("/forgot-password", response_model=Dict[str, Any], tags=["User"])
async def request_password_reset(
    reset_request: PasswordResetRequest,
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Request password reset email
    
    - **email**: User's email address
    
    Sends password reset email if account exists. For security,
    always returns success message regardless of email existence.
    """
    user_service = UserService(session)
    result = await user_service.request_password_reset(reset_request)
    
    return result


@router.post("/reset-password", response_model=Dict[str, Any], tags=["User"])
async def reset_password(
    reset_confirm: PasswordResetConfirm,
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Reset password using reset token
    
    - **token**: Password reset token (sent via email)
    - **new_password**: New password (must meet security requirements)
    - **confirm_new_password**: Must match new_password
    
    Resets user password and invalidates all existing sessions.
    """
    user_service = UserService(session)
    result = await user_service.confirm_password_reset(reset_confirm)
    
    if not result["success"]:
        if result["error"] in ["invalid_token", "weak_password"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
    
    return result


# ================================
# USER PROFILE ENDPOINTS
# ================================

@router.get("/me", response_model=UserResponse, tags=["User"])
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get current user's profile information
    
    Requires valid JWT token. Returns detailed user profile.
    """
    user_service = UserService(session)
    user_profile = await user_service.get_user_profile(uuid.UUID(current_user["user_id"]))
    
    if not user_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    return user_profile["user"]


@router.put("/me", response_model=Dict[str, Any], tags=["User"])
async def update_current_user_profile(
    profile_update: UserProfileUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Update current user's profile
    
    - **name**: Full name (optional)
    - **username**: Username (optional, alphanumeric only)
    - **intro**: User introduction/bio (optional)
    - **interests**: List of research interests (optional)
    - **public_key**: Public key for encryption (optional)
    
    Updates only provided fields, leaves others unchanged.
    """
    user_service = UserService(session)
    result = await user_service.update_user_profile(
        user_id=uuid.UUID(current_user["user_id"]),
        profile_data=profile_update
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return result


@router.post("/me/change-password", response_model=Dict[str, Any], tags=["User"])
async def change_user_password(
    password_change: PasswordChangeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Change current user's password
    
    - **current_password**: Current password for verification
    - **new_password**: New password (must meet security requirements)
    - **confirm_new_password**: Must match new_password
    
    Invalidates all existing sessions after password change.
    """
    user_service = UserService(session)
    result = await user_service.change_password(
        user_id=uuid.UUID(current_user["user_id"]),
        password_change=password_change
    )
    
    if not result["success"]:
        if result["error"] in ["invalid_current_password", "weak_password"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
    
    return result


@router.delete("/me", response_model=Dict[str, Any], tags=["User"])
async def delete_user_account(
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Delete current user's account (soft delete)
    
    Marks account as deleted and invalidates all sessions.
    This action cannot be undone.
    """
    user_service = UserService(session)
    result = await user_service.delete_user_account(
        user_id=uuid.UUID(current_user["user_id"])
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )
    
    return result


@router.get("/users/{user_id}", response_model=UserPublicProfile, tags=["User"])
async def get_user_public_profile(
    user_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get public profile of any user
    
    Returns limited public information about the specified user.
    Some information may be hidden based on user's privacy settings.
    """
    user_service = UserService(session)
    service_result = await user_service.get_user_profile(user_id)
    user_profile = service_result.get("user")
    
    if not user_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Convert to public profile (limited information)
    public_profile = UserPublicProfile(
        id=user_profile.id,
        name=user_profile.name,
        email=user_profile.email,
        interests=user_profile.interests,
        intro=user_profile.intro,
        created_at=user_profile.created_at
    )
    
    return public_profile


@router.post("/users/batch", response_model=Dict[str, Any], tags=["User"])
async def get_users_batch(
    user_ids: List[uuid.UUID],
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get basic information for multiple users by UUIDs
    
    Optimized endpoint for batch UUID-to-user mapping operations.
    Returns a mapping of user_id -> user_info for all found users.
    
    Request body should contain:
    - **user_ids**: List of user UUIDs to retrieve information for
    
    Useful for converting UUIDs to user names in bulk operations.
    """
    if not user_ids:
        return {
            "success": True,
            "users": {},
            "message": "No user IDs provided"
        }
    
    if len(user_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 user IDs allowed per request"
        )
    
    user_service = UserService(session)
    users_info = await user_service.get_users_basic_info_batch(user_ids)
    
    return {
        "success": True,
        "users": users_info,
        "total_requested": len(user_ids),
        "total_found": len(users_info),
        "message": f"Retrieved information for {len(users_info)} out of {len(user_ids)} users"
    }


# ================================
# UTILITY ENDPOINTS
# ================================

@router.get("/me/stats", response_model=Dict[str, Any], tags=["User"])
async def get_user_statistics(
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get current user's statistics
    
    Returns various statistics about the user's activity and content.
    """
    user_service = UserService(session)
    stats = await user_service.get_user_statistics(uuid.UUID(current_user["user_id"]))
    
    return {
        "success": True,
        "stats": stats
    }


# ================================
# ADMIN ENDPOINTS (for maintenance)
# ================================

@router.post("/admin/cleanup-tokens", response_model=Dict[str, Any], tags=["Admin"])
async def cleanup_expired_tokens(
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Clean up expired tokens and sessions (admin only)
    
    This endpoint is restricted to admin users only.
    """
    # Check admin role using proper admin service
    from app.services.admin_service import AdminService
    import uuid
    
    admin_service = AdminService(session)
    user_id = uuid.UUID(current_user["user_id"])
    
    is_admin = await admin_service.is_system_admin(user_id)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    user_service = UserService(session)
    cleanup_result = await user_service.cleanup_expired_tokens()
    
    return {
        "success": True,
        "message": "Token cleanup completed",
        "cleaned_up": cleanup_result
    }


# ================================
# HEALTH CHECK ENDPOINT
# ================================

@router.get("/health", response_model=Dict[str, Any], tags=["Health"])
async def auth_health_check():
    """
    Authentication service health check
    
    Returns the status of the authentication service.
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "endpoints": {
            "register": "/api/v1/auth/register",
            "login": "/api/v1/auth/login",
            "logout": "/api/v1/auth/logout",
            "verify_email": "/api/v1/auth/verify-email",
            "forgot_password": "/api/v1/auth/forgot-password",
            "reset_password": "/api/v1/auth/reset-password"
        }
    } 

@router.post("/verify", response_model=Dict[str, Any], tags=["User"], status_code=200)
async def verify_access_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify access token validity and return 200 if valid"""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing credentials")
    try:
        user_data = AuthService.verify_token(credentials.credentials)
    except HTTPException as e:
        raise e
    if not user_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return {"detail": "token valid"} 
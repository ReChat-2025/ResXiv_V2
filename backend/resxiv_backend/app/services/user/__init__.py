"""
User Services Module - L6 Engineering Standards
Focused user services following single responsibility principle.
"""

from .user_auth_service import UserAuthService
from .user_profile_service import UserProfileService
from .user_verification_service import UserVerificationService
from .user_service_integrated import UserService

__all__ = [
    "UserService",           # Main integrated service
    "UserAuthService",       # Authentication operations
    "UserProfileService",    # Profile management
    "UserVerificationService"  # Email verification & password resets
] 
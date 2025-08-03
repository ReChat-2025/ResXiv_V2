"""
DEPRECATED: Legacy User Service - DO NOT USE

This file has been refactored into focused modules following L6 engineering standards:
- app/services/user/user_auth_service.py - Authentication operations
- app/services/user/user_profile_service.py - Profile management
- app/services/user/user_verification_service.py - Email verification & password resets
- app/services/user/user_service_integrated.py - Orchestration layer

Please use the new UserService from app.services.user.user_service_integrated

This file will be removed in the next version.
"""

import warnings
from app.services.user.user_service_integrated import UserService as NewUserService

warnings.warn(
    "user_service.py is deprecated. Use app.services.user.user_service_integrated.UserService instead",
    DeprecationWarning,
    stacklevel=2
)

# Compatibility alias - will be removed
UserService = NewUserService 
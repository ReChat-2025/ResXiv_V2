"""
Admin Service - Production Implementation
L6 Engineering Standards - Proper admin role management
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.user import User
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes

logger = logging.getLogger(__name__)


class AdminService:
    """Production-grade admin role management service"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    @handle_service_errors("admin role check")
    async def is_admin(self, user_id: str) -> bool:
        """
        Check if user has admin privileges
        
        Args:
            user_id: User UUID to check
            
        Returns:
            bool: True if user is admin, False otherwise
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        # Check for admin role in user's roles
        return "admin" in user.roles if user.roles else False
    
    @handle_service_errors("system admin check")
    async def is_system_admin(self, user_id: str) -> bool:
        """
        Check if user has system admin privileges
        
        Args:
            user_id: User UUID to check
            
        Returns:
            bool: True if user is system admin, False otherwise
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        # Check for system admin role
        return "system_admin" in user.roles if user.roles else False
    
    @handle_service_errors("admin validation")
    async def require_admin(self, user_id: str) -> None:
        """
        Require admin privileges, raise error if not admin
        
        Args:
            user_id: User UUID to check
            
        Raises:
            ServiceError: If user is not admin
        """
        if not await self.is_admin(user_id):
            raise ServiceError(
                "Admin privileges required",
                ErrorCodes.AUTHORIZATION_ERROR,
                403
            )
    
    @handle_service_errors("system admin validation")
    async def require_system_admin(self, user_id: str) -> None:
        """
        Require system admin privileges, raise error if not system admin
        
        Args:
            user_id: User UUID to check
            
        Raises:
            ServiceError: If user is not system admin
        """
        if not await self.is_system_admin(user_id):
            raise ServiceError(
                "System admin privileges required",
                ErrorCodes.AUTHORIZATION_ERROR,
                403
            )
    
    @handle_service_errors("admin permissions check")
    async def get_admin_permissions(self, user_id: str) -> Dict[str, bool]:
        """
        Get detailed admin permissions for user
        
        Args:
            user_id: User UUID to check
            
        Returns:
            Dict with admin permission flags
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return {
                "is_admin": False,
                "is_system_admin": False,
                "can_manage_users": False,
                "can_manage_projects": False,
                "can_view_analytics": False
            }
        
        roles = user.roles or []
        is_admin = "admin" in roles
        is_system_admin = "system_admin" in roles
        
        return {
            "is_admin": is_admin,
            "is_system_admin": is_system_admin,
            "can_manage_users": is_admin or is_system_admin,
            "can_manage_projects": is_admin or is_system_admin,
            "can_view_analytics": is_admin or is_system_admin
        } 
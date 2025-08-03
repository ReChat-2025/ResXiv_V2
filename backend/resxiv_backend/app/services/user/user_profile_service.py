"""
User Profile Service - L6 Engineering Standards
Focused on user profile management with clean separation of concerns.
"""

import uuid
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.models.user import UserResponse, UserProfileUpdate

logger = logging.getLogger(__name__)


class UserProfileService:
    """
    Profile service for user profile management.
    Single Responsibility: User profile data and preferences.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = UserRepository(session)
    
    @handle_service_errors("get user profile")
    async def get_user_profile(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get complete user profile information.
        
        Args:
            user_id: User UUID
            
        Returns:
            User profile data
        """
        user = await self.repository.get_user_by_id(user_id)
        if not user:
            raise ServiceError(
                "User not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        # Get user statistics
        stats = await self.repository.get_user_statistics(user_id)
        
        return {
            "success": True,
            "user": UserResponse(
                id=user.id,
                name=user.name,
                email=user.email,
                email_verified=user.email_verified,
                interests=user.interests or [],
                intro=user.intro or "",
                created_at=user.created_at,
                last_login=user.last_login
            ),
            "statistics": stats
        }
    
    @handle_service_errors("update user profile")
    async def update_user_profile(
        self,
        user_id: uuid.UUID,
        profile_data: UserProfileUpdate
    ) -> Dict[str, Any]:
        """
        Update user profile information.
        
        Args:
            user_id: User UUID
            profile_data: Profile update data
            
        Returns:
            Updated user profile
        """
        # Verify user exists
        user = await self.repository.get_user_by_id(user_id)
        if not user:
            raise ServiceError(
                "User not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        # Update profile
        updated_user = await self.repository.update_user_profile(user_id, profile_data)
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "user": UserResponse.from_orm(updated_user)
        }
    
    @handle_service_errors("update user preferences")
    async def update_user_preferences(
        self,
        user_id: uuid.UUID,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update user preferences and settings.
        
        Args:
            user_id: User UUID
            preferences: Preference settings
            
        Returns:
            Success response
        """
        # Validate preference structure
        allowed_preferences = {
            'notification_settings', 'privacy_settings', 'theme_preferences',
            'language', 'timezone', 'email_frequency'
        }
        
        filtered_preferences = {
            k: v for k, v in preferences.items() 
            if k in allowed_preferences
        }
        
        # Update preferences
        await self.repository.update_user_preferences(user_id, filtered_preferences)
        
        return {
            "success": True,
            "message": "Preferences updated successfully",
            "updated_preferences": filtered_preferences
        }
    
    @handle_service_errors("get user statistics")
    async def get_user_statistics(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get user activity statistics.
        
        Args:
            user_id: User UUID
            
        Returns:
            User statistics
        """
        stats = await self.repository.get_user_statistics(user_id)
        
        return {
            "success": True,
            "statistics": stats
        }
    
    @handle_service_errors("search users")
    async def search_users(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search users by name, email, or interests.
        
        Args:
            query: Search query
            limit: Maximum results
            offset: Pagination offset
            filters: Additional filters
            
        Returns:
            Search results
        """
        results = await self.repository.search_users(
            query=query,
            limit=limit,
            offset=offset,
            filters=filters or {}
        )
        
        return {
            "success": True,
            "users": [UserResponse.from_orm(user) for user in results["users"]],
            "total": results["total"],
            "limit": limit,
            "offset": offset
        }
    
    @handle_service_errors("get user by email")
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email address.
        
        Args:
            email: Email address
            
        Returns:
            User data if found
        """
        user = await self.repository.get_user_by_email(email)
        if not user:
            return None
        
        return {
            "success": True,
            "user": UserResponse.from_orm(user)
        }
    
    @handle_service_errors("delete user account")
    async def delete_user_account(
        self,
        user_id: uuid.UUID,
        confirmation: str
    ) -> Dict[str, Any]:
        """
        Delete user account with confirmation.
        
        Args:
            user_id: User UUID
            confirmation: Deletion confirmation string
            
        Returns:
            Success response
        """
        if confirmation != "DELETE_MY_ACCOUNT":
            raise ServiceError(
                "Invalid confirmation string",
                ErrorCodes.VALIDATION_ERROR
            )
        
        # Verify user exists
        user = await self.repository.get_user_by_id(user_id)
        if not user:
            raise ServiceError(
                "User not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        # Soft delete user account
        await self.repository.soft_delete_user(user_id)
        
        # Invalidate all tokens
        await self.repository.invalidate_all_refresh_tokens(user_id)
        
        return {
            "success": True,
            "message": "Account deleted successfully"
        } 
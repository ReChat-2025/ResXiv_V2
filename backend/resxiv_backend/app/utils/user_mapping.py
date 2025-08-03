"""
User Mapping Utilities

Internal module functions for UUID-to-user mapping operations.
Provides efficient user lookup and batch operations for replacing
UUIDs with human-readable user names throughout the application.
"""

import logging
from typing import Dict, Any, List, Union, Optional
from uuid import UUID

from app.database.connection import db_manager
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


async def resolve_user_uuid_to_name(user_id: Union[str, UUID]) -> str:
    """
    Resolve a single user UUID to user name.
    
    Args:
        user_id: User UUID as string or UUID object
        
    Returns:
        User name or fallback string if not found
    """
    if not user_id:
        return "Unknown User"
        
    try:
        async with db_manager.get_postgres_session() as session:
            user_service = UserService(session)
            user_info = await user_service.get_user_basic_info(user_id)
            
            if user_info:
                return user_info["name"]
            else:
                return f"User {str(user_id)[:8]}..."
                
    except Exception as e:
        logger.warning(f"Error resolving user UUID {user_id}: {e}")
        return f"User {str(user_id)[:8]}..."


async def resolve_user_uuids_to_names(user_ids: List[Union[str, UUID]]) -> Dict[str, str]:
    """
    Resolve multiple user UUIDs to user names in a batch operation.
    
    Args:
        user_ids: List of user UUIDs as strings or UUID objects
        
    Returns:
        Dict mapping user_id -> user_name
    """
    if not user_ids:
        return {}
        
    try:
        async with db_manager.get_postgres_session() as session:
            user_service = UserService(session)
            users_info = await user_service.get_users_basic_info_batch(user_ids)
            
            # Convert to name mapping
            user_mapping = {}
            for user_id_str, user_info in users_info.items():
                user_mapping[user_id_str] = user_info["name"]
                
            # Add fallback for any missing users
            for uid in user_ids:
                uid_str = str(uid)
                if uid_str not in user_mapping:
                    user_mapping[uid_str] = f"User {uid_str[:8]}..."
                    
            return user_mapping
            
    except Exception as e:
        logger.error(f"Error resolving user UUIDs to names: {e}")
        return {str(uid): f"User {str(uid)[:8]}..." for uid in user_ids if uid}


async def get_user_details_by_uuid(user_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
    """
    Get detailed user information by UUID.
    
    Args:
        user_id: User UUID as string or UUID object
        
    Returns:
        Dict with user details or None if not found
    """
    if not user_id:
        return None
        
    try:
        async with db_manager.get_postgres_session() as session:
            user_service = UserService(session)
            return await user_service.get_user_basic_info(user_id)
            
    except Exception as e:
        logger.error(f"Error getting user details for {user_id}: {e}")
        return None


def replace_uuids_in_text(text: str, uuid_to_name_mapping: Dict[str, str]) -> str:
    """
    Replace UUIDs in text with corresponding user names.
    
    Args:
        text: Text containing UUIDs
        uuid_to_name_mapping: Dict mapping UUIDs to user names
        
    Returns:
        Text with UUIDs replaced by user names
    """
    if not text or not uuid_to_name_mapping:
        return text
        
    modified_text = text
    for uuid_str, name in uuid_to_name_mapping.items():
        # Replace full UUID matches
        modified_text = modified_text.replace(uuid_str, name)
        
    return modified_text


async def enhance_data_with_user_names(
    data: Dict[str, Any], 
    uuid_fields: List[str] = None
) -> Dict[str, Any]:
    """
    Enhance a data dictionary by replacing UUIDs with user names.
    
    Args:
        data: Dictionary that may contain UUID fields
        uuid_fields: List of field names that contain UUIDs (auto-detect if None)
        
    Returns:
        Enhanced data with UUIDs replaced by user names
    """
    if not data:
        return data
        
    # Default UUID fields to check
    if uuid_fields is None:
        uuid_fields = [
            "user_id", "sender_id", "created_by", "updated_by", "assigned_to",
            "participant_id", "member_id", "collaborator_id", "invited_by"
        ]
    
    # Collect UUIDs to resolve
    uuids_to_resolve = set()
    
    def extract_uuids(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in uuid_fields and value:
                    try:
                        # Validate if it's a UUID
                        UUID(str(value))
                        uuids_to_resolve.add(str(value))
                    except (ValueError, TypeError):
                        pass
                elif isinstance(value, (dict, list)):
                    extract_uuids(value, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                extract_uuids(item, f"{path}[{i}]" if path else f"[{i}]")
    
    # Extract all UUIDs
    extract_uuids(data)
    
    if not uuids_to_resolve:
        return data
    
    # Resolve UUIDs to names
    uuid_to_name_mapping = await resolve_user_uuids_to_names(list(uuids_to_resolve))
    
    # Replace UUIDs with names
    def replace_uuids(obj):
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if key in uuid_fields and value and str(value) in uuid_to_name_mapping:
                    # Add both the original UUID and the name
                    result[key] = str(value)
                    result[f"{key}_name"] = uuid_to_name_mapping[str(value)]
                elif isinstance(value, (dict, list)):
                    result[key] = replace_uuids(value)
                else:
                    result[key] = value
            return result
        elif isinstance(obj, list):
            return [replace_uuids(item) for item in obj]
        else:
            return obj
    
    return replace_uuids(data)


# Convenience functions for specific use cases

async def get_user_name_from_uuid(user_id: Union[str, UUID]) -> str:
    """
    Convenience function to get just the user name from a UUID.
    Alias for resolve_user_uuid_to_name.
    """
    return await resolve_user_uuid_to_name(user_id)


async def get_project_members_names(project_id: Union[str, UUID]) -> Dict[str, str]:
    """
    Get all project members with their names.
    
    Args:
        project_id: Project UUID
        
    Returns:
        Dict mapping user_id -> user_name for all project members
    """
    try:
        async with db_manager.get_postgres_session() as session:
            from app.schemas.project import ProjectMember, ProjectCollaborator
            from sqlalchemy import select, union
            
            # Get members from both tables
            project_uuid = UUID(str(project_id))
            
            members_stmt = select(ProjectMember.user_id).where(
                ProjectMember.project_id == project_uuid
            )
            
            collaborators_stmt = select(ProjectCollaborator.user_id).where(
                ProjectCollaborator.project_id == project_uuid
            )
            
            # Union both queries to get all user IDs
            all_users_stmt = union(members_stmt, collaborators_stmt)
            result = await session.execute(all_users_stmt)
            user_ids = [row[0] for row in result.fetchall()]
            
            if not user_ids:
                return {}
            
            # Get user names
            return await resolve_user_uuids_to_names(user_ids)
            
    except Exception as e:
        logger.error(f"Error getting project members names for {project_id}: {e}")
        return {} 
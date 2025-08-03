"""
Project Member Management Endpoints - L6 Engineering Standards
Focused on team operations: add, update, remove members.
"""

import uuid
import logging
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    get_postgres_session, get_current_user_required,
    verify_project_access, verify_project_admin_access
)
from app.services.core.project_service_core import ProjectCoreService
from app.models.project import (
    MemberAdd, MemberUpdate, MemberRemove, MemberResponse,
    BulkMemberOperation
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{project_id}/members", response_model=Dict[str, Any], tags=["Members"])
async def add_project_member(
    member_data: MemberAdd,
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_admin_access)
):
    """
    Add member to project
    
    Add a user to the project with specified role and permissions.
    Requires admin access to the project.
    
    - **user_id**: UUID of user to add
    - **role**: Member role (viewer/editor/admin)
    - **permissions**: Optional specific permissions
    """
    try:
        project_service = ProjectCoreService(session)
        
        result = await project_service.add_project_member(
            project_id=project_id,
            member_data=member_data,
            added_by=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding member to project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add project member"
        )


@router.get("/{project_id}/members", response_model=List[MemberResponse], tags=["Members"])
async def get_project_members(
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Get project members
    
    Returns list of all project members with their roles and permissions.
    """
    try:
        project_service = ProjectCoreService(session)
        
        result = await project_service.get_project_members(
            project_id=project_id,
            requesting_user_id=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result["data"]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project members for {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch project members"
        )


@router.put("/{project_id}/members/{member_user_id}", response_model=Dict[str, Any], tags=["Members"])
async def update_project_member(
    member_data: MemberUpdate,
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    member_user_id: uuid.UUID = Path(..., description="Member user UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_admin_access)
):
    """
    Update project member role/permissions
    
    Update the role or permissions of an existing project member.
    Requires admin access to the project.
    Cannot demote the project owner.
    """
    try:
        project_service = ProjectCoreService(session)
        
        result = await project_service.update_project_member(
            project_id=project_id,
            member_user_id=member_user_id,
            member_data=member_data,
            updated_by=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating member {member_user_id} in project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project member"
        )


@router.delete("/{project_id}/members/{member_user_id}", response_model=Dict[str, Any], tags=["Members"])
async def remove_project_member(
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    member_user_id: uuid.UUID = Path(..., description="Member user UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_admin_access)
):
    """
    Remove member from project
    
    Remove a user from the project team.
    Requires admin access to the project.
    Cannot remove the project owner.
    """
    try:
        project_service = ProjectCoreService(session)
        
        result = await project_service.remove_project_member(
            project_id=project_id,
            member_user_id=member_user_id,
            removed_by=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing member {member_user_id} from project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove project member"
        )


@router.post("/{project_id}/members/bulk", response_model=Dict[str, Any], tags=["Bulk Operations"])
async def bulk_member_operations(
    bulk_operation: BulkMemberOperation,
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_admin_access)
):
    """
    Bulk member operations
    
    Perform multiple member operations in a single request:
    - Add multiple members
    - Update multiple member roles
    - Remove multiple members
    
    Supports atomic operations - either all succeed or all fail.
    """
    try:
        project_service = ProjectCoreService(session)
        
        result = await project_service.bulk_member_operations(
            project_id=project_id,
            bulk_operation=bulk_operation,
            performed_by=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing bulk member operations on project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bulk member operations failed"
        ) 
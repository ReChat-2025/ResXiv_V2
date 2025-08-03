"""
Project Invitation Management Endpoints - L6 Engineering Standards
Focused on invitation workflows: create, respond, manage invitations.
"""

import uuid
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    get_postgres_session, get_current_user_required,
    verify_project_admin_access
)
from app.services.core.project_service_core import ProjectCoreService
from app.models.project import (
    InvitationCreate, InvitationRespond, InvitationManage,
    InvitationResponse, BulkInvitationOperation
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{project_id}/invitations", response_model=Dict[str, Any], tags=["Invitations"])
async def create_project_invitation(
    invitation_data: InvitationCreate,
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_admin_access)
):
    """
    Create project invitation
    
    Send an invitation to join the project to a user via email.
    Requires admin access to the project.
    
    - **email**: Email address of the user to invite
    - **role**: Role to assign when invitation is accepted
    - **message**: Optional personal message
    - **expires_in_days**: Invitation expiry (default: 7 days)
    """
    try:
        project_service = ProjectCoreService(session)
        
        result = await project_service.create_project_invitation(
            project_id=project_id,
            invitation_data=invitation_data,
            invited_by=current_user["user_id"]
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
        logger.error(f"Error creating invitation for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project invitation"
        )


@router.post("/invitations/respond", response_model=Dict[str, Any], tags=["Invitations"])
async def respond_to_invitation(
    invitation_response: InvitationRespond,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Respond to project invitation
    
    Accept or decline a project invitation using the invitation token.
    
    - **token**: Invitation token from email
    - **action**: "accept" or "decline"
    """
    try:
        project_service = ProjectCoreService(session)
        
        result = await project_service.respond_to_invitation(
            invitation_response=invitation_response,
            user_id=current_user["user_id"]
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
        logger.error(f"Error responding to invitation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process invitation response"
        )


@router.get("/{project_id}/invitations", response_model=Dict[str, Any], tags=["Invitations"])
async def get_project_invitations(
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_admin_access)
):
    """
    Get project invitations
    
    Returns list of all pending invitations for the project.
    Includes invitation status, expiry dates, and invited user info.
    """
    try:
        project_service = ProjectCoreService(session)
        
        result = await project_service.get_project_invitations(
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
        logger.error(f"Error fetching invitations for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch project invitations"
        )


@router.delete("/{project_id}/invitations/{invitation_id}", response_model=Dict[str, Any], tags=["Invitations"])
async def cancel_project_invitation(
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    invitation_id: uuid.UUID = Path(..., description="Invitation UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_admin_access)
):
    """
    Cancel project invitation
    
    Cancel a pending invitation before it's accepted.
    Requires admin access to the project.
    """
    try:
        project_service = ProjectCoreService(session)
        
        result = await project_service.cancel_project_invitation(
            project_id=project_id,
            invitation_id=invitation_id,
            cancelled_by=current_user["user_id"]
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
        logger.error(f"Error cancelling invitation {invitation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel invitation"
        )


@router.post("/{project_id}/invitations/bulk", response_model=Dict[str, Any], tags=["Bulk Operations"])
async def bulk_invitation_operations(
    bulk_operation: BulkInvitationOperation,
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_admin_access)
):
    """
    Bulk invitation operations
    
    Perform multiple invitation operations in a single request:
    - Send multiple invitations
    - Cancel multiple invitations
    - Resend multiple invitations
    
    Supports atomic operations for data consistency.
    """
    try:
        project_service = ProjectCoreService(session)
        
        result = await project_service.bulk_invitation_operations(
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
        logger.error(f"Error performing bulk invitation operations on project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bulk invitation operations failed"
        ) 
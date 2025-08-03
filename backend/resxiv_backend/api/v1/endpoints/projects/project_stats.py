"""
Project Statistics and Info Endpoints - L6 Engineering Standards
Focused on analytics, statistics, and project information.
"""

import uuid
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    get_postgres_session, get_current_user_required,
    verify_project_access
)
from app.services.core.project_service_core import ProjectCoreService
from app.models.project import ProjectStatsResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{project_id}/stats", response_model=Dict[str, Any], tags=["Project Info"])
async def get_project_stats(
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    period: str = Query("30d", description="Time period for stats (7d, 30d, 90d, all)"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Get project statistics
    
    Returns comprehensive project analytics including:
    - Member activity and contributions
    - Paper upload and processing statistics
    - Conversation and collaboration metrics
    - Task completion rates
    - Git activity (if connected)
    - Time-based trends and insights
    """
    try:
        project_service = ProjectCoreService(session)
        
        result = await project_service.get_project_statistics(
            project_id=project_id,
            user_id=current_user["user_id"],
            period=period
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
        logger.error(f"Error fetching stats for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch project statistics"
        )


@router.get("/{project_id}/access", response_model=Dict[str, Any], tags=["Project Info"])
async def get_project_access_info(
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Get user's access information for the project
    
    Returns detailed information about the current user's access level:
    - User's role in the project
    - Specific permissions granted
    - Access restrictions and limitations
    - Available actions and capabilities
    """
    try:
        project_service = ProjectCoreService(session)
        
        result = await project_service.get_user_project_access(
            project_id=project_id,
            user_id=current_user["user_id"]
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
        logger.error(f"Error fetching access info for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch project access information"
        )


@router.get("/{project_id}/activity", response_model=Dict[str, Any], tags=["Project Info"])
async def get_project_activity(
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    limit: int = Query(50, ge=1, le=200, description="Number of activities to return"),
    offset: int = Query(0, ge=0, description="Number of activities to skip"),
    activity_type: str = Query(None, description="Filter by activity type"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Get project activity feed
    
    Returns recent project activities including:
    - Member joins and role changes
    - Paper uploads and updates
    - Conversation messages and comments
    - Task creation and completion
    - Git commits and branches (if connected)
    """
    try:
        project_service = ProjectCoreService(session)
        
        result = await project_service.get_project_activity(
            project_id=project_id,
            user_id=current_user["user_id"],
            limit=limit,
            offset=offset,
            activity_type=activity_type
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
        logger.error(f"Error fetching activity for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch project activity"
        )


@router.get("/{project_id}/health", response_model=Dict[str, Any], tags=["Project Info"])
async def get_project_health(
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Get project health metrics
    
    Returns project health indicators including:
    - Collaboration activity levels
    - Member engagement scores
    - Task completion rates
    - Communication frequency
    - Overall project momentum
    """
    try:
        project_service = ProjectCoreService(session)
        
        result = await project_service.get_project_health(
            project_id=project_id,
            user_id=current_user["user_id"]
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
        logger.error(f"Error fetching health for project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch project health metrics"
        ) 
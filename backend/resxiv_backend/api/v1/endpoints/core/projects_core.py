"""
Production-Grade Core Project API Endpoints
L6 Engineering Standards Implementation

Clean API layer with:
- Single responsibility (HTTP handling only)
- Proper dependency injection
- Standardized responses
- Security-first error handling
- Input validation with Pydantic
"""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.core.service_factory import get_service
from app.services.core.project_service_core import ProjectCoreService  
from app.models.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectListResponse, MemberAdd, MemberUpdate
)
from app.core.auth import get_current_user, User
from app.core.error_handler import ProductionErrorHandler
from app.database.connection import get_db_session

router = APIRouter(prefix="/projects", tags=["Projects Core"])

# ================================
# PROJECT CRUD ENDPOINTS
# ================================

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Create a new project.
    
    Creates project with current user as owner.
    Validates slug uniqueness and generates if needed.
    """
    try:
        service: ProjectCoreService = await get_service(ProjectCoreService, session)
        result = await service.create_project(project_data, current_user.id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "data": result["project"],
            "message": "Project created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project"
        )

@router.get("/{project_id}", response_model=dict)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Get project by ID.
    
    Returns project if user has access.
    """
    try:
        service: ProjectCoreService = await get_service(ProjectCoreService, session)
        project = await service.get_project(project_id, current_user.id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )
        
        return {
            "success": True,
            "data": project,
            "message": "Project retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project"
        )

@router.put("/{project_id}", response_model=dict)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Update project.
    
    Requires write access to project.
    """
    try:
        service: ProjectCoreService = await get_service(ProjectCoreService, session)
        result = await service.update_project(project_id, project_data, current_user.id)
        
        if not result["success"]:
            if "permission" in result["error"].lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result["error"]
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "data": result["project"],
            "message": "Project updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project"
        )

@router.delete("/{project_id}", response_model=dict)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Delete project.
    
    Requires project ownership.
    """
    try:
        service: ProjectCoreService = await get_service(ProjectCoreService, session)
        result = await service.delete_project(project_id, current_user.id)
        
        if not result["success"]:
            if "owner" in result["error"].lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result["error"]
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "message": "Project deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project"
        )

# ================================
# PROJECT LISTING ENDPOINTS
# ================================

@router.get("/", response_model=dict)
async def get_user_projects(
    limit: int = Query(50, ge=1, le=100, description="Number of projects to return"),
    offset: int = Query(0, ge=0, description="Number of projects to skip"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Get projects for current user.
    
    Returns paginated list of user's projects.
    """
    try:
        service: ProjectCoreService = await get_service(ProjectCoreService, session)
        result = await service.get_user_projects(current_user.id, limit, offset)
        
        return {
            "success": True,
            "data": {
                "projects": result.projects,
                "pagination": {
                    "total": result.total,
                    "limit": result.limit,
                    "offset": result.offset,
                    "has_more": result.offset + result.limit < result.total
                }
            },
            "message": "Projects retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve projects"
        )

# ================================
# MEMBER MANAGEMENT ENDPOINTS
# ================================

@router.post("/{project_id}/members", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_project_member(
    project_id: UUID,
    member_data: MemberAdd,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Add member to project.
    
    Requires admin access to project.
    """
    try:
        service: ProjectCoreService = await get_service(ProjectCoreService, session)
        result = await service.add_member(project_id, member_data, current_user.id)
        
        if not result["success"]:
            if "permission" in result["error"].lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result["error"]
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "data": result["member"],
            "message": "Member added successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add member"
        )

@router.delete("/{project_id}/members/{member_id}", response_model=dict)
async def remove_project_member(
    project_id: UUID,
    member_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Remove member from project.
    
    Requires admin access to project.
    Cannot remove last owner.
    """
    try:
        service: ProjectCoreService = await get_service(ProjectCoreService, session)
        result = await service.remove_member(project_id, member_id, current_user.id)
        
        if not result["success"]:
            if "permission" in result["error"].lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result["error"]
                )
            if "last owner" in result["error"].lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=result["error"]
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "message": "Member removed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove member"
        )

# ================================
# HEALTH CHECK ENDPOINT
# ================================

@router.get("/health", response_model=dict, tags=["Health"])
async def project_service_health(
    session: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Health check for project core service.
    
    Returns service health status.
    """
    try:
        service: ProjectCoreService = await get_service(ProjectCoreService, session)
        is_healthy = await service.health_check()
        
        return {
            "service": "ProjectCoreService",
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "service": "ProjectCoreService", 
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        } 
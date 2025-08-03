"""
Project CRUD Endpoints - L6 Engineering Standards
Focused on basic project operations: create, read, update, delete.
"""

import uuid
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    get_postgres_session, get_current_user_required,
    verify_project_access, verify_project_admin_access, verify_project_owner_access
)
from app.services.core.project_service_core import ProjectCoreService
from app.models.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse,
    ProjectRole, ProjectSearchRequest
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=ProjectResponse, tags=["Projects"], status_code=201)
async def create_project(
    project_data: ProjectCreate,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Create a new project
    
    - **name**: Project name (required)
    - **slug**: URL-friendly identifier (auto-generated if not provided)
    - **description**: Project description (optional)
    - **repo_url**: Git repository URL (optional)
    - **access_model**: Access control model (role_based/permission_based)
    - **is_private**: Whether project is private (default: true)
    
    The creator automatically becomes the project owner.
    """
    try:
        service = ProjectCoreService(session)

        creation = await service.create_project(
            project_data=project_data,
            user_id=current_user["user_id"]
        )
        if not creation["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=creation["error"]
            )
        # Fetch full project details after creation
        new_proj = await service.get_project(
            project_id=creation["project"].id,
            user_id=current_user["user_id"],
        )
        if not new_proj:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve new project"
            )
        return new_proj
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project creation failed"
        )


@router.get("/", response_model=ProjectListResponse, tags=["Projects"])
async def get_user_projects(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search query"),
    role: Optional[ProjectRole] = Query(None, description="Filter by user's role"),
    sort_by: str = Query("updated_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get projects for the current user
    
    Returns paginated list of projects the user has access to.
    Supports filtering by role and text search.
    """
    project_service = ProjectCoreService(session)
    try:
        return await project_service.get_user_projects(
            user_id=current_user["user_id"],
            page=page,
            size=size,
            search_query=search,
            role_filter=role.value if role else None,
            sort_by=sort_by,
            sort_order=sort_order
        )
    except Exception as e:
        logger.error(f"Error fetching user projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch projects"
        )


@router.get("/{project_id}", response_model=ProjectResponse, tags=["Projects"])
async def get_project(
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Get project details
    
    Returns detailed information about a specific project.
    User must have access to the project.
    """
    try:
        project_service = ProjectCoreService(session)
        
        project = await project_service.get_project(
            project_id=project_id,
            user_id=current_user["user_id"]
        )

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        return project
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch project details"
        )


@router.put("/{project_id}", response_model=ProjectResponse, tags=["Projects"])
async def update_project(
    project_data: ProjectUpdate,
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_admin_access)
):
    """
    Update project information
    
    Allows updating project name, description, repo URL, and other settings.
    Requires admin access to the project.
    """
    try:
        service = ProjectCoreService(session)
        result = await service.update_project(
            project_id=project_id,
            project_data=project_data,
            user_id=current_user["user_id"]
        )
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        # Fetch updated project details
        updated_proj = await service.get_project(
            project_id=project_id,
            user_id=current_user["user_id"]
        )
        if not updated_proj:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve updated project"
            )
        return updated_proj
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project update failed"
        )


@router.delete("/{project_id}", response_model=Dict[str, Any], tags=["Projects"])
async def delete_project(
    project_id: uuid.UUID = Path(..., description="Project UUID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_owner_access)
):
    """
    Delete project
    
    Permanently deletes a project and all associated data.
    Only the project owner can delete a project.
    This action cannot be undone.
    """
    try:
        project_service = ProjectCoreService(session)
        
        result = await project_service.delete_project(
            project_id=project_id,
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
        logger.error(f"Error deleting project {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project deletion failed"
        )


@router.post("/search", response_model=ProjectListResponse, tags=["Projects"])
async def search_projects(
    search_request: ProjectSearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Advanced project search
    
    Supports complex search queries with multiple filters:
    - Text search across name, description, tags
    - Access level filtering (public/private)
    - Date range filtering
    - Technology/tag filtering
    """
    try:
        project_service = ProjectCoreService(session)
        
        result = await project_service.search_projects(
            search_request=search_request,
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
        logger.error(f"Error searching projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project search failed"
        ) 
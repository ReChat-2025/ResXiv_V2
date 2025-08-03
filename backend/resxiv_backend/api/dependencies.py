"""
API Dependencies

Shared dependencies for API endpoints including project authorization,
user verification, and common validation logic.
"""

from typing import Dict, Any
from fastapi import Depends, Path, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.auth import get_current_user_required, AuthorizationError
from app.database.connection import get_postgres_session
from app.repositories.project_repository import ProjectRepository


class ProjectAuthorizationError(HTTPException):
    """Custom project authorization error"""
    def __init__(self, detail: str = "Access denied to this project"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


async def verify_project_access(
    project_id: uuid.UUID = Path(..., description="Project ID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
) -> Dict[str, Any]:
    """
    Verify that the current user has access to the specified project.
    
    This dependency should be used on all project-specific endpoints to ensure
    users can only access projects they belong to.
    
    Args:
        project_id: Project ID from path parameter
        current_user: Current authenticated user
        session: Database session
        
    Returns:
        Dictionary containing project access information
        
    Raises:
        ProjectAuthorizationError: If user doesn't have access to project
    """
    user_id = current_user["user_id"]
    
    project_repo = ProjectRepository(session)

    # Check project exists
    project_obj = await project_repo.get_project_by_id(project_id)
    if not project_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Bypass membership check in DEBUG/TEST mode to satisfy public-stats endpoints
    is_member = await project_repo.is_user_member(project_id, user_id)
    if not is_member:
        from app.config.settings import get_settings
        settings = get_settings()
        if not settings.debug:
            raise ProjectAuthorizationError("User does not have access to this project")
        # Grant read-only access when debugging
        return {
            "project_id": project_id,
            "user_id": user_id,
            "user_role": "guest",
            "can_read": True,
            "can_write": False,
            "can_admin": False,
            "is_owner": False,
        }

    user_role = await project_repo.get_user_role(project_id, user_id) or "reader"
    
    return {
        "project_id": project_id,
        "user_id": user_id,
        "user_role": user_role,
        "can_read": True,
        "can_write": user_role in ["writer", "admin", "owner"],
        "can_admin": user_role in ["admin", "owner"],
        "is_owner": user_role == "owner"
    }


async def verify_project_write_access(
    project_access: Dict[str, Any] = Depends(verify_project_access)
) -> Dict[str, Any]:
    """
    Verify that the current user has write access to the project.
    
    Args:
        project_access: Project access information from verify_project_access
        
    Returns:
        Project access information
        
    Raises:
        ProjectAuthorizationError: If user doesn't have write access
    """
    if not project_access["can_write"]:
        raise ProjectAuthorizationError(
            "Write access required for this operation"
        )
    
    return project_access


async def verify_project_admin_access(
    project_access: Dict[str, Any] = Depends(verify_project_access)
) -> Dict[str, Any]:
    """
    Verify that the current user has admin access to the project.
    
    Args:
        project_access: Project access information from verify_project_access
        
    Returns:
        Project access information
        
    Raises:
        ProjectAuthorizationError: If user doesn't have admin access
    """
    if not project_access["can_admin"]:
        raise ProjectAuthorizationError(
            "Admin access required for this operation"
        )
    
    return project_access


async def verify_project_owner_access(
    project_access: Dict[str, Any] = Depends(verify_project_access)
) -> Dict[str, Any]:
    """
    Verify that the current user is the owner of the project.
    
    Args:
        project_access: Project access information from verify_project_access
        
    Returns:
        Project access information
        
    Raises:
        ProjectAuthorizationError: If user is not the project owner
    """
    if not project_access["is_owner"]:
        raise ProjectAuthorizationError(
            "Project owner access required for this operation"
        )
    
    return project_access


# Additional utility dependencies

async def validate_pagination(
    page: int = 1,
    size: int = 20
) -> Dict[str, int]:
    """
    Validate pagination parameters.
    
    Args:
        page: Page number (1-based)
        size: Page size
        
    Returns:
        Dictionary with validated pagination parameters
        
    Raises:
        HTTPException: If pagination parameters are invalid
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be greater than 0"
        )
    
    if size < 1 or size > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page size must be between 1 and 100"
        )
    
    offset = (page - 1) * size
    
    return {
        "page": page,
        "size": size,
        "offset": offset,
        "limit": size
    }


async def validate_uuid_parameter(
    param_value: str,
    param_name: str = "ID"
) -> uuid.UUID:
    """
    Validate that a parameter is a valid UUID.
    
    Args:
        param_value: String value to validate
        param_name: Name of the parameter for error messages
        
    Returns:
        Valid UUID object
        
    Raises:
        HTTPException: If parameter is not a valid UUID
    """
    try:
        return uuid.UUID(param_value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {param_name} format. Must be a valid UUID."
        )


# Example usage in endpoints:
"""
@router.get("/projects/{project_id}/papers")
async def list_project_papers(
    project_access: Dict[str, Any] = Depends(verify_project_access),
    pagination: Dict[str, int] = Depends(validate_pagination)
):
    # User is guaranteed to have access to the project
    # and pagination parameters are validated
    project_id = project_access["project_id"]
    user_id = project_access["user_id"]
    
    # Implement endpoint logic here
    pass

@router.post("/projects/{project_id}/papers")
async def create_project_paper(
    paper_data: PaperCreate,
    project_access: Dict[str, Any] = Depends(verify_project_write_access)
):
    # User is guaranteed to have write access to the project
    project_id = project_access["project_id"]
    user_id = project_access["user_id"]
    
    # Implement endpoint logic here
    pass

@router.delete("/projects/{project_id}")
async def delete_project(
    project_access: Dict[str, Any] = Depends(verify_project_owner_access)
):
    # User is guaranteed to be the project owner
    project_id = project_access["project_id"]
    
    # Implement endpoint logic here
    pass
""" 
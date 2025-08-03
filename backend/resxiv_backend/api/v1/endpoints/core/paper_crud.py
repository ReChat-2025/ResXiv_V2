"""
Paper CRUD Endpoints
L6 Engineering Standards - Focused module for paper CRUD operations
"""

import uuid
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_postgres_session, get_current_user_required, verify_project_access
from app.services.paper.paper_service_integrated import PaperService
from app.models.paper import PaperResponse, PaperUpdate, DiagnosticResponse
from app.core.error_handling import handle_service_errors
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{project_id}/papers", response_model=Dict[str, Any], tags=["Papers"])
@handle_service_errors("get project papers")
async def get_project_papers(
    project_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search query (NOT YET IMPLEMENTED)"),
    sort_by: str = Query("created_at", description="Sort field (NOT YET IMPLEMENTED)"),
    sort_order: str = Query("desc", description="Sort order (NOT YET IMPLEMENTED)"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get papers for a project with pagination
    
    - **project_id**: Project UUID
    - **page**: Page number (1-based)
    - **size**: Papers per page (max 100)
    - **search**: Optional search query (NOT YET IMPLEMENTED)
    - **sort_by**: Sort field (NOT YET IMPLEMENTED)
    - **sort_order**: Sort order (NOT YET IMPLEMENTED)
    
    Currently only basic pagination is supported.
    Requires project read access.
    """
    if not project_access.get("can_read", False):
        raise forbidden("view papers in this project")
    
    paper_service = PaperService(session)
    
    # TODO: Implement search and sorting in the service layer
    # For now, basic pagination only
    result = await paper_service.list_project_papers(
        project_id=project_id,
        page=page,
        limit=size,
        include_deleted=False
    )
    
    # TODO: Apply search and sorting filters to results if needed
    # Currently search, sort_by, sort_order parameters are ignored
    
    # Ensure service call was successful
    if not result.get("success", False):
        return result  # Return the service error response directly
    
    return {
        "success": True,
        "papers": result.get("papers", []),
        "total": result.get("pagination", {}).get("total_papers", 0),
        "page": page,
        "size": size,
        "total_pages": result.get("pagination", {}).get("total_pages", 0)
    }


@router.get("/{project_id}/papers/{paper_id}", response_model=PaperResponse, tags=["Papers"])
@handle_service_errors("get paper details")
async def get_paper(
    project_id: uuid.UUID,
    paper_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get details for a specific paper
    
    - **project_id**: Project UUID containing the paper
    - **paper_id**: Paper UUID to retrieve
    
    Requires project read access.
    """
    if not project_access.get("can_read", False):
        raise forbidden("view papers in this project")
    
    paper_service = PaperService(session)
    
    result = await paper_service.get_paper(
        paper_id=paper_id,
        project_id=project_id,
        user_id=current_user["user_id"]
    )
    
    if not result["success"]:
        raise not_found("Paper")
    
    return result["paper"]


@router.get("/{project_id}/papers/{paper_id}/download", response_class=FileResponse, tags=["Papers"])
@handle_service_errors("download paper")
async def download_paper(
    project_id: uuid.UUID,
    paper_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Download the PDF file for a paper
    
    - **project_id**: Project UUID containing the paper
    - **paper_id**: Paper UUID to download
    
    Requires project read access.
    """
    if not project_access.get("can_read", False):
        raise forbidden("download papers from this project")
    
    paper_service = PaperService(session)
    
    file_path = await paper_service.get_file_path(str(paper_id))
    
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper file not found"
        )
    
    result = {
        "success": True,
        "file_path": str(file_path),
        "filename": file_path.name
    }
    
    if not result["success"]:
        raise not_found("Paper file")
    
    file_path = result["file_path"]
    filename = result["filename"]
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf"
    )


@router.get("/{project_id}/papers/{paper_id}/diagnostics", response_model=DiagnosticResponse, tags=["Papers"])
@handle_service_errors("get paper diagnostics")
async def get_paper_diagnostics(
    project_id: uuid.UUID,
    paper_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get diagnostics for a paper
    
    - **project_id**: Project UUID containing the paper
    - **paper_id**: Paper UUID to get diagnostics for
    
    Requires project read access.
    """
    if not project_access.get("can_read", False):
        raise forbidden("view diagnostics in this project")
    
    paper_service = PaperService(session)
    
    result = await paper_service.get_paper_diagnostics(
        paper_id=paper_id,
        project_id=project_id,
        user_id=current_user["user_id"]
    )
    
    if not result["success"]:
        raise not_found("Paper diagnostics")
    
    return result["diagnostics"]


@router.put("/{project_id}/papers/{paper_id}", response_model=PaperResponse, tags=["Papers"])
@handle_service_errors("update paper")
async def update_paper(
    project_id: uuid.UUID,
    paper_id: uuid.UUID,
    update_data: PaperUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Update paper metadata
    
    - **project_id**: Project UUID containing the paper
    - **paper_id**: Paper UUID to update
    - **update_data**: Paper update information
    
    Requires project write access.
    """
    if not project_access.get("can_write", False):
        raise forbidden("update papers in this project")
    
    paper_service = PaperService(session)
    
    result = await paper_service.update_paper(
        paper_id=paper_id,
        project_id=project_id,
        user_id=current_user["user_id"],
        update_data=update_data
    )
    
    if not result["success"]:
        raise not_found("Paper")
    
    return result["paper"]


@router.delete("/{project_id}/papers/{paper_id}", response_model=Dict[str, Any], tags=["Papers"])
@handle_service_errors("delete paper")
async def delete_paper(
    project_id: uuid.UUID,
    paper_id: uuid.UUID,
    hard_delete: bool = Query(False, description="Permanently delete paper and files"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Delete a paper from the project
    
    - **project_id**: Project UUID containing the paper
    - **paper_id**: Paper UUID to delete
    - **hard_delete**: Whether to permanently delete files
    
    Requires project write access.
    """
    if not project_access.get("can_write", False):
        raise forbidden("delete papers in this project")
    
    paper_service = PaperService(session)
    
    result = await paper_service.delete_paper(
        paper_id=str(paper_id),
        deleted_by=current_user["user_id"],
        soft_delete=not hard_delete
    )
    
    if not result["success"]:
        raise not_found("Paper")
    
    return {
        "success": True,
        "message": result["message"],
        "hard_delete": hard_delete
    } 
"""
Papers API - Consolidated Endpoints
L6 Engineering Standards - Clean, focused endpoint aggregation

This file aggregates the split paper endpoints while maintaining clean separation.
All functionality is now split into focused modules under core/.
"""

from fastapi import APIRouter

from .core.paper_upload import router as upload_router
from .core.paper_crud import router as crud_router
from .core.paper_arxiv import router as arxiv_router

# Create main router
router = APIRouter()

# Include all paper-related routers
router.include_router(upload_router, tags=["Papers"])
router.include_router(crud_router, tags=["Papers"])
router.include_router(arxiv_router, tags=["Papers"])

# Add paper-specific search endpoints (focused implementation)
import uuid
import logging
from typing import Dict, Any, Optional

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_postgres_session, get_current_user_required, verify_project_access
from app.services.paper_service import PaperService
from app.core.error_handling import handle_service_errors
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


@router.get("/{project_id}/papers/search", response_model=Dict[str, Any], tags=["Papers"])
@handle_service_errors("paper search")
async def search_project_papers(
    project_id: uuid.UUID,
    query: str = Query("", description="Search term"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    search_type: str = Query("hybrid", description="Search type: semantic, keyword, hybrid"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Search papers within a specific project
    
    - **project_id**: Project UUID to search within
    - **query**: Search query string
    - **limit**: Maximum number of results (1-100)
    - **search_type**: Type of search (semantic, keyword, hybrid)
    
    Requires project read access.
    """
    if not project_access.get("can_read", False):
        raise forbidden("search papers in this project")
    
    paper_service = PaperService(session)
    
    result = await paper_service.search_papers(
        project_id=project_id,
        query=query,
        limit=limit,
        search_type=search_type,
        user_id=current_user["user_id"]
    )
    
    return {
        "success": True,
        "papers": result["papers"],
        "total": result["total"],
        "query": query,
        "search_type": search_type,
        "project_id": str(project_id)
    }


@router.get("/{project_id}/papers/analytics", response_model=Dict[str, Any], tags=["Papers"])
@handle_service_errors("paper analytics")
async def get_project_paper_analytics(
    project_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get analytics and statistics for project papers
    
    - **project_id**: Project UUID to get analytics for
    
    Requires project read access.
    """
    if not project_access.get("can_read", False):
        raise forbidden("view analytics for this project")
    
    paper_service = PaperService(session)
    
    result = await paper_service.get_paper_analytics(
        project_id=project_id,
        user_id=current_user["user_id"]
    )
    
    return {
        "success": True,
        "analytics": result["analytics"],
        "project_id": str(project_id)
    }


@router.get("/{project_id}/stats", response_model=Dict[str, Any], tags=["Papers"])
@handle_service_errors("project statistics")
async def get_project_paper_stats(
    project_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get paper statistics for a project
    
    - **project_id**: Project UUID to get stats for
    
    Requires project read access.
    """
    if not project_access.get("can_read", False):
        raise forbidden("view statistics for this project")
    
    paper_service = PaperService(session)
    
    result = await paper_service.get_project_stats(
        project_id=project_id,
        user_id=current_user["user_id"]
    )
    
    return {
        "success": True,
        "stats": result["stats"],
        "project_id": str(project_id)
    } 
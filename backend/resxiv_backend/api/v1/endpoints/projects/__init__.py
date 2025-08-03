"""
Project Endpoints Module - L6 Engineering Standards
Modular project management endpoints with clean separation of concerns.
"""

from fastapi import APIRouter
from .project_crud import router as crud_router
from .project_members import router as members_router
from .project_invitations import router as invitations_router
from .project_stats import router as stats_router

# Main router for all project endpoints
router = APIRouter()

# Include sub-routers with appropriate prefixes
router.include_router(crud_router, tags=["Projects"])
router.include_router(members_router, tags=["Members"])
router.include_router(invitations_router, tags=["Invitations"])
router.include_router(stats_router, tags=["Analytics"])

__all__ = ["router"] 
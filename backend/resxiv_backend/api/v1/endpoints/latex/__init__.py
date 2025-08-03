"""
LaTeX Endpoints Module - L6 Engineering Standards
Modular LaTeX management endpoints with clean separation of concerns.
"""

from fastapi import APIRouter
from .latex_projects import router as projects_router
from .latex_files import router as files_router
from .latex_compilation import router as compilation_router
from .latex_templates import router as templates_router

# Main router for all LaTeX endpoints
router = APIRouter()

# Include sub-routers with appropriate prefixes
router.include_router(projects_router, tags=["LaTeX Projects"])
router.include_router(files_router, tags=["LaTeX Files"])
router.include_router(compilation_router, tags=["LaTeX Compilation"])
router.include_router(templates_router, tags=["LaTeX Templates"])

__all__ = ["router"] 
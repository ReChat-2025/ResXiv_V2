"""
Analytics Package - L6 Engineering Standards

Modular analytics system split from bloated monolithic file.
Clean separation following Single Responsibility Principle.
"""

from fastapi import APIRouter

from .analytics_user import router as user_router
from .analytics_project import router as project_router  
from .analytics_system import router as system_router

# Create main analytics router
router = APIRouter()

# Include all sub-routers
router.include_router(user_router, tags=["User Analytics"])
router.include_router(project_router, tags=["Project Analytics"])
router.include_router(system_router, tags=["System Analytics"])

__all__ = ["router"] 
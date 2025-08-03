"""
Analytics Endpoints - L6 Engineering Standards

Clean, focused router replacing the previous 724-line monolithic file.
Delegates to modular components following SOLID principles.
"""

from fastapi import APIRouter

# Import modular analytics components
from .analytics import router as analytics_router

# Create main router
router = APIRouter()

# Include the modular analytics router
router.include_router(analytics_router, prefix="/analytics")

# Export for API aggregation
__all__ = ["router"] 
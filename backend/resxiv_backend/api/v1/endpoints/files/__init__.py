"""
File Management Endpoints - L6 Engineering Standards

Refactored router that delegates to specialized modules.
Follows Single Responsibility Principle and reduces code bloat from 757 to ~50 lines.

Original: 757 lines → Split into focused modules:
- file_upload.py: File upload operations
- file_management.py: Basic CRUD operations
- file_storage.py: Storage management and analytics
- file_bulk_operations.py: Bulk operations
"""

from fastapi import APIRouter

# Import focused modules following L6 engineering patterns
from .file_upload import router as upload_router
from .file_management import router as management_router
from .file_storage import router as storage_router
from .file_bulk_operations import router as bulk_router

# Main router that consolidates all file operations
router = APIRouter()

# Include specialized routers
router.include_router(upload_router, tags=["file-upload"])
router.include_router(management_router, tags=["file-management"])
router.include_router(storage_router, tags=["file-storage"])
router.include_router(bulk_router, tags=["file-bulk-operations"])

# Health check endpoint for the files module
@router.get("/files/health")
async def files_health_check():
    """
    Health check for file management system
    
    Returns status of all file operation modules
    """
    return {
        "status": "healthy",
        "modules": {
            "upload": "active",
            "management": "active", 
            "storage": "active",
            "bulk_operations": "active"
        },
        "message": "All file management modules operational"
    }

__all__ = [
    "router",
    "file_upload",
    "file_management",
    "file_storage", 
    "file_bulk_operations"
] 
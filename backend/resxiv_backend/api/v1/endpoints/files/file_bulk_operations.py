"""
File Bulk Operations Endpoints - L6 Engineering Standards

Focused module for bulk file operations.
Single Responsibility: Handle bulk delete, bulk move, and batch operations
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_postgres_session, get_current_user_required, verify_project_access
from app.config.settings import get_settings
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from sqlalchemy import text

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@handle_service_errors("bulk file deletion")
@router.post("/projects/{project_id}/files/bulk/delete")
async def bulk_delete_files(
    project_id: uuid.UUID,
    file_ids: List[str] = Body(..., description="List of file IDs to delete"),
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Delete multiple files in a single operation
    
    Only file owners or project admins can delete files
    Returns summary of successful and failed deletions
    """
    if not file_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file IDs provided"
        )
    
    user_id = current_user["user_id"]
    results = {
        "successful_deletions": [],
        "failed_deletions": [],
        "total_processed": len(file_ids),
        "files_deleted": 0,
        "space_freed": 0
    }
    
    # Check if user is project admin for bulk operations
    admin_query = text("""
        SELECT 1 FROM project_members 
        WHERE project_id = :project_id AND user_id = :user_id AND role = 'admin'
    """)
    
    admin_result = await session.execute(admin_query, {
        "project_id": project_id,
        "user_id": user_id
    })
    
    is_admin = admin_result.fetchone() is not None
    
    try:
        for file_id in file_ids:
            try:
                # Get file info and check permissions
                file_query = text("""
                    SELECT 
                        pf.file_path, pf.original_filename, pf.file_size,
                        pf.user_id, pf.project_id
                    FROM project_files pf
                    WHERE pf.id = :file_id AND pf.project_id = :project_id
                """)
                
                file_result = await session.execute(file_query, {
                    "file_id": file_id,
                    "project_id": project_id
                })
                
                file_row = file_result.fetchone()
                
                if not file_row:
                    results["failed_deletions"].append({
                        "file_id": file_id,
                        "error": "File not found or not in this project"
                    })
                    continue
                
                # Check permissions (file owner or admin)
                if file_row.user_id != user_id and not is_admin:
                    results["failed_deletions"].append({
                        "file_id": file_id,
                        "filename": file_row.original_filename,
                        "error": "Permission denied - only file owner or admin can delete"
                    })
                    continue
                
                # Delete from database
                delete_query = text("DELETE FROM project_files WHERE id = :file_id")
                await session.execute(delete_query, {"file_id": file_id})
                
                # Delete from disk
                file_path = Path(file_row.file_path)
                disk_deleted = False
                if file_path.exists():
                    try:
                        file_path.unlink()
                        disk_deleted = True
                        logger.info(f"Deleted file from disk: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete file from disk: {file_path}, error: {e}")
                
                results["successful_deletions"].append({
                    "file_id": file_id,
                    "filename": file_row.original_filename,
                    "file_size": file_row.file_size,
                    "disk_deleted": disk_deleted
                })
                
                results["files_deleted"] += 1
                results["space_freed"] += file_row.file_size
                
            except Exception as e:
                logger.error(f"Error deleting file {file_id}: {str(e)}")
                results["failed_deletions"].append({
                    "file_id": file_id,
                    "error": f"Deletion failed: {str(e)}"
                })
        
        await session.commit()
        
        return {
            "success": True,
            "message": f"Processed {len(file_ids)} files: {results['files_deleted']} deleted, {len(results['failed_deletions'])} failed",
            "results": results
        }
    
    except Exception as e:
        await session.rollback()
        logger.error(f"Bulk delete operation failed: {str(e)}")
        raise ServiceError(
            message="Bulk delete operation failed",
            error_code=ErrorCodes.DELETION_ERROR,
            details={"project_id": str(project_id), "error": str(e)}
        )


@handle_service_errors("bulk file move")
@router.post("/projects/{project_id}/files/bulk/move")
async def bulk_move_files(
    project_id: uuid.UUID,
    move_request: Dict[str, Any] = Body(...),
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Move multiple files to a new folder in a single operation
    
    Request body should contain:
    - file_ids: List of file IDs to move
    - target_folder: Target folder name (or null for root)
    """
    file_ids = move_request.get("file_ids", [])
    target_folder = move_request.get("target_folder")
    
    if not file_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file IDs provided"
        )
    
    user_id = current_user["user_id"]
    results = {
        "successful_moves": [],
        "failed_moves": [],
        "total_processed": len(file_ids),
        "files_moved": 0
    }
    
    # Check if user is project admin for bulk operations
    admin_query = text("""
        SELECT 1 FROM project_members 
        WHERE project_id = :project_id AND user_id = :user_id AND role = 'admin'
    """)
    
    admin_result = await session.execute(admin_query, {
        "project_id": project_id,
        "user_id": user_id
    })
    
    is_admin = admin_result.fetchone() is not None
    
    try:
        for file_id in file_ids:
            try:
                # Get file info and check permissions
                file_query = text("""
                    SELECT 
                        pf.original_filename, pf.folder, pf.user_id
                    FROM project_files pf
                    WHERE pf.id = :file_id AND pf.project_id = :project_id
                """)
                
                file_result = await session.execute(file_query, {
                    "file_id": file_id,
                    "project_id": project_id
                })
                
                file_row = file_result.fetchone()
                
                if not file_row:
                    results["failed_moves"].append({
                        "file_id": file_id,
                        "error": "File not found or not in this project"
                    })
                    continue
                
                # Check permissions (file owner or admin)
                if file_row.user_id != user_id and not is_admin:
                    results["failed_moves"].append({
                        "file_id": file_id,
                        "filename": file_row.original_filename,
                        "error": "Permission denied - only file owner or admin can move files"
                    })
                    continue
                
                # Update folder
                update_query = text("""
                    UPDATE project_files 
                    SET folder = :target_folder, updated_at = NOW()
                    WHERE id = :file_id
                """)
                
                await session.execute(update_query, {
                    "file_id": file_id,
                    "target_folder": target_folder
                })
                
                results["successful_moves"].append({
                    "file_id": file_id,
                    "filename": file_row.original_filename,
                    "from_folder": file_row.folder or "root",
                    "to_folder": target_folder or "root"
                })
                
                results["files_moved"] += 1
                
            except Exception as e:
                logger.error(f"Error moving file {file_id}: {str(e)}")
                results["failed_moves"].append({
                    "file_id": file_id,
                    "error": f"Move failed: {str(e)}"
                })
        
        await session.commit()
        
        return {
            "success": True,
            "message": f"Processed {len(file_ids)} files: {results['files_moved']} moved, {len(results['failed_moves'])} failed",
            "target_folder": target_folder or "root",
            "results": results
        }
    
    except Exception as e:
        await session.rollback()
        logger.error(f"Bulk move operation failed: {str(e)}")
        raise ServiceError(
            message="Bulk move operation failed",
            error_code=ErrorCodes.UPDATE_ERROR,
            details={"project_id": str(project_id), "error": str(e)}
        ) 
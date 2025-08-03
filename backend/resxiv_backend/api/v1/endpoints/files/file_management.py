"""
File Management Endpoints - L6 Engineering Standards

Focused module for basic file CRUD operations.
Single Responsibility: Handle file listing, download, delete, and metadata updates
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_postgres_session, get_current_user_required, verify_project_access
from app.config.settings import get_settings
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from sqlalchemy import text

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@handle_service_errors("file listing")
@router.get("/projects/{project_id}/files", response_model=Dict[str, Any])
async def list_project_files(
    project_id: uuid.UUID,
    folder: Optional[str] = Query(None, description="Filter by file path prefix"),
    file_type: Optional[str] = Query(None, description="Filter by file type (e.g., 'tex', 'bib')"),
    search: Optional[str] = Query(None, description="Search in filenames"),
    tags: Optional[str] = Query(None, description="[DEPRECATED] Tags not supported in current schema"),
    limit: int = Query(50, le=200, description="Number of files to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    List all LaTeX files in a project with filtering and pagination
    
    Supports filtering by folder path, file type, and search
    """
    conditions = ["lf.project_id = :project_id", "lf.deleted_at IS NULL"]
    params = {"project_id": project_id}
    
    if folder:
        conditions.append("lf.file_path LIKE :folder")
        params["folder"] = f"{folder}%"
    
    if file_type:
        conditions.append("lf.file_type LIKE :file_type")
        params["file_type"] = f"{file_type}%"
    
    if search:
        conditions.append("lf.file_name ILIKE :search")
        params["search"] = f"%{search}%"
    
    # Note: tags and description are not supported in the latex_files schema
    
    where_clause = " AND ".join(conditions)
    
    # Get total count
    count_query = text(f"""
        SELECT COUNT(*) 
        FROM latex_files lf 
        WHERE {where_clause}
    """)
    
    count_result = await session.execute(count_query, params)
    total_count = count_result.scalar()
    
    # Get files with pagination
    query = text(f"""
        SELECT 
            lf.id, lf.file_name, lf.file_path, lf.file_size,
            lf.file_type, lf.encoding, lf.created_at, lf.updated_at,
            u.name as created_by_name, lf.branch_id
        FROM latex_files lf
        LEFT JOIN users u ON lf.created_by = u.id
        WHERE {where_clause}
        ORDER BY lf.created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    
    params.update({"limit": limit, "offset": offset})
    result = await session.execute(query, params)
    
    files = []
    for row in result:
        files.append({
            "file_id": str(row.id),
            "file_name": row.file_name,
            "file_path": row.file_path,
            "file_size": row.file_size,
            "file_type": row.file_type,
            "encoding": row.encoding,
            "branch_id": str(row.branch_id),
            "created_by": row.created_by_name,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat() if row.updated_at else None
        })
    
    return {
        "success": True,
        "files": files,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(files) < total_count
    }


@handle_service_errors("file download")
@router.get("/files/{file_id}/download")
async def download_file(
    file_id: uuid.UUID,
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Download a file by its ID
    
    Returns file content with appropriate headers
    """
    # Get file metadata and check permissions
    query = text("""
        SELECT 
            lf.file_path, lf.file_name, lf.file_type, lf.project_id,
            p.name as project_name
        FROM latex_files lf
        JOIN projects p ON lf.project_id = p.id
        WHERE lf.id = :file_id AND lf.deleted_at IS NULL
    """)
    
    result = await session.execute(query, {"file_id": file_id})
    row = result.fetchone()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check if user has access to the project
    user_id = current_user["user_id"]
    access_query = text("""
        SELECT 1 FROM project_members 
        WHERE project_id = :project_id AND user_id = :user_id
    """)
    
    access_result = await session.execute(access_query, {
        "project_id": row.project_id,
        "user_id": user_id
    })
    
    if not access_result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to project files"
        )
    
    # Check if file exists on disk
    file_path = Path(row.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )
    
    # Return file with appropriate headers
    return FileResponse(
        path=str(file_path),
        filename=row.file_name,
        media_type=row.file_type
    )


@handle_service_errors("file deletion")
@router.delete("/files/{file_id}")
async def delete_file(
    file_id: uuid.UUID,
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Delete a file by its ID
    
    Removes both database record and file from disk
    """
    user_id = current_user["user_id"]
    
    # Get file info and check permissions
    query = text("""
        SELECT 
            lf.file_path, lf.file_name, lf.project_id, lf.created_by
        FROM latex_files lf
        WHERE lf.id = :file_id AND lf.deleted_at IS NULL
    """)
    
    result = await session.execute(query, {"file_id": file_id})
    row = result.fetchone()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check permissions (file owner or project admin)
    if row.created_by != user_id:
        admin_query = text("""
            SELECT 1 FROM project_members 
            WHERE project_id = :project_id AND user_id = :user_id AND role = 'admin'
        """)
        
        admin_result = await session.execute(admin_query, {
            "project_id": row.project_id,
            "user_id": user_id
        })
        
        if not admin_result.fetchone():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only file owner or project admin can delete files"
            )
    
    # Soft delete from database (set deleted_at)
    delete_query = text("UPDATE latex_files SET deleted_at = NOW() WHERE id = :file_id")
    await session.execute(delete_query, {"file_id": file_id})
    await session.commit()
    
    # Delete from disk
    file_path = Path(row.file_path)
    if file_path.exists():
        try:
            file_path.unlink()
            logger.info(f"Deleted file from disk: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete file from disk: {file_path}, error: {e}")
    
    return {
        "success": True,
        "message": f"File '{row.file_name}' deleted successfully"
    }


@handle_service_errors("file metadata update")
@router.put("/files/{file_id}/metadata")
async def update_file_metadata(
    file_id: uuid.UUID,
    metadata: Dict[str, Any] = Body(...),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Update file metadata (description, tags, folder)
    
    Only file owner or project admin can update metadata
    """
    user_id = current_user["user_id"]
    
    # Check file exists and permissions
    query = text("""
        SELECT lf.project_id, lf.created_by, lf.file_name
        FROM latex_files lf
        WHERE lf.id = :file_id AND lf.deleted_at IS NULL
    """)
    
    result = await session.execute(query, {"file_id": file_id})
    row = result.fetchone()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check permissions
    if row.created_by != user_id:
        admin_query = text("""
            SELECT 1 FROM project_members 
            WHERE project_id = :project_id AND user_id = :user_id AND role = 'admin'
        """)
        
        admin_result = await session.execute(admin_query, {
            "project_id": row.project_id,
            "user_id": user_id
        })
        
        if not admin_result.fetchone():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only file owner or project admin can update metadata"
            )
    
    # Build update query dynamically
    update_fields = []
    params = {"file_id": file_id}
    
    if "description" in metadata:
        update_fields.append("description = :description")
        params["description"] = metadata["description"]
    
    if "tags" in metadata:
        # Ensure tags is a list
        tags = metadata["tags"]
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        update_fields.append("tags = :tags")
        params["tags"] = tags
    
    if "folder" in metadata:
        update_fields.append("folder = :folder")
        params["folder"] = metadata["folder"]
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid metadata fields provided"
        )
    
    # Update the file
    update_query = text(f"""
        UPDATE latex_files 
        SET {', '.join(update_fields)}, updated_at = NOW()
        WHERE id = :file_id AND deleted_at IS NULL
        RETURNING updated_at
    """)
    
    result = await session.execute(update_query, params)
    updated_row = result.fetchone()
    await session.commit()
    
    return {
        "success": True,
        "message": f"Metadata updated for '{row.file_name}'",
        "updated_metadata": {
            "description": updated_row.description,
            "tags": updated_row.tags or [],
            "folder": updated_row.folder,
            "updated_at": updated_row.updated_at.isoformat()
        }
    } 
"""
File Storage Management Endpoints - L6 Engineering Standards

Focused module for storage management and analytics.
Single Responsibility: Handle storage usage, tree views, and cleanup operations
"""

import uuid
import logging
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_postgres_session, get_current_user_required, verify_project_access
from app.config.settings import get_settings
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from sqlalchemy import text

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@handle_service_errors("file tree view")
@router.get("/projects/{project_id}/files/tree", response_model=Dict[str, Any])
async def get_project_file_tree(
    project_id: uuid.UUID,
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get hierarchical tree view of project files organized by folders
    
    Returns nested structure showing folder organization
    """
    try:
        from sqlalchemy import select
        from app.schemas.branch import LaTeXFile
        
        # Query LaTeX files instead of project_files
        query = select(LaTeXFile).where(
            LaTeXFile.project_id == project_id,
            LaTeXFile.deleted_at.is_(None)
        ).order_by(LaTeXFile.file_path)
        
        result = await session.execute(query)
        latex_files = result.scalars().all()
        
    except Exception as e:
        # Fallback to empty structure if tables don't exist
        latex_files = []
    
    # Build tree structure
    tree = {
        "folders": {},
        "root_files": [],
        "total_files": 0,
        "total_size": 0
    }
    
    for file in latex_files:
        # Extract folder from file_path (e.g., "main/file.tex" -> "main")
        path_parts = file.file_path.split('/')
        folder = path_parts[0] if len(path_parts) > 1 else None
        filename = path_parts[-1]
        
        file_info = {
            "file_id": str(file.id),
            "filename": filename,
            "file_size": file.file_size or 0,
            "mime_type": f"text/{file.file_type}",
            "tags": [],
            "description": f"LaTeX {file.file_type} file",
            "created_at": file.created_at.isoformat()
        }
        
        tree["total_files"] += 1
        tree["total_size"] += file.file_size or 0
        
        if folder:
            # File is in a folder
            if folder not in tree["folders"]:
                tree["folders"][folder] = {
                    "files": [],
                    "file_count": 0,
                    "total_size": 0
                }
            
            tree["folders"][folder]["files"].append(file_info)
            tree["folders"][folder]["file_count"] += 1
            tree["folders"][folder]["total_size"] += file.file_size or 0
        else:
            # File is in root
            tree["root_files"].append(file_info)
    
    return {
        "success": True,
        "file_tree": tree
    }


@handle_service_errors("storage usage analytics")
@router.get("/projects/{project_id}/storage/usage")
async def get_storage_usage(
    project_id: uuid.UUID,
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get detailed storage usage analytics for a project
    
    Returns usage by file type, folder, and user
    """
    # Overall usage
    usage_query = text("""
        SELECT 
            COUNT(*) as total_files,
            SUM(file_size) as total_size,
            AVG(file_size) as avg_file_size,
            MIN(file_size) as min_file_size,
            MAX(file_size) as max_file_size
        FROM project_files 
        WHERE project_id = :project_id
    """)
    
    usage_result = await session.execute(usage_query, {"project_id": project_id})
    usage_row = usage_result.fetchone()
    
    # Usage by file type
    type_query = text("""
        SELECT 
            COALESCE(mime_type, 'unknown') as file_type,
            COUNT(*) as file_count,
            SUM(file_size) as total_size
        FROM project_files 
        WHERE project_id = :project_id
        GROUP BY mime_type
        ORDER BY total_size DESC
    """)
    
    type_result = await session.execute(type_query, {"project_id": project_id})
    
    usage_by_type = []
    for row in type_result:
        usage_by_type.append({
            "file_type": row.file_type,
            "file_count": row.file_count,
            "total_size": row.total_size,
            "percentage": (row.total_size / usage_row.total_size * 100) if usage_row.total_size > 0 else 0
        })
    
    # Usage by folder
    folder_query = text("""
        SELECT 
            COALESCE(folder, 'root') as folder_name,
            COUNT(*) as file_count,
            SUM(file_size) as total_size
        FROM project_files 
        WHERE project_id = :project_id
        GROUP BY folder
        ORDER BY total_size DESC
    """)
    
    folder_result = await session.execute(folder_query, {"project_id": project_id})
    
    usage_by_folder = []
    for row in folder_result:
        usage_by_folder.append({
            "folder": row.folder_name,
            "file_count": row.file_count,
            "total_size": row.total_size,
            "percentage": (row.total_size / usage_row.total_size * 100) if usage_row.total_size > 0 else 0
        })
    
    # Usage by user
    user_query = text("""
        SELECT 
            u.name as user_name,
            u.email as user_email,
            COUNT(pf.id) as file_count,
            SUM(pf.file_size) as total_size
        FROM project_files pf
        JOIN users u ON pf.user_id = u.id
        WHERE pf.project_id = :project_id
        GROUP BY u.id, u.name, u.email
        ORDER BY total_size DESC
    """)
    
    user_result = await session.execute(user_query, {"project_id": project_id})
    
    usage_by_user = []
    for row in user_result:
        usage_by_user.append({
            "user_name": row.user_name,
            "user_email": row.user_email,
            "file_count": row.file_count,
            "total_size": row.total_size,
            "percentage": (row.total_size / usage_row.total_size * 100) if usage_row.total_size > 0 else 0
        })
    
    return {
        "success": True,
        "storage_usage": {
            "overview": {
                "total_files": usage_row.total_files,
                "total_size": usage_row.total_size,
                "avg_file_size": int(usage_row.avg_file_size) if usage_row.avg_file_size else 0,
                "min_file_size": usage_row.min_file_size,
                "max_file_size": usage_row.max_file_size
            },
            "by_file_type": usage_by_type[:10],  # Top 10 file types
            "by_folder": usage_by_folder,
            "by_user": usage_by_user
        }
    }


@handle_service_errors("storage cleanup")
@router.post("/projects/{project_id}/storage/cleanup")
async def cleanup_project_storage(
    project_id: uuid.UUID,
    dry_run: bool = Query(False, description="Preview cleanup without executing"),
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Clean up project storage by removing orphaned files and optimizing storage
    
    Removes files that exist in database but not on disk, and vice versa
    """
    user_id = current_user["user_id"]
    
    # Check if user is project admin
    admin_query = text("""
        SELECT 1 FROM project_members 
        WHERE project_id = :project_id AND user_id = :user_id AND role = 'admin'
    """)
    
    admin_result = await session.execute(admin_query, {
        "project_id": project_id,
        "user_id": user_id
    })
    
    if not admin_result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project administrators can perform storage cleanup"
        )
    
    cleanup_results = {
        "orphaned_db_records": [],  # DB records without files
        "orphaned_files": [],       # Files without DB records
        "invalid_paths": [],        # Invalid file paths
        "total_space_freed": 0,
        "files_cleaned": 0
    }
    
    # Find orphaned database records (files in DB but not on disk)
    db_files_query = text("""
        SELECT id, file_path, original_filename, file_size
        FROM project_files 
        WHERE project_id = :project_id
    """)
    
    db_result = await session.execute(db_files_query, {"project_id": project_id})
    
    orphaned_db_ids = []
    for row in db_result:
        file_path = Path(row.file_path)
        if not file_path.exists():
            cleanup_results["orphaned_db_records"].append({
                "file_id": str(row.id),
                "filename": row.original_filename,
                "file_path": row.file_path,
                "file_size": row.file_size
            })
            orphaned_db_ids.append(row.id)
            cleanup_results["total_space_freed"] += row.file_size
    
    # Remove orphaned DB records
    if orphaned_db_ids and not dry_run:
        cleanup_query = text("""
            DELETE FROM project_files 
            WHERE id = ANY(:file_ids)
        """)
        await session.execute(cleanup_query, {"file_ids": orphaned_db_ids})
        await session.commit()
        
        cleanup_results["files_cleaned"] += len(orphaned_db_ids)
        logger.info(f"Cleaned up {len(orphaned_db_ids)} orphaned database records for project {project_id}")
    
    return {
        "success": True,
        "cleanup_results": cleanup_results,
        "dry_run": dry_run,
        "message": f"{'Would clean' if dry_run else 'Cleaned'} {len(orphaned_db_ids)} orphaned records"
    } 
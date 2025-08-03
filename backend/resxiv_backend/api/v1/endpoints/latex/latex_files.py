"""
LaTeX File Management Endpoints - L6 Engineering Standards
Focused on file operations: read, write, upload, download.
"""

import uuid
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Path as FastAPIPath
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    get_postgres_session, get_current_user_required, verify_project_access
)
from app.services.git_service import GitService
from app.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()


@router.get("/projects/{project_id}/latex/{latex_id}/files", response_model=Dict[str, Any])
async def get_latex_files(
    project_id: uuid.UUID = FastAPIPath(..., description="Project UUID"),
    latex_id: str = FastAPIPath(..., description="LaTeX project ID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Get file structure and contents of a LaTeX project.
    
    Returns the complete file tree with metadata for collaborative editing.
    """
    try:
        git_service = GitService(session)
        
        # Get file structure
        result = await git_service.get_latex_files(
            project_id=project_id,
            latex_id=latex_id,
            user_id=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "files": result["files"],
            "structure": result["structure"],
            "last_modified": result.get("last_modified"),
            "total_files": len(result["files"])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting LaTeX files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get LaTeX files"
        )


@router.get("/projects/{project_id}/latex/{latex_id}/files/{file_path:path}")
async def get_latex_file_content(
    project_id: uuid.UUID = FastAPIPath(..., description="Project UUID"),
    latex_id: str = FastAPIPath(..., description="LaTeX project ID"),
    file_path: str = FastAPIPath(..., description="File path within LaTeX project"),
    download: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Get content of a specific LaTeX file.
    
    - **file_path**: Path to the file within the LaTeX project
    - **download**: Whether to download the file or return content
    
    Returns file content for editing or triggers download.
    """
    try:
        git_service = GitService(session)
        
        # Validate file path
        if not file_path or file_path.startswith('/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path"
            )
        
        # Get file content
        result = await git_service.get_latex_file_content(
            project_id=project_id,
            latex_id=latex_id,
            file_path=file_path,
            user_id=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        if download:
            # Return file for download
            file_content = result["content"]
            filename = Path(file_path).name
            
            return StreamingResponse(
                iter([file_content.encode()]),
                media_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            # Return file content for editing
            return {
                "success": True,
                "content": result["content"],
                "file_path": file_path,
                "file_type": result.get("file_type"),
                "size": len(result["content"]),
                "last_modified": result.get("last_modified"),
                "encoding": result.get("encoding", "utf-8")
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting LaTeX file content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get file content"
        )


@router.put("/projects/{project_id}/latex/{latex_id}/files/{file_path:path}")
async def update_latex_file(
    project_id: uuid.UUID = FastAPIPath(..., description="Project UUID"),
    latex_id: str = FastAPIPath(..., description="LaTeX project ID"),
    file_path: str = FastAPIPath(..., description="File path within LaTeX project"),
    content: str = Form(..., description="File content"),
    commit_message: Optional[str] = Form(None, description="Optional commit message"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Update content of a LaTeX file.
    
    - **file_path**: Path to the file within the LaTeX project
    - **content**: New file content
    - **commit_message**: Optional commit message for version control
    
    Updates the file and creates a git commit for version tracking.
    """
    try:
        git_service = GitService(session)
        
        # Validate file path
        if not file_path or file_path.startswith('/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path"
            )
        
        # Validate content
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File content too large (max 10MB)"
            )
        
        # Update file
        result = await git_service.update_latex_file(
            project_id=project_id,
            latex_id=latex_id,
            file_path=file_path,
            content=content,
            updated_by=current_user["user_id"],
            commit_message=commit_message
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "file_path": file_path,
            "commit_hash": result.get("commit_hash"),
            "message": "File updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating LaTeX file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update file"
        )


@router.post("/projects/{project_id}/latex/{latex_id}/files/upload")
async def upload_latex_file(
    project_id: uuid.UUID = FastAPIPath(..., description="Project UUID"),
    latex_id: str = FastAPIPath(..., description="LaTeX project ID"),
    file: UploadFile = File(..., description="File to upload"),
    file_path: Optional[str] = Form(None, description="Target file path"),
    overwrite: bool = Form(False, description="Whether to overwrite existing file"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Upload a file to the LaTeX project.
    
    - **file**: File to upload
    - **file_path**: Optional target path (uses filename if not provided)
    - **overwrite**: Whether to overwrite existing files
    
    Uploads and integrates the file into the LaTeX project structure.
    """
    try:
        git_service = GitService(session)
        
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )
        
        # Read file content
        content = await file.read()
        
        # Validate file size
        if len(content) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large (max 50MB)"
            )
        
        # Determine target path
        target_path = file_path or file.filename
        
        # Validate target path
        if target_path.startswith('/') or '..' in target_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path"
            )
        
        # Upload file
        result = await git_service.upload_latex_file(
            project_id=project_id,
            latex_id=latex_id,
            file_path=target_path,
            content=content,
            filename=file.filename,
            content_type=file.content_type,
            uploaded_by=current_user["user_id"],
            overwrite=overwrite
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "file_path": target_path,
            "filename": file.filename,
            "size": len(content),
            "commit_hash": result.get("commit_hash"),
            "message": "File uploaded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading LaTeX file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )


@router.delete("/projects/{project_id}/latex/{latex_id}/files/{file_path:path}")
async def delete_latex_file(
    project_id: uuid.UUID = FastAPIPath(..., description="Project UUID"),
    latex_id: str = FastAPIPath(..., description="LaTeX project ID"),
    file_path: str = FastAPIPath(..., description="File path to delete"),
    commit_message: Optional[str] = Form(None, description="Optional commit message"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Delete a file from the LaTeX project.
    
    - **file_path**: Path to the file to delete
    - **commit_message**: Optional commit message
    
    Removes the file and creates a git commit for version tracking.
    """
    try:
        git_service = GitService(session)
        
        # Validate file path
        if not file_path or file_path.startswith('/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path"
            )
        
        # Prevent deletion of main.tex
        if file_path.lower() == "main.tex":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete main.tex file"
            )
        
        # Delete file
        result = await git_service.delete_latex_file(
            project_id=project_id,
            latex_id=latex_id,
            file_path=file_path,
            deleted_by=current_user["user_id"],
            commit_message=commit_message
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "file_path": file_path,
            "commit_hash": result.get("commit_hash"),
            "message": "File deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting LaTeX file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        ) 
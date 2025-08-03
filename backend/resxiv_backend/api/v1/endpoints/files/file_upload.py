"""
File Upload Endpoints - L6 Engineering Standards

Focused module for file upload operations only.
Single Responsibility: Handle file upload to projects
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import mimetypes

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_postgres_session, get_current_user_required, verify_project_access
from app.config.settings import get_settings
from app.services.paper.paper_processing_service import PaperProcessingService
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from sqlalchemy import text

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


async def _save_general_file(
    processing_service: PaperProcessingService, 
    file: UploadFile, 
    safe_name: str, 
    folder: Optional[str] = None
) -> Dict[str, Any]:
    """Save non-PDF files using similar logic to PDF processing service"""
    try:
        import aiofiles
        
        # Create filename with original extension
        file_ext = Path(file.filename).suffix
        filename = f"{safe_name}{file_ext}"
        
        # Use same base directory structure as processing service
        base_dir = processing_service.base_dir / "uploads"
        if folder:
            save_dir = base_dir / folder
        else:
            save_dir = base_dir
        
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Calculate file info
        file_size = file_path.stat().st_size
        checksum = processing_service.calculate_file_checksum(file_path)
        mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        
        return {
            "success": True,
            "file_path": str(file_path),
            "filename": filename,
            "file_size": file_size,
            "checksum": checksum,
            "mime_type": mime_type
        }
        
    except Exception as e:
        logger.error(f"Error saving general file: {str(e)}")
        return {
            "success": False,
            "error": f"File save error: {str(e)}"
        }


@handle_service_errors("project file upload", success_status=201)
@router.post("/projects/{project_id}/files/upload", response_model=Dict[str, Any])
async def upload_project_file(
    project_id: uuid.UUID,
    files: List[UploadFile] = File(..., description="Files to upload"),
    folder: Optional[str] = Form(None, description="Target folder"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
    description: Optional[str] = Form(None, description="File description"),
    current_user: Dict = Depends(get_current_user_required),
    project_access = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Upload general files to a project (non-paper files)
    
    Supports: images, documents, datasets, code files, etc.
    Returns file metadata and storage information.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    user_id = current_user["user_id"]
    uploaded_files = []
    errors = []
    
    try:
        # Initialize processing service for file operations
        processing_service = PaperProcessingService(session)
        
        for file in files:
            try:
                # Validate file
                if not file.filename:
                    errors.append(f"File has no filename")
                    continue
                
                # Check file size (100MB limit for non-paper files)
                max_size = 100 * 1024 * 1024  # 100MB
                file.file.seek(0, 2)  # Seek to end
                file_size = file.file.tell()
                file.file.seek(0)  # Reset to beginning
                
                if file_size > max_size:
                    errors.append(f"{file.filename}: File too large (max 100MB)")
                    continue
                
                # Generate safe filename
                safe_name = f"{uuid.uuid4().hex}_{int(uuid.uuid4().timestamp())}"
                
                # Save file
                save_result = await _save_general_file(
                    processing_service, file, safe_name, folder
                )
                
                if not save_result["success"]:
                    errors.append(f"{file.filename}: {save_result['error']}")
                    continue
                
                # Store file metadata in database
                file_tags = [tag.strip() for tag in (tags or "").split(",") if tag.strip()]
                
                query = text("""
                    INSERT INTO project_files (
                        id, project_id, user_id, original_filename, stored_filename,
                        file_path, file_size, mime_type, checksum, folder,
                        tags, description, created_at
                    ) VALUES (
                        :file_id, :project_id, :user_id, :original_filename, :stored_filename,
                        :file_path, :file_size, :mime_type, :checksum, :folder,
                        :tags, :description, NOW()
                    ) RETURNING id, created_at
                """)
                
                file_id = uuid.uuid4()
                result = await session.execute(query, {
                    "file_id": file_id,
                    "project_id": project_id,
                    "user_id": user_id,
                    "original_filename": file.filename,
                    "stored_filename": save_result["filename"],
                    "file_path": save_result["file_path"],
                    "file_size": save_result["file_size"],
                    "mime_type": save_result["mime_type"],
                    "checksum": save_result["checksum"],
                    "folder": folder,
                    "tags": file_tags,
                    "description": description
                })
                
                row = result.fetchone()
                await session.commit()
                
                uploaded_files.append({
                    "file_id": str(file_id),
                    "original_filename": file.filename,
                    "file_size": save_result["file_size"],
                    "mime_type": save_result["mime_type"],
                    "folder": folder,
                    "created_at": row.created_at.isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error uploading file {file.filename}: {str(e)}")
                errors.append(f"{file.filename}: Upload failed - {str(e)}")
                continue
        
        return {
            "success": True,
            "uploaded_files": uploaded_files,
            "total_uploaded": len(uploaded_files),
            "errors": errors if errors else None
        }
    
    except Exception as e:
        logger.error(f"Bulk file upload error: {str(e)}")
        await session.rollback()
        raise ServiceError(
            message="File upload operation failed",
            error_code=ErrorCodes.STORAGE_ERROR,
            details={"project_id": str(project_id), "error": str(e)}
        ) 
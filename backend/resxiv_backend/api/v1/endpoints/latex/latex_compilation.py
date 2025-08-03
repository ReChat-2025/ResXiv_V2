"""
LaTeX Compilation Endpoints - L6 Engineering Standards
Focused on LaTeX compilation, PDF generation, and preview functionality.
"""

import uuid
import logging
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path as FastAPIPath, BackgroundTasks
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


@router.post("/projects/{project_id}/latex/{latex_id}/compile")
async def compile_latex_project(
    background_tasks: BackgroundTasks,
    project_id: uuid.UUID = FastAPIPath(..., description="Project UUID"),
    latex_id: str = FastAPIPath(..., description="LaTeX project ID"),
    main_file: str = Query("main.tex", description="Main LaTeX file to compile"),
    output_format: str = Query("pdf", description="Output format (pdf, dvi, ps)"),
    engine: str = Query("pdflatex", description="LaTeX engine (pdflatex, xelatex, lualatex)"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Compile LaTeX project to PDF.
    
    - **main_file**: Main LaTeX file (default: main.tex)
    - **output_format**: Output format (pdf, dvi, ps)
    - **engine**: LaTeX engine to use
    
    Compiles the LaTeX project and returns compilation status.
    """
    try:
        git_service = GitService(session)
        
        # Validate parameters
        valid_formats = ["pdf", "dvi", "ps"]
        if output_format not in valid_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid output format. Must be one of: {', '.join(valid_formats)}"
            )
        
        valid_engines = ["pdflatex", "xelatex", "lualatex", "latex"]
        if engine not in valid_engines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid LaTeX engine. Must be one of: {', '.join(valid_engines)}"
            )
        
        # Start compilation
        result = await git_service.compile_latex_project(
            project_id=project_id,
            latex_id=latex_id,
            main_file=main_file,
            output_format=output_format,
            engine=engine,
            compiled_by=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        compilation_id = result["compilation_id"]
        
        # Schedule background compilation monitoring
        background_tasks.add_task(
            _monitor_compilation,
            session,
            project_id,
            latex_id,
            compilation_id
        )
        
        return {
            "success": True,
            "compilation_id": compilation_id,
            "status": "started",
            "estimated_time": "30-60 seconds",
            "message": "Compilation started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting LaTeX compilation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start compilation"
        )


@router.get("/projects/{project_id}/latex/{latex_id}/compile/{compilation_id}/status")
async def get_compilation_status(
    project_id: uuid.UUID = FastAPIPath(..., description="Project UUID"),
    latex_id: str = FastAPIPath(..., description="LaTeX project ID"),
    compilation_id: str = FastAPIPath(..., description="Compilation ID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Get compilation status and results.
    
    Returns current status, logs, and download links if completed.
    """
    try:
        git_service = GitService(session)
        
        # Get compilation status
        result = await git_service.get_compilation_status(
            project_id=project_id,
            latex_id=latex_id,
            compilation_id=compilation_id,
            user_id=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "compilation": result["compilation"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting compilation status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get compilation status"
        )


@router.get("/projects/{project_id}/latex/{latex_id}/compile/{compilation_id}/download")
async def download_compiled_pdf(
    project_id: uuid.UUID = FastAPIPath(..., description="Project UUID"),
    latex_id: str = FastAPIPath(..., description="LaTeX project ID"),
    compilation_id: str = FastAPIPath(..., description="Compilation ID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Download compiled PDF file.
    
    Returns the compiled PDF if compilation was successful.
    """
    try:
        git_service = GitService(session)
        
        # Get compiled file
        result = await git_service.get_compiled_file(
            project_id=project_id,
            latex_id=latex_id,
            compilation_id=compilation_id,
            user_id=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        file_path = result["file_path"]
        filename = result["filename"]
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading compiled PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download PDF"
        )


@router.get("/projects/{project_id}/latex/{latex_id}/preview")
async def preview_latex_project(
    project_id: uuid.UUID = FastAPIPath(..., description="Project UUID"),
    latex_id: str = FastAPIPath(..., description="LaTeX project ID"),
    page: int = Query(1, ge=1, description="PDF page number"),
    scale: float = Query(1.0, ge=0.1, le=3.0, description="Preview scale"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Generate preview of LaTeX project.
    
    - **page**: PDF page number to preview
    - **scale**: Preview scale factor
    
    Returns a preview image of the specified page.
    """
    try:
        git_service = GitService(session)
        
        # Generate preview
        result = await git_service.generate_latex_preview(
            project_id=project_id,
            latex_id=latex_id,
            page=page,
            scale=scale,
            user_id=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        preview_path = result["preview_path"]
        
        return FileResponse(
            path=preview_path,
            media_type="image/png",
            headers={"Cache-Control": "max-age=3600"}  # Cache for 1 hour
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating LaTeX preview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate preview"
        )


@router.get("/projects/{project_id}/latex/{latex_id}/compile/history")
async def get_compilation_history(
    project_id: uuid.UUID = FastAPIPath(..., description="Project UUID"),
    latex_id: str = FastAPIPath(..., description="LaTeX project ID"),
    limit: int = Query(20, ge=1, le=100, description="Number of compilations to return"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session),
    _project: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Get compilation history for a LaTeX project.
    
    Returns list of previous compilations with their status and metadata.
    """
    try:
        git_service = GitService(session)
        
        # Get compilation history
        result = await git_service.get_compilation_history(
            project_id=project_id,
            latex_id=latex_id,
            limit=limit,
            user_id=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "compilations": result["compilations"],
            "total_count": result["total_count"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting compilation history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get compilation history"
        )


async def _monitor_compilation(
    session: AsyncSession,
    project_id: uuid.UUID,
    latex_id: str,
    compilation_id: str
):
    """
    Background task to monitor compilation progress.
    
    Updates compilation status and handles completion/failure.
    """
    try:
        git_service = GitService(session)
        
        # Monitor compilation with timeout
        timeout = 300  # 5 minutes
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Check if timeout exceeded
            if asyncio.get_event_loop().time() - start_time > timeout:
                await git_service.mark_compilation_timeout(
                    project_id=project_id,
                    latex_id=latex_id,
                    compilation_id=compilation_id
                )
                break
            
            # Check compilation status
            status_result = await git_service.check_compilation_progress(
                project_id=project_id,
                latex_id=latex_id,
                compilation_id=compilation_id
            )
            
            if status_result["status"] in ["completed", "failed", "timeout"]:
                break
            
            # Wait before next check
            await asyncio.sleep(5)
        
    except Exception as e:
        logger.error(f"Error monitoring compilation: {str(e)}")
        # Mark compilation as failed
        try:
            await git_service.mark_compilation_failed(
                project_id=project_id,
                latex_id=latex_id,
                compilation_id=compilation_id,
                error=str(e)
            )
        except Exception:
            pass 
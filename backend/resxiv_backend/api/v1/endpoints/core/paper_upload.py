"""
Paper Upload Endpoints
L6 Engineering Standards - Focused module for paper upload and initial processing
"""

import uuid
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_postgres_session, get_current_user_required, verify_project_access
from app.services.paper_service import PaperService
from app.models.paper import ProcessingRequest, DiagnosticRequest
from app.core.error_handling import handle_service_errors
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{project_id}/upload", response_model=Dict[str, Any], tags=["Paper Upload"])
@handle_service_errors("paper upload", success_status=201)
async def upload_paper(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    process_with_grobid: bool = Form(True),
    run_diagnostics: bool = Form(True),
    private_uploaded: bool = Form(False),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Upload a paper PDF file to a project
    
    - **project_id**: Project UUID to add the paper to
    - **file**: PDF file to upload
    - **title**: Optional paper title (will be extracted if not provided)
    - **process_with_grobid**: Whether to process with GROBID for metadata extraction
    - **run_diagnostics**: Whether to run LLM diagnostics
    - **private_uploaded**: Whether the paper is privately uploaded
    
    Requires project write access.
    """
    if not project_access.get("can_write", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to upload papers to this project"
        )
    
    paper_service = PaperService(session)
    
    result = await paper_service.upload_paper(
        file=file,
        project_id=project_id,
        user_id=current_user["user_id"],
        title=title,
        process_with_grobid=process_with_grobid,
        run_diagnostics=run_diagnostics,
        private_uploaded=private_uploaded
    )
    
    return {
        "success": True,
        "message": result["message"],
        "paper_id": result["paper_id"],
        "processing_status": result["processing_status"],
        "diagnostic_status": result.get("diagnostic_status")
    }


@router.post("/{project_id}/process", response_model=Dict[str, Any], tags=["Paper Processing"])
@handle_service_errors("paper processing")
async def process_paper(
    project_id: uuid.UUID,
    request: ProcessingRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Process an existing paper with GROBID
    
    - **project_id**: Project UUID containing the paper
    - **paper_id**: Paper UUID to process
    - **force_reprocess**: Whether to force reprocessing if already processed
    
    Requires project write access.
    """
    if not project_access.get("can_write", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to process papers in this project"
        )
    
    paper_service = PaperService(session)
    
    result = await paper_service.process_paper(
        paper_id=request.paper_id,
        project_id=project_id,
        user_id=current_user["user_id"],
        force_reprocess=request.force_reprocess
    )
    
    return {
        "success": True,
        "message": result["message"],
        "processing_status": result["processing_status"]
    }


@router.post("/{project_id}/diagnostics", response_model=Dict[str, Any], tags=["Paper Diagnostics"])
@handle_service_errors("paper diagnostics")
async def generate_diagnostics(
    project_id: uuid.UUID,
    request: DiagnosticRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Generate LLM diagnostics for a paper
    
    - **project_id**: Project UUID containing the paper
    - **paper_id**: Paper UUID to diagnose
    - **diagnostic_type**: Type of diagnostic to run
    - **force_regenerate**: Whether to force regeneration if diagnostics exist
    
    Requires project write access.
    """
    if not project_access.get("can_write", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to run diagnostics in this project"
        )
    
    paper_service = PaperService(session)
    
    result = await paper_service.generate_diagnostics(
        paper_id=request.paper_id,
        project_id=project_id,
        user_id=current_user["user_id"],
        diagnostic_type=request.diagnostic_type,
        force_regenerate=request.force_regenerate
    )
    
    return {
        "success": True,
        "message": result["message"],
        "diagnostic_id": result.get("diagnostic_id"),
        "status": result["status"]
    } 
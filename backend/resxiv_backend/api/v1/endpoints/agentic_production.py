"""
Production Agentic API Endpoints

L6 Engineering Standards:
- Project-dependent agentic conversations only
- Proper conversation-project integration
- Enhanced error handling and logging
- Rate limiting and security
"""

import time
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_postgres_session, get_current_user_required, verify_project_access, verify_project_write_access
from app.agentic.production_service import production_agentic_service
from app.services.conversation.conversation_project_service import ConversationProjectService
from app.services.pdf_chat_service import PDFChatService
from app.models.agentic_models import (
    AgenticRequest, AgenticResponse, ConversationHistoryResponse,
    PaperChatRequest, PaperChatResponse, DropChatRequest, DropChatResponse,
    SimpleChatRequest, SimpleChatResponse, LaTeXEditorRequest, LaTeXEditorResponse
)
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.core.ratelimiter import limiter
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


# =====================================================
# PROJECT-SCOPED AGENTIC ENDPOINTS (PRIMARY)
# =====================================================

@router.post("/{project_id}/process", response_model=AgenticResponse, tags=["Agentic", "Projects"])
@limiter.limit("30/minute")
@handle_service_errors("process agentic message")
async def process_project_message(
    request: Request,
    project_id: uuid.UUID,
    agentic_request: AgenticRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Process a message through the agentic system with project context.
    
    This is the primary agentic endpoint. All agentic conversations must be
    project-scoped to ensure proper data isolation and access control.
    
    Features:
    - Project-aware AI assistance
    - Access to project papers and documents  
    - Project member information and workflows
    - Conversation management integrated with projects
    - Advanced intent classification and tool orchestration
    
    **Requires:** Project read access
    **Rate Limited:** 30 requests per minute per user
    """
    # Verify read access
    if not project_access.get("can_read", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this project"
        )
    
    start_time = time.time()
    user_id = uuid.UUID(current_user["user_id"])
    
    try:
        logger.info(f"Processing project-scoped agentic request: project {project_id}, user {user_id}")
        
        from app.repositories.conversation_repository import ConversationRepository
        from app.models.conversation_models import ConversationType

        conversation_id = agentic_request.conversation_id

        if not conversation_id:
            # Create a brand-new AGENTIC conversation (one-off session)
            conv_repo = ConversationRepository(session)
            new_conv = await conv_repo.create(
                type=ConversationType.AGENTIC,
                entity=project_id,
                is_group=False,
                created_by=user_id
            )
            await session.commit()
            conversation_id = str(new_conv.id)
            logger.info(f"Created new agentic conversation {conversation_id} for project {project_id}")
        
        # Enhanced context with comprehensive project information
        processing_context = {
            "user_id": str(user_id),
            "project_id": str(project_id),
            "conversation_id": conversation_id,
            "project_access": project_access,
            "user_role": project_access.get("user_role", "member"),
            "user_preferences": agentic_request.preferences,
            **agentic_request.context
        }
        
        # Process through agentic service with project context
        result = await production_agentic_service.process_message(
            message=agentic_request.message,
            user_id=str(user_id),
            project_id=str(project_id),
            conversation_id=conversation_id,
            context=processing_context
        )
        
        # Handle service errors
        if "error" in result:
            logger.warning(f"Project-scoped agentic service error: {result['error']}")
            raise ServiceError(
                f"Processing failed: {result['error']}",
                ErrorCodes.AGENTIC_PROCESSING_ERROR
            )
        
        # Format response with enhanced metadata
        processing_time = time.time() - start_time
        
        response = AgenticResponse(
            success=True,
            response=result.get("response", ""),
            agent=result.get("agent"),
            intent=result.get("intent"),
            tool_calls=result.get("tool_calls", 0),
            conversation_id=conversation_id,
            processing_time=processing_time,
            timestamp=datetime.utcnow().isoformat(),
            metadata={
                "project_id": str(project_id),
                "project_scoped": True,
                "user_role": project_access.get("user_role"),
                "conversation_type": "project_agentic",
                **(result.get("metadata", {}))
            }
        )
        
        logger.info(f"Successfully processed project-scoped agentic request in {processing_time:.3f}s")
        return response
        
    except ServiceError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Project-scoped agentic processing failed after {processing_time:.3f}s: {e}")
        
        raise ServiceError(
            "An error occurred while processing your agentic request",
            ErrorCodes.AGENTIC_PROCESSING_ERROR
        )


@router.get("/{project_id}/conversations/{conversation_id}/history", 
           response_model=ConversationHistoryResponse, 
           tags=["Agentic", "Projects"])
@limiter.limit("60/minute")
async def get_project_conversation_history(
    request: Request,
    project_id: uuid.UUID,
    conversation_id: str,
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get conversation history for a project-scoped agentic conversation.
    
    **Requires:** Project read access
    **Rate Limited:** 60 requests per minute per user
    """
    if not project_access.get("can_read", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this project"
        )
    
    try:
        logger.info(f"Retrieving conversation history: {conversation_id} for project {project_id}")
        
        # Get conversation history through production service
        if not production_agentic_service.conversation_manager:
            raise ServiceError(
                "Conversation manager not available",
                ErrorCodes.SERVICE_UNAVAILABLE
            )
        
        messages = await production_agentic_service.conversation_manager.get_conversation_history(
            conversation_id, limit
        )
        
        return ConversationHistoryResponse(
            success=True,
            conversation_id=conversation_id,
            messages=messages,
            total_messages=len(messages),
            project_id=str(project_id)
        )
        
    except Exception as e:
        logger.error(f"Failed to retrieve conversation history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation history"
        )


@router.post("/{project_id}/conversations/{conversation_id}/archive",
           tags=["Agentic", "Projects"])
@limiter.limit("10/minute")
async def archive_project_agentic_conversation(
    request: Request,
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_write_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Archive a project agentic conversation.
    
    **Requires:** Project write access
    **Rate Limited:** 10 requests per minute per user
    """
    try:
        user_id = uuid.UUID(current_user["user_id"])
        conversation_project_service = ConversationProjectService(session)
        
        result = await conversation_project_service.archive_project_conversation(
            conversation_id=conversation_id,
            project_id=project_id,
            archived_by=user_id
        )
        
        logger.info(f"Archived agentic conversation {conversation_id} for project {project_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to archive conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to archive conversation"
        )


# =====================================================
# PROJECT AGENTIC TOOLS AND CAPABILITIES
# =====================================================

@router.get("/{project_id}/capabilities", tags=["Agentic", "Projects"])
@limiter.limit("100/minute")
async def get_project_agentic_capabilities(
    request: Request,
    project_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access)
):
    """
    Get available agentic capabilities for a specific project.
    
    Returns tools, agents, and features available in the project context.
    
    **Requires:** Project read access
    **Rate Limited:** 100 requests per minute per user
    """
    if not project_access.get("can_read", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this project"
        )
    
    try:
        # Get project-specific capabilities
        capabilities = {
            "agents": [
                {
                    "name": "research_agent",
                    "description": "Research papers and academic content",
                    "capabilities": ["paper_search", "citation_analysis", "research_planning"]
                },
                {
                    "name": "project_agent", 
                    "description": "Project management and collaboration",
                    "capabilities": ["task_management", "member_coordination", "progress_tracking"]
                },
                {
                    "name": "data_agent",
                    "description": "Data analysis and visualization",
                    "capabilities": ["data_processing", "chart_creation", "statistical_analysis"]
                },
                {
                    "name": "latex_editor",
                    "description": "AI-powered LaTeX document editing for research papers",
                    "capabilities": ["content_editing", "formatting_improvement", "grammar_correction", "structure_optimization", "citation_formatting", "image_to_latex"]
                }
            ],
            "tools": [
                "paper_search", "add_paper", "create_task", "update_project",
                "generate_charts", "analyze_data", "search_documents", "latex_editor", "latex_editor_image"
            ],
            "project_context": {
                "project_id": str(project_id),
                "user_role": project_access.get("user_role"),
                "permissions": {
                    "can_read": project_access.get("can_read", False),
                    "can_write": project_access.get("can_write", False),
                    "can_admin": project_access.get("can_admin", False)
                }
            }
        }
        
        return {
            "success": True,
            "capabilities": capabilities,
            "project_id": str(project_id)
        }
        
    except Exception as e:
        logger.error(f"Failed to get project capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project capabilities"
        )


# =====================================================
# PDF CHAT ENDPOINTS (NEW)
# =====================================================

@router.post("/{project_id}/paper_chat", response_model=PaperChatResponse, tags=["Agentic", "PDF Chat"])
@limiter.limit("20/minute")
@handle_service_errors("paper chat")
async def paper_chat(
    request: Request,
    project_id: uuid.UUID,
    chat_request: PaperChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Chat with a paper using its UUID. Reads the PDF content and enables
    AI-powered conversation about the paper using GPT-4o-mini.
    
    Features:
    - Read existing paper PDF content using PyPDF
    - Project-scoped paper access control
    - Conversation history management
    - GPT-4o-mini powered responses
    - MongoDB conversation storage
    
    **Requires:** Project read access
    **Rate Limited:** 20 requests per minute per user
    """
    # Verify read access
    if not project_access.get("can_read", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access papers in this project"
        )
    
    try:
        user_id = str(current_user["user_id"])
        
        # Initialize PDF chat service
        pdf_chat_service = PDFChatService(session)
        await pdf_chat_service.initialize()
        
        # Process paper chat
        result = await pdf_chat_service.chat_with_paper(
            paper_id=chat_request.paper_id,
            project_id=str(project_id),
            user_id=user_id,
            message=chat_request.message,
            conversation_id=chat_request.conversation_id
        )
        
        # Format response
        return PaperChatResponse(
            success=result["success"],
            response=result["response"],
            conversation_id=result["conversation_id"],
            paper_id=result["paper_id"],
            processing_time=result["processing_time"],
            timestamp=result["timestamp"],
            metadata=result["metadata"]
        )
        
    except ServiceError:
        raise
    except Exception as e:
        logger.error(f"Paper chat failed: {e}")
        raise ServiceError(
            "Failed to process paper chat request",
            ErrorCodes.AGENTIC_PROCESSING_ERROR
        )


@router.post("/{project_id}/drop_chat", response_model=DropChatResponse, tags=["Agentic", "PDF Chat"])
@limiter.limit("10/minute")
@handle_service_errors("drop chat")
async def drop_chat(
    request: Request,
    project_id: uuid.UUID,
    file: UploadFile = File(..., description="PDF file to chat with"),
    message: str = Form(..., description="Your message about the PDF"),
    conversation_id: Optional[str] = Form(None, description="Optional conversation ID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Chat with a dropped PDF file within a project context. Reads the uploaded PDF 
    content and enables AI-powered conversation about the document using GPT-4o-mini.
    
    Features:
    - Upload and read PDF content using PyPDF (configurable size limit)
    - Project-scoped for proper access control and organization
    - Conversation history management
    - GPT-4o-mini powered responses
    - MongoDB conversation storage
    
    **Requires:** Project read access
    **Rate Limited:** 10 requests per minute per user
    **File Limit:** Configurable (default 50MB) for research papers
    """
    # Verify read access
    if not project_access.get("can_read", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this project"
        )
    
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )
    
    # Validate file size using configurable limit
    settings = get_settings()
    max_file_size = settings.agentic.max_pdf_upload_size_mb * 1024 * 1024
    
    # Log file information for debugging
    file_size_mb = round(file.size / (1024 * 1024), 2) if file.size else 0
    logger.info(f"Processing PDF upload: {file.filename} ({file_size_mb}MB)")
    
    if file.size and file.size > max_file_size:
        max_size_mb = settings.agentic.max_pdf_upload_size_mb
        logger.warning(f"File size rejected: {file_size_mb}MB > {max_size_mb}MB limit")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({file_size_mb}MB) exceeds the maximum allowed size of {max_size_mb}MB"
        )
    
    try:
        user_id = str(current_user["user_id"])
        
        # Initialize PDF chat service
        pdf_chat_service = PDFChatService(session)
        await pdf_chat_service.initialize()
        
        # Process drop chat
        result = await pdf_chat_service.chat_with_dropped_file(
            file=file,
            project_id=str(project_id),
            user_id=user_id,
            message=message,
            conversation_id=conversation_id
        )
        
        # Format response
        return DropChatResponse(
            success=result["success"],
            response=result["response"],
            conversation_id=result["conversation_id"],
            file_id=result["file_id"],
            processing_time=result["processing_time"],
            timestamp=result["timestamp"],
            metadata=result["metadata"]
        )
        
    except ServiceError:
        raise
    except Exception as e:
        logger.error(f"Drop chat failed: {e}")
        raise ServiceError(
            "Failed to process drop chat request",
            ErrorCodes.AGENTIC_PROCESSING_ERROR
        )


# =====================================================
# SIMPLE CHAT ENDPOINTS (NEW)
# =====================================================

@router.post("/{project_id}/simple_chat", response_model=SimpleChatResponse, tags=["Agentic", "Simple Chat"])
@limiter.limit("20/minute")
@handle_service_errors("simple chat")
async def simple_chat(
    request: Request,
    project_id: uuid.UUID,
    chat_request: SimpleChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Simple GPT conversation holder. Project-scoped AI chat with conversation persistence.
    No complex orchestration - just pure AI chat within project context.
    
    Features:
    - Simple GPT powered responses (configurable model)
    - Project-scoped AI conversations (type=AI)
    - Conversation history management
    - MongoDB message storage
    - Project access control
    
    **Requires:** Project read access
    **Rate Limited:** 20 requests per minute per user
    """
    # Verify read access
    if not project_access.get("can_read", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this project"
        )
    
    try:
        user_id = str(current_user["user_id"])
        
        # Initialize simple AI chat service
        from app.services.simple_ai_chat_service import SimpleAIChatService
        ai_chat_service = SimpleAIChatService(session)
        await ai_chat_service.initialize()
        
        # Process simple AI chat with project context
        result = await ai_chat_service.chat(
            user_id=user_id,
            project_id=str(project_id),
            message=chat_request.message,
            conversation_id=chat_request.conversation_id
        )
        
        # Format response
        return SimpleChatResponse(
            success=result["success"],
            response=result["response"],
            conversation_id=result["conversation_id"],
            processing_time=result["processing_time"],
            timestamp=result["timestamp"],
            metadata=result["metadata"]
        )
        
    except ServiceError:
        raise
    except Exception as e:
        logger.error(f"Simple AI chat failed: {e}")
        raise ServiceError(
            "Failed to process simple AI chat request",
            ErrorCodes.AGENTIC_PROCESSING_ERROR
        )


# =====================================================
# LATEX EDITOR ENDPOINTS (NEW)
# =====================================================

@router.post("/{project_id}/latex_editor", response_model=LaTeXEditorResponse, tags=["Agentic", "LaTeX Editor"])
@limiter.limit("15/minute")
@handle_service_errors("LaTeX editor")
async def latex_editor(
    request: Request,
    project_id: uuid.UUID,
    editor_request: LaTeXEditorRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    AI-powered LaTeX editor using GPT-4o mini for research document editing.
    
    Features:
    - Research-focused LaTeX content editing
    - Multiple edit types: general, formatting, content, structure, citations, grammar
    - Project-scoped with access control
    - Conversation history management
    - Specialized prompts for academic writing
    - MongoDB conversation storage
    
    **Requires:** Project read access
    **Rate Limited:** 15 requests per minute per user
    """
    # Verify read access
    if not project_access.get("can_read", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this project"
        )
    
    try:
        user_id = str(current_user["user_id"])
        
        # Initialize LaTeX editor service
        from app.services.latex_editor_service import LaTeXEditorService
        latex_editor_service = LaTeXEditorService(session)
        await latex_editor_service.initialize()
        
        # Process LaTeX editing request
        result = await latex_editor_service.edit_latex_content(
            prompt=editor_request.prompt,
            project_id=str(project_id),
            user_id=user_id,
            latex_content=editor_request.latex_content,
            edit_type=editor_request.edit_type,
            conversation_id=editor_request.conversation_id
        )
        
        # Format response
        return LaTeXEditorResponse(
            success=result["success"],
            edited_content=result["edited_content"],
            changes_made=result["changes_made"],
            suggestions=result["suggestions"],
            conversation_id=result["conversation_id"],
            processing_time=result["processing_time"],
            timestamp=result["timestamp"],
            metadata=result["metadata"]
        )
        
    except ServiceError:
        raise
    except Exception as e:
        logger.error(f"LaTeX editor failed: {e}")
        raise ServiceError(
            "Failed to process LaTeX editing request",
            ErrorCodes.AGENTIC_PROCESSING_ERROR
        )


@router.post("/{project_id}/latex_editor_image", response_model=LaTeXEditorResponse, tags=["Agentic", "LaTeX Editor"])
@limiter.limit("10/minute")
@handle_service_errors("LaTeX editor with image")
async def latex_editor_with_image(
    request: Request,
    project_id: uuid.UUID,
    image: UploadFile = File(..., description="Image containing LaTeX content to edit"),
    prompt: str = Form(..., description="Research editing instructions"),
    edit_type: str = Form(default="general", description="Type of edit to perform"),
    conversation_id: Optional[str] = Form(None, description="Optional conversation ID"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    project_access: Dict[str, Any] = Depends(verify_project_access),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    AI-powered LaTeX editor with image input using GPT-4o mini vision capabilities.
    
    Features:
    - Extract LaTeX content from images (screenshots, photos of papers, etc.)
    - Research-focused editing with academic writing improvements
    - Support for mathematical equations and academic formatting
    - Project-scoped with access control
    - Conversation history management
    - Multiple edit types for different improvement areas
    
    **Requires:** Project read access
    **Rate Limited:** 10 requests per minute per user
    **File Limit:** Standard image formats (PNG, JPG, JPEG, GIF)
    """
    # Verify read access
    if not project_access.get("can_read", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to access this project"
        )
    
    # Validate image file
    if not image.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image file is required"
        )
    
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif'}
    file_extension = '.' + image.filename.split('.')[-1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Validate file size (10MB limit for images)
    max_file_size = 10 * 1024 * 1024  # 10MB
    if image.size and image.size > max_file_size:
        file_size_mb = round(image.size / (1024 * 1024), 2)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image size ({file_size_mb}MB) exceeds the maximum allowed size of 10MB"
        )
    
    try:
        user_id = str(current_user["user_id"])
        
        # Initialize LaTeX editor service
        from app.services.latex_editor_service import LaTeXEditorService
        latex_editor_service = LaTeXEditorService(session)
        await latex_editor_service.initialize()
        
        # Process LaTeX editing request with image
        result = await latex_editor_service.edit_latex_content(
            prompt=prompt,
            project_id=str(project_id),
            user_id=user_id,
            latex_content=None,  # Will be extracted from image
            image_file=image,
            edit_type=edit_type,
            conversation_id=conversation_id
        )
        
        # Format response
        return LaTeXEditorResponse(
            success=result["success"],
            edited_content=result["edited_content"],
            changes_made=result["changes_made"],
            suggestions=result["suggestions"],
            conversation_id=result["conversation_id"],
            processing_time=result["processing_time"],
            timestamp=result["timestamp"],
            metadata=result["metadata"]
        )
        
    except ServiceError:
        raise
    except Exception as e:
        logger.error(f"LaTeX editor with image failed: {e}")
        raise ServiceError(
            "Failed to process LaTeX editing request with image",
            ErrorCodes.AGENTIC_PROCESSING_ERROR
        )


# =====================================================
# DEPRECATED ENDPOINTS (REMOVED)
# =====================================================

# The following endpoint has been REMOVED to enforce project dependency:
# POST /process - Non-project-dependent processing
# 
# All agentic conversations must now be project-scoped using:
# POST /{project_id}/process
#
# This ensures proper data isolation, access control, and conversation management. 
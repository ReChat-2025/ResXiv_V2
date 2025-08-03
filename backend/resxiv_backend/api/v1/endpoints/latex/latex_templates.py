"""
LaTeX Templates Endpoints - L6 Engineering Standards
Focused on template management, sharing, and customization.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_postgres_session, get_current_user_required
from app.services.git_service import GitService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/latex/templates", response_model=Dict[str, Any])
async def get_latex_templates(
    category: Optional[str] = Query(None, description="Template category filter"),
    search: Optional[str] = Query(None, description="Search templates"),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get available LaTeX templates.
    
    - **category**: Filter by category (article, report, book, beamer, custom)
    - **search**: Search templates by name or description
    
    Returns list of available templates with metadata.
    """
    try:
        # Built-in templates
        builtin_templates = [
            {
                "id": "article",
                "name": "Scientific Article",
                "description": "Standard academic paper template with abstract, sections, and bibliography",
                "category": "article",
                "author": "ResXiv",
                "tags": ["academic", "paper", "research"],
                "preview_url": "/api/v1/latex/templates/article/preview",
                "is_builtin": True,
                "created_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": "report",
                "name": "Technical Report",
                "description": "Comprehensive report template with chapters and table of contents",
                "category": "report",
                "author": "ResXiv",
                "tags": ["report", "technical", "chapters"],
                "preview_url": "/api/v1/latex/templates/report/preview",
                "is_builtin": True,
                "created_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": "book",
                "name": "Academic Book",
                "description": "Full book template with parts, chapters, and appendices",
                "category": "book",
                "author": "ResXiv",
                "tags": ["book", "academic", "comprehensive"],
                "preview_url": "/api/v1/latex/templates/book/preview",
                "is_builtin": True,
                "created_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": "beamer",
                "name": "Presentation Slides",
                "description": "Professional presentation template using Beamer",
                "category": "beamer",
                "author": "ResXiv",
                "tags": ["presentation", "slides", "beamer"],
                "preview_url": "/api/v1/latex/templates/beamer/preview",
                "is_builtin": True,
                "created_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": "ieee",
                "name": "IEEE Conference Paper",
                "description": "IEEE conference paper format with proper styling",
                "category": "article",
                "author": "ResXiv",
                "tags": ["ieee", "conference", "academic"],
                "preview_url": "/api/v1/latex/templates/ieee/preview",
                "is_builtin": True,
                "created_at": "2024-01-01T00:00:00Z"
            },
            {
                "id": "acm",
                "name": "ACM Article",
                "description": "ACM journal/conference article template",
                "category": "article",
                "author": "ResXiv",
                "tags": ["acm", "journal", "academic"],
                "preview_url": "/api/v1/latex/templates/acm/preview",
                "is_builtin": True,
                "created_at": "2024-01-01T00:00:00Z"
            }
        ]
        
        # Get custom templates from database
        git_service = GitService(session)
        custom_result = await git_service.get_custom_latex_templates(
            user_id=current_user["user_id"],
            category=category,
            search=search
        )
        
        custom_templates = custom_result.get("templates", [])
        
        # Combine and filter templates
        all_templates = builtin_templates + custom_templates
        
        # Apply filters
        if category:
            all_templates = [t for t in all_templates if t.get("category") == category]
        
        if search:
            search_lower = search.lower()
            all_templates = [
                t for t in all_templates 
                if search_lower in t.get("name", "").lower() 
                or search_lower in t.get("description", "").lower()
                or any(search_lower in tag.lower() for tag in t.get("tags", []))
            ]
        
        # Group by category
        categories = {}
        for template in all_templates:
            cat = template.get("category", "other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(template)
        
        return {
            "success": True,
            "templates": all_templates,
            "categories": categories,
            "total_count": len(all_templates),
            "builtin_count": len([t for t in all_templates if t.get("is_builtin")]),
            "custom_count": len([t for t in all_templates if not t.get("is_builtin")])
        }
        
    except Exception as e:
        logger.error(f"Error getting LaTeX templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get templates"
        )


@router.get("/latex/templates/{template_id}", response_model=Dict[str, Any])
async def get_latex_template_details(
    template_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get detailed information about a specific template.
    
    Returns template metadata, file structure, and preview information.
    """
    try:
        git_service = GitService(session)
        
        # Check if it's a builtin template
        builtin_templates = {
            "article": {
                "id": "article",
                "name": "Scientific Article",
                "description": "Standard academic paper template with abstract, sections, and bibliography",
                "category": "article",
                "author": "ResXiv",
                "tags": ["academic", "paper", "research"],
                "is_builtin": True,
                "files": ["main.tex", "references.bib"],
                "packages": ["amsmath", "amsfonts", "amssymb", "graphicx", "cite", "hyperref"],
                "structure": {
                    "title": True,
                    "abstract": True,
                    "sections": ["Introduction", "Methods", "Results", "Conclusion"],
                    "bibliography": True
                }
            },
            "report": {
                "id": "report",
                "name": "Technical Report",
                "description": "Comprehensive report template with chapters and table of contents",
                "category": "report",
                "author": "ResXiv",
                "tags": ["report", "technical", "chapters"],
                "is_builtin": True,
                "files": ["main.tex", "references.bib"],
                "packages": ["amsmath", "amsfonts", "amssymb", "graphicx", "cite", "hyperref"],
                "structure": {
                    "title": True,
                    "abstract": True,
                    "tableofcontents": True,
                    "chapters": ["Introduction", "Background", "Analysis", "Conclusion"],
                    "bibliography": True
                }
            },
            # Add other builtin templates...
        }
        
        if template_id in builtin_templates:
            return {
                "success": True,
                "template": builtin_templates[template_id]
            }
        
        # Get custom template details
        result = await git_service.get_latex_template_details(
            template_id=template_id,
            user_id=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "template": result["template"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get template details"
        )


@router.post("/latex/templates", response_model=Dict[str, Any])
async def create_custom_template(
    template_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Create a custom LaTeX template.
    
    - **name**: Template name
    - **description**: Template description
    - **category**: Template category
    - **files**: Template files with content
    - **tags**: Optional tags
    
    Creates a new custom template that can be shared with others.
    """
    try:
        git_service = GitService(session)
        
        # Validate template data
        required_fields = ["name", "description", "category", "files"]
        for field in required_fields:
            if field not in template_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}"
                )
        
        # Validate files
        files = template_data["files"]
        if not files or not isinstance(files, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template must include at least one file"
            )
        
        # Check if main.tex exists
        if "main.tex" not in files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template must include main.tex file"
            )
        
        # Create template
        result = await git_service.create_latex_template(
            template_data=template_data,
            created_by=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "template": result["template"],
            "message": "Custom template created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating custom template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create template"
        )


@router.put("/latex/templates/{template_id}", response_model=Dict[str, Any])
async def update_custom_template(
    template_id: str,
    template_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Update a custom LaTeX template.
    
    Only the template creator can update their custom templates.
    """
    try:
        git_service = GitService(session)
        
        # Update template
        result = await git_service.update_latex_template(
            template_id=template_id,
            template_data=template_data,
            updated_by=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "template": result["template"],
            "message": "Template updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update template"
        )


@router.delete("/latex/templates/{template_id}", response_model=Dict[str, Any])
async def delete_custom_template(
    template_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Delete a custom LaTeX template.
    
    Only the template creator can delete their custom templates.
    """
    try:
        git_service = GitService(session)
        
        # Delete template
        result = await git_service.delete_latex_template(
            template_id=template_id,
            deleted_by=current_user["user_id"]
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        return {
            "success": True,
            "message": "Template deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete template"
        ) 
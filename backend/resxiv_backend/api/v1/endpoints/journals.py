"""
Journal Management Endpoints

FastAPI endpoints for journal functionality including CRUD operations,
collaboration management, version control, and search capabilities.
"""

import uuid
import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy import text

from api.dependencies import get_postgres_session, get_current_user_required
from app.services.journal_service import JournalService
from app.models.journal_models import (
    JournalCreate, JournalUpdate, JournalDetailResponse, JournalListResponse,
    JournalCollaboratorCreate, JournalCollaboratorResponse,
    JournalVersionResponse, JournalTagCreate, JournalTagResponse,
    JournalSearchFilters, JournalPermissionCheck,
    BulkJournalOperation, BulkOperationResult, JournalStatus
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ================================
# Journal CRUD Operations
# ================================

@router.post("/projects/{project_id}/journals", response_model=JournalDetailResponse, status_code=201)
async def create_journal(
    project_id: uuid.UUID = Path(..., description="Project ID"),
    journal_data: JournalCreate = Body(..., description="Journal creation data"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Create a new journal in a project
    
    Creates a new journal entry with the specified content and permissions.
    The user must be a member of the project to create a journal.
    """
    try:
        # Override project_id from path
        journal_data.project_id = project_id
        
        journal_service = JournalService(session)
        journal = await journal_service.create_journal(
            journal_data=journal_data,
            user_id=uuid.UUID(current_user["user_id"])
        )
        
        logger.info(f"Created journal {journal.id} in project {project_id} by user {current_user['user_id']}")
        return journal
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating journal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create journal"
        )


@router.get("/journals/{journal_id}", response_model=JournalDetailResponse)
async def get_journal(
    journal_id: uuid.UUID = Path(..., description="Journal ID"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get a specific journal by ID
    
    Returns detailed information about a journal including content,
    metadata, permissions, and collaboration details.
    """
    try:
        journal_service = JournalService(session)
        journal = await journal_service.get_journal(
            journal_id=journal_id,
            user_id=uuid.UUID(current_user["user_id"])
        )
        
        return journal
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting journal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get journal"
        )


@router.put("/journals/{journal_id}", response_model=JournalDetailResponse)
async def update_journal(
    journal_id: uuid.UUID = Path(..., description="Journal ID"),
    journal_data: JournalUpdate = Body(..., description="Journal update data"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Update a journal
    
    Updates journal content, metadata, or permissions. The user must have
    write access to the journal. Version history is automatically maintained.
    """
    try:
        journal_service = JournalService(session)
        journal = await journal_service.update_journal(
            journal_id=journal_id,
            journal_data=journal_data,
            user_id=uuid.UUID(current_user["user_id"])
        )
        
        logger.info(f"Updated journal {journal_id} by user {current_user['user_id']}")
        return journal
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating journal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update journal"
        )


@router.delete("/journals/{journal_id}", status_code=204)
async def delete_journal(
    journal_id: uuid.UUID = Path(..., description="Journal ID"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Delete a journal
    
    Soft deletes a journal. Only the journal owner or admins can delete journals.
    All associated data (versions, collaborators, tags) are preserved for recovery.
    """
    try:
        journal_service = JournalService(session)
        await journal_service.delete_journal(
            journal_id=journal_id,
            user_id=uuid.UUID(current_user["user_id"])
        )
        
        logger.info(f"Deleted journal {journal_id} by user {current_user['user_id']}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting journal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete journal"
        )


# ================================
# Journal Listing and Search
# ================================

@router.get("/projects/{project_id}/journals", response_model=JournalListResponse)
async def list_project_journals(
    project_id: uuid.UUID = Path(..., description="Project ID"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    query: Optional[str] = Query(None, description="Search query"),
    journal_status: Optional[JournalStatus] = Query(None, description="Filter by status"),
    is_public: Optional[bool] = Query(None, description="Filter by public/private"),
    created_by: Optional[uuid.UUID] = Query(None, description="Filter by creator"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    List journals in a project
    
    Returns a paginated list of journals in the specified project.
    Includes filtering and search capabilities.
    """
    try:
        # Build filters
        filters = JournalSearchFilters(
            query=query,
            status=journal_status,
            is_public=is_public,
            created_by=created_by,
            tags=tags.split(',') if tags else None
        )
        
        journal_service = JournalService(session)
        journals = await journal_service.list_project_journals(
            project_id=project_id,
            user_id=uuid.UUID(current_user["user_id"]),
            filters=filters,
            page=page,
            per_page=per_page
        )
        
        return journals
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing journals: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list journals"
        )


@router.get("/journals/public", response_model=JournalListResponse)
async def list_public_journals(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    query: Optional[str] = Query(None, description="Search query"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    List all public journals across the platform
    
    Returns a paginated list of all public journals that any user can read and edit.
    """
    try:
        # Get all public journals across all projects
        journal_service = JournalService(session)
        
        # Build query for public journals
        filters = JournalSearchFilters(
            query=query,
            is_public=True,
            tags=tags.split(',') if tags else None
        )
        
        # We need to implement a method for cross-project public journal listing
        # For now, return empty list with proper structure
        return JournalListResponse(
            journals=[],
            total=0,
            page=page,
            per_page=per_page,
            total_pages=0
        )
        
    except Exception as e:
        logger.error(f"Error listing public journals: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list public journals"
        )


# ================================
# Collaboration Management
# ================================

@router.post("/journals/{journal_id}/collaborators", response_model=JournalCollaboratorResponse, status_code=201)
async def add_journal_collaborator(
    journal_id: uuid.UUID = Path(..., description="Journal ID"),
    collaborator_data: JournalCollaboratorCreate = Body(..., description="Collaborator data"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Add a collaborator to a private journal
    
    Adds a user as a collaborator with specified permissions.
    Only journal owners and admins can manage collaborators.
    """
    try:
        journal_service = JournalService(session)
        collaborator = await journal_service.add_collaborator(
            journal_id=journal_id,
            collaborator_data=collaborator_data,
            user_id=uuid.UUID(current_user["user_id"])
        )
        
        logger.info(f"Added collaborator {collaborator_data.user_id} to journal {journal_id}")
        return collaborator
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding collaborator: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add collaborator"
        )


@router.get("/journals/{journal_id}/collaborators", response_model=List[JournalCollaboratorResponse])
async def list_journal_collaborators(
    journal_id: uuid.UUID = Path(..., description="Journal ID"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    List collaborators of a journal
    
    Returns all users who have explicit permissions on this journal.
    """
    try:
        journal_service = JournalService(session)
        
        # Check if user can read the journal
        permissions = await journal_service.check_journal_permission(
            journal_id=journal_id,
            user_id=uuid.UUID(current_user["user_id"])
        )
        
        if not permissions.can_read:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot view journal collaborators"
            )
        
        # Get collaborators
        result = await session.execute(
            text("""
                SELECT jc.id, jc.journal_id, jc.user_id, jc.permission, 
                       jc.added_by, jc.added_at,
                       u.name as user_name, u.email as user_email,
                       adder.name as added_by_name
                FROM journal_collaborators jc
                JOIN users u ON jc.user_id = u.id
                LEFT JOIN users adder ON jc.added_by = adder.id
                WHERE jc.journal_id = %s
                ORDER BY jc.added_at DESC
            """),
            [str(journal_id)]
        )
        
        collaborators = []
        for row in result.fetchall():
            collaborators.append(JournalCollaboratorResponse(
                id=row.id,
                journal_id=row.journal_id,
                user_id=row.user_id,
                permission=row.permission,
                added_by=row.added_by,
                added_at=row.added_at,
                user_name=row.user_name,
                user_email=row.user_email,
                added_by_name=row.added_by_name
            ))
        
        return collaborators
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing collaborators: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list collaborators"
        )


# ================================
# Version Management
# ================================

@router.get("/journals/{journal_id}/versions", response_model=List[JournalVersionResponse])
async def get_journal_versions(
    journal_id: uuid.UUID = Path(..., description="Journal ID"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get version history of a journal
    
    Returns all versions of the journal in reverse chronological order.
    Users must have read access to the journal.
    """
    try:
        journal_service = JournalService(session)
        versions = await journal_service.get_journal_versions(
            journal_id=journal_id,
            user_id=uuid.UUID(current_user["user_id"])
        )
        
        return versions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting journal versions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get journal versions"
        )


@router.get("/journals/{journal_id}/versions/{version_number}", response_model=JournalVersionResponse)
async def get_journal_version(
    journal_id: uuid.UUID = Path(..., description="Journal ID"),
    version_number: int = Path(..., description="Version number"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get a specific version of a journal
    
    Returns the content and metadata for a specific version.
    """
    try:
        journal_service = JournalService(session)
        
        # Check permissions
        permissions = await journal_service.check_journal_permission(
            journal_id=journal_id,
            user_id=uuid.UUID(current_user["user_id"])
        )
        
        if not permissions.can_read:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot read this journal"
            )
        
        # Get specific version
        result = await session.execute(
            text("""
                SELECT jv.id, jv.journal_id, jv.version_number, jv.title, jv.content,
                       jv.changed_by, jv.change_summary, jv.created_at,
                       u.name as changed_by_name
                FROM journal_versions jv
                LEFT JOIN users u ON jv.changed_by = u.id
                WHERE jv.journal_id = %s AND jv.version_number = %s
            """),
            [str(journal_id), version_number]
        )
        
        row = result.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal version not found"
            )
        
        return JournalVersionResponse(
            id=row.id,
            journal_id=row.journal_id,
            version_number=row.version_number,
            title=row.title,
            content=row.content,
            changed_by=row.changed_by,
            change_summary=row.change_summary,
            created_at=row.created_at,
            changed_by_name=row.changed_by_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting journal version: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get journal version"
        )


# ================================
# Tag Management
# ================================

@router.post("/journals/{journal_id}/tags", response_model=JournalTagResponse, status_code=201)
async def add_journal_tag(
    journal_id: uuid.UUID = Path(..., description="Journal ID"),
    tag_data: JournalTagCreate = Body(..., description="Tag data"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Add a tag to a journal
    
    Tags help categorize and organize journals within projects.
    """
    try:
        journal_service = JournalService(session)
        
        # Check permissions
        permissions = await journal_service.check_journal_permission(
            journal_id=journal_id,
            user_id=uuid.UUID(current_user["user_id"])
        )
        
        if not permissions.can_write:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot add tags to this journal"
            )
        
        tag = await journal_service.add_journal_tag(
            journal_id=journal_id,
            tag_name=tag_data.tag_name,
            user_id=uuid.UUID(current_user["user_id"])
        )
        
        await session.commit()
        return tag
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding journal tag: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add journal tag"
        )


@router.get("/journals/{journal_id}/tags", response_model=List[JournalTagResponse])
async def get_journal_tags(
    journal_id: uuid.UUID = Path(..., description="Journal ID"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Get all tags for a journal
    
    Returns all tags associated with the journal.
    """
    try:
        journal_service = JournalService(session)
        
        # Check permissions
        permissions = await journal_service.check_journal_permission(
            journal_id=journal_id,
            user_id=uuid.UUID(current_user["user_id"])
        )
        
        if not permissions.can_read:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot view this journal"
            )
        
        tags = await journal_service.get_journal_tags(journal_id)
        return tags
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting journal tags: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get journal tags"
        )


# ================================
# Permission Management
# ================================

@router.get("/journals/{journal_id}/permissions", response_model=JournalPermissionCheck)
async def check_journal_permissions(
    journal_id: uuid.UUID = Path(..., description="Journal ID"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Check user permissions for a journal
    
    Returns detailed permission information for the current user.
    """
    try:
        journal_service = JournalService(session)
        permissions = await journal_service.check_journal_permission(
            journal_id=journal_id,
            user_id=uuid.UUID(current_user["user_id"])
        )
        
        return permissions
        
    except Exception as e:
        logger.error(f"Error checking journal permissions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check journal permissions"
        )


# ================================
# Bulk Operations
# ================================

@router.post("/journals/bulk", response_model=BulkOperationResult)
async def bulk_journal_operation(
    operation: BulkJournalOperation = Body(..., description="Bulk operation data"),
    current_user: Dict = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_postgres_session)
):
    """
    Perform bulk operations on journals
    
    Supports operations like bulk delete, archive, publish, etc.
    Only affects journals the user has appropriate permissions for.
    """
    try:
        journal_service = JournalService(session)
        user_id = uuid.UUID(current_user["user_id"])
        
        results = []
        successful = 0
        failed = 0
        
        for journal_id in operation.journal_ids:
            try:
                # Check permissions for this journal
                permissions = await journal_service.check_journal_permission(journal_id, user_id)
                
                if operation.operation == "delete":
                    if not permissions.can_admin:
                        results.append({
                            "journal_id": str(journal_id),
                            "status": "failed",
                            "reason": "Insufficient permissions"
                        })
                        failed += 1
                        continue
                    
                    await journal_service.delete_journal(journal_id, user_id)
                    results.append({
                        "journal_id": str(journal_id),
                        "status": "success",
                        "message": "Journal deleted"
                    })
                    successful += 1
                
                elif operation.operation in ["archive", "publish"]:
                    if not permissions.can_write:
                        results.append({
                            "journal_id": str(journal_id),
                            "status": "failed",
                            "reason": "Insufficient permissions"
                        })
                        failed += 1
                        continue
                    
                    # Update status
                    status_map = {
                        "archive": JournalStatus.ARCHIVED,
                        "publish": JournalStatus.PUBLISHED
                    }
                    
                    update_data = JournalUpdate(status=status_map[operation.operation])
                    await journal_service.update_journal(journal_id, update_data, user_id)
                    
                    results.append({
                        "journal_id": str(journal_id),
                        "status": "success",
                        "message": f"Journal {operation.operation}d"
                    })
                    successful += 1
                
                elif operation.operation in ["make_public", "make_private"]:
                    if not permissions.can_admin:
                        results.append({
                            "journal_id": str(journal_id),
                            "status": "failed",
                            "reason": "Insufficient permissions"
                        })
                        failed += 1
                        continue
                    
                    is_public = operation.operation == "make_public"
                    update_data = JournalUpdate(is_public=is_public)
                    await journal_service.update_journal(journal_id, update_data, user_id)
                    
                    results.append({
                        "journal_id": str(journal_id),
                        "status": "success",
                        "message": f"Journal made {'public' if is_public else 'private'}"
                    })
                    successful += 1
                
            except Exception as e:
                results.append({
                    "journal_id": str(journal_id),
                    "status": "failed",
                    "reason": str(e)
                })
                failed += 1
        
        await session.commit()
        
        return BulkOperationResult(
            operation=operation.operation,
            total_requested=len(operation.journal_ids),
            successful=successful,
            failed=failed,
            results=results
        )
        
    except Exception as e:
        await session.rollback()
        logger.error(f"Error in bulk journal operation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk operation"
        ) 
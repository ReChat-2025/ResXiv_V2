"""
Paper CRUD Service - L6 Engineering Standards
Focused on basic CRUD operations and database management.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.repositories.paper_repository import PaperRepository
from app.models.paper import PaperCreate, PaperUpdate, PaperResponse

logger = logging.getLogger(__name__)


class PaperCrudService:
    """
    CRUD service for paper database operations.
    Single Responsibility: Basic CRUD operations and data management.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = PaperRepository(session)
    
    @handle_service_errors("create paper")
    async def create_paper(
        self,
        project_id: uuid.UUID,
        paper_data: PaperCreate,
        created_by: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Create a new paper record.
        
        Args:
            project_id: Project UUID
            paper_data: Paper creation data
            created_by: User creating the paper
            
        Returns:
            Created paper data
        """
        try:
            # Persist paper
            paper = await self.repository.create_paper(paper_data)

            # Link to project (many-to-many)
            await self.repository.add_paper_to_project(project_id, paper.id)

            await self.session.commit()

            return {
                "success": True,
                "paper": PaperResponse.from_orm(paper),
                "message": "Paper created successfully"
            }

        except Exception as e:
            await self.session.rollback()
            raise ServiceError(
                f"Failed to create paper: {str(e)}",
                ErrorCodes.CREATION_ERROR
            )
    
    @handle_service_errors("get paper")
    async def get_paper(
        self,
        paper_id: str,
        user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Get paper by ID.
        
        Args:
            paper_id: Paper UUID
            user_id: Optional user ID for access control
            
        Returns:
            Paper data
        """
        paper = await self.repository.get_paper_by_id(paper_id)
        if not paper:
            raise ServiceError(
                "Paper not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        return {
            "success": True,
            "paper": PaperResponse.from_orm(paper)
        }
    
    @handle_service_errors("update paper")
    async def update_paper(
        self,
        paper_id: str,
        paper_data: PaperUpdate,
        updated_by: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Update paper information.
        
        Args:
            paper_id: Paper UUID
            paper_data: Paper update data
            updated_by: User performing the update
            
        Returns:
            Updated paper data
        """
        try:
            # Check if paper exists
            existing_paper = await self.repository.get_paper_by_id(paper_id)
            if not existing_paper:
                raise ServiceError(
                    "Paper not found",
                    ErrorCodes.NOT_FOUND_ERROR
                )
            
            # Update paper
            updated_paper = await self.repository.update_paper(
                paper_id,
                paper_data.dict(exclude_none=True)
            )
            
            await self.session.commit()
            
            return {
                "success": True,
                "paper": PaperResponse.from_orm(updated_paper),
                "message": "Paper updated successfully"
            }
            
        except Exception as e:
            await self.session.rollback()
            raise ServiceError(
                f"Failed to update paper: {str(e)}",
                ErrorCodes.UPDATE_ERROR
            )
    
    @handle_service_errors("delete paper")
    async def delete_paper(
        self,
        paper_id: str,
        deleted_by: uuid.UUID,
        soft_delete: bool = True
    ) -> Dict[str, Any]:
        """
        Delete a paper.
        
        Args:
            paper_id: Paper UUID
            deleted_by: User performing the deletion
            soft_delete: Whether to soft delete (default) or hard delete
            
        Returns:
            Deletion result
        """
        try:
            # Check if paper exists
            paper = await self.repository.get_paper_by_id(paper_id)
            if not paper:
                raise ServiceError(
                    "Paper not found",
                    ErrorCodes.NOT_FOUND_ERROR
                )
            
            if soft_delete:
                # Soft delete
                await self.repository.soft_delete_paper(paper_id)
            else:
                # Hard delete
                await self.repository.hard_delete_paper(paper_id)
            
            await self.session.commit()
            
            return {
                "success": True,
                "message": f"Paper {'soft' if soft_delete else 'hard'} deleted successfully"
            }
            
        except Exception as e:
            await self.session.rollback()
            raise ServiceError(
                f"Failed to delete paper: {str(e)}",
                ErrorCodes.DELETION_ERROR
            )
    
    @handle_service_errors("list project papers")
    async def list_project_papers(
        self,
        project_id: uuid.UUID,
        page: int = 1,
        limit: int = 50,
        include_deleted: bool = False
    ) -> Dict[str, Any]:
        """
        List papers in a project.
        
        Args:
            project_id: Project UUID
            page: Page number (1-based)
            limit: Papers per page
            include_deleted: Whether to include soft-deleted papers
            
        Returns:
            Paginated list of papers
        """
        offset = (page - 1) * limit
        
        papers, total_count = await self.repository.get_papers_by_project(
            project_id,
            page=page,
            size=limit,
            include_diagnostics=True,
        )
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "success": True,
            "papers": [PaperResponse.from_orm(paper) for paper in papers],
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_papers": total_count,
                "papers_per_page": limit,
                "has_next": has_next,
                "has_prev": has_prev
            }
        }
    
    @handle_service_errors("search papers")
    async def search_papers(
        self,
        query: str,
        project_id: Optional[uuid.UUID] = None,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search papers by text query.
        
        Args:
            query: Search query
            project_id: Optional project filter
            filters: Additional search filters
            page: Page number
            limit: Results per page
            
        Returns:
            Search results
        """
        if not query or not query.strip():
            raise ServiceError(
                "Search query is required",
                ErrorCodes.VALIDATION_ERROR
            )
        
        offset = (page - 1) * limit
        
        papers, total_count = await self.repository.search_papers(
            query=query,
            project_id=project_id,
            filters=filters or {},
            limit=limit,
            offset=offset
        )
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "success": True,
            "query": query,
            "papers": [PaperResponse.from_orm(paper) for paper in papers],
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_results": total_count,
                "results_per_page": limit,
                "has_next": has_next,
                "has_prev": has_prev
            },
            "search_timestamp": datetime.utcnow().isoformat()
        }
    
    @handle_service_errors("get paper statistics")
    async def get_paper_statistics(
        self,
        project_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Get paper statistics.
        
        Args:
            project_id: Optional project filter
            
        Returns:
            Paper statistics
        """
        stats = await self.repository.get_paper_statistics(project_id)
        
        return {
            "success": True,
            "statistics": stats,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    @handle_service_errors("bulk update papers")
    async def bulk_update_papers(
        self,
        paper_ids: List[str],
        update_data: Dict[str, Any],
        updated_by: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Bulk update multiple papers.
        
        Args:
            paper_ids: List of paper UUIDs
            update_data: Update data to apply
            updated_by: User performing the update
            
        Returns:
            Bulk update results
        """
        if not paper_ids:
            raise ServiceError(
                "Paper IDs list is required",
                ErrorCodes.VALIDATION_ERROR
            )
        
        try:
            updated_count = await self.repository.bulk_update_papers(
                paper_ids=paper_ids,
                update_data=update_data,
                updated_by=updated_by
            )
            
            await self.session.commit()
            
            return {
                "success": True,
                "updated_count": updated_count,
                "total_papers": len(paper_ids),
                "message": f"Successfully updated {updated_count} papers"
            }
            
        except Exception as e:
            await self.session.rollback()
            raise ServiceError(
                f"Bulk update failed: {str(e)}",
                ErrorCodes.UPDATE_ERROR
            )
    
    @handle_service_errors("restore paper")
    async def restore_paper(
        self,
        paper_id: str,
        restored_by: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Restore a soft-deleted paper.
        
        Args:
            paper_id: Paper UUID
            restored_by: User performing the restoration
            
        Returns:
            Restoration result
        """
        try:
            # Check if paper exists and is deleted
            paper = await self.repository.get_paper_by_id(paper_id, include_deleted=True)
            if not paper:
                raise ServiceError(
                    "Paper not found",
                    ErrorCodes.NOT_FOUND_ERROR
                )
            
            if not paper.deleted_at:
                return {
                    "success": True,
                    "message": "Paper is not deleted"
                }
            
            # Restore paper
            restored_paper = await self.repository.restore_paper(paper_id, restored_by)
            
            await self.session.commit()
            
            return {
                "success": True,
                "paper": PaperResponse.from_orm(restored_paper),
                "message": "Paper restored successfully"
            }
            
        except Exception as e:
            await self.session.rollback()
            raise ServiceError(
                f"Failed to restore paper: {str(e)}",
                ErrorCodes.UPDATE_ERROR
            )
    
    @handle_service_errors("get paper metadata")
    async def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """
        Get paper metadata and processing status.
        
        Args:
            paper_id: Paper UUID
            
        Returns:
            Paper metadata and status
        """
        paper = await self.repository.get_paper_by_id(paper_id)
        if not paper:
            raise ServiceError(
                "Paper not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        metadata = {
            "basic_info": {
                "id": str(paper.id),
                "title": paper.title,
                "abstract": paper.abstract,
                "authors": paper.authors,
                "keywords": paper.keywords,
                "created_at": paper.created_at.isoformat() if paper.created_at else None,
                "updated_at": paper.updated_at.isoformat() if paper.updated_at else None
            },
            "file_info": {
                "has_file": bool(paper.file_path),
                "file_path": paper.file_path,
                "file_size": paper.file_size,
                "checksum": paper.checksum
            },
            "processing_status": {
                "has_content": bool(paper.content),
                "has_embedding": bool(paper.embedding),
                "embedding_dimension": len(paper.embedding) if paper.embedding else 0,
                "processed": bool(paper.content or paper.embedding)
            },
            "project_info": {
                "project_id": str(paper.project_id),
                "created_by": str(paper.created_by) if paper.created_by else None
            }
        }
        
        return {
            "success": True,
            "metadata": metadata
        } 
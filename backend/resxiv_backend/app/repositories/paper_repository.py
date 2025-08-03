"""
Paper Repository

Data access layer for paper-related database operations.
Handles CRUD operations for papers, diagnostics, and related entities.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, update, delete, and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging

from app.schemas.paper import Paper, Diagnostic, ProjectPaper, Highlight, Note
from app.models.paper import PaperCreate, DiagnosticCreate

logger = logging.getLogger(__name__)


class PaperRepository:
    """Repository for paper-related database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ================================
    # PAPER CRUD OPERATIONS
    # ================================
    
    async def create_paper(self, paper_data: PaperCreate) -> Paper:
        """
        Create a new paper in the database
        
        Args:
            paper_data: Paper creation data
            
        Returns:
            Created paper object
        """
        try:
            paper = Paper(**paper_data.dict())
            self.session.add(paper)
            await self.session.flush()
            await self.session.refresh(paper)

            # Re-select with diagnostics relationship eagerly loaded so
            # Pydantic serialization later doesn’t trigger lazy-load IO.
            result = await self.session.execute(
                select(Paper).options(selectinload(Paper.diagnostics)).where(Paper.id == paper.id)
            )
            paper_full = result.scalar_one()

            return paper_full
        except Exception as e:
            logger.error(f"Error creating paper: {str(e)}")
            await self.session.rollback()
            raise
    
    async def get_paper_by_id(self, paper_id: uuid.UUID, include_diagnostics: bool = True) -> Optional[Paper]:
        """
        Get paper by ID with optional diagnostics
        
        Args:
            paper_id: Paper UUID
            include_diagnostics: Whether to include diagnostics data
            
        Returns:
            Paper object if found, None otherwise
        """
        try:
            query = select(Paper).where(
                and_(
                    Paper.id == paper_id,
                    Paper.deleted_at.is_(None)
                )
            )
            
            if include_diagnostics:
                query = query.options(selectinload(Paper.diagnostics))
            
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting paper by ID {paper_id}: {str(e)}")
            raise
    
    async def get_paper_by_safe_title(self, safe_title: str) -> Optional[Paper]:
        """
        Get paper by safe title to check for duplicates
        
        Args:
            safe_title: Safe title used for file storage
            
        Returns:
            Paper object if found, None otherwise
        """
        try:
            stmt = select(Paper).where(
                and_(
                    Paper.safe_title == safe_title,
                    Paper.deleted_at.is_(None)
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting paper by safe title {safe_title}: {str(e)}")
            raise
    
    async def get_papers_by_project(
        self,
        project_id: uuid.UUID,
        page: int = 1,
        size: int = 20,
        include_diagnostics: bool = True,
        search_query: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Paper], int]:
        """
        Get papers for a specific project with pagination and search
        
        Args:
            project_id: Project UUID
            page: Page number (1-based)
            size: Page size
            include_diagnostics: Whether to include diagnostics
            search_query: Optional search query for title/authors
            sort_by: Sort field
            sort_order: Sort order (asc/desc)
            
        Returns:
            Tuple of (papers list, total count)
        """
        try:
            # Build base query
            query = select(Paper).join(ProjectPaper).where(
                and_(
                    ProjectPaper.project_id == project_id,
                    Paper.deleted_at.is_(None)
                )
            )
            
            # Add search filter
            if search_query:
                search_filter = or_(
                    Paper.title.ilike(f"%{search_query}%"),
                    Paper.abstract.ilike(f"%{search_query}%"),
                    func.array_to_string(Paper.authors, ' ').ilike(f"%{search_query}%"),
                    func.array_to_string(Paper.keywords, ' ').ilike(f"%{search_query}%")
                )
                query = query.where(search_filter)
            
            # Add sorting
            sort_column = getattr(Paper, sort_by, Paper.created_at)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await self.session.execute(count_query)
            total = total_result.scalar()
            
            # Add pagination
            offset = (page - 1) * size
            query = query.offset(offset).limit(size)
            
            # Include diagnostics if requested
            if include_diagnostics:
                query = query.options(selectinload(Paper.diagnostics))
            
            result = await self.session.execute(query)
            papers = result.scalars().all()
            
            return list(papers), total
            
        except Exception as e:
            logger.error(f"Error getting papers for project {project_id}: {str(e)}")
            raise
    
    async def update_paper(self, paper_id: uuid.UUID, update_data: Dict[str, Any]) -> Optional[Paper]:
        """
        Update paper information
        
        Args:
            paper_id: Paper UUID
            update_data: Data to update
            
        Returns:
            Updated paper object if found, None otherwise
        """
        try:
            # Add updated_at timestamp
            update_data['updated_at'] = datetime.utcnow()
            
            stmt = (
                update(Paper)
                .where(
                    and_(
                        Paper.id == paper_id,
                        Paper.deleted_at.is_(None)
                    )
                )
                .values(**update_data)
                .returning(Paper)
            )
            
            result = await self.session.execute(stmt)
            updated_paper = result.scalar_one_or_none()
            
            if updated_paper:
                await self.session.refresh(updated_paper)
            
            return updated_paper
            
        except Exception as e:
            logger.error(f"Error updating paper {paper_id}: {str(e)}")
            await self.session.rollback()
            raise
    
    async def soft_delete_paper(self, paper_id: uuid.UUID) -> bool:
        """
        Soft delete a paper by setting deleted_at timestamp
        
        Args:
            paper_id: Paper UUID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            stmt = (
                update(Paper)
                .where(
                    and_(
                        Paper.id == paper_id,
                        Paper.deleted_at.is_(None)
                    )
                )
                .values(deleted_at=datetime.utcnow())
            )
            
            result = await self.session.execute(stmt)
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error soft deleting paper {paper_id}: {str(e)}")
            await self.session.rollback()
            raise
    
    async def hard_delete_paper(self, paper_id: uuid.UUID) -> bool:
        """
        Hard delete a paper from database
        
        Args:
            paper_id: Paper UUID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            stmt = delete(Paper).where(Paper.id == paper_id)
            result = await self.session.execute(stmt)
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error hard deleting paper {paper_id}: {str(e)}")
            await self.session.rollback()
            raise
    
    # ================================
    # PROJECT-PAPER OPERATIONS
    # ================================
    
    async def add_paper_to_project(self, project_id: uuid.UUID, paper_id: uuid.UUID) -> ProjectPaper:
        """
        Add paper to project (many-to-many relationship)
        
        Args:
            project_id: Project UUID
            paper_id: Paper UUID
            
        Returns:
            Created ProjectPaper relationship
        """
        try:
            project_paper = ProjectPaper(
                project_id=project_id,
                paper_id=paper_id,
                uploaded=True
            )
            
            self.session.add(project_paper)
            await self.session.flush()
            await self.session.refresh(project_paper)
            return project_paper
            
        except Exception as e:
            logger.error(f"Error adding paper {paper_id} to project {project_id}: {str(e)}")
            await self.session.rollback()
            raise
    
    async def remove_paper_from_project(self, project_id: uuid.UUID, paper_id: uuid.UUID) -> bool:
        """
        Remove paper from project
        
        Args:
            project_id: Project UUID
            paper_id: Paper UUID
            
        Returns:
            True if removed, False if not found
        """
        try:
            stmt = delete(ProjectPaper).where(
                and_(
                    ProjectPaper.project_id == project_id,
                    ProjectPaper.paper_id == paper_id
                )
            )
            
            result = await self.session.execute(stmt)
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error removing paper {paper_id} from project {project_id}: {str(e)}")
            await self.session.rollback()
            raise
    
    async def is_paper_in_project(self, project_id: uuid.UUID, paper_id: uuid.UUID) -> bool:
        """
        Check if paper belongs to project
        
        Args:
            project_id: Project UUID
            paper_id: Paper UUID
            
        Returns:
            True if paper is in project, False otherwise
        """
        try:
            stmt = select(ProjectPaper).where(
                and_(
                    ProjectPaper.project_id == project_id,
                    ProjectPaper.paper_id == paper_id
                )
            )
            
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none() is not None
            
        except Exception as e:
            logger.error(f"Error checking paper {paper_id} in project {project_id}: {str(e)}")
            raise
    
    async def get_papers_by_file_hash_and_project(
        self, 
        file_hash: str, 
        project_id: uuid.UUID
    ) -> List[Paper]:
        """
        Find papers by file hash within a specific project
        
        Args:
            file_hash: MD5 hash of the file content
            project_id: Project UUID to search within
            
        Returns:
            List of matching papers
        """
        try:
            stmt = (
                select(Paper)
                .join(ProjectPaper)
                .where(
                    and_(
                        Paper.checksum == file_hash,
                        ProjectPaper.project_id == project_id,
                        Paper.deleted_at.is_(None)
                    )
                )
                .options(selectinload(Paper.diagnostics))
            )
            
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error finding papers by hash {file_hash} in project {project_id}: {str(e)}")
            raise
    
    # ================================
    # DIAGNOSTIC OPERATIONS
    # ================================
    
    async def create_diagnostic(self, diagnostic_data: DiagnosticCreate) -> Diagnostic:
        """
        Create diagnostic for a paper
        
        Args:
            diagnostic_data: Diagnostic creation data
            
        Returns:
            Created diagnostic object
        """
        try:
            diagnostic = Diagnostic(**diagnostic_data.dict())
            self.session.add(diagnostic)
            await self.session.flush()
            await self.session.refresh(diagnostic)
            return diagnostic
            
        except Exception as e:
            logger.error(f"Error creating diagnostic: {str(e)}")
            await self.session.rollback()
            raise
    
    async def get_diagnostic_by_paper_id(self, paper_id: uuid.UUID) -> Optional[Diagnostic]:
        """
        Get diagnostic by paper ID
        
        Args:
            paper_id: Paper UUID
            
        Returns:
            Diagnostic object if found, None otherwise
        """
        try:
            stmt = select(Diagnostic).where(Diagnostic.paper_id == paper_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting diagnostic for paper {paper_id}: {str(e)}")
            raise
    
    async def update_diagnostic(self, paper_id: uuid.UUID, update_data: Dict[str, Any]) -> Optional[Diagnostic]:
        """
        Update diagnostic information
        
        Args:
            paper_id: Paper UUID
            update_data: Data to update
            
        Returns:
            Updated diagnostic object if found, None otherwise
        """
        try:
            # Add updated_at timestamp
            update_data['updated_at'] = datetime.utcnow()
            
            stmt = (
                update(Diagnostic)
                .where(Diagnostic.paper_id == paper_id)
                .values(**update_data)
                .returning(Diagnostic)
            )
            
            result = await self.session.execute(stmt)
            updated_diagnostic = result.scalar_one_or_none()
            
            if updated_diagnostic:
                await self.session.refresh(updated_diagnostic)
            
            return updated_diagnostic
            
        except Exception as e:
            logger.error(f"Error updating diagnostic for paper {paper_id}: {str(e)}")
            await self.session.rollback()
            raise
    
    async def delete_diagnostic(self, paper_id: uuid.UUID) -> bool:
        """
        Delete diagnostic for a paper
        
        Args:
            paper_id: Paper UUID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            stmt = delete(Diagnostic).where(Diagnostic.paper_id == paper_id)
            result = await self.session.execute(stmt)
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error deleting diagnostic for paper {paper_id}: {str(e)}")
            await self.session.rollback()
            raise
    
    # ================================
    # SEARCH AND FILTER OPERATIONS
    # ================================
    
    async def search_papers(
        self,
        search_query: str,
        project_ids: Optional[List[uuid.UUID]] = None,
        authors: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        has_diagnostics: Optional[bool] = None,
        page: int = 1,
        size: int = 20
    ) -> Tuple[List[Paper], int]:
        """
        Advanced search for papers with multiple filters
        
        Args:
            search_query: Text search query
            project_ids: Filter by project IDs
            authors: Filter by authors
            keywords: Filter by keywords
            date_from: Filter by date range start
            date_to: Filter by date range end
            has_diagnostics: Filter papers with/without diagnostics
            page: Page number
            size: Page size
            
        Returns:
            Tuple of (papers list, total count)
        """
        try:
            # Build base query
            query = select(Paper).where(Paper.deleted_at.is_(None))
            
            # Add text search
            if search_query:
                search_filter = or_(
                    Paper.title.ilike(f"%{search_query}%"),
                    Paper.abstract.ilike(f"%{search_query}%"),
                    func.array_to_string(Paper.authors, ' ').ilike(f"%{search_query}%")
                )
                query = query.where(search_filter)
            
            # Add project filter
            if project_ids:
                query = query.join(ProjectPaper).where(
                    ProjectPaper.project_id.in_(project_ids)
                )
            
            # Add author filter
            if authors:
                author_filters = [
                    func.array_to_string(Paper.authors, ' ').ilike(f"%{author}%")
                    for author in authors
                ]
                query = query.where(or_(*author_filters))
            
            # Add keyword filter
            if keywords:
                keyword_filters = [
                    Paper.keywords.contains([keyword])
                    for keyword in keywords
                ]
                query = query.where(or_(*keyword_filters))
            
            # Add date range filter
            if date_from:
                query = query.where(Paper.created_at >= date_from)
            if date_to:
                query = query.where(Paper.created_at <= date_to)
            
            # Add diagnostics filter
            if has_diagnostics is not None:
                if has_diagnostics:
                    query = query.join(Diagnostic)
                else:
                    query = query.outerjoin(Diagnostic).where(Diagnostic.id.is_(None))
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await self.session.execute(count_query)
            total = total_result.scalar()
            
            # Add pagination and sorting
            offset = (page - 1) * size
            query = query.order_by(desc(Paper.created_at)).offset(offset).limit(size)
            
            # Include diagnostics
            query = query.options(selectinload(Paper.diagnostics))
            
            result = await self.session.execute(query)
            papers = result.scalars().all()
            
            return list(papers), total
            
        except Exception as e:
            logger.error(f"Error searching papers: {str(e)}")
            raise
    
    # ================================
    # UTILITY OPERATIONS
    # ================================
    
    async def get_papers_count_by_project(self, project_id: uuid.UUID) -> int:
        """
        Get count of papers in a project
        
        Args:
            project_id: Project UUID
            
        Returns:
            Number of papers in project
        """
        try:
            stmt = select(func.count(Paper.id)).join(ProjectPaper).where(
                and_(
                    ProjectPaper.project_id == project_id,
                    Paper.deleted_at.is_(None)
                )
            )
            
            result = await self.session.execute(stmt)
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Error getting papers count for project {project_id}: {str(e)}")
            raise
    
    async def get_papers_without_diagnostics(self, limit: int = 100) -> List[Paper]:
        """
        Get papers that don't have diagnostics yet
        
        Args:
            limit: Maximum number of papers to return
            
        Returns:
            List of papers without diagnostics
        """
        try:
            stmt = (
                select(Paper)
                .outerjoin(Diagnostic)
                .where(
                    and_(
                        Paper.deleted_at.is_(None),
                        Diagnostic.id.is_(None)
                    )
                )
                .order_by(Paper.created_at)
                .limit(limit)
            )
            
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting papers without diagnostics: {str(e)}")
            raise 
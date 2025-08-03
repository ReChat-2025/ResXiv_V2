"""
Paper Service Integrated - L6 Engineering Standards
Orchestrates specialized paper sub-services with clean separation of concerns.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.models.paper import (
    PaperCreate, PaperUpdate, PaperResponse,
    ArXivSearchRequest, ArXivDownloadRequest,
    ProcessingRequest, DiagnosticRequest, BulkPaperOperation
)

from .paper_storage_service import PaperStorageService
from .paper_processing_service import PaperProcessingService
from .paper_embedding_service import PaperEmbeddingService
from .paper_crud_service import PaperCrudService

logger = logging.getLogger(__name__)


class PaperService:
    """
    Integrated paper service orchestrating specialized sub-services.
    
    Follows Composition over Inheritance principle with clean separation:
    - Storage service: File upload, storage, and validation
    - Processing service: GROBID processing and metadata extraction
    - Embedding service: AI embeddings and semantic search
    - CRUD service: Basic database operations
    
    Single point of access for all paper operations while maintaining
    focused, testable components.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
        # Initialize specialized services
        self.storage_service = PaperStorageService(session)
        self.processing_service = PaperProcessingService(session)
        self.embedding_service = PaperEmbeddingService(session)
        self.crud_service = PaperCrudService(session)

    # ================================
    # ARXIV INTEGRATION
    # ================================

    async def download_arxiv_paper(
        self,
        arxiv_id: str,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        process_with_grobid: bool = True,
        run_diagnostics: bool = True
    ) -> Dict[str, Any]:
        """Download an ArXiv paper PDF, create a Paper record, and (optionally) process it.

        This mirrors the logic used by the /arxiv/download endpoint so it can be
        invoked programmatically by the agentic layer.
        """
        from app.services.arxiv_service import ArXivService  # local import to avoid cycles
        import aiofiles

        # Step 1: Download ArXiv paper
        async with ArXivService() as arxiv_service:
            dl_result = await arxiv_service.download_paper(arxiv_id)
        
        if not dl_result.get("success"):
            raise ServiceError(f"Failed to download arXiv paper: {dl_result.get('error')}", ErrorCodes.EXTERNAL_API_ERROR)

        pdf_path: Path = dl_result["file_path"]  # type: ignore
        metadata = dl_result.get("metadata", {})

        # Step 2: Wrap file in UploadFile for reuse of existing workflow
        file_handle = open(pdf_path, "rb")
        upload_file = UploadFile(filename=f"{arxiv_id}.pdf", file=file_handle)

        # Step 3: Build PaperCreate payload
        from app.models.paper import PaperCreate
        
        # Handle authors - they might be string representations of Author objects
        authors_list = []
        if metadata.get("authors"):
            for author in metadata.get("authors", []):
                if isinstance(author, str):
                    # Parse string representation like "id=None name='John Doe' affiliation=None..."
                    if "name='" in author and "'" in author:
                        name_start = author.find("name='") + 6
                        name_end = author.find("'", name_start)
                        if name_end > name_start:
                            name = author[name_start:name_end]
                            authors_list.append(name)
                elif hasattr(author, 'get'):
                    # It's already a dict
                    authors_list.append(author.get("name", "Unknown"))
                elif hasattr(author, 'name'):
                    # It's an object with name attribute
                    authors_list.append(author.name)
                else:
                    logger.error(f"Unknown author format: {type(author)} - {author}")
        
        paper_create = PaperCreate(
            title=metadata.get("title", "Unknown Title"),
            abstract=metadata.get("abstract", ""),
            arxiv_id=arxiv_id,
            authors=authors_list,
            doi=metadata.get("doi")
        )

        # Step 4: Complete upload workflow (stores file, creates DB row, optional processing)
        workflow_res = await self.complete_upload_workflow(
            file=upload_file,
            project_id=project_id,
            paper_data=paper_create,
            created_by=user_id,
            process_immediately=process_with_grobid,
            run_diagnostics=run_diagnostics
        )

        # Close the file handle
        await upload_file.close()

        return {
            "success": workflow_res.get("success", False),
            "message": workflow_res.get("message", "Paper added"),
            "paper_id": str(workflow_res["paper"].id) if workflow_res.get("paper") else None,
            "processing_status": workflow_res.get("workflow_steps", {}).get("processing"),
            "diagnostic_status": workflow_res.get("workflow_steps", {}).get("diagnostics")
        }
    
    # ================================
    # PAPER CRUD OPERATIONS
    # ================================
    
    async def create_paper(
        self,
        project_id: uuid.UUID,
        paper_data: PaperCreate,
        created_by: uuid.UUID
    ) -> Dict[str, Any]:
        """Create new paper."""
        return await self.crud_service.create_paper(project_id, paper_data, created_by)
    
    async def get_paper(
        self,
        paper_id: str,
        user_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Get paper by ID. project_id currently unused but accepted for endpoint compatibility."""
        return await self.crud_service.get_paper(paper_id, user_id)
    
    async def update_paper(
        self,
        paper_id: str,
        paper_data: PaperUpdate,
        updated_by: uuid.UUID
    ) -> Dict[str, Any]:
        """Update paper information."""
        return await self.crud_service.update_paper(paper_id, paper_data, updated_by)
    
    async def delete_paper(
        self,
        paper_id: str,
        deleted_by: uuid.UUID,
        soft_delete: bool = True
    ) -> Dict[str, Any]:
        """Delete paper."""
        return await self.crud_service.delete_paper(paper_id, deleted_by, soft_delete)
    
    async def list_project_papers(
        self,
        project_id: uuid.UUID,
        page: int = 1,
        limit: int = 50,
        include_deleted: bool = False
    ) -> Dict[str, Any]:
        """List papers in project."""
        return await self.crud_service.list_project_papers(project_id, page, limit, include_deleted)
    
    # ================================
    # FILE OPERATIONS
    # ================================
    
    async def validate_upload(self, file: UploadFile) -> Dict[str, Any]:
        """Validate uploaded file."""
        return await self.storage_service.validate_upload(file)
    
    async def store_file(
        self,
        file: UploadFile,
        paper_id: str,
        title: str
    ) -> Dict[str, Any]:
        """Store uploaded file."""
        return await self.storage_service.store_file(file, paper_id, title)
    
    async def get_file_path(self, paper_id: str) -> Optional[Path]:
        """Get file path for paper."""
        return await self.storage_service.get_file_path(paper_id)
    
    async def delete_file(self, paper_id: str) -> Dict[str, Any]:
        """Delete stored file."""
        return await self.storage_service.delete_file(paper_id)
    
    async def verify_file_integrity(self, paper_id: str) -> Dict[str, Any]:
        """Verify file integrity."""
        return await self.storage_service.verify_file_integrity(paper_id)
    
    # ================================
    # PROCESSING OPERATIONS
    # ================================
    
    async def process_with_grobid(
        self,
        paper_id: str
    ) -> Dict[str, Any]:
        """Process paper with GROBID."""
        file_path = await self.storage_service.get_file_path(paper_id)
        if not file_path:
            return {
                "success": False,
                "error": "Paper file not found"
            }
        
        return await self.processing_service.process_with_grobid(file_path, paper_id)
    
    async def extract_text_content(self, paper_id: str) -> Dict[str, Any]:
        """Extract text content from paper."""
        file_path = await self.storage_service.get_file_path(paper_id)
        if not file_path:
            return {
                "success": False,
                "error": "Paper file not found"
            }
        
        return await self.processing_service.extract_text_content(file_path, paper_id)
    
    async def get_processing_status(self, paper_id: str) -> Dict[str, Any]:
        """Get processing status."""
        return await self.processing_service.get_processing_status(paper_id)
    
    # ================================
    # EMBEDDING OPERATIONS
    # ================================
    
    async def generate_embedding(
        self,
        paper_id: str,
        text_content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate embedding for paper using AI diagnostics text preferentially."""
        
        # Strategy 1: Use AI-generated diagnostics as primary source for embeddings
        try:
            paper_db = await self.crud_service.repository.get_paper_by_id(
                uuid.UUID(paper_id), include_diagnostics=True
            )
            
            # Check if we have AI-generated diagnostics to use for embedding
            if hasattr(paper_db, 'diagnostic') and paper_db.diagnostic:
                diagnostic = paper_db.diagnostic
                
                # Construct comprehensive text from AI diagnostics
                diagnostic_parts = []
                
                if hasattr(diagnostic, 'summary') and diagnostic.summary:
                    diagnostic_parts.append(f"Summary: {diagnostic.summary}")
                    
                if hasattr(diagnostic, 'abstract') and diagnostic.abstract:
                    diagnostic_parts.append(f"Abstract: {diagnostic.abstract}")
                    
                if hasattr(diagnostic, 'highlights') and diagnostic.highlights:
                    diagnostic_parts.append(f"Highlights: {diagnostic.highlights}")
                    
                if hasattr(diagnostic, 'contributions') and diagnostic.contributions:
                    diagnostic_parts.append(f"Contributions: {diagnostic.contributions}")
                    
                if hasattr(diagnostic, 'method') and diagnostic.method:
                    diagnostic_parts.append(f"Method: {diagnostic.method}")
                    
                if hasattr(diagnostic, 'strengths') and diagnostic.strengths:
                    diagnostic_parts.append(f"Strengths: {diagnostic.strengths}")
                
                # Use AI diagnostics text if available and meaningful
                if diagnostic_parts and len(' '.join(diagnostic_parts)) > 100:
                    text_content = '\n'.join(diagnostic_parts)
                    logger.info(f"Using AI diagnostics text for embedding generation for paper {paper_id}")
                
        except Exception as e:
            logger.warning(f"Could not retrieve diagnostics for embedding {paper_id}: {e}")
        
        # Strategy 2: Fallback to PyPDF text extraction
        if not text_content or not text_content.strip():
            try:
                logger.info(f"Attempting PyPDF text extraction for embedding generation for paper {paper_id}")
                file_path = await self._get_stored_file_path(paper_id)
                pypdf_result = await self.processing_service.extract_text_with_pypdf(file_path, paper_id)
                
                if pypdf_result.get("success") and pypdf_result.get("text_content", "").strip():
                    text_content = pypdf_result["text_content"]
                    logger.info(f"Using PyPDF-extracted text ({pypdf_result['word_count']} words) for embedding generation for paper {paper_id}")
            except Exception as e:
                logger.warning(f"PyPDF text extraction failed for embedding {paper_id}: {e}")
            
            # Strategy 3: Final fallback to basic paper fields
            if not text_content or not text_content.strip():
                try:
                    if not paper_db:
                        paper_db = await self.crud_service.repository.get_paper_by_id(uuid.UUID(paper_id))
                    
                    parts = []
                    if hasattr(paper_db, "title") and paper_db.title:
                        parts.append(paper_db.title)
                    if hasattr(paper_db, "abstract") and paper_db.abstract:
                        parts.append(paper_db.abstract)
                    
                    if parts:
                        text_content = "\n\n".join(parts)
                        logger.info(f"Using basic paper fields for embedding generation for paper {paper_id}")
                except Exception as e:
                    logger.error(f"Failed to retrieve paper fields for embedding {paper_id}: {e}")
        
        # Final validation
        if not text_content or not text_content.strip():
            return {
                "success": False,
                "error": "No suitable text content available for embedding generation"
            }
        
        # Delegate to embedding service
        return await self.embedding_service.generate_embedding(
            paper_id,
            text_content.strip(),
            metadata
        )
    
    async def semantic_search(
        self,
        query: str,
        project_id: Optional[str] = None,
        limit: int = 10,
        similarity_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """Perform semantic search."""
        return await self.embedding_service.semantic_search(query, project_id, limit, similarity_threshold)
    
    async def find_similar_papers(
        self,
        paper_id: str,
        limit: int = 5,
        similarity_threshold: float = 0.6
    ) -> Dict[str, Any]:
        """Find similar papers."""
        return await self.embedding_service.find_similar_papers(paper_id, limit, similarity_threshold)
    
    async def get_embedding_status(self, paper_id: str) -> Dict[str, Any]:
        """Get embedding status."""
        return await self.embedding_service.get_embedding_status(paper_id)
    
    # ================================
    # SEARCH OPERATIONS
    # ================================
    
    async def search_papers(
        self,
        query: str,
        project_id: Optional[uuid.UUID] = None,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Search papers by text."""
        return await self.crud_service.search_papers(query, project_id, filters, page, limit)
    
    # ================================
    # BULK OPERATIONS
    # ================================
    
    async def bulk_update_papers(
        self,
        paper_ids: List[str],
        update_data: Dict[str, Any],
        updated_by: uuid.UUID
    ) -> Dict[str, Any]:
        """Bulk update papers."""
        return await self.crud_service.bulk_update_papers(paper_ids, update_data, updated_by)
    
    async def batch_generate_embeddings(
        self,
        paper_ids: List[str],
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """Batch generate embeddings."""
        return await self.embedding_service.batch_generate_embeddings(paper_ids, force_regenerate)
    
    @handle_service_errors("complete paper upload workflow")
    async def complete_upload_workflow(
        self,
        file: UploadFile,
        project_id: uuid.UUID,
        paper_data: PaperCreate,
        created_by: uuid.UUID,
        process_immediately: bool = True,
        run_diagnostics: bool = True
    ) -> Dict[str, Any]:
        """
        Complete upload workflow: validation → storage → processing → embedding.
        
        Args:
            file: Uploaded file
            project_id: Project UUID
            paper_data: Paper metadata
            created_by: User creating the paper
            process_immediately: Whether to process immediately
            
        Returns:
            Complete workflow result
        """
        # Step 1: Validate file
        validation_result = await self.validate_upload(file)
        if not validation_result["success"]:
            return validation_result
        
        # Step 2: Check for existing paper by hash and reuse its ID
        existing_paper = await self._find_existing_paper(file, project_id)
        paper_result = None
        if existing_paper:
            paper_id = str(existing_paper.id)
            needs_reprocessing = True
            logger.info(f"Found existing paper {paper_id} by hash; reprocessing in-place")
        else:
            # Create new paper record
            paper_result = await self.create_paper(project_id, paper_data, created_by)
            if not paper_result["success"]:
                return paper_result
            paper_id = str(paper_result["paper"].id)
            needs_reprocessing = True
        
        try:
            # Step 3: Store file (only if new paper or reprocessing needed)
            if not existing_paper or needs_reprocessing:
                storage_result = await self.store_file(file, paper_id, paper_data.title)
                if not storage_result["success"]:
                    # Cleanup: delete paper record (only if new)
                    if not existing_paper:
                        await self.delete_paper(paper_id, created_by, soft_delete=False)
                    return storage_result
            else:
                storage_result = {"success": True, "file_info": {"message": "File storage skipped - paper already exists"}}
            
            # Get the paper object for response
            if existing_paper:
                paper_obj = existing_paper
            elif paper_result and paper_result.get("paper"):
                paper_obj = paper_result["paper"]
            else:
                # Fallback: get paper from database
                paper_obj = await self.crud_service.repository.get_paper_by_id(
                    uuid.UUID(paper_id), include_diagnostics=True
                )
            
            workflow_result = {
                "success": True,
                "paper": paper_obj,
                "file_info": storage_result["file_info"],
                "workflow_steps": {
                    "validation": "completed",
                    "paper_creation": "completed" if not existing_paper else "skipped",
                    "file_storage": "completed" if not existing_paper or needs_reprocessing else "skipped",
                    "processing": "pending",
                    "embedding": "pending"
                }
            }
            
            if process_immediately and needs_reprocessing:
                # Two parallel processing groups for PDFs
                if file.filename.lower().endswith('.pdf'):
                    # Get file path for processing
                    file_path = await self._get_stored_file_path(paper_id)
                    
                    # GROUP 1: GROBID Processing (metadata + bib file)
                    grobid_task = self._process_grobid_group(paper_id, file_path, workflow_result)
                    
                    # GROUP 2: Text/AI Processing (PyPDF + diagnostics + embeddings)  
                    text_ai_task = self._process_text_ai_group(paper_id, file_path, workflow_result, run_diagnostics)
                    
                    # Run both groups in parallel
                    import asyncio
                    await asyncio.gather(grobid_task, text_ai_task, return_exceptions=True)
                    
                else:
                    # Non-PDF files skip both processing groups
                    workflow_result["workflow_steps"]["processing"] = "skipped"
                    workflow_result["workflow_steps"]["diagnostics"] = "skipped"
                    workflow_result["workflow_steps"]["embedding"] = "skipped"
            
            return workflow_result
        
        except Exception as e:
            # Cleanup on failure
            if not existing_paper and paper_result:
                try:
                    await self.delete_paper(paper_id, created_by, soft_delete=False)
                except Exception:
                    pass  # Log but don't fail on cleanup
            raise ServiceError(
                f"Workflow failed: {str(e)}",
                ErrorCodes.PROCESSING_ERROR
            )
    
    async def upload_paper(
        self,
        file: UploadFile,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        title: Optional[str] = None,
        process_with_grobid: bool = True,
        run_diagnostics: bool = True,
        private_uploaded: bool = False
    ) -> Dict[str, Any]:
        """Endpoint convenience wrapper around `complete_upload_workflow`."""
        paper_data = PaperCreate(
            title=title or file.filename,
            private_uploaded=private_uploaded,
        )
        workflow_result = await self.complete_upload_workflow(
            file,
            project_id,
            paper_data,
            created_by=user_id,
            process_immediately=process_with_grobid,
            run_diagnostics=run_diagnostics,
        )

        if not workflow_result["success"]:
            return workflow_result

        paper_id = str(workflow_result["paper"].id)
        processing_status = workflow_result["workflow_steps"].get("processing", "pending")

        return {
            "success": True,
            "message": "Paper uploaded successfully",
            "paper_id": paper_id,
            "processing_status": processing_status,
            "diagnostic_status": workflow_result["workflow_steps"].get("diagnostics", "pending"),
            "embedding_status": workflow_result["workflow_steps"].get("embedding", "pending"),
            }
    
    # ================================
    # STATISTICS AND HEALTH
    # ================================
    
    async def get_paper_statistics(
        self,
        project_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Get paper statistics."""
        return await self.crud_service.get_paper_statistics(project_id)
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return await self.storage_service.get_storage_stats()
    
    async def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """Get comprehensive paper metadata."""
        return await self.crud_service.get_paper_metadata(paper_id)
    
    @handle_service_errors("paper service health check")
    async def health_check(self) -> Dict[str, Any]:
        """Service health check."""
        try:
            # Check GROBID availability
            grobid_health = await self.processing_service.check_grobid_health()
            
            return {
                "success": True,
                "status": "healthy",
                "services": {
                    "storage": "healthy",
                    "processing": "healthy" if grobid_health["success"] else "degraded",
                    "embedding": "healthy",
                    "crud": "healthy"
                },
                "grobid_status": grobid_health["status"]
            }
        except Exception as e:
            logger.error(f"Paper service health check failed: {e}")
            return {
                "success": False,
                "status": "unhealthy",
                "error": str(e)
            }

    async def get_service_health(self) -> Dict[str, Any]:
        """Get health status of all paper services."""
        return await self.processing_service.get_service_health()

    # ================================ 
    # PRIVATE HELPER METHODS
    # ================================

    async def _find_existing_paper(self, file: UploadFile, project_id: uuid.UUID) -> Optional[Any]:
        """Find an existing paper by file hash and project ID."""
        try:
            # Generate a unique hash for the file content
            file_hash = await self.storage_service.generate_file_hash(file)
            
            # Find papers with the same file hash and project ID
            existing_papers = await self.crud_service.repository.get_papers_by_file_hash_and_project(file_hash, project_id)
            
            if existing_papers:
                # Return the first paper found
                return existing_papers[0]
            return None
        except Exception as e:
            logger.error(f"Error finding existing paper: {e}")
            return None
 
    def _needs_reprocessing(self, existing_paper: Any) -> bool:
        """Determine if an existing paper needs reprocessing based on missing metadata."""
        # Check multiple indicators of incomplete processing
        incomplete_indicators = [
            not existing_paper.title or existing_paper.title.endswith('.pdf'),  # Title not extracted
            not existing_paper.abstract,  # No abstract extracted
            not existing_paper.authors,   # No authors extracted
            not existing_paper.safe_title, # No safe title generated
            not existing_paper.xml_path,   # No GROBID XML processed
            not existing_paper.diagnostics # No diagnostics generated
        ]
        
        missing_count = sum(incomplete_indicators)
        
        # If more than 2 key fields are missing, reprocess
        return missing_count >= 2

    async def _update_paper_with_grobid_metadata(self, paper_id: str, metadata: Dict[str, Any]) -> None:
        """Update paper record with extracted GROBID metadata."""
        try:
            update_data = {}
            
            # Extract title
            if metadata.get("title"):
                update_data["title"] = metadata["title"]
                # Generate safe title for file storage
                safe_title = self.storage_service.generate_safe_title(metadata["title"])
                update_data["safe_title"] = safe_title
            
            # Extract authors (convert to simple string list)
            if metadata.get("authors"):
                authors = []
                for author in metadata["authors"]:
                    if isinstance(author, dict) and author.get("name"):
                        authors.append(author["name"])
                    elif isinstance(author, str):
                        authors.append(author)
                update_data["authors"] = authors
            
            # Extract abstract
            if metadata.get("abstract"):
                update_data["abstract"] = metadata["abstract"]
            
            # Extract keywords if available
            if metadata.get("keywords"):
                update_data["keywords"] = metadata["keywords"]
            
            # Update XML path if available
            if metadata.get("xml_path"):
                update_data["xml_path"] = metadata["xml_path"]
            
            # Update BibTeX path if available
            if metadata.get("bib_path"):
                update_data["bib_path"] = metadata["bib_path"]
            
            if update_data:
                await self.crud_service.repository.update_paper(uuid.UUID(paper_id), update_data)
                await self.crud_service.session.commit()
                
        except Exception as e:
            logger.error(f"Failed to update paper {paper_id} with GROBID metadata: {e}")
            # Don't fail the entire workflow for metadata update issues
    
    async def _generate_diagnostics_from_grobid(self, paper_id: str, metadata: Dict[str, Any]) -> None:
        """Generate AI-powered diagnostics from GROBID-extracted text using GPT-4o mini."""
        try:
            from app.repositories.paper_repository import PaperRepository
            from app.models.paper import DiagnosticCreate
            from app.services.ai_diagnostics_service import AIDiagnosticsService
            
            repository = PaperRepository(self.crud_service.session)
            ai_service = AIDiagnosticsService()
            
            # Check if diagnostic already exists
            existing_diagnostic = await repository.get_diagnostic_by_paper_id(uuid.UUID(paper_id))
            
            # Extract text content for AI analysis
            title = metadata.get("title", "")
            abstract = metadata.get("abstract", "")
            full_text = metadata.get("full_text", "")
            
            # Validate we have sufficient content for AI analysis
            total_content_length = len(title) + len(abstract) + len(full_text)
            if total_content_length < 200:
                logger.warning(f"Insufficient content for AI diagnostics for paper {paper_id}")
                # Fallback to basic diagnostics
                await self._generate_basic_diagnostics_fallback(paper_id, metadata, repository, existing_diagnostic)
                return
            
            # Generate AI-powered diagnostics using GPT-4o mini
            ai_result = await ai_service.generate_diagnostics_from_text(
                title=title,
                abstract=abstract,
                full_text=full_text,
                paper_metadata=metadata
            )
            
            if not ai_result["success"]:
                logger.error(f"AI diagnostics failed for paper {paper_id}")
                await self._generate_basic_diagnostics_fallback(paper_id, metadata, repository, existing_diagnostic)
                return
            
            # Use AI-generated diagnostics
            ai_diagnostics = ai_result["diagnostics"]
            diagnostic_data = {
                "abstract": abstract,
                "summary": ai_diagnostics.get("summary", ""),
                "method": ai_diagnostics.get("method", ""),
                "dataset": ai_diagnostics.get("dataset", ""),
                "highlights": ai_diagnostics.get("highlights", ""),
                "weakness": ai_diagnostics.get("weakness", ""),
                "future_scope": ai_diagnostics.get("future_scope", ""),
                "strengths": ai_diagnostics.get("strengths", ""),
                "contributions": ai_diagnostics.get("contributions", ""),
                "limitations": f"Generated using AI analysis ({ai_result['model_used']}) - content length: {ai_result['content_length']} chars"
            }
            
            if existing_diagnostic:
                # Update existing diagnostic
                await repository.update_diagnostic(uuid.UUID(paper_id), diagnostic_data)
            else:
                # Create new diagnostic
                diagnostic_create = DiagnosticCreate(
                    paper_id=uuid.UUID(paper_id),
                    **diagnostic_data
                )
                await repository.create_diagnostic(diagnostic_create)
                
            await self.crud_service.session.commit()
            logger.info(f"Generated AI diagnostics for paper {paper_id} using {ai_result['model_used']}")
            
        except Exception as e:
            logger.error(f"Failed to generate AI diagnostics for paper {paper_id}: {e}")
            # Fallback to basic diagnostics on error
            try:
                await self._generate_basic_diagnostics_fallback(paper_id, metadata, repository, existing_diagnostic)
            except Exception as fallback_error:
                logger.error(f"Fallback diagnostics also failed for paper {paper_id}: {fallback_error}")

    async def _generate_basic_diagnostics_fallback(
        self, 
        paper_id: str, 
        metadata: Dict[str, Any], 
        repository, 
        existing_diagnostic
    ) -> None:
        """Generate basic diagnostics as fallback when AI fails."""
        abstract = metadata.get("abstract", "")
        title = metadata.get("title", "")
        sections = metadata.get("sections", [])
        references_count = len(metadata.get("references", []))
        authors_count = len(metadata.get("authors", []))
        
        # Generate basic diagnostic content
        highlights = self._extract_key_insights(abstract, title, sections)
        strengths = self._analyze_strengths(abstract, sections, references_count)
        limitations = self._identify_limitations(abstract, sections)
        contributions = self._extract_contributions(abstract, title)
        
        diagnostic_data = {
            "abstract": abstract,
            "summary": f"Academic paper with {authors_count} authors containing {len(sections)} sections and {references_count} references. Processed via GROBID extraction.",
            "method": "GROBID TEI-XML parsing with content analysis",
            "dataset": self._extract_dataset_info(abstract, sections),
            "highlights": highlights,
            "weakness": limitations,
            "future_scope": self._suggest_future_work(abstract, sections),
            "strengths": strengths,
            "contributions": contributions,
            "limitations": "Basic automated analysis - AI analysis unavailable"
        }
        
        if existing_diagnostic:
            await repository.update_diagnostic(uuid.UUID(paper_id), diagnostic_data)
        else:
            from app.models.paper import DiagnosticCreate
            diagnostic_create = DiagnosticCreate(
                paper_id=uuid.UUID(paper_id),
                **diagnostic_data
            )
            await repository.create_diagnostic(diagnostic_create)
            
        await self.crud_service.session.commit()
    
    def _extract_key_insights(self, abstract: str, title: str, sections: List[str]) -> str:
        """Extract key insights from paper content."""
        insights = []
        
        # Extract methodology keywords
        method_keywords = ['transformer', 'attention', 'neural network', 'deep learning', 'machine learning', 
                          'algorithm', 'model', 'framework', 'approach', 'method']
        found_methods = [kw for kw in method_keywords if kw.lower() in abstract.lower() or kw.lower() in title.lower()]
        
        if found_methods:
            insights.append(f"Key methodologies: {', '.join(found_methods[:3])}")
        
        # Extract performance metrics
        metrics = ['accuracy', 'performance', 'BLEU', 'F1', 'precision', 'recall', 'error rate']
        found_metrics = [m for m in metrics if m.lower() in abstract.lower()]
        if found_metrics:
            insights.append(f"Performance metrics discussed: {', '.join(found_metrics[:3])}")
        
        # Extract application domains
        domains = ['translation', 'parsing', 'classification', 'detection', 'generation', 'processing']
        found_domains = [d for d in domains if d.lower() in abstract.lower() or d.lower() in title.lower()]
        if found_domains:
            insights.append(f"Application domains: {', '.join(found_domains[:3])}")
        
        return "; ".join(insights) if insights else "Technical paper with novel contributions"
    
    def _analyze_strengths(self, abstract: str, sections: List[str], ref_count: int) -> str:
        """Analyze paper strengths based on content."""
        strengths = []
        
        # Check for comparative analysis
        if any(word in abstract.lower() for word in ['compared', 'comparison', 'outperform', 'better than', 'superior']):
            strengths.append("Includes comparative analysis")
        
        # Check for experimental validation
        if any(word in abstract.lower() for word in ['experiment', 'evaluation', 'tested', 'validated']):
            strengths.append("Experimental validation provided")
        
        # Check reference quality
        if ref_count > 20:
            strengths.append("Well-referenced work")
        elif ref_count > 10:
            strengths.append("Adequately referenced")
        
        # Check for novelty indicators
        if any(word in abstract.lower() for word in ['novel', 'new', 'propose', 'introduce']):
            strengths.append("Novel approach or contribution")
        
        return "; ".join(strengths) if strengths else "Structured academic contribution"
    
    def _identify_limitations(self, abstract: str, sections: List[str]) -> str:
        """Identify potential limitations from content."""
        limitations = []
        
        # Check for limitation keywords
        if any(word in abstract.lower() for word in ['limited', 'constraint', 'challenge', 'limitation']):
            limitations.append("Acknowledged limitations in methodology")
        
        # Check for dataset size mentions
        if any(word in abstract.lower() for word in ['small dataset', 'limited data', 'few samples']):
            limitations.append("Dataset size constraints mentioned")
        
        # Check for computational constraints
        if any(word in abstract.lower() for word in ['computational', 'compute', 'resource']):
            limitations.append("Computational resource considerations")
        
        return "; ".join(limitations) if limitations else "Further analysis needed to identify specific limitations"
    
    def _extract_contributions(self, abstract: str, title: str) -> str:
        """Extract key contributions from abstract and title."""
        contributions = []
        
        # Look for contribution indicators
        contrib_patterns = ['we propose', 'we introduce', 'we present', 'we show', 'we demonstrate']
        for pattern in contrib_patterns:
            if pattern in abstract.lower():
                # Extract sentence containing the contribution
                sentences = abstract.split('.')
                for sentence in sentences:
                    if pattern in sentence.lower():
                        clean_sentence = sentence.strip()
                        if len(clean_sentence) > 20:  # Avoid very short sentences
                            contributions.append(clean_sentence[:100] + "..." if len(clean_sentence) > 100 else clean_sentence)
                        break
                break
        
        if not contributions:
            # Fallback: use title-based contribution
            contributions.append(f"Research on {title.lower()}")
        
        return "; ".join(contributions[:2])  # Limit to top 2 contributions
    
    def _extract_dataset_info(self, abstract: str, sections: List[str]) -> Optional[str]:
        """Extract dataset information if mentioned."""
        datasets = ['WMT', 'ImageNet', 'COCO', 'BERT', 'GPT', 'dataset', 'corpus', 'benchmark']
        found_datasets = [d for d in datasets if d in abstract]
        return ", ".join(found_datasets[:3]) if found_datasets else None
    
    def _suggest_future_work(self, abstract: str, sections: List[str]) -> str:
        """Suggest future work directions based on content."""
        suggestions = []
        
        # Check for future work indicators
        if any(word in abstract.lower() for word in ['future', 'extend', 'improve', 'enhance']):
            suggestions.append("Authors indicate potential extensions")
        
        # Domain-specific suggestions
        if 'attention' in abstract.lower():
            suggestions.append("Exploration of attention mechanisms variants")
        
        if 'performance' in abstract.lower():
            suggestions.append("Further performance optimization and analysis")
        
        return "; ".join(suggestions) if suggestions else "Potential for methodological extensions and broader applications" 

    async def _get_stored_file_path(self, paper_id: str) -> Path:
        """Get the stored file path for a paper using storage service."""
        file_path = await self.storage_service.get_file_path(paper_id)
        
        if not file_path:
            raise ServiceError(
                f"Could not find stored file for paper {paper_id}",
                ErrorCodes.NOT_FOUND_ERROR
            )
            
        return file_path
    
    async def _process_grobid_group(self, paper_id: str, file_path: Path, workflow_result: Dict[str, Any]) -> None:
        """GROUP 1: GROBID Processing - Extract metadata and create bib file."""
        try:
            logger.info(f"Starting GROBID processing for paper {paper_id}")
            processing_result = await self.processing_service.process_with_grobid(file_path, paper_id)
            
            if processing_result["success"]:
                workflow_result["workflow_steps"]["processing"] = "completed"
                workflow_result["processing_result"] = processing_result
                
                # Update paper with GROBID metadata (includes bib_path if created)
                await self._update_paper_with_grobid_metadata(paper_id, processing_result["metadata"])
                logger.info(f"GROBID processing completed for paper {paper_id}")
            else:
                workflow_result["workflow_steps"]["processing"] = "failed"
                workflow_result["processing_error"] = processing_result.get("error", "Unknown processing error")
                logger.warning(f"GROBID processing failed for paper {paper_id}: {processing_result.get('error')}")
                
        except Exception as e:
            workflow_result["workflow_steps"]["processing"] = "failed"
            workflow_result["processing_error"] = str(e)
            logger.error(f"GROBID processing encountered error for paper {paper_id}: {e}")
    
    async def _process_text_ai_group(self, paper_id: str, file_path: Path, workflow_result: Dict[str, Any], run_diagnostics: bool) -> None:
        """GROUP 2: Text/AI Processing - PyPDF extraction, AI diagnostics, and embeddings."""
        try:
            logger.info(f"Starting Text/AI processing for paper {paper_id}")
            
            # Step 1: Extract text using PyPDF
            text_result = await self.processing_service.extract_text_with_pypdf(file_path, paper_id)
            
            if not text_result["success"]:
                workflow_result["workflow_steps"]["diagnostics"] = "failed"
                workflow_result["workflow_steps"]["embedding"] = "failed"
                workflow_result["text_extraction_error"] = text_result.get("error")
                logger.warning(f"PyPDF text extraction failed for paper {paper_id}")
                return
            
            extracted_text = text_result["text_content"]
            logger.info(f"PyPDF extracted {text_result['word_count']} words for paper {paper_id}")
            
            # Step 2: Generate AI diagnostics from extracted text
            if run_diagnostics:
                try:
                    await self._generate_ai_diagnostics_from_text(paper_id, extracted_text)
                    workflow_result["workflow_steps"]["diagnostics"] = "completed"
                    logger.info(f"AI diagnostics completed for paper {paper_id}")
                except Exception as e:
                    workflow_result["workflow_steps"]["diagnostics"] = "failed"
                    workflow_result["diagnostics_error"] = str(e)
                    logger.error(f"AI diagnostics failed for paper {paper_id}: {e}")
            else:
                workflow_result["workflow_steps"]["diagnostics"] = "skipped"
            
            # Step 3: Generate embeddings from AI diagnostics
            try:
                embedding_result = await self.generate_embedding(paper_id)
                if embedding_result.get("success"):
                    workflow_result["workflow_steps"]["embedding"] = "completed"
                    workflow_result["embedding_result"] = embedding_result
                    logger.info(f"Embedding generation completed for paper {paper_id}")
                else:
                    workflow_result["workflow_steps"]["embedding"] = "failed"
                    workflow_result["embedding_error"] = embedding_result.get("error")
            except Exception as e:
                workflow_result["workflow_steps"]["embedding"] = "failed"
                workflow_result["embedding_error"] = str(e)
                logger.error(f"Embedding generation failed for paper {paper_id}: {e}")
                
        except Exception as e:
            workflow_result["workflow_steps"]["diagnostics"] = "failed"
            workflow_result["workflow_steps"]["embedding"] = "failed"
            workflow_result["text_ai_error"] = str(e)
            logger.error(f"Text/AI processing encountered error for paper {paper_id}: {e}")
    
    async def _generate_ai_diagnostics_from_text(self, paper_id: str, extracted_text: str) -> None:
        """Generate AI-powered diagnostics from PyPDF-extracted text using GPT-4o mini."""
        try:
            from app.repositories.paper_repository import PaperRepository
            from app.models.paper import DiagnosticCreate
            from app.services.ai_diagnostics_service import AIDiagnosticsService
            
            repository = PaperRepository(self.crud_service.session)
            ai_service = AIDiagnosticsService()
            
            # Check if diagnostic already exists
            existing_diagnostic = await repository.get_diagnostic_by_paper_id(uuid.UUID(paper_id))
            
            # Get paper title for context
            paper_db = await self.crud_service.repository.get_paper_by_id(uuid.UUID(paper_id))
            paper_title = getattr(paper_db, 'title', '') if paper_db else ''
            
            # Generate AI-powered diagnostics using GPT-4o mini
            ai_result = await ai_service.generate_diagnostics_from_text(
                title=paper_title,
                abstract="",  # We don't have abstract from PyPDF, let AI extract it
                full_text=extracted_text,
                paper_metadata=None
            )
            
            if not ai_result["success"]:
                raise ServiceError(
                    f"AI diagnostics generation failed for paper {paper_id}",
                    ErrorCodes.PROCESSING_ERROR
                )
            
            # Use AI-generated diagnostics
            ai_diagnostics = ai_result["diagnostics"]
            diagnostic_data = {
                "abstract": ai_diagnostics.get("summary", ""),  # Use summary as abstract
                "summary": ai_diagnostics.get("summary", ""),
                "method": ai_diagnostics.get("method", ""),
                "dataset": ai_diagnostics.get("dataset", ""),
                "highlights": ai_diagnostics.get("highlights", ""),
                "weakness": ai_diagnostics.get("weakness", ""),
                "future_scope": ai_diagnostics.get("future_scope", ""),
                "strengths": ai_diagnostics.get("strengths", ""),
                "contributions": ai_diagnostics.get("contributions", ""),
                "limitations": ai_diagnostics.get("limitations", "Not clearly specified in the provided text")
            }
            
            if existing_diagnostic:
                # Update existing diagnostic
                await repository.update_diagnostic(uuid.UUID(paper_id), diagnostic_data)
            else:
                # Create new diagnostic
                diagnostic_create = DiagnosticCreate(
                    paper_id=uuid.UUID(paper_id),
                    **diagnostic_data
                )
                await repository.create_diagnostic(diagnostic_create)
                
            await self.crud_service.session.commit()
            logger.info(f"Generated AI diagnostics for paper {paper_id} using GPT-4o mini from PyPDF text")
            
        except Exception as e:
            logger.error(f"Failed to generate AI diagnostics for paper {paper_id}: {e}")
            raise

    @handle_service_errors("get paper diagnostics")
    async def get_paper_diagnostics(
        self,
        paper_id: uuid.UUID,
        project_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get diagnostics for a paper. If diagnostics don't exist, generate them.
        
        Args:
            paper_id: Paper UUID
            project_id: Project UUID (for access control)
            user_id: User UUID (for access control)
            
        Returns:
            Dictionary with success status and diagnostics data
        """
        try:
            repository = self.crud_service.repository
            
            # First verify the paper exists and user has access
            paper = await repository.get_paper_by_id(paper_id, include_diagnostics=False)
            if not paper:
                return {"success": False, "error": "Paper not found"}
            
            # Verify paper belongs to project
            is_in_project = await repository.is_paper_in_project(project_id, paper_id)
            if not is_in_project:
                return {"success": False, "error": "Paper not found in project"}
            
            # Get existing diagnostics
            existing_diagnostic = await repository.get_diagnostic_by_paper_id(paper_id)
            
            if existing_diagnostic:
                # Return existing diagnostics
                from app.models.paper import DiagnosticResponse
                diagnostic_response = DiagnosticResponse.from_orm(existing_diagnostic)
                return {
                    "success": True,
                    "diagnostics": diagnostic_response
                }
            
            # No diagnostics exist, generate them
            logger.info(f"No diagnostics found for paper {paper_id}, generating...")
            
            # Check if we have a PDF file to extract text from
            file_path = await self.get_file_path(str(paper_id))
            if file_path and file_path.exists():
                # Extract text content from PDF first
                text_result = await self.processing_service.extract_text_with_pypdf(file_path, str(paper_id))
                if text_result.get("success") and text_result.get("text_content", "").strip():
                    extracted_text = text_result["text_content"]
                    # Generate diagnostics using AI from PDF text
                    await self._generate_ai_diagnostics_from_text(str(paper_id), extracted_text)
                else:
                    # Try basic text extraction as fallback
                    text_content_result = await self.extract_text_content(str(paper_id))
                    if text_content_result.get("success") and text_content_result.get("text_content", "").strip():
                        extracted_text = text_content_result["text_content"]
                        await self._generate_ai_diagnostics_from_text(str(paper_id), extracted_text)
                
                # Fetch the newly created diagnostics
                new_diagnostic = await repository.get_diagnostic_by_paper_id(paper_id)
                if new_diagnostic:
                    from app.models.paper import DiagnosticResponse
                    diagnostic_response = DiagnosticResponse.from_orm(new_diagnostic)
                    return {
                        "success": True,
                        "diagnostics": diagnostic_response
                    }
            
            # If we couldn't generate diagnostics, return empty response
            return {
                "success": False,
                "error": "Could not generate diagnostics for this paper"
            }
            
        except Exception as e:
            logger.error(f"Error getting diagnostics for paper {paper_id}: {e}")
            return {"success": False, "error": str(e)}

    @handle_service_errors("generate diagnostics")
    async def generate_diagnostics(
        self,
        paper_id: uuid.UUID,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        diagnostic_type: str = "ai",
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Generate diagnostics for a paper.
        
        Args:
            paper_id: Paper UUID
            project_id: Project UUID (for access control)
            user_id: User UUID (for access control)
            diagnostic_type: Type of diagnostics to generate
            force_regenerate: Whether to regenerate existing diagnostics
            
        Returns:
            Dictionary with success status and operation result
        """
        try:
            repository = self.crud_service.repository
            
            # First verify the paper exists and user has access
            paper = await repository.get_paper_by_id(paper_id, include_diagnostics=False)
            if not paper:
                return {"success": False, "error": "Paper not found"}
            
            # Verify paper belongs to project
            is_in_project = await repository.is_paper_in_project(project_id, paper_id)
            if not is_in_project:
                return {"success": False, "error": "Paper not found in project"}
            
            # Check if diagnostics already exist
            existing_diagnostic = await repository.get_diagnostic_by_paper_id(paper_id)
            
            if existing_diagnostic and not force_regenerate:
                return {
                    "success": True,
                    "message": "Diagnostics already exist. Use force_regenerate=true to regenerate.",
                    "diagnostic_id": str(existing_diagnostic.id)
                }
            
            # Generate diagnostics based on type
            if diagnostic_type == "ai":
                # Check if we have a PDF file
                file_path = await self.get_file_path(str(paper_id))
                if file_path and file_path.exists():
                    # Extract text content from PDF first
                    text_result = await self.processing_service.extract_text_with_pypdf(file_path, str(paper_id))
                    if text_result.get("success") and text_result.get("text_content", "").strip():
                        extracted_text = text_result["text_content"]
                        await self._generate_ai_diagnostics_from_text(str(paper_id), extracted_text)
                    else:
                        # Try basic text extraction as fallback
                        text_content_result = await self.extract_text_content(str(paper_id))
                        if text_content_result.get("success") and text_content_result.get("text_content", "").strip():
                            extracted_text = text_content_result["text_content"]
                            await self._generate_ai_diagnostics_from_text(str(paper_id), extracted_text)
                    
                    # Get the generated diagnostics
                    new_diagnostic = await repository.get_diagnostic_by_paper_id(paper_id)
                    if new_diagnostic:
                        return {
                            "success": True,
                            "message": "AI diagnostics generated successfully",
                            "diagnostic_id": str(new_diagnostic.id)
                        }
                else:
                    return {
                        "success": False,
                        "error": "PDF file not found for AI diagnostic generation"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Unsupported diagnostic type: {diagnostic_type}"
                }
            
            return {
                "success": False,
                "error": "Failed to generate diagnostics"
            }
            
        except Exception as e:
            logger.error(f"Error generating diagnostics for paper {paper_id}: {e}")
            return {"success": False, "error": str(e)} 
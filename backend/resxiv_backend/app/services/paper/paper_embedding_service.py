"""
Paper Embedding Service - L6 Engineering Standards
Focused on AI-powered semantic embeddings and semantic search operations.
"""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sentence_transformers import SentenceTransformer

from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.repositories.paper_embedding_repository import PaperEmbeddingRepository

logger = logging.getLogger(__name__)


class PaperEmbeddingService:
    """
    Embedding service for paper semantic analysis.
    Single Responsibility: AI embeddings and semantic search.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = PaperEmbeddingRepository(session)
        
        # Embedding configuration
        self.model_name = "all-MiniLM-L6-v2"
        self.model = None
        self._model_initialized = False
        self.embedding_dimension = 384  # Dimension for all-MiniLM-L6-v2
        
        # Thread pool for CPU-intensive operations
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    def _initialize_model(self) -> None:
        """Initialize the sentence transformer model (CPU-intensive)"""
        if not self._model_initialized:
            try:
                self.model = SentenceTransformer(self.model_name)
                self._model_initialized = True
                logger.info(f"Initialized embedding model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize embedding model: {e}")
                raise ServiceError(
                    f"Failed to initialize embedding model: {str(e)}",
                    ErrorCodes.INITIALIZATION_ERROR
                )
    
    def _generate_embedding_sync(self, text: str) -> np.ndarray:
        """Generate embedding synchronously (runs in thread pool)"""
        if not self._model_initialized:
            self._initialize_model()
        
        if not text or not text.strip():
            return np.zeros(self.embedding_dimension)
        
        # Truncate text to avoid memory issues
        max_length = 512  # Tokens
        if len(text) > max_length * 4:  # Rough character estimate
            text = text[:max_length * 4]
        
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0]
    
    @handle_service_errors("generate paper embedding")
    async def generate_embedding(
        self,
        paper_id: str,
        text_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate semantic embedding for a paper.
        
        Args:
            paper_id: Paper UUID
            text_content: Text content to embed
            metadata: Optional metadata for context
            
        Returns:
            Embedding generation result
        """
        if not text_content or not text_content.strip():
            raise ServiceError(
                "Text content is required for embedding generation",
                ErrorCodes.VALIDATION_ERROR
            )
        
        try:
            # Prepare text for embedding
            embedding_text = self._prepare_text_for_embedding(text_content, metadata)
            
            # Generate embedding in thread pool (CPU-intensive)
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                self.executor,
                self._generate_embedding_sync,
                embedding_text
            )
            
            # Convert to list for JSON serialization
            embedding_list = embedding.tolist()

            # Store embedding in database (upsert)
            await self.repository.update_paper_embedding(
                paper_id,
                embedding_list,
                embedding_text,
                self.model_name,
            )
            
            return {
                "success": True,
                "paper_id": paper_id,
                "embedding_dimension": len(embedding_list),
                "text_length": len(embedding_text),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise ServiceError(
                f"Embedding generation failed: {str(e)}",
                ErrorCodes.PROCESSING_ERROR
            )
    
    def _prepare_text_for_embedding(
        self,
        text_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Prepare text content for embedding generation.
        
        Args:
            text_content: Raw text content
            metadata: Optional metadata for context
            
        Returns:
            Prepared text for embedding
        """
        text_parts = []
        
        # Add metadata context if available
        if metadata:
            if metadata.get("title"):
                text_parts.append(f"Title: {metadata['title']}")
            
            if metadata.get("abstract"):
                text_parts.append(f"Abstract: {metadata['abstract']}")
            
            if metadata.get("keywords"):
                keywords_str = ", ".join(metadata["keywords"])
                text_parts.append(f"Keywords: {keywords_str}")
        
        # Add main content
        text_parts.append(text_content)
        
        # Combine all parts
        combined_text = "\n\n".join(text_parts)
        
        # Limit length for embedding model
        max_chars = 8000  # Conservative limit
        if len(combined_text) > max_chars:
            combined_text = combined_text[:max_chars] + "..."
        
        return combined_text
    
    @handle_service_errors("semantic search")
    async def semantic_search(
        self,
        query: str,
        project_id: Optional[str] = None,
        limit: int = 10,
        similarity_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Perform semantic search across papers.
        
        Args:
            query: Search query
            project_id: Optional project filter
            limit: Maximum results to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            Search results with similarity scores
        """
        if not query or not query.strip():
            raise ServiceError(
                "Search query is required",
                ErrorCodes.VALIDATION_ERROR
            )
        
        try:
            # Generate query embedding
            loop = asyncio.get_event_loop()
            query_embedding = await loop.run_in_executor(
                self.executor,
                self._generate_embedding_sync,
                query
            )
            
            # Search for similar papers
            papers = await self.repository.search_by_embedding(
                query_embedding.tolist(),
                project_id=project_id,
                limit=limit * 2,  # Get more to filter by threshold
                similarity_threshold=similarity_threshold
            )
            
            # Calculate similarity scores and prepare results
            results = []
            for paper in papers[:limit]:
                if hasattr(paper, 'similarity_score'):
                    similarity = paper.similarity_score
                else:
                    # Calculate similarity if not provided by repository
                    paper_embedding = np.array(paper.embedding)
                    similarity = float(np.dot(query_embedding, paper_embedding))
                
                if similarity >= similarity_threshold:
                    results.append({
                        "paper_id": str(paper.id),
                        "title": paper.title,
                        "authors": paper.authors,
                        "abstract": paper.abstract[:200] + "..." if paper.abstract and len(paper.abstract) > 200 else paper.abstract,
                        "similarity_score": round(similarity, 4),
                        "created_at": paper.created_at.isoformat() if paper.created_at else None
                    })
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "total_found": len(results),
                "similarity_threshold": similarity_threshold,
                "search_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise ServiceError(
                f"Semantic search failed: {str(e)}",
                ErrorCodes.SEARCH_ERROR
            )
    
    @handle_service_errors("find similar papers")
    async def find_similar_papers(
        self,
        paper_id: str,
        limit: int = 5,
        similarity_threshold: float = 0.6
    ) -> Dict[str, Any]:
        """
        Find papers similar to a given paper.
        
        Args:
            paper_id: Reference paper UUID
            limit: Maximum results to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            Similar papers with similarity scores
        """
        # Get the reference paper
        paper = await self.repository.get_paper_by_id(paper_id)
        if not paper:
            raise ServiceError(
                "Paper not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        if not paper.embedding:
            raise ServiceError(
                "Paper has no embedding. Generate embedding first.",
                ErrorCodes.VALIDATION_ERROR
            )
        
        try:
            # Use paper's embedding for similarity search
            similar_papers = await self.repository.search_by_embedding(
                paper.embedding,
                exclude_paper_id=paper_id,
                limit=limit,
                similarity_threshold=similarity_threshold
            )
            
            results = []
            for similar_paper in similar_papers:
                # Calculate similarity score
                paper_embedding = np.array(paper.embedding)
                similar_embedding = np.array(similar_paper.embedding)
                similarity = float(np.dot(paper_embedding, similar_embedding))
                
                if similarity >= similarity_threshold:
                    results.append({
                        "paper_id": str(similar_paper.id),
                        "title": similar_paper.title,
                        "authors": similar_paper.authors,
                        "abstract": similar_paper.abstract[:200] + "..." if similar_paper.abstract and len(similar_paper.abstract) > 200 else similar_paper.abstract,
                        "similarity_score": round(similarity, 4),
                        "created_at": similar_paper.created_at.isoformat() if similar_paper.created_at else None
                    })
            
            return {
                "success": True,
                "reference_paper_id": paper_id,
                "reference_title": paper.title,
                "similar_papers": results,
                "total_found": len(results),
                "similarity_threshold": similarity_threshold
            }
            
        except Exception as e:
            raise ServiceError(
                f"Similar papers search failed: {str(e)}",
                ErrorCodes.SEARCH_ERROR
            )
    
    @handle_service_errors("get paper embedding")
    async def get_paper_embedding(self, paper_id) -> Optional[List[float]]:
        """
        Get embedding vector for a paper.
        
        Args:
            paper_id: Paper UUID (can be string or UUID object)
            
        Returns:
            Embedding vector as list of floats, or None if not found
        """
        try:
            # Handle both string and UUID object inputs
            if isinstance(paper_id, str):
                paper_uuid = uuid.UUID(paper_id)
            elif hasattr(paper_id, 'hex'):  # UUID-like object
                paper_uuid = uuid.UUID(str(paper_id))
            else:
                paper_uuid = paper_id  # Assume it's already a proper UUID
            
            # Get embedding data from repository
            embedding_data = await self.repository.get_embedding_by_paper_id(paper_uuid)
            
            if not embedding_data or not embedding_data.get("embedding"):
                return None
            
            # Parse the embedding vector from string format if necessary
            embedding = embedding_data["embedding"]
            
            # Handle different embedding formats
            if isinstance(embedding, str):
                # Parse string representation of list: "[1.0, 2.0, 3.0]"
                try:
                    # Remove any whitespace and parse as JSON
                    embedding_str = embedding.strip()
                    if embedding_str.startswith('[') and embedding_str.endswith(']'):
                        embedding = json.loads(embedding_str)
                    else:
                        logger.error(f"Invalid embedding format for paper {paper_id}: {embedding_str[:100]}...")
                        return None
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Failed to parse embedding for paper {paper_id}: {str(e)}")
                    return None
            elif hasattr(embedding, 'tolist'):
                # Convert numpy array to list
                embedding = embedding.tolist()
            
            # Ensure we have a list of numbers
            if not isinstance(embedding, list) or not all(isinstance(x, (int, float)) for x in embedding):
                logger.error(f"Embedding is not a list of numbers for paper {paper_id}")
                return None
            
            return embedding
            
        except (ValueError, TypeError) as e:
            # Invalid UUID format
            logger.error(f"Invalid paper ID format {paper_id}: {str(e)}")
            raise ServiceError(
                "Invalid paper ID format",
                ErrorCodes.VALIDATION_ERROR
            )
        except Exception as e:
            logger.error(f"Error getting paper embedding {paper_id}: {str(e)}")
            raise ServiceError(
                f"Failed to get paper embedding: {str(e)}",
                ErrorCodes.PROCESSING_ERROR
            )
    
    @handle_service_errors("get embedding status")
    async def get_embedding_status(self, paper_id: str) -> Dict[str, Any]:
        """
        Get embedding status for a paper.
        
        Args:
            paper_id: Paper UUID
            
        Returns:
            Embedding status information
        """
        paper = await self.repository.get_paper_by_id(paper_id)
        if not paper:
            raise ServiceError(
                "Paper not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        has_embedding = bool(paper.embedding)
        embedding_dimension = len(paper.embedding) if paper.embedding else 0
        
        return {
            "success": True,
            "paper_id": paper_id,
            "has_embedding": has_embedding,
            "embedding_dimension": embedding_dimension,
            "model_name": self.model_name,
            "last_updated": paper.updated_at.isoformat() if paper.updated_at else None
        }
    
    @handle_service_errors("batch generate embeddings")
    async def batch_generate_embeddings(
        self,
        paper_ids: List[str],
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Generate embeddings for multiple papers.
        
        Args:
            paper_ids: List of paper UUIDs
            force_regenerate: Whether to regenerate existing embeddings
            
        Returns:
            Batch processing results
        """
        if not paper_ids:
            raise ServiceError(
                "Paper IDs list is required",
                ErrorCodes.VALIDATION_ERROR
            )
        
        results = {
            "processed": [],
            "skipped": [],
            "failed": []
        }
        
        for paper_id in paper_ids:
            try:
                paper = await self.repository.get_paper_by_id(paper_id)
                if not paper:
                    results["failed"].append({
                        "paper_id": paper_id,
                        "error": "Paper not found"
                    })
                    continue
                
                # Skip if embedding exists and not forcing regeneration
                if paper.embedding and not force_regenerate:
                    results["skipped"].append({
                        "paper_id": paper_id,
                        "reason": "Embedding already exists"
                    })
                    continue
                
                # Prepare text content
                text_content = ""
                if paper.content:
                    text_content = paper.content
                elif paper.abstract:
                    text_content = paper.abstract
                else:
                    results["failed"].append({
                        "paper_id": paper_id,
                        "error": "No text content available"
                    })
                    continue
                
                # Generate embedding
                embedding_result = await self.generate_embedding(
                    paper_id,
                    text_content,
                    metadata={
                        "title": paper.title,
                        "abstract": paper.abstract,
                        "authors": paper.authors
                    }
                )
                
                if embedding_result["success"]:
                    results["processed"].append({
                        "paper_id": paper_id,
                        "embedding_dimension": embedding_result["embedding_dimension"]
                    })
                else:
                    results["failed"].append({
                        "paper_id": paper_id,
                        "error": "Embedding generation failed"
                    })
                    
            except Exception as e:
                results["failed"].append({
                    "paper_id": paper_id,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "summary": {
                "total_papers": len(paper_ids),
                "processed": len(results["processed"]),
                "skipped": len(results["skipped"]),
                "failed": len(results["failed"])
            },
            "results": results,
            "batch_timestamp": datetime.utcnow().isoformat()
        } 
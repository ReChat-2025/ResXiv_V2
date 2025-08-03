"""
Paper Embedding Repository

Database operations for paper embeddings.
Handles CRUD operations for the paper_embeddings table.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, update, delete
from sqlalchemy.exc import IntegrityError

from app.schemas.paper_embedding import PaperEmbeddingCreate, PaperEmbeddingUpdate

logger = logging.getLogger(__name__)


class PaperEmbeddingRepository:
    """Repository for paper embedding database operations"""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session
        
        Args:
            session: Database session
        """
        self.session = session
    
    async def create_embedding(self, embedding_data: PaperEmbeddingCreate) -> uuid.UUID:
        """
        Create a new paper embedding record
        
        Args:
            embedding_data: Embedding data to create
            
        Returns:
            Created embedding ID
        """
        try:
            embedding_id = uuid.uuid4()
            
            await self.session.execute(
                text("""
                    INSERT INTO paper_embeddings (
                        id, paper_id, source_text, model_name, model_version,
                        embedding_metadata, processing_status, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """),
                [
                    str(embedding_id),
                    str(embedding_data.paper_id),
                    embedding_data.source_text,
                    embedding_data.model_name,
                    embedding_data.model_version,
                    embedding_data.embedding_metadata,
                    embedding_data.processing_status,
                    datetime.utcnow(),
                    datetime.utcnow()
                ]
            )
            
            return embedding_id
            
        except IntegrityError as e:
            logger.error(f"Integrity error creating embedding: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating embedding: {str(e)}")
            raise
    
    async def get_embedding_by_paper_id(self, paper_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get embedding by paper ID
        
        Args:
            paper_id: Paper ID
            
        Returns:
            Embedding data if found
        """
        try:
            result = await self.session.execute(
                text("""
                    SELECT id, paper_id, embedding, source_text, model_name, model_version,
                           embedding_metadata, processing_status, error_message,
                           created_at, updated_at
                    FROM paper_embeddings 
                    WHERE paper_id = :paper_id
                """),
                {"paper_id": str(paper_id)}
            )
            
            row = result.fetchone()
            if not row:
                return None
            
            return {
                "id": row.id,
                "paper_id": row.paper_id,
                "embedding": row.embedding,
                "source_text": row.source_text,
                "model_name": row.model_name,
                "model_version": row.model_version,
                "embedding_metadata": row.embedding_metadata,
                "processing_status": row.processing_status,
                "error_message": row.error_message,
                "created_at": row.created_at,
                "updated_at": row.updated_at
            }
            
        except Exception as e:
            logger.error(f"Error getting embedding for paper {paper_id}: {str(e)}")
            raise
    
    async def update_embedding(
        self,
        embedding_id: uuid.UUID,
        update_data: PaperEmbeddingUpdate
    ) -> bool:
        """
        Update embedding record
        
        Args:
            embedding_id: Embedding ID to update
            update_data: Update data
            
        Returns:
            True if update successful
        """
        try:
            # Build dynamic update query
            set_clauses = []
            params = []
            
            if update_data.embedding is not None:
                set_clauses.append("embedding = %s")
                params.append(update_data.embedding)
            
            if update_data.model_version is not None:
                set_clauses.append("model_version = %s")
                params.append(update_data.model_version)
            
            if update_data.embedding_metadata is not None:
                set_clauses.append("embedding_metadata = %s")
                params.append(update_data.embedding_metadata)
            
            if update_data.processing_status is not None:
                set_clauses.append("processing_status = %s")
                params.append(update_data.processing_status)
            
            if update_data.error_message is not None:
                set_clauses.append("error_message = %s")
                params.append(update_data.error_message)
            
            # Always update the timestamp
            set_clauses.append("updated_at = %s")
            params.append(datetime.utcnow())
            
            # Add WHERE clause parameter
            params.append(str(embedding_id))
            
            if not set_clauses:
                return True  # Nothing to update
            
            query = f"""
                UPDATE paper_embeddings 
                SET {', '.join(set_clauses)}
                WHERE id = %s
            """
            
            result = await self.session.execute(text(query), params)
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error updating embedding {embedding_id}: {str(e)}")
            raise
    
    async def delete_embedding(self, paper_id: uuid.UUID) -> bool:
        """
        Delete embedding by paper ID
        
        Args:
            paper_id: Paper ID
            
        Returns:
            True if deletion successful
        """
        try:
            result = await self.session.execute(
                text("DELETE FROM paper_embeddings WHERE paper_id = :paper_id"),
                {"paper_id": str(paper_id)}
            )
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error deleting embedding for paper {paper_id}: {str(e)}")
            raise
    
    async def get_embeddings_by_status(
        self,
        status: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get embeddings by processing status
        
        Args:
            status: Processing status to filter by
            limit: Maximum number of results
            
        Returns:
            List of embedding records
        """
        try:
            result = await self.session.execute(
                text("""
                    SELECT id, paper_id, source_text, model_name, processing_status,
                           error_message, created_at, updated_at
                    FROM paper_embeddings 
                                    WHERE processing_status = :status
                    ORDER BY created_at DESC
                LIMIT :limit
                """),
                {"status": status, "limit": limit}
            )
            
            rows = result.fetchall()
            return [
                {
                    "id": row.id,
                    "paper_id": row.paper_id,
                    "source_text": row.source_text[:200] + "..." if len(row.source_text) > 200 else row.source_text,
                    "model_name": row.model_name,
                    "processing_status": row.processing_status,
                    "error_message": row.error_message,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Error getting embeddings by status {status}: {str(e)}")
            raise
    
    async def get_embedding_stats(self) -> Dict[str, Any]:
        """
        Get embedding statistics
        
        Returns:
            Statistics about embeddings
        """
        try:
            result = await self.session.execute(
                text("""
                    SELECT 
                        processing_status,
                        COUNT(*) as count,
                        AVG(CASE WHEN processing_status = 'completed' THEN 
                            EXTRACT(EPOCH FROM (updated_at - created_at)) 
                        END) as avg_processing_time_seconds
                    FROM paper_embeddings 
                    GROUP BY processing_status
                """)
            )
            
            rows = result.fetchall()
            stats = {
                "total_embeddings": 0,
                "by_status": {},
                "avg_processing_time": None
            }
            
            total_processing_time = 0
            completed_count = 0
            
            for row in rows:
                stats["total_embeddings"] += row.count
                stats["by_status"][row.processing_status] = row.count
                
                if row.processing_status == "completed" and row.avg_processing_time_seconds:
                    total_processing_time += row.avg_processing_time_seconds
                    completed_count += 1
            
            if completed_count > 0:
                stats["avg_processing_time"] = total_processing_time / completed_count
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting embedding stats: {str(e)}")
            raise 

    async def update_paper_embedding(
        self,
        paper_id: uuid.UUID,
        embedding: List[float],
        source_text: str,
        model_name: str = "all-mini-lmv6",
    ) -> None:
        """Create or update embedding vector for a paper (upsert)."""
        try:
            # pgvector expects a string literal like '[0.1,0.2, ...]'
            embedding_str = '[' + ','.join(f"{x:.6f}" for x in embedding) + ']'

            await self.session.execute(
                text("""
                    INSERT INTO paper_embeddings (
                        paper_id, embedding, source_text, model_name, processing_status, created_at, updated_at
                    ) VALUES (
                        :paper_id, :embedding, :source_text, :model_name, 'completed', now(), now()
                    )
                    ON CONFLICT (paper_id)
                    DO UPDATE SET 
                        embedding        = EXCLUDED.embedding,
                        source_text      = EXCLUDED.source_text,
                        model_name       = EXCLUDED.model_name,
                        processing_status = 'completed',
                        updated_at       = now()
                """),
                {
                    "paper_id": str(paper_id),
                    "embedding": embedding_str,
                    "source_text": source_text,
                    "model_name": model_name,
                }
            )
        except Exception as e:
            logger.error(f"Error upserting embedding for paper {paper_id}: {str(e)}")
            raise 
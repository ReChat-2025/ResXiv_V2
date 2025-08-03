"""
Paper Services Module - L6 Engineering Standards
Focused paper services following single responsibility principle.
"""

from .paper_storage_service import PaperStorageService
from .paper_processing_service import PaperProcessingService
from .paper_embedding_service import PaperEmbeddingService
from .paper_crud_service import PaperCrudService
from .paper_service_integrated import PaperService

__all__ = [
    "PaperService",           # Main integrated service
    "PaperStorageService",    # File storage operations
    "PaperProcessingService", # GROBID processing
    "PaperEmbeddingService",  # AI embeddings
    "PaperCrudService"        # Database operations
] 
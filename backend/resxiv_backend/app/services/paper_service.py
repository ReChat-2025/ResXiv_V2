"""
DEPRECATED: Legacy Paper Service - DO NOT USE

This file has been refactored into focused modules following L6 engineering standards:
- app/services/paper/paper_storage_service.py - File upload, storage, and validation
- app/services/paper/paper_processing_service.py - GROBID processing and metadata extraction
- app/services/paper/paper_embedding_service.py - AI embeddings and semantic search
- app/services/paper/paper_crud_service.py - Basic database operations
- app/services/paper/paper_service_integrated.py - Orchestration layer

Please use the new PaperService from app.services.paper.paper_service_integrated

This file will be removed in the next version.
"""

import warnings
from app.services.paper.paper_service_integrated import PaperService as NewPaperService
from app.services.paper.paper_processing_service import PaperProcessingService as _RealProcessingService

warnings.warn(
    "paper_service.py is deprecated. Use app.services.paper.paper_service_integrated.PaperService instead",
    DeprecationWarning,
    stacklevel=2
)

# Compatibility aliases - will be removed
PaperService = NewPaperService
# Keep old import path working for processing service without creating recursion
PaperProcessingService = _RealProcessingService
PaperEmbeddingService = NewPaperService 
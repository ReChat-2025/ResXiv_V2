"""
Services Layer Package

Business logic layer for all application operations.
Clean segregation: one service per data source/functionality.
"""

# Import the refactored user service
from .user.user_service_integrated import UserService as RefactoredUserService
from .user.user_auth_service import UserAuthService
from .user.user_profile_service import UserProfileService
from .user.user_verification_service import UserVerificationService

# Import the old service for gradual migration  
try:
    from .user_service import UserService as LegacyUserService
except ImportError:
    LegacyUserService = None

# Use the refactored service as the default
UserService = RefactoredUserService

# Import the refactored paper service
from .paper.paper_service_integrated import PaperService as RefactoredPaperService
from .paper.paper_storage_service import PaperStorageService
from .paper.paper_processing_service import PaperProcessingService
# from .paper.paper_embedding_service import PaperEmbeddingService  # Disabled for demo
from .paper.paper_crud_service import PaperCrudService

# Import the old service for gradual migration
try:
    from .paper_service import PaperService as LegacyPaperService
except ImportError:
    LegacyPaperService = None

# Use the refactored service as the default
PaperService = RefactoredPaperService
# Compatibility aliases
PaperProcessingService = PaperProcessingService  # type: ignore  # noqa: F811
# PaperEmbeddingService = PaperEmbeddingService  # type: ignore  # noqa: F811  # Disabled for demo

from .email_service import EmailService, get_email_service

# Import the refactored conversation service
from .conversation.conversation_service_integrated import ConversationService as RefactoredConversationService
from .conversation.conversation_crud_service import ConversationCrudService
from .conversation.conversation_access_service import ConversationAccessService
from .conversation.conversation_project_service import ConversationProjectService

# Import the old service for gradual migration
try:
    from .conversation_service import ConversationService as LegacyConversationService
except ImportError:
    LegacyConversationService = None

# Use the refactored service as the default
ConversationService = RefactoredConversationService

# Research Agent Services - Clean segregation by data source
from .research_agent_core import (
    BaseResearchService, SearchQuery, SearchResponse, Paper, Author, Dataset,
    Model, Conference, Grant, DataSource, RateLimitConfig, ResearchServiceError,
    ResearchServiceFactory
)
from .openalex_service import OpenAlexService
from .papers_with_code_service import PapersWithCodeService
from .arxiv_service import ArXivService  # Consolidated arXiv service
from .crossref_service import CrossRefService  # DOI-based service
from .ai_deadlines_service import AIDeadlinesService
from .grant_scraper_service import GrantScraperService
from .research_aggregator_service import ResearchAggregatorService

# Message Services - Refactored Architecture (L6 Standards)
from .message.message_service_integrated import MessageService as RefactoredMessageService
from .message.message_core import MessageCoreService
from .message.message_realtime import MessageRealtimeService
from .message.message_reactions import MessageReactionsService

# Import the old service for gradual migration
try:
    from .message_service import MessageService as LegacyMessageService
except ImportError:
    LegacyMessageService = None

# Use the refactored service as the default
MessageService = RefactoredMessageService

# Register services with the factory
ResearchServiceFactory.register_service(DataSource.OPENALEX, OpenAlexService)
ResearchServiceFactory.register_service(DataSource.PAPERS_WITH_CODE, PapersWithCodeService)
ResearchServiceFactory.register_service(DataSource.ARXIV, ArXivService)
ResearchServiceFactory.register_service(DataSource.CROSSREF, CrossRefService)
ResearchServiceFactory.register_service(DataSource.AI_DEADLINES, AIDeadlinesService)
ResearchServiceFactory.register_service(DataSource.GRANTS_GOV, GrantScraperService)

__all__ = [
    # User Services - New Architecture
    "UserService",           # Points to RefactoredUserService
    "UserAuthService",
    "UserProfileService", 
    "UserVerificationService",
    
    # Paper Services - New Architecture
    "PaperService",          # Points to RefactoredPaperService
    "PaperStorageService",
    "PaperProcessingService", # Now points to RefactoredPaperService
    "PaperEmbeddingService",  # Now points to RefactoredPaperService
    "PaperCrudService",
    
    # Conversation Services - New Architecture
    "ConversationService",   # Points to RefactoredConversationService
    "ConversationCrudService",
    "ConversationAccessService",
    "ConversationProjectService",
    
    # Core Services
    "EmailService",
    "get_email_service",
    
    # Research Agent Core
    "BaseResearchService",
    "SearchQuery",
    "SearchResponse",
    "Paper",
    "Author",
    "Dataset",
    "Model",
    "Conference",
    "Grant",
    "DataSource",
    "RateLimitConfig",
    "ResearchServiceError",
    "ResearchServiceFactory",
    
    # Research Agent Services
    "OpenAlexService",         # Academic papers data source
    "PapersWithCodeService",   # ML papers with code data source
    "ArXivService",            # arXiv preprints data source
    "CrossRefService",         # DOI-based metadata source
    "AIDeadlinesService",      # Conference deadlines data source
    "GrantScraperService",     # Grant opportunities data source
    "ResearchAggregatorService", # Multi-source orchestrator
    
    # Message Services - New Architecture
    "MessageService",  # Points to RefactoredMessageService
    "MessageCoreService",
    "MessageRealtimeService", 
    "MessageReactionsService",
] 
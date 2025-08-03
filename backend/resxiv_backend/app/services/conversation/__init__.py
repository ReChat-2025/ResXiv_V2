"""
Conversation Services Module - L6 Engineering Standards
Focused conversation services following single responsibility principle.
"""

from .conversation_crud_service import ConversationCrudService
from .conversation_access_service import ConversationAccessService
from .conversation_project_service import ConversationProjectService
from .conversation_service_integrated import ConversationService

__all__ = [
    "ConversationService",           # Main integrated service
    "ConversationCrudService",       # Basic CRUD operations
    "ConversationAccessService",     # Access control and participants
    "ConversationProjectService"     # Project-specific operations
] 
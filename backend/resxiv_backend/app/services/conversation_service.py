"""
DEPRECATED: Legacy Conversation Service - DO NOT USE

This file has been refactored into focused modules following L6 engineering standards:
- app/services/conversation/conversation_crud_service.py - Basic CRUD operations
- app/services/conversation/conversation_access_service.py - Access control and participants
- app/services/conversation/conversation_project_service.py - Project-specific operations
- app/services/conversation/conversation_service_integrated.py - Orchestration layer

Please use the new ConversationService from app.services.conversation.conversation_service_integrated

This file will be removed in the next version.
"""

import warnings
from app.services.conversation.conversation_service_integrated import ConversationService as NewConversationService

warnings.warn(
    "conversation_service.py is deprecated. Use app.services.conversation.conversation_service_integrated.ConversationService instead",
    DeprecationWarning,
    stacklevel=2
)

# Compatibility aliases - will be removed
ConversationService = NewConversationService 
"""
DEPRECATED: Legacy Message Service - DO NOT USE

This file has been refactored into focused modules following L6 engineering standards:
- app/services/message/message_core.py - Core CRUD operations
- app/services/message/message_realtime.py - Real-time messaging
- app/services/message/message_reactions.py - Reactions and interactions
- app/services/message/message_service_integrated.py - Orchestration layer

Please use the new MessageService from app.services.message.message_service_integrated

This file will be removed in the next version.
"""

import warnings
from app.services.message.message_service_integrated import MessageService as NewMessageService

warnings.warn(
    "message_service.py is deprecated. Use app.services.message.message_service_integrated.MessageService instead",
    DeprecationWarning,
    stacklevel=2
)

# Compatibility alias - will be removed
MessageService = NewMessageService 
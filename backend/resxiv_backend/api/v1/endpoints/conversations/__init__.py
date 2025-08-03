"""
Conversations Package - L6 Engineering Standards
Split from monolithic conversations.py for better maintainability.
"""

from fastapi import APIRouter
from .conversation_crud import router as conversation_crud_router
from .message_crud import router as message_crud_router
from .conversation_features import router as conversation_features_router

# Create main router that aggregates all conversation-related routes
router = APIRouter()

# Include all sub-routers under unified "Conversations" tag
router.include_router(conversation_crud_router)
router.include_router(message_crud_router)
router.include_router(conversation_features_router)

__all__ = ["router"] 
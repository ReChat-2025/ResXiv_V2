"""
Conversation Service Integrated - L6 Engineering Standards
Orchestrates specialized conversation sub-services with clean separation of concerns.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_handling import handle_service_errors
from app.services.redis_service import RedisService
from app.models.conversation_models import (
    ConversationCreate, ConversationUpdate, ConversationResponse,
    ConversationType
)

from .conversation_crud_service import ConversationCrudService
from .conversation_access_service import ConversationAccessService
from .conversation_project_service import ConversationProjectService

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Integrated conversation service orchestrating specialized sub-services.
    
    Follows Composition over Inheritance principle with clean separation:
    - CRUD service: Basic conversation operations
    - Access service: Permissions and participant management
    - Project service: Project-specific conversation operations
    
    Single point of access for all conversation operations while maintaining
    focused, testable components.
    """
    
    def __init__(self, session: AsyncSession, redis_service: RedisService):
        self.session = session
        self.redis_service = redis_service
        
        # Initialize specialized services
        self.crud_service = ConversationCrudService(session)
        self.access_service = ConversationAccessService(session)
        self.project_service = ConversationProjectService(session)
    
    # ================================
    # CONVERSATION CRUD OPERATIONS
    # ================================
    
    async def create_conversation(
        self,
        conversation_data: ConversationCreate,
        created_by: uuid.UUID
    ) -> Dict[str, Any]:
        """Create new conversation."""
        return await self.crud_service.create_conversation(conversation_data, created_by)
    
    async def get_conversation(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        include_messages: bool = False
    ) -> Dict[str, Any]:
        """Get conversation by ID."""
        return await self.crud_service.get_conversation(conversation_id, user_id, include_messages)
    
    async def get_conversation_details(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        include_messages: bool = False,
        message_limit: int = 50
    ) -> Dict[str, Any]:
        """Get conversation details with optional message history."""
        return await self.crud_service.get_conversation_details(conversation_id, user_id, include_messages, message_limit)
    
    async def update_conversation(
        self,
        conversation_id: uuid.UUID,
        conversation_data: ConversationUpdate,
        updated_by: uuid.UUID
    ) -> Dict[str, Any]:
        """Update conversation information."""
        return await self.crud_service.update_conversation(conversation_id, conversation_data, updated_by)
    
    async def delete_conversation(
        self,
        conversation_id: uuid.UUID,
        deleted_by: uuid.UUID,
        soft_delete: bool = True
    ) -> Dict[str, Any]:
        """Delete conversation."""
        return await self.crud_service.delete_conversation(conversation_id, deleted_by, soft_delete)
    
    async def get_user_conversations(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        conversation_type: Optional[ConversationType] = None
    ) -> Dict[str, Any]:
        """Get conversations for user."""
        return await self.crud_service.get_user_conversations(user_id, page, limit, conversation_type)
    
    async def get_project_conversations(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        conversation_type: Optional[ConversationType] = None
    ) -> Dict[str, Any]:
        """Get conversations for a project with pagination and filtering."""
        return await self.crud_service.get_project_conversations(project_id, user_id, page, limit, conversation_type)
    
    async def start_pdf_conversation(
        self,
        user_id: uuid.UUID,
        paper_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Create or retrieve a private PDF chat for a paper."""
        conv = await self.crud_service.conversation_repo.get_or_create_pdf_conversation(user_id, paper_id)
        # Ensure the requester is participant (for completeness)
        await self.access_service.add_participant(conv.id, user_id, user_id, role="owner")
        return {
            "success": True,
            "conversation_id": str(conv.id),
            "paper_id": str(paper_id)
        }
    
    # ================================
    # ACCESS AND PARTICIPANT MANAGEMENT
    # ================================
    
    async def get_conversation_participants(
        self,
        conversation_id: uuid.UUID,
        requesting_user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get conversation participants."""
        return await self.access_service.get_conversation_participants(conversation_id, requesting_user_id)
    
    async def add_participant(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        added_by: uuid.UUID,
        role: str = "member"
    ) -> Dict[str, Any]:
        """Add participant to conversation."""
        return await self.access_service.add_participant(conversation_id, user_id, added_by, role)
    
    async def remove_participant(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        removed_by: uuid.UUID
    ) -> Dict[str, Any]:
        """Remove participant from conversation."""
        return await self.access_service.remove_participant(conversation_id, user_id, removed_by)
    
    async def check_conversation_access(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """Check conversation access."""
        return await self.access_service.check_conversation_access(conversation_id, user_id)
    
    async def get_user_access_info(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get user access information."""
        return await self.access_service.get_user_access_info(conversation_id, user_id)
    
    async def update_participant_role(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        new_role: str,
        updated_by: uuid.UUID
    ) -> Dict[str, Any]:
        """Update participant role."""
        return await self.access_service.update_participant_role(conversation_id, user_id, new_role, updated_by)
    
    # ================================
    # PROJECT-SPECIFIC OPERATIONS
    # ================================
    
    async def get_or_create_project_conversation(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get or create project conversation."""
        return await self.project_service.get_or_create_project_conversation(project_id, user_id, title)
    
    async def get_project_conversations(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
        conversation_type: Optional[ConversationType] = None
    ) -> Dict[str, Any]:
        """Get conversations for a project with pagination and filtering."""
        return await self.crud_service.get_project_conversations(project_id, user_id, page, limit, conversation_type)
    
    async def create_project_thread(
        self,
        project_id: uuid.UUID,
        title: str,
        description: Optional[str],
        created_by: uuid.UUID,
        parent_conversation_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Create project thread."""
        return await self.project_service.create_project_thread(
            project_id, title, description, created_by, parent_conversation_id
        )
    
    async def archive_project_conversation(
        self,
        conversation_id: uuid.UUID,
        project_id: uuid.UUID,
        archived_by: uuid.UUID
    ) -> Dict[str, Any]:
        """Archive project conversation."""
        return await self.project_service.archive_project_conversation(conversation_id, project_id, archived_by)
    
    async def sync_project_members_to_conversation(
        self,
        project_id: uuid.UUID,
        conversation_id: uuid.UUID,
        synced_by: uuid.UUID
    ) -> Dict[str, Any]:
        """Sync project members to conversation."""
        return await self.project_service.sync_project_members_to_conversation(project_id, conversation_id, synced_by)
    
    # ================================
    # STATISTICS AND ANALYTICS
    # ================================
    
    async def get_conversation_stats(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get conversation statistics.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User requesting stats
            
        Returns:
            Conversation statistics
        """
        # Verify access
        has_access = await self.access_service.check_conversation_access(conversation_id, user_id)
        if not has_access:
            return {
                "success": False,
                "error": "Access denied to conversation",
                "error_code": "ACCESS_DENIED"
            }
        
        # Get comprehensive stats from CRUD service
        metadata_result = await self.crud_service.get_conversation_metadata(conversation_id)
        if not metadata_result["success"]:
            return metadata_result
        
        # Add real-time stats from Redis if available
        try:
            redis_stats = await self._get_realtime_stats(conversation_id)
            metadata_result["metadata"]["realtime"] = redis_stats
        except Exception as e:
            logger.warning(f"Failed to get realtime stats for conversation {conversation_id}: {e}")
            metadata_result["metadata"]["realtime"] = {"online_participants": 0, "active_sessions": 0}
        
        return metadata_result
    
    async def get_project_conversation_stats(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get project conversation stats."""
        return await self.project_service.get_project_conversation_stats(project_id, user_id)
    
    # ================================
    # REAL-TIME INTEGRATION
    # ================================
    
    async def _get_realtime_stats(self, conversation_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get real-time statistics from Redis.
        
        Args:
            conversation_id: Conversation UUID
            
        Returns:
            Real-time statistics
        """
        try:
            # Get online participants count
            online_key = f"conversation:{conversation_id}:online"
            online_count = await self.redis_service.scard(online_key)
            
            # Get active sessions count
            sessions_key = f"conversation:{conversation_id}:sessions"
            active_sessions = await self.redis_service.hlen(sessions_key)
            
            return {
                "online_participants": online_count or 0,
                "active_sessions": active_sessions or 0
            }
        except Exception as e:
            logger.warning(f"Failed to get realtime stats: {e}")
            return {"online_participants": 0, "active_sessions": 0}
    
    @handle_service_errors("conversation service health check")
    async def health_check(self) -> Dict[str, Any]:
        """Service health check."""
        try:
            # Test database connectivity
            await self.session.execute("SELECT 1")
            
            # Test Redis connectivity
            redis_healthy = False
            try:
                await self.redis_service.ping()
                redis_healthy = True
            except Exception:
                pass
            
            return {
                "success": True,
                "status": "healthy",
                "services": {
                    "crud": "healthy",
                    "access": "healthy",
                    "project": "healthy",
                    "redis": "healthy" if redis_healthy else "degraded"
                }
            }
        except Exception as e:
            logger.error(f"Conversation service health check failed: {e}")
            return {
                "success": False,
                "status": "unhealthy",
                "error": str(e)
            }

 
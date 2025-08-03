"""
Conversation Project Service - L6 Engineering Standards
Focused on project-specific conversation operations and management.
"""

import uuid
import logging
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.project_repository import ProjectRepository
from app.models.conversation_models import (
    ConversationCreate, ConversationResponse, ConversationType
)

logger = logging.getLogger(__name__)


class ConversationProjectService:
    """
    Project service for conversation-project integration.
    Single Responsibility: Project-specific conversation management.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.conversation_repo = ConversationRepository(session)
        self.project_repo = ProjectRepository(session)
    
    @handle_service_errors("get or create project conversation")
    async def get_or_create_project_conversation(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get existing project conversation or create one if it doesn't exist.
        
        Args:
            project_id: Project UUID
            user_id: User requesting/creating the conversation
            title: Optional custom title for the conversation
            
        Returns:
            Project conversation data
        """
        try:
            # Verify project exists and user has access
            project = await self.project_repo.get_project_by_id(project_id)
            if not project:
                raise ServiceError(
                    "Project not found",
                    ErrorCodes.NOT_FOUND_ERROR
                )
            
            is_member = await self.project_repo.is_user_member(project_id, user_id)
            if not is_member:
                raise ServiceError(
                    "User is not a member of this project",
                    ErrorCodes.AUTHORIZATION_ERROR
                )
            
            # Check if project conversation already exists
            existing_conversation = await self.conversation_repo.get_project_conversation(project_id)
            
            if existing_conversation:
                return {
                    "success": True,
                    "conversation": ConversationResponse.from_orm(existing_conversation),
                    "created": False,
                    "message": "Retrieved existing project conversation"
                }
            
            # Create new project conversation
            conversation_title = title or f"{project.name} Discussion"
            
            conversation = await self.conversation_repo.create(
                type=ConversationType.GROUP,
                entity=project_id,
                is_group=True,
                created_by=user_id
            )
            
            await self.session.commit()
            
            return {
                "success": True,
                "conversation": ConversationResponse.from_orm(conversation),
                "created": True,
                "message": "Created new project conversation"
            }
            
        except Exception as e:
            await self.session.rollback()
            raise ServiceError(
                f"Failed to get or create project conversation: {str(e)}",
                ErrorCodes.CREATION_ERROR
            )
    
    @handle_service_errors("get project conversations")
    async def get_project_conversations(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        include_archived: bool = False
    ) -> Dict[str, Any]:
        """
        Get all conversations for a project.
        
        Args:
            project_id: Project UUID
            user_id: User requesting the conversations
            include_archived: Whether to include archived conversations
            
        Returns:
            List of project conversations
        """
        # Verify project access
        is_member = await self.project_repo.is_user_member(project_id, user_id)
        if not is_member:
            raise ServiceError(
                "User is not a member of this project",
                ErrorCodes.AUTHORIZATION_ERROR
            )
        
        conversations = await self.conversation_repo.list_project_group_conversations(project_id)
        
        return {
            "success": True,
            "conversations": [ConversationResponse.from_orm(conv) for conv in conversations],
            "total_count": len(conversations),
            "project_id": str(project_id)
        }
    
    @handle_service_errors("create project thread")
    async def create_project_thread(
        self,
        project_id: uuid.UUID,
        title: str,
        description: Optional[str],
        created_by: uuid.UUID,
        parent_conversation_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Create a specialized thread/topic within a project.
        
        Args:
            project_id: Project UUID
            title: Thread title
            description: Thread description
            created_by: User creating the thread
            parent_conversation_id: Optional parent conversation
            
        Returns:
            Created thread conversation
        """
        try:
            # Verify project access
            is_member = await self.project_repo.is_user_member(project_id, created_by)
            if not is_member:
                raise ServiceError(
                    "User is not a member of this project",
                    ErrorCodes.AUTHORIZATION_ERROR
                )
            
            # Create thread conversation
            conversation = await self.conversation_repo.create(
                type=ConversationType.GROUP,
                entity=project_id,
                title=title,
                description=description,
                created_by=created_by,
                parent_id=parent_conversation_id
            )
            
            await self.session.commit()
            
            return {
                "success": True,
                "conversation": ConversationResponse.from_orm(conversation),
                "message": "Project thread created successfully"
            }
            
        except Exception as e:
            await self.session.rollback()
            raise ServiceError(
                f"Failed to create project thread: {str(e)}",
                ErrorCodes.CREATION_ERROR
            )
    
    @handle_service_errors("archive project conversation")
    async def archive_project_conversation(
        self,
        conversation_id: uuid.UUID,
        project_id: uuid.UUID,
        archived_by: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Archive a project conversation.
        
        Args:
            conversation_id: Conversation UUID
            project_id: Project UUID
            archived_by: User archiving the conversation
            
        Returns:
            Archive result
        """
        try:
            # Verify permissions
            is_admin = await self.project_repo.is_user_admin(project_id, archived_by)
            if not is_admin:
                # Check if user is conversation creator
                conversation = await self.conversation_repo.get_conversation_by_id(conversation_id)
                if not conversation or conversation.created_by != archived_by:
                    raise ServiceError(
                        "Insufficient permissions to archive conversation",
                        ErrorCodes.AUTHORIZATION_ERROR
                    )
            
            # Archive conversation
            await self.conversation_repo.archive_conversation(conversation_id, archived_by)
            
            await self.session.commit()
            
            return {
                "success": True,
                "message": "Conversation archived successfully"
            }
            
        except Exception as e:
            await self.session.rollback()
            raise ServiceError(
                f"Failed to archive conversation: {str(e)}",
                ErrorCodes.UPDATE_ERROR
            )
    
    @handle_service_errors("get project conversation stats")
    async def get_project_conversation_stats(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get conversation statistics for a project.
        
        Args:
            project_id: Project UUID
            user_id: User requesting the stats
            
        Returns:
            Project conversation statistics
        """
        # Verify project access
        is_member = await self.project_repo.is_user_member(project_id, user_id)
        if not is_member:
            raise ServiceError(
                "User is not a member of this project",
                ErrorCodes.AUTHORIZATION_ERROR
            )
        
        stats = await self.conversation_repo.get_project_conversation_stats(project_id)
        
        return {
            "success": True,
            "project_id": str(project_id),
            "statistics": stats
        }
    
    @handle_service_errors("sync project members to conversation")
    async def sync_project_members_to_conversation(
        self,
        project_id: uuid.UUID,
        conversation_id: uuid.UUID,
        synced_by: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Sync project members to the project conversation.
        
        Args:
            project_id: Project UUID
            conversation_id: Conversation UUID
            synced_by: User performing the sync
            
        Returns:
            Sync result
        """
        try:
            # Verify permissions
            is_admin = await self.project_repo.is_user_admin(project_id, synced_by)
            if not is_admin:
                raise ServiceError(
                    "Only project admins can sync members to conversations",
                    ErrorCodes.AUTHORIZATION_ERROR
                )
            
            # Get project members
            project_members = await self.project_repo.get_project_members(project_id)
            
            # Get current conversation participants
            current_participants = await self.conversation_repo.get_conversation_participants(conversation_id)
            current_participant_ids = {p["user_id"] for p in current_participants}
            
            added_count = 0
            skipped_count = 0
            
            # Add missing project members to conversation
            for member in project_members:
                if member["user_id"] not in current_participant_ids:
                    await self.conversation_repo.add_participant(
                        conversation_id=conversation_id,
                        user_id=member["user_id"],
                        role="member",
                        added_by=synced_by
                    )
                    added_count += 1
                else:
                    skipped_count += 1
            
            await self.session.commit()
            
            return {
                "success": True,
                "message": "Project members synced to conversation",
                "added_count": added_count,
                "skipped_count": skipped_count,
                "total_members": len(project_members)
            }
            
        except Exception as e:
            await self.session.rollback()
            raise ServiceError(
                f"Failed to sync project members to conversation: {str(e)}",
                ErrorCodes.UPDATE_ERROR
            ) 
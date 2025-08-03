"""
Conversation Access Service - L6 Engineering Standards
Focused on access control, permissions, and participant management.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.project_repository import ProjectRepository
from app.models.conversation_models import ConversationType

logger = logging.getLogger(__name__)


class ConversationAccessService:
    """
    Access service for conversation permissions and participants.
    Single Responsibility: Access control and participant management.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.conversation_repo = ConversationRepository(session)
        self.project_repo = ProjectRepository(session)
    
    @handle_service_errors("get conversation participants")
    async def get_conversation_participants(
        self,
        conversation_id: uuid.UUID,
        requesting_user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get participants of a conversation.
        
        Args:
            conversation_id: Conversation UUID
            requesting_user_id: User requesting the participants
            
        Returns:
            List of participants with their roles
        """
        # Check if conversation exists
        conversation = await self.conversation_repo.get_conversation_by_id(conversation_id)
        if not conversation:
            raise ServiceError(
                "Conversation not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        # Check access permissions
        has_access = await self.check_conversation_access(conversation_id, requesting_user_id)
        if not has_access:
            raise ServiceError(
                "Access denied to conversation",
                ErrorCodes.AUTHORIZATION_ERROR
            )
        
        participants = await self.conversation_repo.get_conversation_participants(conversation_id)
        
        return {
            "success": True,
            "participants": participants,
            "total_count": len(participants)
        }
    
    @handle_service_errors("add conversation participant")
    async def add_participant(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        added_by: uuid.UUID,
        role: str = "member"
    ) -> Dict[str, Any]:
        """
        Add a participant to a conversation.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User to add as participant
            added_by: User adding the participant
            role: Role of the participant
            
        Returns:
            Success result
        """
        try:
            # Check if conversation exists
            conversation = await self.conversation_repo.get_conversation_by_id(conversation_id)
            if not conversation:
                raise ServiceError(
                    "Conversation not found",
                    ErrorCodes.NOT_FOUND_ERROR
                )
            
            # Check permissions to add participants
            can_add = await self._can_manage_participants(conversation_id, added_by)
            if not can_add:
                raise ServiceError(
                    "Insufficient permissions to add participants",
                    ErrorCodes.AUTHORIZATION_ERROR
                )
            
            # Check if user is already a participant
            is_participant = await self.conversation_repo.is_user_participant(conversation_id, user_id)
            if is_participant:
                return {
                    "success": False,
                    "error": "User is already a participant",
                    "error_code": "ALREADY_PARTICIPANT"
                }
            
            # Add participant
            await self.conversation_repo.add_participant(
                conversation_id=conversation_id,
                user_id=user_id,
                role=role,
                added_by=added_by
            )
            
            await self.session.commit()
            
            return {
                "success": True,
                "message": "Participant added successfully"
            }
            
        except Exception as e:
            await self.session.rollback()
            raise ServiceError(
                f"Failed to add participant: {str(e)}",
                ErrorCodes.UPDATE_ERROR
            )
    
    @handle_service_errors("remove conversation participant")
    async def remove_participant(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        removed_by: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Remove a participant from a conversation.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User to remove
            removed_by: User removing the participant
            
        Returns:
            Success result
        """
        try:
            # Check if conversation exists
            conversation = await self.conversation_repo.get_conversation_by_id(conversation_id)
            if not conversation:
                raise ServiceError(
                    "Conversation not found",
                    ErrorCodes.NOT_FOUND_ERROR
                )
            
            # Check permissions
            can_remove = await self._can_manage_participants(conversation_id, removed_by)
            if not can_remove and user_id != removed_by:  # Users can remove themselves
                raise ServiceError(
                    "Insufficient permissions to remove participants",
                    ErrorCodes.AUTHORIZATION_ERROR
                )
            
            # Check if user is a participant
            is_participant = await self.conversation_repo.is_user_participant(conversation_id, user_id)
            if not is_participant:
                return {
                    "success": False,
                    "error": "User is not a participant",
                    "error_code": "NOT_PARTICIPANT"
                }
            
            # Remove participant
            await self.conversation_repo.remove_participant(conversation_id, user_id)
            
            await self.session.commit()
            
            return {
                "success": True,
                "message": "Participant removed successfully"
            }
            
        except Exception as e:
            await self.session.rollback()
            raise ServiceError(
                f"Failed to remove participant: {str(e)}",
                ErrorCodes.UPDATE_ERROR
            )
    
    @handle_service_errors("check conversation access")
    async def check_conversation_access(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """
        Check if user has access to conversation.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User UUID
            
        Returns:
            True if user has access, False otherwise
        """
        # Get conversation details
        conversation = await self.conversation_repo.get_conversation_by_id(conversation_id)
        if not conversation:
            return False
        
        # Check based on conversation type
        if conversation.type == ConversationType.AI.value:
            # For AI conversations, check if user is a participant
            return await self.conversation_repo.is_user_participant(conversation_id, user_id)
        
        elif conversation.type == ConversationType.GROUP.value:
            if conversation.entity:
                # For project conversations, check project membership
                return await self.project_repo.is_user_member(conversation.entity, user_id)
            else:
                # For general group conversations, check if user is a participant
                return await self.conversation_repo.is_user_participant(conversation_id, user_id)
        
        elif conversation.type in [ConversationType.PDF.value, ConversationType.DROP.value, ConversationType.AGENTIC.value]:
            # For PDF, DROP, and AGENTIC conversations, check project membership
            if conversation.entity:
                return await self.project_repo.is_user_member(conversation.entity, user_id)
            else:
                # Fallback: check if user created the conversation
                return conversation.created_by == user_id
        
        return False
    
    @handle_service_errors("get user conversation access")
    async def get_user_access_info(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get detailed access information for a user in a conversation.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User UUID
            
        Returns:
            Detailed access information
        """
        # Check if conversation exists
        conversation = await self.conversation_repo.get_conversation_by_id(conversation_id)
        if not conversation:
            raise ServiceError(
                "Conversation not found",
                ErrorCodes.NOT_FOUND_ERROR
            )
        
        # Get user's role and permissions
        is_participant = await self.conversation_repo.is_user_participant(conversation_id, user_id)
        participant_role = None
        
        if is_participant:
            participant_info = await self.conversation_repo.get_participant_info(conversation_id, user_id)
            participant_role = participant_info.get("role") if participant_info else None
        
        # Check various permissions
        can_read = await self.check_conversation_access(conversation_id, user_id)
        can_write = can_read and is_participant
        can_manage_participants = await self._can_manage_participants(conversation_id, user_id)
        can_delete = (conversation.created_by == user_id)
        
        # For project conversations, check project-level permissions
        project_role = None
        if conversation.type == ConversationType.GROUP.value and conversation.entity:
            is_project_member = await self.project_repo.is_user_member(conversation.entity, user_id)
            if is_project_member:
                project_info = await self.project_repo.get_user_project_role(conversation.entity, user_id)
                project_role = project_info.get("role") if project_info else None
                
                # Project admins can manage participants
                if project_role in ["admin", "owner"]:
                    can_manage_participants = True
        
        access_info = {
            "conversation_id": str(conversation_id),
            "user_id": str(user_id),
            "access_level": {
                "can_read": can_read,
                "can_write": can_write,
                "can_manage_participants": can_manage_participants,
                "can_delete": can_delete
            },
            "participation": {
                "is_participant": is_participant,
                "participant_role": participant_role,
                "joined_at": None  # Would need to track this in participant table
            },
            "project_context": {
                "is_project_conversation": conversation.type == ConversationType.GROUP.value and bool(conversation.entity),
                "project_id": str(conversation.entity) if conversation.entity else None,
                "project_role": project_role
            }
        }
        
        return {
            "success": True,
            "access_info": access_info
        }
    
    async def _can_manage_participants(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """
        Check if user can manage participants in conversation.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User UUID
            
        Returns:
            True if user can manage participants
        """
        # Get conversation
        conversation = await self.conversation_repo.get_conversation_by_id(conversation_id)
        if not conversation:
            return False
        
        # Conversation creator can always manage participants
        if conversation.created_by == user_id:
            return True
        
        # For project conversations, project admins can manage participants
        if conversation.type == ConversationType.GROUP.value and conversation.entity:
            is_admin = await self.project_repo.is_user_admin(conversation.entity, user_id)
            if is_admin:
                return True
        
        # Check if user has admin role in conversation
        participant_info = await self.conversation_repo.get_participant_info(conversation_id, user_id)
        if participant_info and participant_info.get("role") == "admin":
            return True
        
        return False
    
    @handle_service_errors("update participant role")
    async def update_participant_role(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        new_role: str,
        updated_by: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Update a participant's role in a conversation.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User whose role to update
            new_role: New role to assign
            updated_by: User making the change
            
        Returns:
            Success result
        """
        try:
            # Check permissions
            can_manage = await self._can_manage_participants(conversation_id, updated_by)
            if not can_manage:
                raise ServiceError(
                    "Insufficient permissions to update participant roles",
                    ErrorCodes.AUTHORIZATION_ERROR
                )
            
            # Check if user is a participant
            is_participant = await self.conversation_repo.is_user_participant(conversation_id, user_id)
            if not is_participant:
                raise ServiceError(
                    "User is not a participant in this conversation",
                    ErrorCodes.NOT_FOUND_ERROR
                )
            
            # Update role
            await self.conversation_repo.update_participant_role(
                conversation_id=conversation_id,
                user_id=user_id,
                role=new_role
            )
            
            await self.session.commit()
            
            return {
                "success": True,
                "message": f"Participant role updated to {new_role}"
            }
            
        except Exception as e:
            await self.session.rollback()
            raise ServiceError(
                f"Failed to update participant role: {str(e)}",
                ErrorCodes.UPDATE_ERROR
            ) 
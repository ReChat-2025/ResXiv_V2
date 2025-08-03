"""
Conversation Repository

This module handles all database operations for conversations in PostgreSQL.
Provides CRUD operations and conversation-specific queries.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.schemas.conversation import Conversation
from app.schemas.project import Project, ProjectMember
from app.schemas.user import User
from app.models.conversation_models import ConversationType


class ConversationRepository:
    """
    Repository for conversation database operations.
    
    Handles:
    - CRUD operations for conversations
    - Project conversation management
    - Conversation membership queries
    - Access control verification
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ================================
    # BASIC CRUD OPERATIONS
    # ================================
    
    async def create(
        self,
        type: ConversationType,
        entity: Optional[uuid.UUID] = None,
        is_group: bool = True,
        created_by: Optional[uuid.UUID] = None,
        group_key_encrypted: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            type: Conversation type (GROUP, AI, PDF, etc.)
            entity: Related entity ID (project_id, paper_id, etc.)
            is_group: Whether this is a group conversation
            created_by: User who created the conversation
            group_key_encrypted: Encrypted group key for security
            
        Returns:
            Created conversation object
        """
        conversation = Conversation(
            type=type.value,
            entity=entity,
            is_group=is_group,
            created_by=created_by,
            group_key_encrypted=group_key_encrypted
        )
        
        self.session.add(conversation)
        await self.session.flush()  # Get ID without committing
        await self.session.refresh(conversation)
        
        return conversation
    
    async def get_by_id(self, conversation_id: uuid.UUID) -> Optional[Conversation]:
        """
        Get conversation by ID.
        
        Args:
            conversation_id: Conversation UUID
            
        Returns:
            Conversation object or None if not found
        """
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_conversation_by_id(self, conversation_id: uuid.UUID) -> Optional[Conversation]:
        """
        Get conversation by ID (alias for get_by_id for backward compatibility).
        
        Args:
            conversation_id: Conversation UUID
            
        Returns:
            Conversation object or None if not found
        """
        return await self.get_by_id(conversation_id)
    
    async def get_by_id_with_creator(self, conversation_id: uuid.UUID) -> Optional[Conversation]:
        """
        Get conversation by ID with creator information.
        
        Args:
            conversation_id: Conversation UUID
            
        Returns:
            Conversation object with creator loaded
        """
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.creator))
            .where(Conversation.id == conversation_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update(
        self,
        conversation_id: uuid.UUID,
        **updates
    ) -> Optional[Conversation]:
        """
        Update conversation.
        
        Args:
            conversation_id: Conversation UUID
            **updates: Fields to update
            
        Returns:
            Updated conversation object or None if not found
        """
        if not updates:
            return await self.get_by_id(conversation_id)
        
        # Add updated timestamp
        updates['updated_at'] = datetime.utcnow()
        
        stmt = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(**updates)
            .returning(Conversation)
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def delete(self, conversation_id: uuid.UUID) -> bool:
        """
        Delete conversation.
        
        Args:
            conversation_id: Conversation UUID
            
        Returns:
            True if deleted, False if not found
        """
        stmt = delete(Conversation).where(Conversation.id == conversation_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    # ================================
    # PROJECT CONVERSATION MANAGEMENT
    # ================================
    
    async def get_project_conversation(self, project_id: uuid.UUID) -> Optional[Conversation]:
        """
        Get the main conversation for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Project's conversation or None if not found
        """
        stmt = (
            select(Conversation)
            .where(
                and_(
                    Conversation.type == ConversationType.GROUP.value,
                    Conversation.entity == project_id
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_project_conversation(
        self,
        project_id: uuid.UUID,
        created_by: uuid.UUID
    ) -> Conversation:
        """
        Create a new conversation for a project.
        
        Args:
            project_id: Project UUID
            created_by: User who created the conversation
            
        Returns:
            Created conversation
        """
        return await self.create(
            type=ConversationType.GROUP,
            entity=project_id,
            is_group=True,
            created_by=created_by
        )
    
    async def get_or_create_project_conversation(
        self,
        project_id: uuid.UUID,
        created_by: uuid.UUID
    ) -> Conversation:
        """
        Get existing project conversation or create new one.
        
        Args:
            project_id: Project UUID
            created_by: User who would create the conversation if needed
            
        Returns:
            Project conversation
        """
        conversation = await self.get_project_conversation(project_id)
        
        if not conversation:
            conversation = await self.create_project_conversation(project_id, created_by)
        
        return conversation
    
    # ================================
    # USER CONVERSATION QUERIES
    # ================================
    
    async def get_user_conversations(
        self,
        user_id: uuid.UUID,
        conversation_type: Optional[ConversationType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Conversation]:
        """
        Get conversations accessible to a user.
        
        This includes:
        - Conversations they created
        - Group conversations for projects they're members of
        
        Args:
            user_id: User UUID
            conversation_type: Filter by conversation type
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of conversations
        """
        # Build base query
        stmt = select(Conversation)
        
        # Add type filter if specified
        if conversation_type:
            stmt = stmt.where(Conversation.type == conversation_type.value)
        
        # Get conversations user has access to
        access_conditions = []
        
        # 1. Conversations user created
        access_conditions.append(Conversation.created_by == user_id)
        
        # 2. Group conversations for projects user is member of
        project_conversation_subquery = (
            select(Conversation.id)
            .select_from(
                Conversation.__table__.join(ProjectMember.__table__, Conversation.entity == ProjectMember.project_id)
            )
            .where(
                and_(
                    Conversation.type == ConversationType.GROUP.value,
                    ProjectMember.user_id == user_id
                )
            )
        )
        access_conditions.append(Conversation.id.in_(project_conversation_subquery))
        
        # Combine access conditions with OR
        stmt = stmt.where(or_(*access_conditions))
        
        # Order by most recent activity
        stmt = stmt.order_by(desc(Conversation.updated_at))
        
        # Add pagination
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def count_user_conversations(
        self,
        user_id: uuid.UUID,
        conversation_type: Optional[ConversationType] = None
    ) -> int:
        """
        Count conversations accessible to a user.
        
        Args:
            user_id: User UUID
            conversation_type: Filter by conversation type
            
        Returns:
            Number of accessible conversations
        """
        # Build base query
        stmt = select(func.count(Conversation.id))
        
        # Add type filter if specified
        if conversation_type:
            stmt = stmt.where(Conversation.type == conversation_type.value)
        
        # Get conversations user has access to
        access_conditions = []
        
        # 1. Conversations user created
        access_conditions.append(Conversation.created_by == user_id)
        
        # 2. Group conversations for projects user is member of
        project_conversation_subquery = (
            select(Conversation.id)
            .select_from(
                Conversation.__table__.join(ProjectMember.__table__, Conversation.entity == ProjectMember.project_id)
            )
            .where(
                and_(
                    Conversation.type == ConversationType.GROUP.value,
                    ProjectMember.user_id == user_id
                )
            )
        )
        access_conditions.append(Conversation.id.in_(project_conversation_subquery))
        
        # Combine access conditions with OR
        stmt = stmt.where(or_(*access_conditions))
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    # ================================
    # CONVERSATION PARTICIPANTS
    # ================================
    
    async def get_conversation_participants(self, conversation_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Get participants in a conversation based on conversation type.
        
        For GROUP conversations, returns project members.
        For other types, returns creator only.
        
        Args:
            conversation_id: Conversation UUID
            
        Returns:
            List of participant info dictionaries
        """
        conversation = await self.get_by_id(conversation_id)
        if not conversation:
            return []
        
        if conversation.type == ConversationType.GROUP.value and conversation.entity:
            # Get project members
            stmt = (
                select(User.id, User.name, User.email, ProjectMember.role)
                .select_from(
                    User
                    .join(ProjectMember, User.id == ProjectMember.user_id)
                )
                .where(ProjectMember.project_id == conversation.entity)
            )
            result = await self.session.execute(stmt)
            
            participants = []
            for row in result:
                participants.append({
                    "user_id": row.id,
                    "name": row.name,
                    "email": row.email,
                    "role": row.role
                })
            
            return participants
        
        elif conversation.created_by:
            # Get creator only
            stmt = select(User).where(User.id == conversation.created_by)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                return [{
                    "user_id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "role": "owner"
                }]
        
        return []
    
    async def get_conversation_participant_ids(self, conversation_id: uuid.UUID) -> List[uuid.UUID]:
        """
        Get participant user IDs for a conversation.
        
        Args:
            conversation_id: Conversation UUID
            
        Returns:
            List of participant user IDs
        """
        participants = await self.get_conversation_participants(conversation_id)
        return [p["user_id"] for p in participants]
    
    # ================================
    # ACCESS CONTROL
    # ================================
    
    async def can_user_access_conversation(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """
        Check if user can access a conversation.
        
        Args:
            conversation_id: Conversation UUID
            user_id: User UUID
            
        Returns:
            True if user has access, False otherwise
        """
        conversation = await self.get_by_id(conversation_id)
        if not conversation:
            return False
        
        # Use same logic as CRUD service that works
        # Check based on conversation type
        if conversation.type == ConversationType.AI.value:
            # For AI conversations, check if user is a participant
            return await self.is_user_participant(conversation_id, user_id)
        
        elif conversation.type == ConversationType.GROUP.value:
            if conversation.entity:
                # For project conversations, check project membership
                from app.repositories.project_repository import ProjectRepository
                project_repo = ProjectRepository(self.session)
                return await project_repo.is_user_member(conversation.entity, user_id)
            else:
                # For general group conversations, check if user is a participant
                return await self.is_user_participant(conversation_id, user_id)
        
        elif conversation.type in [ConversationType.PDF.value, ConversationType.DROP.value, ConversationType.AGENTIC.value]:
            # For PDF, DROP, and AGENTIC conversations, check project membership
            if conversation.entity:
                from app.repositories.project_repository import ProjectRepository
                project_repo = ProjectRepository(self.session)
                return await project_repo.is_user_member(conversation.entity, user_id)
            else:
                # Fallback: check if user created the conversation
                return conversation.created_by == user_id
        
        return False 

    async def get_user_pdf_conversation(
        self,
        user_id: uuid.UUID,
        paper_id: uuid.UUID
    ) -> Optional[Conversation]:
        """Return user's private PDF conversation for a paper if exists"""
        stmt = (
            select(Conversation)
            .where(
                and_(
                    Conversation.type == ConversationType.PDF.value,
                    Conversation.entity == paper_id,
                    Conversation.created_by == user_id,
                    Conversation.is_group == False
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_pdf_conversation(
        self,
        user_id: uuid.UUID,
        paper_id: uuid.UUID
    ) -> Conversation:
        """Create a new private PDF conversation bound to a paper."""
        return await self.create(
            type=ConversationType.PDF,
            entity=paper_id,
            is_group=False,
            created_by=user_id
        )
    
    async def get_or_create_pdf_conversation(
        self,
        user_id: uuid.UUID,
        paper_id: uuid.UUID
    ) -> Conversation:
        conv = await self.get_user_pdf_conversation(user_id, paper_id)
        if conv:
            return conv
        return await self.create_pdf_conversation(user_id, paper_id) 

    async def list_project_group_conversations(self, project_id: uuid.UUID) -> List[Conversation]:
        """Return all group conversations for a given project ordered by creation date."""
        stmt = (
            select(Conversation)
            .where(
                and_(
                    Conversation.entity == project_id,
                    Conversation.type == ConversationType.GROUP.value
                )
            )
            .order_by(Conversation.created_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_project_conversations(
        self,
        project_id: uuid.UUID,
        conversation_type: Optional[ConversationType] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Conversation]:
        """
        Get conversations for a project with filtering and pagination.
        
        Args:
            project_id: Project UUID
            conversation_type: Filter by conversation type (optional)
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of conversations
        """
        # Build base query for project conversations
        stmt = select(Conversation).where(Conversation.entity == project_id)
        
        # Add type filter if specified
        if conversation_type:
            stmt = stmt.where(Conversation.type == conversation_type.value)
        
        # Order by most recent activity (updated_at), then creation
        stmt = stmt.order_by(desc(Conversation.updated_at), desc(Conversation.created_at))
        
        # Add pagination
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_project_conversations(
        self,
        project_id: uuid.UUID,
        conversation_type: Optional[ConversationType] = None
    ) -> int:
        """
        Count conversations for a project.
        
        Args:
            project_id: Project UUID
            conversation_type: Filter by conversation type (optional)
            
        Returns:
            Number of conversations
        """
        # Build base query for project conversations
        stmt = select(func.count(Conversation.id)).where(Conversation.entity == project_id)
        
        # Add type filter if specified
        if conversation_type:
            stmt = stmt.where(Conversation.type == conversation_type.value)
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0 
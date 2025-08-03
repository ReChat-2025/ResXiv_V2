"""
Dependency Injection Container
L6 Engineering Standards - Eliminates service instantiation DRY violations

This module provides a centralized dependency injection system to eliminate
the repeated "service = SomeService(session)" pattern found in every endpoint.
"""

import logging
from typing import TypeVar, Type, Dict, Any, Callable
from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.database.connection import get_postgres_session, db_manager
from app.services.user_service import UserService
from app.services.core.project_service_core import ProjectCoreService
from app.services.paper_service import PaperService
from app.services.task_service import TaskService
from app.services.conversation.conversation_service_integrated import ConversationService
from app.services.message_service import MessageService
from app.services.branch_service import BranchService
from app.services.arxiv_service import ArXivService
from app.services.redis_service import RedisService
from app.services.email_service import EmailService
from app.repositories.user_repository import UserRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.paper_repository import PaperRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.branch_repository import BranchRepository

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceContainer:
    """
    Centralized service container for dependency injection.
    
    Eliminates the repeated pattern:
    service = SomeService(session)
    
    Replaces with:
    service = container.get_service(SomeService, session)
    """
    
    _instance = None
    _services: Dict[str, Callable] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the service registry."""
        self._register_services()
        self._register_repositories()
    
    def _register_services(self):
        """Register all service classes with their dependencies."""
        self._services.update({
            'UserService': lambda session: UserService(session),
            'ProjectCoreService': lambda session: ProjectCoreService(session),
            'PaperService': lambda session: PaperService(session),
            'TaskService': lambda session: TaskService(session),
            'ConversationService': lambda session: ConversationService(session, RedisService(db_manager)),
            'MessageService': lambda session: MessageService(session, db_manager, RedisService(db_manager)),
            'BranchService': lambda session: BranchService(session),
            'ArXivService': lambda session: ArXivService(),
            'RedisService': lambda session: RedisService(db_manager),
            'EmailService': lambda session: EmailService.get_instance(),
        })
    
    def _register_repositories(self):
        """Register all repository classes with their dependencies."""
        self._services.update({
            'UserRepository': lambda session: UserRepository(session),
            'ProjectRepository': lambda session: ProjectRepository(session),
            'PaperRepository': lambda session: PaperRepository(session),
            'TaskRepository': lambda session: TaskRepository(session),
            'ConversationRepository': lambda session: ConversationRepository(session),
            'MessageRepository': lambda session: MessageRepository(session),
            'BranchRepository': lambda session: BranchRepository(session),
        })
    
    def get_service(self, service_type: Type[T], session: AsyncSession) -> T:
        """
        Get a service instance with proper dependency injection.
        
        Args:
            service_type: The service class type
            session: Database session
            
        Returns:
            Configured service instance
        """
        service_name = service_type.__name__
        
        if service_name not in self._services:
            raise ValueError(f"Service {service_name} not registered")
        
        try:
            return self._services[service_name](session)
        except Exception as e:
            logger.error(f"Failed to create service {service_name}: {str(e)}")
            raise
    
    def register_service(self, service_name: str, factory: Callable):
        """
        Register a custom service factory.
        
        Args:
            service_name: Name of the service
            factory: Factory function that creates the service
        """
        self._services[service_name] = factory
    
    def list_services(self) -> list:
        """List all registered services."""
        return list(self._services.keys())


# Global container instance
container = ServiceContainer()


# Dependency injection helpers for FastAPI endpoints
def get_user_service(session: AsyncSession = Depends(get_postgres_session)) -> UserService:
    """FastAPI dependency for UserService."""
    return container.get_service(UserService, session)


def get_project_service(session: AsyncSession = Depends(get_postgres_session)) -> ProjectCoreService:
    """FastAPI dependency for ProjectCoreService."""
    return container.get_service(ProjectCoreService, session)


def get_paper_service(session: AsyncSession = Depends(get_postgres_session)) -> PaperService:
    """FastAPI dependency for PaperService."""
    return container.get_service(PaperService, session)


def get_task_service(session: AsyncSession = Depends(get_postgres_session)) -> TaskService:
    """FastAPI dependency for TaskService."""
    return container.get_service(TaskService, session)


def get_conversation_service(session: AsyncSession = Depends(get_postgres_session)) -> ConversationService:
    """FastAPI dependency for ConversationService."""
    return container.get_service(ConversationService, session)


def get_message_service(session: AsyncSession = Depends(get_postgres_session)) -> MessageService:
    """FastAPI dependency for MessageService."""
    return container.get_service(MessageService, session)


def get_branch_service(session: AsyncSession = Depends(get_postgres_session)) -> BranchService:
    """FastAPI dependency for BranchService."""
    return container.get_service(BranchService, session)


def get_arxiv_service() -> ArXivService:
    """FastAPI dependency for ArXivService (stateless)."""
    return ArXivService()


def get_redis_service() -> RedisService:
    """FastAPI dependency for RedisService."""
    return RedisService(db_manager)


@lru_cache()
def get_email_service() -> EmailService:
    """FastAPI dependency for EmailService (singleton)."""
    return EmailService.get_instance()


# Repository dependencies
def get_user_repository(session: AsyncSession = Depends(get_postgres_session)) -> UserRepository:
    """FastAPI dependency for UserRepository."""
    return container.get_service(UserRepository, session)


def get_project_repository(session: AsyncSession = Depends(get_postgres_session)) -> ProjectRepository:
    """FastAPI dependency for ProjectRepository."""
    return container.get_service(ProjectRepository, session)


def get_paper_repository(session: AsyncSession = Depends(get_postgres_session)) -> PaperRepository:
    """FastAPI dependency for PaperRepository."""
    return container.get_service(PaperRepository, session)


def get_task_repository(session: AsyncSession = Depends(get_postgres_session)) -> TaskRepository:
    """FastAPI dependency for TaskRepository."""
    return container.get_service(TaskRepository, session)


def get_conversation_repository(session: AsyncSession = Depends(get_postgres_session)) -> ConversationRepository:
    """FastAPI dependency for ConversationRepository."""
    return container.get_service(ConversationRepository, session)


def get_message_repository(session: AsyncSession = Depends(get_postgres_session)) -> MessageRepository:
    """FastAPI dependency for MessageRepository."""
    return container.get_service(MessageRepository, session)


def get_branch_repository(session: AsyncSession = Depends(get_postgres_session)) -> BranchRepository:
    """FastAPI dependency for BranchRepository."""
    return container.get_service(BranchRepository, session)


class ServiceMixin:
    """
    Mixin class to provide service access to any class.
    
    Usage:
    class MyClass(ServiceMixin):
        async def do_something(self, session):
            user_service = self.get_service(UserService, session)
    """
    
    def get_service(self, service_type: Type[T], session: AsyncSession) -> T:
        """Get a service instance through the container."""
        return container.get_service(service_type, session)
    
    def get_repository(self, repository_type: Type[T], session: AsyncSession) -> T:
        """Get a repository instance through the container."""
        return container.get_service(repository_type, session) 
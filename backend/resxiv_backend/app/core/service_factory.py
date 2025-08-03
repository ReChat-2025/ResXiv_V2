"""
Production-Grade Service Factory with Dependency Injection
L6 Engineering Standards Implementation

Follows SOLID principles:
- Single Responsibility: Service creation only
- Open/Closed: Extensible via new service registrations
- Liskov Substitution: All services implement BaseService
- Interface Segregation: Clean service protocols  
- Dependency Inversion: Depend on abstractions
"""

from abc import ABC, abstractmethod
from typing import Dict, Type, TypeVar, Optional, Protocol, runtime_checkable
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

@runtime_checkable
class ServiceProtocol(Protocol):
    """Protocol for all services to ensure consistent interface"""
    def __init__(self, session: AsyncSession) -> None: ...

class BaseService(ABC):
    """Base service class with common functionality"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Service health check - must be implemented by all services"""
        pass

class ServiceContainer:
    """
    Production dependency injection container following SOLID principles.
    Manages service lifecycle and provides clean dependency resolution.
    """
    
    _services: Dict[Type, Type] = {}
    _singletons: Dict[Type, object] = {}
    
    @classmethod
    def register(cls, service_type: Type[T], implementation: Type[T]) -> None:
        """Register service implementation"""
        cls._services[service_type] = implementation
        logger.info(f"Registered service: {service_type.__name__} -> {implementation.__name__}")
    
    @classmethod
    def get(cls, service_type: Type[T], session: Optional[AsyncSession] = None) -> T:
        """Get service instance with proper dependency resolution"""
        if service_type not in cls._services:
            raise ValueError(f"Service {service_type.__name__} not registered")
        
        implementation = cls._services[service_type]
        
        # Create new instance for session-dependent services
        if session is not None:
            return implementation(session)
        
        # Return singleton for session-independent services
        if service_type not in cls._singletons:
            cls._singletons[service_type] = implementation()
        
        return cls._singletons[service_type]
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registrations (for testing)"""
        cls._services.clear()
        cls._singletons.clear()

# Service factory functions for clean dependency injection
async def get_service(service_type: Type[T], session: AsyncSession) -> T:
    """Factory function for FastAPI dependency injection"""
    return ServiceContainer.get(service_type, session)

class ServiceHealthChecker:
    """Health checker for all registered services"""
    
    @staticmethod
    async def check_all_services(session: AsyncSession) -> Dict[str, bool]:
        """Check health of all registered services"""
        health_status = {}
        
        for service_type in ServiceContainer._services:
            try:
                service = ServiceContainer.get(service_type, session)
                if hasattr(service, 'health_check'):
                    health_status[service_type.__name__] = await service.health_check()
                else:
                    health_status[service_type.__name__] = True
            except Exception as e:
                logger.error(f"Health check failed for {service_type.__name__}: {e}")
                health_status[service_type.__name__] = False
        
        return health_status 
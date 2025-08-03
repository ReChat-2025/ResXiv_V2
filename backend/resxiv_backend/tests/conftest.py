"""
Test Configuration and Fixtures
L6 Engineering Standards Implementation

Provides shared fixtures and configuration for all tests.
"""

import pytest
import asyncio
import uuid
from typing import Dict, Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.database.connection import get_postgres_session
from app.core.auth import AuthService
from app.services.admin_service import AdminService


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session using SQLite in-memory database."""
    # Use SQLite in-memory database for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    
    # Create tables
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from app.schemas import user, project, paper, task, conversation
        from app.database.connection import Base
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI application."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """Sample user data for testing."""
    user_id = uuid.uuid4()
    return {
        "id": user_id,
        "user_id": str(user_id),  # Add user_id for JWT compatibility
        "email": "test@example.com",
        "full_name": "Test User",
        "username": "Test User",  # Add username for JWT compatibility
        "password": "TestPassword123!",
        "interests": ["AI", "Machine Learning"],
        "accepted_terms": True,
        "email_verified": True,
        "is_admin": False
    }


@pytest.fixture
def sample_project_data() -> Dict[str, Any]:
    """Sample project data for testing."""
    return {
        "id": uuid.uuid4(),
        "name": "Test Project",
        "description": "A test project for unit testing",
        "slug": "test-project",
        "is_public": False,
        "tags": ["test", "unit-testing"]
    }


@pytest.fixture
def sample_paper_data() -> Dict[str, Any]:
    """Sample paper data for testing."""
    return {
        "id": uuid.uuid4(),
        "title": "Test Paper",
        "authors": ["John Doe", "Jane Smith"],
        "abstract": "This is a test paper abstract.",
        "pdf_path": "/test/path/paper.pdf",
        "arxiv_id": "2024.01001",
        "doi": "10.1000/test.doi"
    }


@pytest.fixture
def sample_task_data() -> Dict[str, Any]:
    """Sample task data for testing."""
    return {
        "id": uuid.uuid4(),
        "title": "Test Task",
        "description": "A test task description",
        "status": "todo",
        "priority": "medium",
        "assignee_id": None,
        "due_date": None
    }


@pytest.fixture
def sample_conversation_data() -> Dict[str, Any]:
    """Sample conversation data for testing."""
    return {
        "id": uuid.uuid4(),
        "title": "Test Conversation",
        "type": "general",
        "is_private": False
    }


@pytest.fixture
def valid_jwt_token(sample_user_data) -> str:
    """Create a valid JWT token for testing."""
    return AuthService.create_access_token({
        "user_id": str(sample_user_data["id"]),
        "email": sample_user_data["email"],
        "username": sample_user_data["full_name"]
    })


@pytest.fixture
def auth_headers(valid_jwt_token) -> Dict[str, str]:
    """Create authentication headers with valid JWT token."""
    return {"Authorization": f"Bearer {valid_jwt_token}"}


@pytest.fixture
def admin_user_data() -> Dict[str, Any]:
    """Sample admin user data for testing."""
    user_id = uuid.uuid4()
    return {
        "id": user_id,
        "user_id": str(user_id),  # Add user_id for JWT compatibility
        "email": "admin@example.com",
        "full_name": "Admin User",
        "username": "Admin User",  # Add username for JWT compatibility
        "password": "AdminPassword123!",
        "interests": ["AI", "Machine Learning"],
        "accepted_terms": True,
        "email_verified": True,
        "is_admin": True
    }


@pytest.fixture
def admin_jwt_token(admin_user_data) -> str:
    """Create a valid admin JWT token for testing."""
    return AuthService.create_access_token({
        "user_id": str(admin_user_data["id"]),
        "email": admin_user_data["email"],
        "username": admin_user_data["full_name"]
    })


@pytest.fixture
def admin_auth_headers(admin_jwt_token) -> Dict[str, str]:
    """Create admin authentication headers with valid JWT token."""
    return {"Authorization": f"Bearer {admin_jwt_token}"}


@pytest.fixture
def mock_redis_service():
    """Create a mock Redis service."""
    redis_mock = AsyncMock()
    redis_mock.publish_message = AsyncMock()
    redis_mock.cache_recent_messages = AsyncMock()
    redis_mock.get_cached_messages = AsyncMock(return_value=[])
    redis_mock.set_user_online = AsyncMock()
    redis_mock.set_user_offline = AsyncMock()
    return redis_mock


@pytest.fixture
def mock_email_service():
    """Create a mock email service."""
    email_mock = AsyncMock()
    email_mock.send_email_verification = AsyncMock(return_value=True)
    email_mock.send_password_reset = AsyncMock(return_value=True)
    email_mock.send_invitation_email = AsyncMock(return_value=True)
    return email_mock


@pytest.fixture
def mock_user_lookup_service():
    """Create a mock user lookup service."""
    service = AsyncMock()
    service.get_user_info = AsyncMock(return_value={
        "id": str(uuid.uuid4()),
        "name": "Test User",
        "email": "test@example.com"
    })
    service.get_users_batch = AsyncMock(return_value={})
    return service


@pytest.fixture
def mock_admin_service():
    """Create a mock admin service."""
    service = MagicMock()
    service.is_admin = AsyncMock(return_value=False)
    service.is_system_admin = AsyncMock(return_value=False)
    service.require_admin = AsyncMock()
    service.require_system_admin = AsyncMock()
    service.get_admin_permissions = AsyncMock(return_value={
        "is_admin": False,
        "is_system_admin": False,
        "can_manage_users": False,
        "can_manage_projects": False,
        "can_view_analytics": False
    })
    return service


@pytest.fixture(autouse=True)
def override_dependencies(test_db_session, mock_admin_service):
    """Override FastAPI dependencies for testing."""
    app.dependency_overrides[get_postgres_session] = lambda: test_db_session
    yield
    app.dependency_overrides.clear()


# Test utilities
class TestHelper:
    """Helper utilities for tests."""
    
    @staticmethod
    def assert_success_response(response_data: Dict[str, Any], expected_data_keys: list = None):
        """Assert that a response is successful and has expected structure."""
        assert response_data["success"] is True
        assert "message" in response_data
        
        if expected_data_keys and "data" in response_data:
            for key in expected_data_keys:
                assert key in response_data["data"]
    
    @staticmethod
    def assert_error_response(response_data: Dict[str, Any], expected_error_code: str = None):
        """Assert that a response is an error with expected structure."""
        assert response_data["success"] is False
        assert "error" in response_data
        assert "message" in response_data
        
        if expected_error_code:
            assert response_data["error"] == expected_error_code
    
    @staticmethod
    async def create_test_user(session: AsyncSession, user_data: Dict[str, Any]):
        """Create a test user in the database."""
        from app.repositories.user_repository import UserRepository
        repo = UserRepository(session)
        return await repo.create_user(
            name=user_data["full_name"],
            email=user_data["email"],
            password=user_data["password"],
            interests=user_data.get("interests", []),
            accepted_terms=user_data.get("accepted_terms", True)
        )
    
    @staticmethod
    async def create_test_project(session: AsyncSession, project_data: Dict[str, Any], creator_id: uuid.UUID):
        """Create a test project in the database."""
        from app.repositories.project_repository import ProjectRepository
        repo = ProjectRepository(session)
        return await repo.create_project(
            name=project_data["name"],
            description=project_data["description"],
            created_by=creator_id,
            slug=project_data.get("slug")
        )


@pytest.fixture
def test_helper():
    """Provide test helper utilities."""
    return TestHelper 
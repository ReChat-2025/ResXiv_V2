"""
Analytics Modules Test Suite - L6 Engineering Standards

Comprehensive test coverage for modular analytics system.
Tests the split modules that replaced the bloated analytics.py file.
"""

import pytest
import uuid
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, Mock, patch
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.endpoints.analytics.analytics_user import get_user_analytics, get_user_engagement
from api.v1.endpoints.analytics.analytics_project import get_project_analytics, get_project_collaboration_analytics
from api.v1.endpoints.analytics.analytics_system import get_system_metrics, get_system_health


class TestAnalyticsUserModule:
    """Test suite for user analytics module"""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_current_user(self):
        return {"user_id": str(uuid.uuid4()), "username": "test_user"}

    @pytest.mark.asyncio
    async def test_get_user_analytics_success(self, mock_session, mock_current_user):
        """Test successful user analytics retrieval"""
        user_id = mock_current_user["user_id"]
        
        # Mock database responses
        mock_user_result = Mock()
        mock_user_result.fetchone.return_value = Mock(
            username="test_user",
            email="test@example.com",
            created_at=datetime.utcnow(),
            projects_joined=3,
            papers_uploaded=5,
            messages_sent=25
        )
        
        mock_activity_result = Mock()
        mock_activity_result.fetchall.return_value = [
            Mock(activity_date=date.today(), activity_count=5, activity_type="messages"),
            Mock(activity_date=date.today() - timedelta(days=1), activity_count=2, activity_type="papers")
        ]
        
        mock_session.execute.side_effect = [mock_user_result, mock_activity_result]
        
        # Test the endpoint
        result = await get_user_analytics(
            user_id=user_id,
            current_user=mock_current_user,
            session=mock_session
        )
        
        # Assertions
        assert result["success"] is True
        assert result["user_info"]["username"] == "test_user"
        assert result["user_info"]["projects_joined"] == 3
        assert result["user_info"]["papers_uploaded"] == 5
        assert result["user_info"]["messages_sent"] == 25
        assert "activity_timeline" in result

    @pytest.mark.asyncio
    async def test_get_user_analytics_permission_denied(self, mock_session, mock_current_user):
        """Test user analytics with permission denied"""
        different_user_id = str(uuid.uuid4())
        
        with pytest.raises(HTTPException) as exc_info:
            await get_user_analytics(
                user_id=different_user_id,
                current_user=mock_current_user,
                session=mock_session
            )
        
        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_user_engagement_success(self, mock_session, mock_current_user):
        """Test successful user engagement retrieval"""
        mock_engagement_result = Mock()
        mock_engagement_result.fetchone.return_value = Mock(
            active_days=15,
            total_messages=75,
            conversations_participated=8,
            avg_message_length=150.5
        )
        
        mock_session.execute.return_value = mock_engagement_result
        
        result = await get_user_engagement(
            days=30,
            current_user=mock_current_user,
            session=mock_session
        )
        
        assert result["success"] is True
        assert result["period_days"] == 30
        assert result["metrics"]["active_days"] == 15
        assert result["metrics"]["total_messages"] == 75
        assert result["metrics"]["engagement_score"] > 0


class TestAnalyticsProjectModule:
    """Test suite for project analytics module"""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_current_user(self):
        return {"user_id": str(uuid.uuid4())}

    @pytest.fixture
    def mock_project_access(self):
        return {"project_id": str(uuid.uuid4()), "role": "member"}

    @pytest.mark.asyncio
    async def test_get_project_analytics_success(self, mock_session, mock_current_user, mock_project_access):
        """Test successful project analytics retrieval"""
        project_id = str(uuid.uuid4())
        
        # Mock project basic info
        mock_project_result = Mock()
        mock_project_result.fetchone.return_value = Mock(
            name="Test Project",
            description="Test Description",
            created_at=datetime.utcnow(),
            member_count=5,
            paper_count=10
        )
        
        # Mock activity data
        mock_activity_result = Mock()
        mock_activity_result.fetchall.return_value = [
            Mock(activity_date=date.today(), active_members=3, message_count=15)
        ]
        
        # Mock collaboration metrics
        mock_collab_result = Mock()
        mock_collab_result.fetchone.return_value = Mock(
            conversation_count=5,
            total_messages=150,
            task_count=20,
            completed_tasks=12
        )
        
        mock_session.execute.side_effect = [
            mock_project_result, mock_activity_result, mock_collab_result
        ]
        
        result = await get_project_analytics(
            project_id=project_id,
            current_user=mock_current_user,
            project_access=mock_project_access,
            session=mock_session
        )
        
        assert result["success"] is True
        assert result["project_info"]["name"] == "Test Project"
        assert result["project_info"]["member_count"] == 5
        assert result["collaboration_metrics"]["task_completion_rate"] == 60.0

    @pytest.mark.asyncio
    async def test_project_not_found(self, mock_session, mock_current_user, mock_project_access):
        """Test project analytics when project not found"""
        project_id = str(uuid.uuid4())
        
        mock_project_result = Mock()
        mock_project_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_project_result
        
        with pytest.raises(HTTPException) as exc_info:
            await get_project_analytics(
                project_id=project_id,
                current_user=mock_current_user,
                project_access=mock_project_access,
                session=mock_session
            )
        
        assert exc_info.value.status_code == 404
        assert "Project not found" in str(exc_info.value.detail)


class TestAnalyticsSystemModule:
    """Test suite for system analytics module"""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_current_user(self):
        return {"user_id": str(uuid.uuid4())}

    @pytest.mark.asyncio
    async def test_get_system_metrics_success(self, mock_session, mock_current_user):
        """Test successful system metrics retrieval"""
        mock_metrics_result = Mock()
        mock_metrics_result.fetchall.return_value = [
            Mock(
                metric_name="response_time",
                metric_category="performance",
                avg_value=150.5,
                min_value=50.0,
                max_value=300.0,
                sample_count=100,
                unit="ms"
            )
        ]
        
        mock_stats_result = Mock()
        mock_stats_result.fetchone.return_value = Mock(
            total_users=1000,
            total_projects=250,
            total_papers=500,
            total_messages=10000
        )
        
        mock_session.execute.side_effect = [mock_metrics_result, mock_stats_result]
        
        result = await get_system_metrics(
            current_user=mock_current_user,
            session=mock_session
        )
        
        assert result["success"] is True
        assert result["time_range_hours"] == 24
        assert len(result["performance_metrics"]) == 1
        assert result["performance_metrics"][0]["metric_name"] == "response_time"
        assert result["system_stats"]["total_users"] == 1000

    @pytest.mark.asyncio
    async def test_get_system_health_success(self, mock_session, mock_current_user):
        """Test successful system health check"""
        mock_error_result = Mock()
        mock_error_result.fetchone.return_value = Mock(error_count=2)
        mock_session.execute.return_value = mock_error_result
        
        result = await get_system_health(
            current_user=mock_current_user,
            session=mock_session
        )
        
        assert result["success"] is True
        assert result["overall_health"] in ["healthy", "degraded", "unhealthy"]
        assert result["health_score"] >= 0
        assert "database" in result["components"]
        assert "error_rate" in result["components"]

    @pytest.mark.asyncio
    async def test_system_health_database_error(self, mock_session, mock_current_user):
        """Test system health when database fails"""
        mock_session.execute.side_effect = Exception("Database connection failed")
        
        result = await get_system_health(
            current_user=mock_current_user,
            session=mock_session
        )
        
        assert result["success"] is True
        assert result["components"]["database"]["status"] == "unhealthy"
        assert result["health_score"] <= 50


@pytest.mark.integration
class TestAnalyticsIntegration:
    """Integration tests for analytics modules"""
    
    @pytest.mark.asyncio
    async def test_analytics_modules_independence(self):
        """Test that analytics modules work independently"""
        # Test that each module can be imported and used independently
        from api.v1.endpoints.analytics.analytics_user import router as user_router
        from api.v1.endpoints.analytics.analytics_project import router as project_router
        from api.v1.endpoints.analytics.analytics_system import router as system_router
        
        assert user_router is not None
        assert project_router is not None
        assert system_router is not None
        
    def test_error_handling_consistency(self):
        """Test that all modules use consistent error handling"""
        # All modules should use the @handle_service_errors decorator
        from api.v1.endpoints.analytics import analytics_user, analytics_project, analytics_system
        
        # Check that error handling decorators are applied
        assert hasattr(analytics_user.get_user_analytics, '__wrapped__')
        assert hasattr(analytics_project.get_project_analytics, '__wrapped__')
        assert hasattr(analytics_system.get_system_metrics, '__wrapped__')


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 
"""
Comprehensive Tests for LangGraph Orchestrator
L6 Engineering Standards - Production-ready LangGraph testing
"""

import pytest
import uuid
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.agentic.production_langgraph import (
    ProductionLangGraphOrchestrator,
    LangGraphConfig,
    TaskType,
    WorkflowStatus,
    AgentState
)
from app.core.error_handling import ServiceError, ErrorCodes


class TestLangGraphConfig:
    """Test LangGraph configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = LangGraphConfig()
        
        assert config.model_name == "gpt-4o-mini"
        assert config.temperature == 0.1
        assert config.max_tool_calls == 15
        assert config.max_retries == 3
        assert config.timeout_seconds == 300
        assert config.enable_memory is True
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = LangGraphConfig(
            model_name="gpt-4",
            temperature=0.2,
            max_tool_calls=20,
            max_retries=5,
            timeout_seconds=600,
            enable_memory=False
        )
        
        assert config.model_name == "gpt-4"
        assert config.temperature == 0.2
        assert config.max_tool_calls == 20
        assert config.max_retries == 5
        assert config.timeout_seconds == 600
        assert config.enable_memory is False


class TestTaskType:
    """Test TaskType enumeration"""
    
    def test_task_types_exist(self):
        """Test that all expected task types exist"""
        expected_types = [
            "research", "project_management", "paper_processing",
            "conversation", "analysis", "file_processing"
        ]
        
        for task_type in expected_types:
            assert hasattr(TaskType, task_type.upper())
            assert getattr(TaskType, task_type.upper()).value == task_type


class TestProductionLangGraphOrchestrator:
    """Test the production LangGraph orchestrator"""
    
    @pytest.fixture
    def mock_openai_key(self):
        return "test-openai-key"
    
    @pytest.fixture
    def test_config(self):
        return LangGraphConfig(
            model_name="gpt-4o-mini",
            temperature=0.1,
            max_tool_calls=10,
            enable_memory=True
        )
    
    @pytest.fixture
    def orchestrator(self, mock_openai_key, test_config):
        """Create orchestrator instance for testing"""
        with patch('app.agentic.production_langgraph.ChatOpenAI') as mock_llm:
            mock_llm.return_value = Mock()
            return ProductionLangGraphOrchestrator(mock_openai_key, test_config)
    
    def test_orchestrator_initialization(self, mock_openai_key, test_config):
        """Test orchestrator initialization"""
        with patch('app.agentic.production_langgraph.ChatOpenAI') as mock_llm, \
             patch('app.agentic.production_langgraph.MemorySaver') as mock_saver:
            
            orchestrator = ProductionLangGraphOrchestrator(mock_openai_key, test_config)
            
            assert orchestrator.config == test_config
            assert orchestrator.openai_api_key == mock_openai_key
            mock_llm.assert_called_once_with(
                api_key=mock_openai_key,
                model=test_config.model_name,
                temperature=test_config.temperature,
                timeout=30
            )
            mock_saver.assert_called_once()
    
    def test_orchestrator_initialization_default_config(self, mock_openai_key):
        """Test orchestrator initialization with default config"""
        with patch('app.agentic.production_langgraph.ChatOpenAI'), \
             patch('app.agentic.production_langgraph.MemorySaver'):
            
            orchestrator = ProductionLangGraphOrchestrator(mock_openai_key)
            
            assert isinstance(orchestrator.config, LangGraphConfig)
            assert orchestrator.config.model_name == "gpt-4o-mini"
    
    @pytest.mark.asyncio
    async def test_classify_intent_research(self, orchestrator):
        """Test intent classification for research tasks"""
        state: AgentState = {
            "messages": [{"content": "I need to research machine learning papers"}],
            "task_type": None,
            "user_intent": None,
            "context": {},
            "current_agent": None,
            "tool_calls_count": 0,
            "max_tool_calls": 15,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "error": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = await orchestrator._classify_intent(state)
        
        assert result["task_type"] == TaskType.RESEARCH.value
        assert result["user_intent"] == "I need to research machine learning papers"
        assert result["updated_at"] > result["created_at"]
    
    @pytest.mark.asyncio
    async def test_classify_intent_project_management(self, orchestrator):
        """Test intent classification for project management tasks"""
        state: AgentState = {
            "messages": [{"content": "I want to create a new project and manage tasks"}],
            "task_type": None,
            "user_intent": None,
            "context": {},
            "current_agent": None,
            "tool_calls_count": 0,
            "max_tool_calls": 15,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "error": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = await orchestrator._classify_intent(state)
        
        assert result["task_type"] == TaskType.PROJECT_MANAGEMENT.value
    
    @pytest.mark.asyncio
    async def test_classify_intent_no_messages(self, orchestrator):
        """Test intent classification with no messages"""
        state: AgentState = {
            "messages": [],
            "task_type": None,
            "user_intent": None,
            "context": {},
            "current_agent": None,
            "tool_calls_count": 0,
            "max_tool_calls": 15,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "error": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = await orchestrator._classify_intent(state)
        
        assert result["error"] == "No messages to process"
    
    @pytest.mark.asyncio
    async def test_route_task(self, orchestrator):
        """Test task routing"""
        state: AgentState = {
            "messages": [],
            "task_type": TaskType.RESEARCH.value,
            "user_intent": "Test intent",
            "context": {},
            "current_agent": None,
            "tool_calls_count": 0,
            "max_tool_calls": 15,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "error": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = await orchestrator._route_task(state)
        
        assert result["current_agent"] == f"{TaskType.RESEARCH.value}_agent"
        assert result["updated_at"] > result["created_at"]
    
    def test_route_by_task_type_valid(self, orchestrator):
        """Test routing by valid task type"""
        state: AgentState = {
            "task_type": TaskType.RESEARCH.value,
            "messages": [],
            "user_intent": None,
            "context": {},
            "current_agent": None,
            "tool_calls_count": 0,
            "max_tool_calls": 15,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "error": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = orchestrator._route_by_task_type(state)
        
        assert result == TaskType.RESEARCH
    
    def test_route_by_task_type_invalid(self, orchestrator):
        """Test routing by invalid task type"""
        state: AgentState = {
            "task_type": "invalid_task_type",
            "messages": [],
            "user_intent": None,
            "context": {},
            "current_agent": None,
            "tool_calls_count": 0,
            "max_tool_calls": 15,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "error": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = orchestrator._route_by_task_type(state)
        
        assert result == "error"
    
    def test_should_use_tools_with_error(self, orchestrator):
        """Test tool usage decision with error"""
        state: AgentState = {
            "error": "Some error occurred",
            "task_type": None,
            "messages": [],
            "user_intent": None,
            "context": {},
            "current_agent": None,
            "tool_calls_count": 0,
            "max_tool_calls": 15,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = orchestrator._should_use_tools(state)
        
        assert result == "error"
    
    def test_should_use_tools_max_calls_reached(self, orchestrator):
        """Test tool usage decision when max calls reached"""
        state: AgentState = {
            "error": None,
            "tool_calls_count": 20,
            "max_tool_calls": 15,
            "task_type": None,
            "messages": [],
            "user_intent": None,
            "context": {},
            "current_agent": None,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = orchestrator._should_use_tools(state)
        
        assert result == "response"
    
    def test_should_use_tools_needs_tools(self, orchestrator):
        """Test tool usage decision when tools are needed"""
        state: AgentState = {
            "error": None,
            "tool_calls_count": 5,
            "max_tool_calls": 15,
            "context": {"needs_tools": True},
            "task_type": None,
            "messages": [],
            "user_intent": None,
            "current_agent": None,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = orchestrator._should_use_tools(state)
        
        assert result == "tools"
    
    def test_should_use_tools_needs_human(self, orchestrator):
        """Test tool usage decision when human feedback is needed"""
        state: AgentState = {
            "error": None,
            "tool_calls_count": 5,
            "max_tool_calls": 15,
            "context": {"needs_human": True},
            "task_type": None,
            "messages": [],
            "user_intent": None,
            "current_agent": None,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = orchestrator._should_use_tools(state)
        
        assert result == "human"
    
    def test_handle_tool_results_with_error(self, orchestrator):
        """Test tool result handling with error"""
        state: AgentState = {
            "error": "Tool execution failed",
            "task_type": None,
            "messages": [],
            "user_intent": None,
            "context": {},
            "current_agent": None,
            "tool_calls_count": 0,
            "max_tool_calls": 15,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = orchestrator._handle_tool_results(state)
        
        assert result == "error"
    
    def test_handle_tool_results_no_results(self, orchestrator):
        """Test tool result handling with no results"""
        state: AgentState = {
            "error": None,
            "context": {},
            "task_type": None,
            "messages": [],
            "user_intent": None,
            "current_agent": None,
            "tool_calls_count": 0,
            "max_tool_calls": 15,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = orchestrator._handle_tool_results(state)
        
        assert result == "error"
    
    def test_handle_tool_results_needs_more_tools(self, orchestrator):
        """Test tool result handling when more tools are needed"""
        state: AgentState = {
            "error": None,
            "context": {
                "tool_results": [{"tool": "test", "result": "success"}],
                "needs_more_tools": True
            },
            "task_type": None,
            "messages": [],
            "user_intent": None,
            "current_agent": None,
            "tool_calls_count": 0,
            "max_tool_calls": 15,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = orchestrator._handle_tool_results(state)
        
        assert result == "retry"
    
    def test_handle_tool_results_continue(self, orchestrator):
        """Test tool result handling when continuing"""
        state: AgentState = {
            "error": None,
            "context": {
                "tool_results": [{"tool": "test", "result": "success"}],
                "needs_more_tools": False
            },
            "task_type": None,
            "messages": [],
            "user_intent": None,
            "current_agent": None,
            "tool_calls_count": 0,
            "max_tool_calls": 15,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = orchestrator._handle_tool_results(state)
        
        assert result == "continue"


class TestAgentHandlers:
    """Test individual agent handlers"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        with patch('app.agentic.production_langgraph.ChatOpenAI'), \
             patch('app.agentic.production_langgraph.MemorySaver'):
            return ProductionLangGraphOrchestrator("test-key")
    
    @pytest.mark.asyncio
    async def test_handle_research(self, orchestrator):
        """Test research agent handler"""
        state: AgentState = {
            "context": {},
            "task_type": None,
            "messages": [],
            "user_intent": None,
            "current_agent": None,
            "tool_calls_count": 0,
            "max_tool_calls": 15,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "error": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = await orchestrator._handle_research(state)
        
        assert result["context"]["agent_type"] == "research"
        assert result["context"]["needs_tools"] is True
        assert result["updated_at"] > result["created_at"]
    
    @pytest.mark.asyncio
    async def test_handle_project(self, orchestrator):
        """Test project agent handler"""
        state: AgentState = {
            "context": {},
            "task_type": None,
            "messages": [],
            "user_intent": None,
            "current_agent": None,
            "tool_calls_count": 0,
            "max_tool_calls": 15,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "error": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = await orchestrator._handle_project(state)
        
        assert result["context"]["agent_type"] == "project"
        assert result["updated_at"] > result["created_at"]
    
    @pytest.mark.asyncio
    async def test_execute_tools(self, orchestrator):
        """Test tool execution"""
        state: AgentState = {
            "tool_calls_count": 5,
            "context": {},
            "task_type": None,
            "messages": [],
            "user_intent": None,
            "current_agent": None,
            "max_tool_calls": 15,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "error": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = await orchestrator._execute_tools(state)
        
        assert result["tool_calls_count"] == 6
        assert "tool_results" in result["context"]
        assert len(result["context"]["tool_results"]) == 1
        assert result["updated_at"] > result["created_at"]
    
    @pytest.mark.asyncio
    async def test_format_response(self, orchestrator):
        """Test response formatting"""
        state: AgentState = {
            "context": {"agent_type": "research"},
            "task_type": TaskType.RESEARCH.value,
            "tool_calls_count": 3,
            "messages": [],
            "user_intent": None,
            "current_agent": None,
            "max_tool_calls": 15,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "error": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = await orchestrator._format_response(state)
        
        assert result["status"] == WorkflowStatus.COMPLETED.value
        assert result["result"]["message"] == "Task completed successfully"
        assert result["result"]["agent_type"] == "research"
        assert result["result"]["task_type"] == TaskType.RESEARCH.value
        assert result["result"]["tool_calls"] == 3
    
    @pytest.mark.asyncio
    async def test_handle_error(self, orchestrator):
        """Test error handling"""
        state: AgentState = {
            "error": "Test error message",
            "context": {},
            "task_type": None,
            "messages": [],
            "user_intent": None,
            "current_agent": None,
            "tool_calls_count": 0,
            "max_tool_calls": 15,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = await orchestrator._handle_error(state)
        
        assert result["status"] == WorkflowStatus.FAILED.value
        assert result["result"]["error"] == "Test error message"
        assert result["result"]["status"] == "failed"
    
    @pytest.mark.asyncio
    async def test_request_human_feedback(self, orchestrator):
        """Test human feedback request"""
        state: AgentState = {
            "context": {"some": "context"},
            "task_type": None,
            "messages": [],
            "user_intent": None,
            "current_agent": None,
            "tool_calls_count": 0,
            "max_tool_calls": 15,
            "status": WorkflowStatus.PENDING.value,
            "result": None,
            "error": None,
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = await orchestrator._request_human_feedback(state)
        
        assert result["status"] == "awaiting_feedback"
        assert result["result"]["message"] == "Human feedback required"
        assert result["result"]["context"] == {"some": "context"}


class TestWorkflowExecution:
    """Test complete workflow execution"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        with patch('app.agentic.production_langgraph.ChatOpenAI'), \
             patch('app.agentic.production_langgraph.MemorySaver'):
            return ProductionLangGraphOrchestrator("test-key")
    
    @pytest.mark.asyncio
    async def test_execute_workflow_success(self, orchestrator):
        """Test successful workflow execution"""
        messages = [{"content": "I need to research AI papers"}]
        session_id = str(uuid.uuid4())
        
        with patch.object(orchestrator.app, 'ainvoke') as mock_invoke:
            mock_invoke.return_value = {
                "status": WorkflowStatus.COMPLETED.value,
                "result": {"message": "Research completed"},
                "tool_calls_count": 2,
                "context": {"agent_type": "research"},
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            result = await orchestrator.execute(messages, session_id)
            
            assert result["success"] is True
            assert result["session_id"] == session_id
            assert result["status"] == WorkflowStatus.COMPLETED.value
            assert "metadata" in result
            assert result["metadata"]["tool_calls"] == 2
            assert result["metadata"]["agent_type"] == "research"
    
    @pytest.mark.asyncio
    async def test_execute_workflow_failure(self, orchestrator):
        """Test workflow execution with failure"""
        messages = [{"content": "Test message"}]
        
        with patch.object(orchestrator.app, 'ainvoke') as mock_invoke:
            mock_invoke.side_effect = Exception("Workflow execution failed")
            
            result = await orchestrator.execute(messages)
            
            assert result["success"] is False
            assert "Workflow execution failed" in result["error"]
            assert result["status"] == WorkflowStatus.FAILED.value
    
    @pytest.mark.asyncio
    async def test_get_session_state_success(self, orchestrator):
        """Test successful session state retrieval"""
        session_id = str(uuid.uuid4())
        
        with patch.object(orchestrator.app, 'aget_state') as mock_get_state:
            mock_checkpoint = Mock()
            mock_checkpoint.values = {"test": "state"}
            mock_get_state.return_value = mock_checkpoint
            
            result = await orchestrator.get_session_state(session_id)
            
            assert result == {"test": "state"}
    
    @pytest.mark.asyncio
    async def test_get_session_state_not_found(self, orchestrator):
        """Test session state retrieval when not found"""
        session_id = str(uuid.uuid4())
        
        with patch.object(orchestrator.app, 'aget_state') as mock_get_state:
            mock_get_state.return_value = None
            
            result = await orchestrator.get_session_state(session_id)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_session_state_no_checkpointer(self):
        """Test session state retrieval without checkpointer"""
        config = LangGraphConfig(enable_memory=False)
        
        with patch('app.agentic.production_langgraph.ChatOpenAI'):
            orchestrator = ProductionLangGraphOrchestrator("test-key", config)
            
            result = await orchestrator.get_session_state("test-session")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_resume_session_success(self, orchestrator):
        """Test successful session resumption"""
        session_id = str(uuid.uuid4())
        additional_messages = [{"content": "Continue the conversation"}]
        
        with patch.object(orchestrator, 'get_session_state') as mock_get_state, \
             patch.object(orchestrator, 'execute') as mock_execute:
            
            mock_get_state.return_value = {
                "messages": [{"content": "Previous message"}],
                "context": {"existing": "context"}
            }
            
            mock_execute.return_value = {"success": True, "result": "resumed"}
            
            result = await orchestrator.resume_session(session_id, additional_messages)
            
            assert result["success"] is True
            
            # Verify execute was called with combined messages
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            expected_messages = [
                {"content": "Previous message"},
                {"content": "Continue the conversation"}
            ]
            assert call_args[0][0] == expected_messages
            assert call_args[0][1] == session_id
            assert call_args[0][2] == {"existing": "context"}
    
    @pytest.mark.asyncio
    async def test_resume_session_not_found(self, orchestrator):
        """Test session resumption when session not found"""
        session_id = str(uuid.uuid4())
        
        with patch.object(orchestrator, 'get_session_state') as mock_get_state:
            mock_get_state.return_value = None
            
            with pytest.raises(ServiceError) as exc_info:
                await orchestrator.resume_session(session_id)
            
            assert exc_info.value.error_code == ErrorCodes.NOT_FOUND
            assert exc_info.value.status_code == 404
            assert "Session not found" in exc_info.value.message 
"""
Agent Modules Test Suite - L6 Engineering Standards

Comprehensive test coverage for modular agent system.
Tests the split modules that replaced the bloated agents.py file.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from app.agentic.graph.agents.base_agent import BaseGraphAgent, AgentCapability
from app.agentic.graph.agents.research_agent import ResearchGraphAgent
from app.agentic.graph.agents.project_agent import ProjectGraphAgent
from app.agentic.graph.agents.paper_agent import PaperGraphAgent


class TestBaseGraphAgent:
    """Test suite for base graph agent"""

    def test_agent_capability_creation(self):
        """Test agent capability creation"""
        capability = AgentCapability(
            name="test_capability",
            description="Test capability description",
            required_tools=["tool1", "tool2"],
            confidence_threshold=0.8
        )
        
        assert capability.name == "test_capability"
        assert capability.description == "Test capability description"
        assert capability.required_tools == ["tool1", "tool2"]
        assert capability.confidence_threshold == 0.8

    def test_base_agent_initialization(self):
        """Test base agent initialization"""
        capabilities = [
            AgentCapability(
                name="test_capability",
                description="Test capability",
                required_tools=["tool1"]
            )
        ]
        
        # Create a concrete implementation for testing
        class TestAgent(BaseGraphAgent):
            async def can_handle(self, context: Dict[str, Any]) -> bool:
                return True
            
            async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
                return {"success": True}
        
        agent = TestAgent("test_agent", capabilities)
        
        assert agent.agent_id == "test_agent"
        assert len(agent.capabilities) == 1
        assert agent.get_capability_names() == ["test_capability"]

    @pytest.mark.asyncio
    async def test_validate_capabilities(self):
        """Test capability validation"""
        capabilities = [
            AgentCapability(
                name="capability1",
                description="Test capability 1",
                required_tools=["tool1", "tool2"]
            ),
            AgentCapability(
                name="capability2",
                description="Test capability 2", 
                required_tools=["tool3"]
            )
        ]
        
        class TestAgent(BaseGraphAgent):
            async def can_handle(self, context: Dict[str, Any]) -> bool:
                return True
            
            async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
                return {"success": True}
        
        agent = TestAgent("test_agent", capabilities)
        
        # Test successful validation
        assert await agent.validate_capabilities(["tool1", "tool2"]) is True
        assert await agent.validate_capabilities(["tool1", "tool3"]) is True
        
        # Test failed validation
        assert await agent.validate_capabilities(["tool1", "tool4"]) is False

    def test_get_agent_info(self):
        """Test agent info retrieval"""
        capabilities = [
            AgentCapability(
                name="test_capability",
                description="Test capability",
                required_tools=["tool1"],
                confidence_threshold=0.9
            )
        ]
        
        class TestAgent(BaseGraphAgent):
            async def can_handle(self, context: Dict[str, Any]) -> bool:
                return True
            
            async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
                return {"success": True}
        
        agent = TestAgent("test_agent", capabilities)
        info = agent.get_agent_info()
        
        assert info["agent_id"] == "test_agent"
        assert len(info["capabilities"]) == 1
        assert info["capabilities"][0]["name"] == "test_capability"
        assert info["capabilities"][0]["confidence_threshold"] == 0.9


class TestResearchGraphAgent:
    """Test suite for research graph agent"""

    @pytest.fixture
    def research_agent(self):
        return ResearchGraphAgent()

    @pytest.mark.asyncio
    async def test_can_handle_research_routing(self, research_agent):
        """Test research agent can handle research routing"""
        context = {"routing": "research"}
        assert await research_agent.can_handle(context) is True

    @pytest.mark.asyncio
    async def test_can_handle_research_keywords(self, research_agent):
        """Test research agent can handle research keywords"""
        context = {"message": "I need to search for papers on machine learning"}
        assert await research_agent.can_handle(context) is True
        
        context = {"message": "Find literature on data analysis"}
        assert await research_agent.can_handle(context) is True
        
        context = {"message": "Hello, how are you?"}
        assert await research_agent.can_handle(context) is False

    @pytest.mark.asyncio
    async def test_handle_paper_search(self, research_agent):
        """Test paper search functionality"""
        context = {
            "task": "search for papers",
            "query": "machine learning",
            "filters": {"year": 2024}
        }
        
        result = await research_agent.execute(context)
        
        assert result["success"] is True
        assert result["operation"] == "paper_search"
        assert result["query"] == "machine learning"
        assert "results" in result
        assert "search_metadata" in result

    @pytest.mark.asyncio
    async def test_handle_literature_analysis(self, research_agent):
        """Test literature analysis functionality"""
        context = {
            "task": "analyze papers",
            "papers": [
                {"id": "paper1", "title": "Test Paper 1"},
                {"id": "paper2", "title": "Test Paper 2"}
            ],
            "analysis_type": "summary"
        }
        
        result = await research_agent.execute(context)
        
        assert result["success"] is True
        assert result["operation"] == "literature_analysis"
        assert result["analysis_type"] == "summary"
        assert result["papers_analyzed"] == 2
        assert "results" in result

    @pytest.mark.asyncio
    async def test_handle_research_synthesis(self, research_agent):
        """Test research synthesis functionality"""
        context = {
            "task": "synthesize research",
            "papers": [
                {"id": "paper1", "title": "Test Paper 1"},
                {"id": "paper2", "title": "Test Paper 2"}
            ],
            "synthesis_type": "thematic"
        }
        
        result = await research_agent.execute(context)
        
        assert result["success"] is True
        assert result["operation"] == "research_synthesis"
        assert result["synthesis_type"] == "thematic"
        assert "key_themes" in result
        assert "synthesis" in result

    @pytest.mark.asyncio
    async def test_general_research_guidance(self, research_agent):
        """Test general research guidance"""
        context = {
            "task": "general help",
            "question": "How do I start my research?"
        }
        
        result = await research_agent.execute(context)
        
        assert result["success"] is True
        assert result["operation"] == "research_guidance"
        assert "guidance" in result
        assert "recommendations" in result


class TestProjectGraphAgent:
    """Test suite for project graph agent"""

    @pytest.fixture
    def project_agent(self):
        return ProjectGraphAgent()

    @pytest.mark.asyncio
    async def test_can_handle_project_routing(self, project_agent):
        """Test project agent can handle project routing"""
        context = {"routing": "project"}
        assert await project_agent.can_handle(context) is True

    @pytest.mark.asyncio
    async def test_can_handle_project_keywords(self, project_agent):
        """Test project agent can handle project keywords"""
        context = {"message": "Create a new project for my research"}
        assert await project_agent.can_handle(context) is True
        
        context = {"message": "Manage tasks for the team"}
        assert await project_agent.can_handle(context) is True
        
        context = {"message": "Search for papers"}
        assert await project_agent.can_handle(context) is False

    @pytest.mark.asyncio
    async def test_handle_project_creation(self, project_agent):
        """Test project creation functionality"""
        context = {
            "task": "create project",
            "project_data": {
                "title": "Test Project",
                "description": "A test project for machine learning research",
                "scope": "medium"
            },
            "user_id": "user123"
        }
        
        result = await project_agent.execute(context)
        
        assert result["success"] is True
        assert result["operation"] == "project_creation"
        assert "project_metadata" in result
        assert "suggested_structure" in result
        assert "project_plan" in result

    @pytest.mark.asyncio
    async def test_handle_task_management(self, project_agent):
        """Test task management functionality"""
        context = {
            "task": "manage tasks",
            "action": "create",
            "project_id": "project123",
            "task_data": {
                "title": "New Task",
                "description": "Test task description",
                "priority": "high"
            }
        }
        
        result = await project_agent.execute(context)
        
        assert result["success"] is True
        assert result["operation"] == "task_creation"
        assert "task_id" in result
        assert result["task"]["title"] == "New Task"

    @pytest.mark.asyncio
    async def test_handle_team_collaboration(self, project_agent):
        """Test team collaboration functionality"""
        context = {
            "task": "team collaboration",
            "project_id": "project123",
            "collaboration_type": "general"
        }
        
        result = await project_agent.execute(context)
        
        assert result["success"] is True
        assert "best_practices" in result


class TestPaperGraphAgent:
    """Test suite for paper graph agent"""

    @pytest.fixture
    def paper_agent(self):
        return PaperGraphAgent()

    @pytest.mark.asyncio
    async def test_can_handle_paper_routing(self, paper_agent):
        """Test paper agent can handle paper routing"""
        context = {"routing": "paper"}
        assert await paper_agent.can_handle(context) is True

    @pytest.mark.asyncio
    async def test_can_handle_paper_keywords(self, paper_agent):
        """Test paper agent can handle paper keywords"""
        context = {"message": "Process this PDF document"}
        assert await paper_agent.can_handle(context) is True
        
        context = {"message": "Extract citations from paper"}
        assert await paper_agent.can_handle(context) is True
        
        context = {"message": "Create a new project"}
        assert await paper_agent.can_handle(context) is False

    @pytest.mark.asyncio
    async def test_handle_paper_processing(self, paper_agent):
        """Test paper processing functionality"""
        context = {
            "task": "process paper",
            "paper_data": {
                "id": "paper123",
                "title": "Test Paper",
                "authors": ["Dr. Smith", "Prof. Johnson"]
            },
            "processing_options": {"extract_figures": True}
        }
        
        result = await paper_agent.execute(context)
        
        assert result["success"] is True
        assert result["operation"] == "paper_processing"
        assert "metadata" in result
        assert "content_analysis" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_handle_annotation_management(self, paper_agent):
        """Test annotation management functionality"""
        context = {
            "task": "annotate paper",
            "action": "create",
            "paper_id": "paper123",
            "annotation_data": {
                "type": "highlight",
                "content": "Important finding",
                "position": {"page": 3, "x": 100, "y": 200}
            }
        }
        
        result = await paper_agent.execute(context)
        
        assert result["success"] is True
        assert result["operation"] == "annotation_creation"
        assert "annotation_id" in result

    @pytest.mark.asyncio
    async def test_handle_citation_extraction(self, paper_agent):
        """Test citation extraction functionality"""
        context = {
            "task": "extract citations",
            "paper_data": {
                "id": "paper123",
                "title": "Test Paper"
            },
            "extraction_options": {"include_references": True}
        }
        
        result = await paper_agent.execute(context)
        
        assert result["success"] is True
        assert result["operation"] == "citation_extraction"
        assert "citations_found" in result
        assert "citations" in result
        assert "bibliography" in result


@pytest.mark.integration
class TestAgentModulesIntegration:
    """Integration tests for agent modules"""
    
    def test_agent_modules_independence(self):
        """Test that agent modules work independently"""
        from app.agentic.graph.agents.base_agent import BaseGraphAgent
        from app.agentic.graph.agents.research_agent import ResearchGraphAgent
        from app.agentic.graph.agents.project_agent import ProjectGraphAgent
        from app.agentic.graph.agents.paper_agent import PaperGraphAgent
        
        assert BaseGraphAgent is not None
        assert ResearchGraphAgent is not None
        assert ProjectGraphAgent is not None
        assert PaperGraphAgent is not None

    @pytest.mark.asyncio
    async def test_agent_polymorphism(self):
        """Test that all agents follow the same interface"""
        agents = [
            ResearchGraphAgent(),
            ProjectGraphAgent(),
            PaperGraphAgent()
        ]
        
        test_context = {"message": "test message"}
        
        for agent in agents:
            assert isinstance(agent, BaseGraphAgent)
            # All agents should have these methods
            can_handle_result = await agent.can_handle(test_context)
            assert isinstance(can_handle_result, bool)
            
            capability_names = agent.get_capability_names()
            assert isinstance(capability_names, list)
            
            agent_info = agent.get_agent_info()
            assert isinstance(agent_info, dict)
            assert "agent_id" in agent_info
            assert "capabilities" in agent_info

    def test_error_handling_consistency(self):
        """Test that all agents use consistent error handling"""
        from app.agentic.graph.agents import research_agent, project_agent, paper_agent
        
        # Check that error handling decorators are applied
        assert hasattr(research_agent.ResearchGraphAgent.execute, '__wrapped__')
        assert hasattr(project_agent.ProjectGraphAgent.execute, '__wrapped__')
        assert hasattr(paper_agent.PaperGraphAgent.execute, '__wrapped__')

    @pytest.mark.asyncio
    async def test_agent_capability_consistency(self):
        """Test that all agents have well-defined capabilities"""
        agents = [
            ResearchGraphAgent(),
            ProjectGraphAgent(),
            PaperGraphAgent()
        ]
        
        for agent in agents:
            capabilities = agent.capabilities
            assert len(capabilities) > 0
            
            for capability in capabilities:
                assert isinstance(capability.name, str)
                assert len(capability.name) > 0
                assert isinstance(capability.description, str)
                assert len(capability.description) > 0
                assert isinstance(capability.required_tools, list)
                assert len(capability.required_tools) > 0
                assert isinstance(capability.confidence_threshold, float)
                assert 0.0 <= capability.confidence_threshold <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 
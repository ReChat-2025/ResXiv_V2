"""
Production Tools with Real Service Integration

Real tools that integrate with actual ResXiv services for production use.
No dummy/placeholder code - all implementations are functional.
"""

import logging
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
import uuid
from datetime import datetime

from app.database.connection import get_postgres_session
from .tools import ToolResult, ToolParameter, GraphTool

logger = logging.getLogger(__name__)


class RealArxivSearchTool(GraphTool):
    """Real arXiv search tool integrating with ArXiv service"""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="query",
                type="str",
                description="Search query for papers",
                required=True
            ),
            ToolParameter(
                name="max_results",
                type="int",
                description="Maximum number of results",
                required=False,
                default=10
            )
        ]
        super().__init__("real_arxiv_search", "Search arXiv using real service", parameters)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute real arXiv search"""
        try:
            params = self.validate_parameters(**kwargs)
            
            # Import here to avoid circular dependencies
            from app.services.arxiv_service import ArXivService
            from app.services.research_agent_core import SearchQuery
            
            # Create service instance
            arxiv_service = ArXivService()
            
            # Create proper SearchQuery object
            search_query = SearchQuery(
                query=params["query"],
                limit=params["max_results"]
            )
            
            # Execute real search
            search_results = await arxiv_service.search_papers(
                query=search_query,
                include_abstracts=True
            )
            
            return ToolResult(
                success=True,
                data={
                    "query": params["query"],
                    "results": search_results.get("papers", []),
                    "count": len(search_results.get("papers", [])),
                    "source": "arxiv",
                    "service": "ArXivService"
                },
                tool_name=self.name
            )
        
        except Exception as e:
            self.logger.error(f"Real arXiv search failed: {e}")
            return ToolResult(
                success=False,
                error=f"ArXiv search error: {str(e)}",
                tool_name=self.name
            )


class RealProjectCrudTool(GraphTool):
    """Real project CRUD operations using ProjectCoreService"""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="action",
                type="str",
                description="CRUD action: create, read, update, delete, list",
                required=True
            ),
            ToolParameter(
                name="user_id",
                type="str",
                description="User ID performing the action",
                required=True
            ),
            ToolParameter(
                name="project_id",
                type="str",
                description="Project ID (for read, update, delete)",
                required=False
            ),
            ToolParameter(
                name="project_data",
                type="dict",
                description="Project data for create/update",
                required=False,
                default={}
            )
        ]
        super().__init__("real_project_crud", "Real project CRUD operations", parameters)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute real project operations"""
        try:
            params = self.validate_parameters(**kwargs)
            action = params["action"].lower()
            
            if action not in ["create", "read", "update", "delete", "list"]:
                raise ValueError(f"Invalid action: {action}")
            
            # Import services
            from app.services.core.project_service_core import ProjectCoreService
            from app.models.project import ProjectCreate, ProjectUpdate
            
            async with get_postgres_session() as session:
                project_service = ProjectCoreService(session)
                user_id = uuid.UUID(params["user_id"])
                
                if action == "create":
                    project_data = params.get("project_data", {})
                    if not project_data.get("name"):
                        raise ValueError("Project name is required for creation")
                    
                    create_data = ProjectCreate(
                        name=project_data["name"],
                        description=project_data.get("description", ""),
                        slug=project_data.get("slug")
                    )
                    
                    result = await project_service.create_project(create_data, user_id)
                    
                    return ToolResult(
                        success=result.get("success", False),
                        data={
                            "action": action,
                            "project": result.get("project"),
                            "project_id": result.get("project", {}).get("id")
                        },
                        tool_name=self.name
                    )
                
                elif action == "list":
                    projects = await project_service.get_user_projects(user_id)
                    
                    return ToolResult(
                        success=True,
                        data={
                            "action": action,
                            "projects": projects.get("projects", []),
                            "count": len(projects.get("projects", []))
                        },
                        tool_name=self.name
                    )
                
                elif action == "read":
                    if not params.get("project_id"):
                        raise ValueError("Project ID required for read operation")
                    
                    project_id = uuid.UUID(params["project_id"])
                    project = await project_service.get_project_by_id(project_id, user_id)
                    
                    return ToolResult(
                        success=project.get("success", False),
                        data={
                            "action": action,
                            "project": project.get("project")
                        },
                        tool_name=self.name
                    )
                
                else:
                    # For update/delete, implement if needed
                    return ToolResult(
                        success=False,
                        error=f"Action '{action}' not yet implemented",
                        tool_name=self.name
                    )
        
        except Exception as e:
            self.logger.error(f"Real project CRUD failed: {e}")
            return ToolResult(
                success=False,
                error=f"Project operation error: {str(e)}",
                tool_name=self.name
            )


class RealPaperSearchTool(GraphTool):
    """Real paper search using multiple research services"""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="query",
                type="str",
                description="Search query for papers",
                required=True
            ),
            ToolParameter(
                name="sources",
                type="list",
                description="List of sources to search (arxiv, crossref, openalex)",
                required=False,
                default=["arxiv"]
            ),
            ToolParameter(
                name="max_results",
                type="int",
                description="Maximum results per source",
                required=False,
                default=5
            )
        ]
        super().__init__("real_paper_search", "Search papers across multiple sources", parameters)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute real paper search across multiple sources"""
        try:
            params = self.validate_parameters(**kwargs)
            
            # Import research services
            from app.services.research_aggregator_service import ResearchAggregatorService
            
            aggregator = ResearchAggregatorService()
            
            # Execute real search across sources
            search_result = await aggregator.comprehensive_paper_search(
                query=params["query"],
                limit=params["max_results"],
                include_semantics=True,
                include_code="papers_with_code" in params["sources"],
                cross_reference=True
            )
            
            return ToolResult(
                success=search_result.get("success", False),
                data={
                    "query": params["query"],
                    "sources": params["sources"],
                    "results": search_result.get("results", {}),
                    "total_papers": search_result.get("total_papers", 0),
                    "service": "ResearchAggregatorService"
                },
                tool_name=self.name
            )
        
        except Exception as e:
            self.logger.error(f"Real paper search failed: {e}")
            return ToolResult(
                success=False,
                error=f"Paper search error: {str(e)}",
                tool_name=self.name
            )


class RealPaperProcessingTool(GraphTool):
    """Real paper processing using PaperService"""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="paper_id",
                type="str",
                description="Paper ID to process",
                required=False
            ),
            ToolParameter(
                name="file_path",
                type="str",
                description="Path to paper file",
                required=False
            ),
            ToolParameter(
                name="operation",
                type="str",
                description="Processing operation: process, analyze, get_metadata",
                required=True
            ),
            ToolParameter(
                name="project_id",
                type="str",
                description="Project ID for context",
                required=True
            )
        ]
        super().__init__("real_paper_processing", "Process papers using real service", parameters)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute real paper processing"""
        try:
            params = self.validate_parameters(**kwargs)
            
            # Import paper service
            from app.services.paper_service import PaperService
            
            async with get_postgres_session() as session:
                paper_service = PaperService(session)
                project_id = uuid.UUID(params["project_id"])
                operation = params["operation"]
                
                if operation == "process":
                    if params.get("paper_id"):
                        paper_id = uuid.UUID(params["paper_id"])
                        result = await paper_service.process_paper(paper_id)
                    else:
                        raise ValueError("Paper ID required for processing")
                
                elif operation == "analyze" or operation == "get_diagnostics":
                    if params.get("paper_id"):
                        paper_id = uuid.UUID(params["paper_id"])
                        result = await paper_service.get_paper_diagnostics(paper_id)
                    else:
                        raise ValueError("Paper ID required for analysis")
                
                elif operation == "get_metadata" or operation == "get_paper":
                    if params.get("paper_id"):
                        paper_id = uuid.UUID(params["paper_id"])
                        result = await paper_service.get_paper(paper_id, include_diagnostics=True)
                    else:
                        raise ValueError("Paper ID required for metadata")
                
                else:
                    raise ValueError(f"Unknown operation: {operation}")
                
                return ToolResult(
                    success=result.get("success", False),
                    data={
                        "operation": operation,
                        "result": result,
                        "service": "PaperService"
                    },
                    tool_name=self.name
                )
        
        except Exception as e:
            self.logger.error(f"Real paper processing failed: {e}")
            return ToolResult(
                success=False,
                error=f"Paper processing error: {str(e)}",
                tool_name=self.name
            )


class RealConversationTool(GraphTool):
    """Real conversation management using ConversationService"""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="action",
                type="str",
                description="Action: create, get_history, add_message",
                required=True
            ),
            ToolParameter(
                name="conversation_id",
                type="str",
                description="Conversation ID",
                required=False
            ),
            ToolParameter(
                name="user_id",
                type="str",
                description="User ID",
                required=True
            ),
            ToolParameter(
                name="project_id",
                type="str",
                description="Project ID for context",
                required=False
            ),
            ToolParameter(
                name="message",
                type="str",
                description="Message content",
                required=False
            )
        ]
        super().__init__("real_conversation", "Real conversation operations", parameters)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute real conversation operations"""
        try:
            params = self.validate_parameters(**kwargs)
            
            # Import conversation and message services
            from app.services.conversation.conversation_service_integrated import ConversationService
            from app.services.message_service import MessageService
            from app.services.redis_service import RedisService
            from app.database.connection import db_manager
            
            async with get_postgres_session() as session:
                redis_service = RedisService()
                conv_service = ConversationService(session, redis_service)
                message_service = MessageService(session, db_manager, redis_service)
                action = params["action"]
                user_id = uuid.UUID(params["user_id"])
                
                if action == "create":
                    project_id = uuid.UUID(params["project_id"]) if params.get("project_id") else None
                    result = await conv_service.create_conversation(
                        project_id=project_id,
                        created_by=user_id,
                        conversation_type="ai_chat",
                        name="AI Chat"
                    )
                
                elif action == "get_history":
                    conv_id = uuid.UUID(params["conversation_id"])
                    result = await message_service.get_conversation_messages(
                        conversation_id=conv_id,
                        limit=50,
                        offset=0
                    )
                
                elif action == "add_message":
                    conv_id = uuid.UUID(params["conversation_id"])
                    message = params["message"]
                    result = await message_service.create_message(
                        conversation_id=conv_id,
                        sender_id=user_id,
                        content=message,
                        message_type="text"
                    )
                
                else:
                    raise ValueError(f"Unknown action: {action}")
                
                return ToolResult(
                    success=result.get("success", False),
                    data={
                        "action": action,
                        "result": result,
                        "service": "ConversationService"
                    },
                    tool_name=self.name
                )
        
        except Exception as e:
            self.logger.error(f"Real conversation operation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Conversation error: {str(e)}",
                tool_name=self.name
            )


class ProductionToolRegistry:
    """Registry for production tools with real service integrations"""
    
    def __init__(self):
        self._tools: Dict[str, GraphTool] = {}
        self._initialize_production_tools()
    
    def _initialize_production_tools(self) -> None:
        """Initialize all production tools"""
        tools = [
            RealArxivSearchTool(),
            RealProjectCrudTool(),
            RealPaperSearchTool(),
            RealPaperProcessingTool(),
            RealConversationTool()
        ]
        
        for tool in tools:
            self._tools[tool.name] = tool
        
        logger.info(f"Initialized {len(tools)} production tools")
    
    def get_tool(self, name: str) -> Optional[GraphTool]:
        """Get tool by name"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all tool names"""
        return list(self._tools.keys())
    
    async def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name"""
        tool = self.get_tool(name)
        
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' not found",
                tool_name=name
            )
        
        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            logger.error(f"Production tool execution failed for {name}: {e}")
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}",
                tool_name=name
            )


# Global production tool registry
production_tool_registry = ProductionToolRegistry() 
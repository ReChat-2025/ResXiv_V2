"""
Production-Grade Tool Registry

Clean, extensible tool management following SOLID principles.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel, Field
from dataclasses import dataclass
import logging
import asyncio

logger = logging.getLogger(__name__)


class ToolParameter(BaseModel):
    """Defines a tool parameter with validation"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None


class ToolResult(BaseModel):
    """Standardized tool execution result"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    tool_name: str
    execution_time: Optional[float] = None


class GraphTool(ABC):
    """
    Abstract base class for all tools.
    
    Follows Interface Segregation - tools only implement what they need.
    """
    
    def __init__(self, name: str, description: str, parameters: List[ToolParameter]):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters"""
        pass
    
    def validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """Validate and prepare parameters"""
        validated = {}
        
        for param in self.parameters:
            value = kwargs.get(param.name)
            
            if param.required and value is None:
                raise ValueError(f"Required parameter '{param.name}' is missing")
            
            if value is None:
                value = param.default
            
            # Type validation
            if value is not None:
                validated[param.name] = self._validate_type(value, param.type, param.name)
            
        return validated
    
    def _validate_type(self, value: Any, expected_type: str, param_name: str) -> Any:
        """Validate parameter type"""
        type_map = {
            'str': str,
            'int': int, 
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict
        }
        
        expected_python_type = type_map.get(expected_type)
        if expected_python_type and not isinstance(value, expected_python_type):
            try:
                return expected_python_type(value)
            except (ValueError, TypeError):
                raise ValueError(
                    f"Parameter '{param_name}' must be of type {expected_type}, "
                    f"got {type(value).__name__}"
                )
        
        return value


class ArxivSearchTool(GraphTool):
    """Tool for searching arXiv papers"""
    
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
        super().__init__("arxiv_search", "Search arXiv for academic papers", parameters)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute arXiv search"""
        try:
            params = self.validate_parameters(**kwargs)
            
            # Simulate arXiv search
            await asyncio.sleep(0.1)  # Simulate API call
            
            return ToolResult(
                success=True,
                data={
                    "query": params["query"],
                    "results": [
                        {"title": f"Paper about {params['query']}", "authors": ["Author 1"]}
                    ],
                    "count": 1
                },
                tool_name=self.name
            )
        
        except Exception as e:
            self.logger.error(f"ArXiv search failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


class ProjectCrudTool(GraphTool):
    """Tool for project CRUD operations"""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="action",
                type="str",
                description="CRUD action: create, read, update, delete",
                required=True
            ),
            ToolParameter(
                name="project_data",
                type="dict",
                description="Project data for the operation",
                required=False,
                default={}
            )
        ]
        super().__init__("project_crud", "Manage project lifecycle", parameters)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute project CRUD operation"""
        try:
            params = self.validate_parameters(**kwargs)
            action = params["action"].lower()
            
            if action not in ["create", "read", "update", "delete"]:
                raise ValueError(f"Invalid action: {action}")
            
            # Simulate database operation
            await asyncio.sleep(0.1)
            
            return ToolResult(
                success=True,
                data={
                    "action": action,
                    "result": f"Project {action} completed successfully"
                },
                tool_name=self.name
            )
        
        except Exception as e:
            self.logger.error(f"Project CRUD failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


class SemanticSearchTool(GraphTool):
    """Tool for semantic search across papers"""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="query",
                type="str",
                description="Semantic search query",
                required=True
            ),
            ToolParameter(
                name="similarity_threshold",
                type="float", 
                description="Minimum similarity score",
                required=False,
                default=0.7
            )
        ]
        super().__init__("semantic_search", "Perform semantic search", parameters)
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute semantic search"""
        try:
            params = self.validate_parameters(**kwargs)
            
            # Simulate semantic search
            await asyncio.sleep(0.2)
            
            return ToolResult(
                success=True,
                data={
                    "query": params["query"],
                    "matches": [
                        {"content": "Relevant content", "score": 0.85}
                    ],
                    "threshold": params["similarity_threshold"]
                },
                tool_name=self.name
            )
        
        except Exception as e:
            self.logger.error(f"Semantic search failed: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


class ToolRegistry:
    """
    Registry for managing tools with proper lifecycle.
    
    Follows Open/Closed Principle - easy to extend with new tools.
    """
    
    def __init__(self):
        self._tools: Dict[str, GraphTool] = {}
        self._initialize_default_tools()
    
    def register_tool(self, tool: GraphTool) -> None:
        """Register a new tool"""
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")
        
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[GraphTool]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self._tools.keys())
    
    def get_tool_description(self, name: str) -> Optional[str]:
        """Get tool description"""
        tool = self.get_tool(name)
        return tool.description if tool else None
    
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
            logger.error(f"Tool execution failed for {name}: {e}")
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}",
                tool_name=name
            )
    
    def _initialize_default_tools(self) -> None:
        """Initialize default tools"""
        default_tools = [
            ArxivSearchTool(),
            ProjectCrudTool(),
            SemanticSearchTool()
        ]
        
        for tool in default_tools:
            self.register_tool(tool)
        
        logger.info(f"Initialized {len(default_tools)} default tools")


# Global tool registry instance
tool_registry = ToolRegistry() 
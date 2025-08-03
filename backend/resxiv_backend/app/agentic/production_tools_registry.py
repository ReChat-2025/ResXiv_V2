"""
Production-Grade Tools Registry

L6 implementation featuring:
- Dynamic tool registration and discovery
- Performance caching with TTL
- Rate limiting and error recovery
- Tool execution monitoring
- Thread-safe operations

Follows SOLID principles:
- Single Responsibility: Tool management only
- Open/Closed: Easy to add new tools
- Liskov Substitution: Consistent tool interface
- Interface Segregation: Minimal tool contracts
- Dependency Inversion: Abstract tool definitions
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Union, TypeVar, Generic
import uuid
import json
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ToolCategory(str, Enum):
    """Tool categorization for organization and routing"""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    FILE_OPERATIONS = "file_operations"
    PROJECT_MANAGEMENT = "project_management"
    COMMUNICATION = "communication"
    DATA_PROCESSING = "data_processing"
    EXTERNAL_API = "external_api"


class ToolStatus(str, Enum):
    """Tool execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


@dataclass
class ToolExecutionMetrics:
    """Performance metrics for tool execution"""
    tool_name: str
    execution_count: int = 0
    total_execution_time: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    average_execution_time: float = 0.0
    last_execution: Optional[datetime] = None
    last_error: Optional[str] = None
    
    def record_execution(self, execution_time: float, success: bool, error: Optional[str] = None):
        """Record a tool execution for metrics"""
        self.execution_count += 1
        self.total_execution_time += execution_time
        
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
            self.last_error = error
        
        self.average_execution_time = self.total_execution_time / self.execution_count
        self.last_execution = datetime.utcnow()


@dataclass
class CacheEntry:
    """Cache entry with TTL support"""
    value: Any
    created_at: datetime
    ttl_seconds: int
    access_count: int = 0
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return datetime.utcnow() > self.created_at + timedelta(seconds=self.ttl_seconds)
    
    def access(self) -> Any:
        """Access cached value and increment counter"""
        self.access_count += 1
        return self.value


class RateLimiter:
    """Token bucket rate limiter for tool execution"""
    
    def __init__(self, max_tokens: int = 100, refill_rate: float = 10.0):
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.tokens = max_tokens
        self.last_refill = time.time()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens for execution"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Refill tokens
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class ProductionTool(ABC):
    """
    Abstract base class for production-grade tools.
    
    Implements common functionality:
    - Execution tracking
    - Error handling
    - Rate limiting
    - Caching support
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        rate_limit: Optional[RateLimiter] = None,
        cache_ttl: int = 300,  # 5 minutes default
        timeout: float = 30.0,
        retries: int = 3
    ):
        self.name = name
        self.description = description
        self.category = category
        self.rate_limiter = rate_limit or RateLimiter(max_tokens=50, refill_rate=5.0)
        self.cache_ttl = cache_ttl
        self.timeout = timeout
        self.retries = retries
        self.metrics = ToolExecutionMetrics(tool_name=name)
        self._cache: Dict[str, CacheEntry] = {}
    
    def _cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = {"args": args, "kwargs": kwargs}
        return f"{self.name}:{hash(json.dumps(key_data, sort_keys=True, default=str))}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if available and not expired"""
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if not entry.is_expired:
                return entry.access()
            else:
                # Remove expired entry
                del self._cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: Any) -> None:
        """Cache execution result"""
        self._cache[cache_key] = CacheEntry(
            value=result,
            created_at=datetime.utcnow(),
            ttl_seconds=self.cache_ttl
        )
    
    @abstractmethod
    async def _execute_impl(self, *args, **kwargs) -> Dict[str, Any]:
        """Implementation-specific execution logic"""
        pass
    
    async def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute tool with full production features:
        - Rate limiting
        - Caching
        - Error handling with retries
        - Performance monitoring
        """
        start_time = time.time()
        cache_key = self._cache_key(*args, **kwargs)
        
        try:
            # Check cache first
            cached_result = self._get_cached_result(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for tool {self.name}")
                return cached_result
            
            # Rate limiting
            if not await self.rate_limiter.acquire():
                raise ToolExecutionError(f"Rate limit exceeded for tool {self.name}")
            
            # Execute with retries
            last_error = None
            for attempt in range(self.retries + 1):
                try:
                    # Execute with timeout
                    result = await asyncio.wait_for(
                        self._execute_impl(*args, **kwargs),
                        timeout=self.timeout
                    )
                    
                    # Cache successful result
                    self._cache_result(cache_key, result)
                    
                    # Record metrics
                    execution_time = time.time() - start_time
                    self.metrics.record_execution(execution_time, True)
                    
                    logger.debug(f"Tool {self.name} executed successfully in {execution_time:.3f}s")
                    return result
                    
                except asyncio.TimeoutError:
                    last_error = f"Tool execution timeout after {self.timeout}s"
                    if attempt < self.retries:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    break
                except Exception as e:
                    last_error = str(e)
                    if attempt < self.retries:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    break
            
            # All retries failed
            execution_time = time.time() - start_time
            self.metrics.record_execution(execution_time, False, last_error)
            
            raise ToolExecutionError(f"Tool {self.name} failed after {self.retries + 1} attempts: {last_error}")
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.metrics.record_execution(execution_time, False, str(e))
            logger.error(f"Tool {self.name} execution failed: {e}")
            raise


class ToolExecutionError(Exception):
    """Custom exception for tool execution failures"""
    pass


class ResearchTool(ProductionTool):
    """Example research tool implementation"""
    
    def __init__(self):
        super().__init__(
            name="research_papers",
            description="Search and analyze academic papers",
            category=ToolCategory.RESEARCH,
            cache_ttl=600,  # 10 minutes for research results
            timeout=45.0    # Longer timeout for research
        )
    
    async def _execute_impl(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Simulate research paper search"""
        await asyncio.sleep(0.1)  # Simulate API call
        
        return {
            "tool": self.name,
            "query": query,
            "results": [
                {
                    "title": f"Research Paper {i}",
                    "authors": ["Author A", "Author B"],
                    "abstract": f"Abstract for paper {i} related to {query}",
                    "relevance_score": 0.9 - (i * 0.1)
                }
                for i in range(min(limit, 5))
            ],
            "total_found": limit,
            "execution_time": 0.1
        }


class AnalysisTool(ProductionTool):
    """Example analysis tool implementation"""
    
    def __init__(self):
        super().__init__(
            name="analyze_data",
            description="Perform data analysis and generate insights",
            category=ToolCategory.ANALYSIS,
            cache_ttl=300,
            timeout=30.0
        )
    
    async def _execute_impl(self, data: Dict[str, Any], analysis_type: str = "summary") -> Dict[str, Any]:
        """Simulate data analysis"""
        await asyncio.sleep(0.2)  # Simulate processing
        
        return {
            "tool": self.name,
            "analysis_type": analysis_type,
            "insights": [
                "Key insight 1 from data analysis",
                "Key insight 2 from data analysis", 
                "Key insight 3 from data analysis"
            ],
            "metrics": {
                "data_points": len(str(data)),
                "confidence": 0.85,
                "processing_time": 0.2
            }
        }


class ProductionToolsRegistry:
    """
    Production-grade tools registry with advanced features:
    - Thread-safe tool registration and execution
    - Performance monitoring and metrics
    - Tool discovery and categorization
    - Health checking and diagnostics
    """
    
    def __init__(self):
        self._tools: Dict[str, ProductionTool] = {}
        self._categories: Dict[ToolCategory, List[str]] = defaultdict(list)
        self._global_metrics = defaultdict(int)
        self._lock = asyncio.Lock()
        
        # Register default tools
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default production tools"""
        default_tools = [
            ResearchTool(),
            AnalysisTool()
        ]
        
        for tool in default_tools:
            self.register_tool(tool)
    
    def register_tool(self, tool: ProductionTool) -> None:
        """Register a tool in the registry"""
        self._tools[tool.name] = tool
        self._categories[tool.category].append(tool.name)
        logger.info(f"Registered tool: {tool.name} (category: {tool.category})")
    
    def get_tool(self, name: str) -> Optional[ProductionTool]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[str]:
        """List available tools, optionally filtered by category"""
        if category:
            return self._categories.get(category, [])
        return list(self._tools.keys())
    
    def get_tools_by_category(self, category: ToolCategory) -> List[ProductionTool]:
        """Get all tools in a specific category"""
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    async def execute_tool(self, tool_name: str, *args, **kwargs) -> Dict[str, Any]:
        """Execute a tool with full monitoring"""
        async with self._lock:
            tool = self.get_tool(tool_name)
            if not tool:
                raise ToolExecutionError(f"Tool '{tool_name}' not found")
            
            # Update global metrics
            self._global_metrics["total_executions"] += 1
            
            try:
                result = await tool.execute(*args, **kwargs)
                self._global_metrics["successful_executions"] += 1
                return result
            except Exception as e:
                self._global_metrics["failed_executions"] += 1
                raise
    
    def get_tool_metrics(self, tool_name: str) -> Optional[ToolExecutionMetrics]:
        """Get metrics for a specific tool"""
        tool = self.get_tool(tool_name)
        return tool.metrics if tool else None
    
    def get_global_metrics(self) -> Dict[str, Any]:
        """Get global registry metrics"""
        total = self._global_metrics["total_executions"]
        successful = self._global_metrics["successful_executions"]
        failed = self._global_metrics["failed_executions"]
        
        return {
            "total_tools": len(self._tools),
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "tools_by_category": {
                category.value: len(tools) 
                for category, tools in self._categories.items()
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all tools"""
        health_status = {
            "registry_status": "healthy",
            "total_tools": len(self._tools),
            "tool_health": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Check each tool's metrics
        for tool_name, tool in self._tools.items():
            metrics = tool.metrics
            tool_health = {
                "status": "healthy",
                "execution_count": metrics.execution_count,
                "success_rate": (metrics.success_count / metrics.execution_count * 100) if metrics.execution_count > 0 else 100,
                "average_execution_time": metrics.average_execution_time,
                "last_execution": metrics.last_execution.isoformat() if metrics.last_execution else None
            }
            
            # Mark as unhealthy if success rate is too low
            if metrics.execution_count > 10 and tool_health["success_rate"] < 80:
                tool_health["status"] = "unhealthy"
                tool_health["issue"] = "Low success rate"
            
            health_status["tool_health"][tool_name] = tool_health
        
        return health_status
    
    def clear_caches(self) -> Dict[str, int]:
        """Clear all tool caches and return cache statistics"""
        cache_stats = {}
        
        for tool_name, tool in self._tools.items():
            cache_size = len(tool._cache)
            tool._cache.clear()
            cache_stats[tool_name] = cache_size
        
        logger.info(f"Cleared caches for {len(self._tools)} tools")
        return cache_stats


# Global registry instance
tools_registry = ProductionToolsRegistry()


def get_tools_registry() -> ProductionToolsRegistry:
    """Get the global tools registry instance"""
    return tools_registry 
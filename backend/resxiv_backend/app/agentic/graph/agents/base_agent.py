"""
Base Graph Agent - L6 Engineering Standards

Abstract base class for all graph agents implementing L6 patterns.
Extracted from bloated agents.py for SOLID compliance.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass

from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes

logger = logging.getLogger(__name__)


@dataclass
class AgentCapability:
    """Defines what an agent can do"""
    name: str
    description: str
    required_tools: List[str]
    confidence_threshold: float = 0.7


class BaseGraphAgent(ABC):
    """
    Base class for all graph agents implementing L6 patterns.
    
    Single Responsibility: Define agent interface
    Open/Closed: Easy to extend with new agents
    Liskov Substitution: All agents interchangeable
    Interface Segregation: Minimal, focused interface
    Dependency Inversion: Depends on abstractions
    """
    
    def __init__(self, agent_id: str, capabilities: List[AgentCapability]):
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.logger = logging.getLogger(f"agent.{agent_id}")
    
    @abstractmethod
    async def can_handle(self, context: Dict[str, Any]) -> bool:
        """Check if this agent can handle the given context"""
        pass
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's functionality"""
        pass
    
    def get_capability_names(self) -> List[str]:
        """Get list of capability names"""
        return [cap.name for cap in self.capabilities]

    @handle_service_errors("agent capability check")
    async def validate_capabilities(self, required_tools: List[str]) -> bool:
        """Validate that agent has required capabilities"""
        available_tools = []
        for capability in self.capabilities:
            available_tools.extend(capability.required_tools)
        
        return all(tool in available_tools for tool in required_tools)

    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information"""
        return {
            "agent_id": self.agent_id,
            "capabilities": [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "required_tools": cap.required_tools,
                    "confidence_threshold": cap.confidence_threshold
                }
                for cap in self.capabilities
            ]
        } 
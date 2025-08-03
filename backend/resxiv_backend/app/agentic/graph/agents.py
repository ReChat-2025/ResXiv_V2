"""
Graph Agents - L6 Engineering Standards

Clean, focused module replacing the previous 836-line monolithic file.
Imports from modular components following SOLID principles.
"""

# Import all agents from the modular structure
from .agents.base_agent import BaseGraphAgent, AgentCapability
from .agents.research_agent import ResearchGraphAgent
from .agents.project_agent import ProjectGraphAgent
from .agents.paper_agent import PaperGraphAgent

# Export for compatibility
__all__ = [
    "BaseGraphAgent",
    "AgentCapability", 
    "ResearchGraphAgent",
    "ProjectGraphAgent",
    "PaperGraphAgent"
] 
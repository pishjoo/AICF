"""
AICF v2 Agents Module

AI Agent system for content production workflow.

Architecture:
    BaseAgent (interface)
        |
    +-- IdeaAgent
    +-- ResearchAgent
    +-- ScriptAgent
    +-- StoryboardAgent
    +-- AssetAgent
    +-- VideoAgent
    +-- SEOAgent
    +-- PublishAgent
        |
    AgentRegistry
        |
    AI Provider Runtime
"""

from .base import BaseAgent, AgentContext, AgentResult
from .provider import AgentProvider
from .registry import AgentRegistry

__all__ = [
    "BaseAgent",
    "AgentContext", 
    "AgentResult",
    "AgentProvider",
    "AgentRegistry"
]

"""
Agent Provider

Provider interface for AI agent execution runtime.
Handles the actual invocation of AI models through various providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging


class AgentProvider(ABC):
    """
    Abstract provider for AI agent execution.
    
    Providers handle the actual AI model invocation.
    Different implementations can support different AI backends:
    - OpenAI
    - Anthropic
    - Local models
    - Mock provider for testing
    """
    
    name: str = "base_provider"
    
    def __init__(self):
        self.logger = logging.getLogger(f"agent_provider.{self.name}")
    
    @abstractmethod
    def execute(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an AI request.
        
        Args:
            prompt: The prompt to send to the AI.
            context: Additional context data.
            
        Returns:
            Dictionary with AI response.
        """
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """
        Validate the provider connection.
        
        Returns:
            True if connection is valid.
        """
        pass
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get provider capabilities."""
        return {
            "name": self.name,
            "supports_streaming": False,
            "max_tokens": 4096,
            "models": []
        }


class MockAgentProvider(AgentProvider):
    """
    Mock provider for testing and development.
    
    Returns predefined mock responses without calling external APIs.
    """
    
    name = "mock_provider"
    
    def __init__(self, mock_responses: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.mock_responses = mock_responses or {}
    
    def execute(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Return mock response based on context."""
        stage_type = context.get("stage_type", "unknown")
        
        # Return predefined mock response or default
        if stage_type in self.mock_responses:
            return self.mock_responses[stage_type]
        
        # Default mock response
        return {
            "success": True,
            "data": {"mock_output": f"Mock response for {stage_type}"},
            "tokens_used": 100
        }
    
    def validate_connection(self) -> bool:
        """Mock provider always has valid connection."""
        return True
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get mock provider capabilities."""
        return {
            "name": self.name,
            "supports_streaming": False,
            "max_tokens": 4096,
            "models": ["mock-v1"],
            "is_mock": True
        }

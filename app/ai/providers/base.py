"""
AI Provider Abstraction Layer - Base Provider Interface

This module defines the abstract base class for all AI providers in AICF v2.
All concrete provider implementations must inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class AIRequest:
    """
    Standardized AI request schema.
    
    Attributes:
        organization_id: Tenant identifier for isolation
        agent_type: Type of agent making the request
        prompt: The main prompt/instruction
        context: AIContext object or dict with contextual information
        memory: Historical data and previous interactions
        parameters: Model-specific parameters (temperature, max_tokens, etc.)
    """
    organization_id: int
    agent_type: str
    prompt: str
    context: Optional[Dict[str, Any]] = None
    memory: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert request to dictionary format."""
        return {
            "request_id": self.request_id,
            "organization_id": self.organization_id,
            "agent_type": self.agent_type,
            "prompt": self.prompt,
            "context": self.context,
            "memory": self.memory,
            "parameters": self.parameters or {},
            "created_at": self.created_at.isoformat()
        }


@dataclass
class AIResponse:
    """
    Standardized AI response schema.
    
    Attributes:
        content: Generated content (text, structured data, etc.)
        provider: Name of the AI provider used
        model: Specific model identifier
        tokens: Token usage information
        cost: Cost incurred for this generation
        execution_time: Time taken in seconds
        metadata: Additional response metadata
    """
    content: Any
    provider: str
    model: str
    tokens: Dict[str, int] = field(default_factory=dict)
    cost: float = 0.0
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format."""
        return {
            "response_id": self.response_id,
            "content": self.content,
            "provider": self.provider,
            "model": self.model,
            "tokens": self.tokens,
            "cost": self.cost,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ModelInfo:
    """Information about an AI model."""
    provider: str
    model_id: str
    name: str
    max_tokens: int
    supports_streaming: bool
    supports_vision: bool
    supports_function_calling: bool
    context_window: int
    pricing: Dict[str, float] = field(default_factory=dict)  # per 1K tokens


class BaseProvider(ABC):
    """
    Abstract base class for AI providers.
    
    All AI provider implementations must inherit from this class
    and implement the required abstract methods.
    
    This abstraction allows agents to work with any provider
    without hard dependencies.
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        """
        Initialize the provider.
        
        Args:
            api_key: API key for authentication (if applicable)
            base_url: Base URL for API calls (if applicable)
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.base_url = base_url
        self.config = kwargs
        self._initialized = False
    
    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse:
        """
        Generate a complete response from the AI model.
        
        Args:
            request: AIRequest object containing prompt and context
            
        Returns:
            AIResponse object with generated content and metadata
            
        Raises:
            ProviderError: If generation fails
        """
        pass
    
    @abstractmethod
    def stream(self, request: AIRequest) -> Generator[str, None, None]:
        """
        Stream response chunks from the AI model.
        
        Args:
            request: AIRequest object containing prompt and context
            
        Yields:
            String chunks of the generated content
            
        Raises:
            ProviderError: If streaming fails
        """
        pass
    
    @abstractmethod
    async def generate_async(self, request: AIRequest) -> AIResponse:
        """
        Async version of generate.
        
        Args:
            request: AIRequest object containing prompt and context
            
        Returns:
            AIResponse object with generated content and metadata
        """
        pass
    
    @abstractmethod
    async def stream_async(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """
        Async version of stream.
        
        Args:
            request: AIRequest object containing prompt and context
            
        Yields:
            String chunks of the generated content
        """
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """
        Validate the connection to the AI provider.
        
        Returns:
            True if connection is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_model_info(self, model_id: str) -> ModelInfo:
        """
        Get information about a specific model.
        
        Args:
            model_id: Identifier of the model
            
        Returns:
            ModelInfo object with model details
        """
        pass
    
    @abstractmethod
    def list_available_models(self) -> list:
        """
        List all available models for this provider.
        
        Returns:
            List of model identifiers
        """
        pass
    
    def get_provider_name(self) -> str:
        """
        Get the name of this provider.
        
        Returns:
            Provider name string
        """
        return self.__class__.__name__.replace("Provider", "").lower()
    
    def _validate_request(self, request: AIRequest) -> None:
        """
        Validate an AI request before processing.
        
        Args:
            request: AIRequest object to validate
            
        Raises:
            ValueError: If request is invalid
        """
        if not request.prompt:
            raise ValueError("Prompt cannot be empty")
        if not request.organization_id:
            raise ValueError("Organization ID is required")
        if not request.agent_type:
            raise ValueError("Agent type is required")


class ProviderError(Exception):
    """Base exception for provider-related errors."""
    
    def __init__(self, message: str, code: Optional[str] = None, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.original_error = original_error


class ProviderConfigurationError(ProviderError):
    """Raised when provider configuration is invalid."""
    pass


class ProviderConnectionError(ProviderError):
    """Raised when connection to provider fails."""
    pass


class ProviderRateLimitError(ProviderError):
    """Raised when rate limit is exceeded."""
    pass


class ProviderAuthenticationError(ProviderError):
    """Raised when authentication fails."""
    pass

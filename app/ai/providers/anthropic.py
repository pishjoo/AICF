"""
Anthropic Provider Implementation

This module implements the Anthropic provider for AICF v2.
Supports Claude 3 family models (Opus, Sonnet, Haiku).
"""

import time
from typing import Any, Dict, Generator, List, Optional, AsyncGenerator

from app.ai.providers.base import (
    BaseProvider,
    AIRequest,
    AIResponse,
    ModelInfo,
    ProviderError,
    ProviderConnectionError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
)


class AnthropicProvider(BaseProvider):
    """
    Anthropic provider implementation.
    
    Supports:
    - Claude 3 Opus
    - Claude 3 Sonnet
    - Claude 3 Haiku
    - Streaming responses
    - Token usage tracking
    - Cost calculation
    """
    
    PROVIDER_NAME = "anthropic"
    
    DEFAULT_MODELS = {
        "claude-3-opus-20240229": {"max_tokens": 4096, "context_window": 200000},
        "claude-3-sonnet-20240229": {"max_tokens": 4096, "context_window": 200000},
        "claude-3-haiku-20240307": {"max_tokens": 4096, "context_window": 200000},
        "claude-3-5-sonnet-20241022": {"max_tokens": 8192, "context_window": 200000},
        "claude-3-5-haiku-20241022": {"max_tokens": 8192, "context_window": 200000},
    }
    
    PRICING = {
        # Per 1K tokens (USD)
        "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
        "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
        "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005},
    }
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
        self._client = None
        self._async_client = None
    
    def _get_client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(
                    api_key=self.api_key,
                    base_url=self.base_url or "https://api.anthropic.com",
                )
                self._initialized = True
            except ImportError:
                raise ProviderConfigurationError(
                    "Anthropic package not installed. Run: pip install anthropic"
                )
        return self._client
    
    async def _get_async_client(self):
        """Lazy initialization of async Anthropic client."""
        if self._async_client is None:
            try:
                from anthropic import AsyncAnthropic
                self._async_client = AsyncAnthropic(
                    api_key=self.api_key,
                    base_url=self.base_url or "https://api.anthropic.com",
                )
                self._initialized = True
            except ImportError:
                raise ProviderConfigurationError(
                    "Anthropic package not installed. Run: pip install anthropic"
                )
        return self._async_client
    
    def generate(self, request: AIRequest) -> AIResponse:
        """Generate a complete response using Anthropic."""
        self._validate_request(request)
        
        start_time = time.time()
        
        try:
            client = self._get_client()
            
            params = self._build_params(request)
            
            response = client.messages.create(**params)
            
            execution_time = time.time() - start_time
            
            content = response.content[0].text if response.content else ""
            tokens = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }
            
            cost = self._calculate_cost(response.model, tokens)
            
            return AIResponse(
                content=content,
                provider=self.PROVIDER_NAME,
                model=response.model,
                tokens=tokens,
                cost=cost,
                execution_time=execution_time,
                metadata={
                    "stop_reason": response.stop_reason,
                }
            )
            
        except Exception as e:
            raise self._handle_error(e)
    
    def stream(self, request: AIRequest) -> Generator[str, None, None]:
        """Stream response chunks from Anthropic."""
        self._validate_request(request)
        
        try:
            client = self._get_client()
            
            params = self._build_params(request)
            
            with client.messages.stream(**params) as stream:
                for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            raise self._handle_error(e)
    
    async def generate_async(self, request: AIRequest) -> AIResponse:
        """Async version of generate."""
        self._validate_request(request)
        
        start_time = time.time()
        
        try:
            client = await self._get_async_client()
            
            params = self._build_params(request)
            
            response = await client.messages.create(**params)
            
            execution_time = time.time() - start_time
            
            content = response.content[0].text if response.content else ""
            tokens = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }
            
            cost = self._calculate_cost(response.model, tokens)
            
            return AIResponse(
                content=content,
                provider=self.PROVIDER_NAME,
                model=response.model,
                tokens=tokens,
                cost=cost,
                execution_time=execution_time,
                metadata={
                    "stop_reason": response.stop_reason,
                }
            )
            
        except Exception as e:
            raise self._handle_error(e)
    
    async def stream_async(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """Async version of stream."""
        self._validate_request(request)
        
        try:
            client = await self._get_async_client()
            
            params = self._build_params(request)
            
            async with client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            raise self._handle_error(e)
    
    def validate_connection(self) -> bool:
        """Validate connection to Anthropic API."""
        try:
            client = self._get_client()
            # Simple test - count tokens
            client.count_tokens(
                model="claude-3-haiku-20240307",
                prompt="Test"
            )
            return True
        except Exception:
            return False
    
    def get_model_info(self, model_id: str) -> ModelInfo:
        """Get information about a specific Anthropic model."""
        model_config = self.DEFAULT_MODELS.get(model_id, {})
        pricing = self.PRICING.get(model_id, {"input": 0.0, "output": 0.0})
        
        # Normalize model_id for lookup
        normalized_id = model_id.split("-20")[0] if "-20" in model_id else model_id
        
        return ModelInfo(
            provider=self.PROVIDER_NAME,
            model_id=model_id,
            name=model_id,
            max_tokens=model_config.get("max_tokens", 4096),
            supports_streaming=True,
            supports_vision=True,  # All Claude 3 models support vision
            supports_function_calling=True,
            context_window=model_config.get("context_window", 200000),
            pricing=pricing,
        )
    
    def list_available_models(self) -> List[str]:
        """List available Anthropic models."""
        return list(self.DEFAULT_MODELS.keys())
    
    def _build_params(self, request: AIRequest) -> Dict[str, Any]:
        """Build parameters for API call."""
        params = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 4096,
            "messages": [
                {"role": "user", "content": request.prompt}
            ]
        }
        
        # Add system prompt if available
        if request.context and "system_prompt" in request.context:
            params["system"] = request.context["system_prompt"]
        
        # Add optional parameters
        if request.parameters:
            optional_params = ["temperature", "top_p", "top_k"]
            for param in optional_params:
                if param in request.parameters:
                    params[param] = request.parameters[param]
        
        # Handle memory/conversation history
        if request.memory and isinstance(request.memory, list):
            for item in request.memory:
                if isinstance(item, dict) and "role" in item and "content" in item:
                    params["messages"].append(item)
        
        return params
    
    def _calculate_cost(self, model: str, tokens: Dict[str, int]) -> float:
        """Calculate cost based on token usage."""
        # Normalize model name for pricing lookup
        normalized_model = model.split("-20")[0] if "-20" in model else model
        
        # Try exact match first, then partial match
        pricing = self.PRICING.get(model)
        if not pricing:
            for key, value in self.PRICING.items():
                if normalized_model in key:
                    pricing = value
                    break
        
        if not pricing:
            pricing = {"input": 0.0, "output": 0.0}
        
        input_cost = (tokens.get("prompt_tokens", 0) / 1000) * pricing.get("input", 0.0)
        output_cost = (tokens.get("completion_tokens", 0) / 1000) * pricing.get("output", 0.0)
        
        return round(input_cost + output_cost, 6)
    
    def _handle_error(self, error: Exception) -> ProviderError:
        """Convert exceptions to appropriate ProviderError types."""
        error_str = str(error).lower()
        
        if "authentication" in error_str or "api key" in error_str or "invalid api" in error_str:
            return ProviderAuthenticationError(
                "Invalid API key or authentication failed",
                code="auth_failed",
                original_error=error
            )
        
        if "rate limit" in error_str or "too many requests" in error_str:
            return ProviderRateLimitError(
                "Rate limit exceeded",
                code="rate_limit",
                original_error=error
            )
        
        if "connection" in error_str or "network" in error_str:
            return ProviderConnectionError(
                "Connection failed",
                code="connection_error",
                original_error=error
            )
        
        return ProviderError(
            str(error),
            original_error=error
        )


# Import for error handling
from app.ai.providers.base import ProviderConfigurationError

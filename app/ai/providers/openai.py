"""
OpenAI Provider Implementation

This module implements the OpenAI provider for AICF v2.
Supports GPT-4, GPT-3.5-turbo, and other OpenAI models.
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


class OpenAIProvider(BaseProvider):
    """
    OpenAI provider implementation.
    
    Supports:
    - GPT-4 family (gpt-4, gpt-4-turbo, gpt-4o)
    - GPT-3.5-turbo
    - Streaming responses
    - Token usage tracking
    - Cost calculation
    """
    
    PROVIDER_NAME = "openai"
    
    DEFAULT_MODELS = {
        "gpt-4": {"max_tokens": 8192, "context_window": 8192},
        "gpt-4-turbo": {"max_tokens": 4096, "context_window": 128000},
        "gpt-4o": {"max_tokens": 4096, "context_window": 128000},
        "gpt-4o-mini": {"max_tokens": 16384, "context_window": 128000},
        "gpt-3.5-turbo": {"max_tokens": 4096, "context_window": 16385},
    }
    
    PRICING = {
        # Per 1K tokens (USD)
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
        self._client = None
        self._async_client = None
    
    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url or "https://api.openai.com/v1",
                )
                self._initialized = True
            except ImportError:
                raise ProviderConfigurationError(
                    "OpenAI package not installed. Run: pip install openai"
                )
        return self._client
    
    async def _get_async_client(self):
        """Lazy initialization of async OpenAI client."""
        if self._async_client is None:
            try:
                from openai import AsyncOpenAI
                self._async_client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url or "https://api.openai.com/v1",
                )
                self._initialized = True
            except ImportError:
                raise ProviderConfigurationError(
                    "OpenAI package not installed. Run: pip install openai"
                )
        return self._async_client
    
    def generate(self, request: AIRequest) -> AIResponse:
        """Generate a complete response using OpenAI."""
        self._validate_request(request)
        
        start_time = time.time()
        
        try:
            client = self._get_client()
            
            messages = self._build_messages(request)
            params = self._build_params(request)
            
            response = client.chat.completions.create(
                model=params.get("model", "gpt-4"),
                messages=messages,
                **{k: v for k, v in params.items() if k != "model"}
            )
            
            execution_time = time.time() - start_time
            
            content = response.choices[0].message.content
            tokens = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
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
                    "finish_reason": response.choices[0].finish_reason,
                    "system_fingerprint": getattr(response, "system_fingerprint", None),
                }
            )
            
        except Exception as e:
            raise self._handle_error(e)
    
    def stream(self, request: AIRequest) -> Generator[str, None, None]:
        """Stream response chunks from OpenAI."""
        self._validate_request(request)
        
        try:
            client = self._get_client()
            
            messages = self._build_messages(request)
            params = self._build_params(request)
            
            stream = client.chat.completions.create(
                model=params.get("model", "gpt-4"),
                messages=messages,
                stream=True,
                **{k: v for k, v in params.items() if k != "model" and k != "stream"}
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            raise self._handle_error(e)
    
    async def generate_async(self, request: AIRequest) -> AIResponse:
        """Async version of generate."""
        self._validate_request(request)
        
        start_time = time.time()
        
        try:
            client = await self._get_async_client()
            
            messages = self._build_messages(request)
            params = self._build_params(request)
            
            response = await client.chat.completions.create(
                model=params.get("model", "gpt-4"),
                messages=messages,
                **{k: v for k, v in params.items() if k != "model"}
            )
            
            execution_time = time.time() - start_time
            
            content = response.choices[0].message.content
            tokens = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
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
                    "finish_reason": response.choices[0].finish_reason,
                }
            )
            
        except Exception as e:
            raise self._handle_error(e)
    
    async def stream_async(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """Async version of stream."""
        self._validate_request(request)
        
        try:
            client = await self._get_async_client()
            
            messages = self._build_messages(request)
            params = self._build_params(request)
            
            stream = await client.chat.completions.create(
                model=params.get("model", "gpt-4"),
                messages=messages,
                stream=True,
                **{k: v for k, v in params.items() if k != "model" and k != "stream"}
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            raise self._handle_error(e)
    
    def validate_connection(self) -> bool:
        """Validate connection to OpenAI API."""
        try:
            client = self._get_client()
            # Simple test request
            client.models.list()
            return True
        except Exception:
            return False
    
    def get_model_info(self, model_id: str) -> ModelInfo:
        """Get information about a specific OpenAI model."""
        model_config = self.DEFAULT_MODELS.get(model_id, {})
        pricing = self.PRICING.get(model_id, {"input": 0.0, "output": 0.0})
        
        return ModelInfo(
            provider=self.PROVIDER_NAME,
            model_id=model_id,
            name=model_id,
            max_tokens=model_config.get("max_tokens", 4096),
            supports_streaming=True,
            supports_vision="vision" in model_id or "gpt-4o" in model_id,
            supports_function_calling=True,
            context_window=model_config.get("context_window", 8192),
            pricing=pricing,
        )
    
    def list_available_models(self) -> List[str]:
        """List available OpenAI models."""
        return list(self.DEFAULT_MODELS.keys())
    
    def _build_messages(self, request: AIRequest) -> List[Dict[str, Any]]:
        """Build messages array from request."""
        messages = []
        
        # Add system prompt from context if available
        if request.context and "system_prompt" in request.context:
            messages.append({
                "role": "system",
                "content": request.context["system_prompt"]
            })
        
        # Add user prompt
        messages.append({
            "role": "user",
            "content": request.prompt
        })
        
        # Add memory/context as previous messages if available
        if request.memory:
            if isinstance(request.memory, list):
                for item in request.memory:
                    if isinstance(item, dict) and "role" in item and "content" in item:
                        messages.insert(len(messages) - 1, item)
        
        return messages
    
    def _build_params(self, request: AIRequest) -> Dict[str, Any]:
        """Build parameters for API call."""
        params = {
            "temperature": 0.7,
            "max_tokens": 4096,
        }
        
        if request.parameters:
            params.update(request.parameters)
        
        # Ensure model is set
        if "model" not in params:
            params["model"] = "gpt-4"
        
        return params
    
    def _calculate_cost(self, model: str, tokens: Dict[str, int]) -> float:
        """Calculate cost based on token usage."""
        pricing = self.PRICING.get(model, {"input": 0.0, "output": 0.0})
        
        input_cost = (tokens.get("prompt_tokens", 0) / 1000) * pricing.get("input", 0.0)
        output_cost = (tokens.get("completion_tokens", 0) / 1000) * pricing.get("output", 0.0)
        
        return round(input_cost + output_cost, 6)
    
    def _handle_error(self, error: Exception) -> ProviderError:
        """Convert exceptions to appropriate ProviderError types."""
        error_str = str(error).lower()
        
        if "authentication" in error_str or "api key" in error_str:
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

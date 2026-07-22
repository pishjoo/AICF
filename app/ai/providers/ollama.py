"""
Ollama Provider Implementation

This module implements the Ollama provider for AICF v2.
Supports local LLM models via Ollama server.
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
)


class OllamaProvider(BaseProvider):
    """
    Ollama provider implementation for local models.
    
    Supports:
    - Any model available in Ollama
    - Streaming responses
    - Local execution (no API costs)
    - Custom base URL configuration
    """
    
    PROVIDER_NAME = "ollama"
    
    DEFAULT_MODELS = {
        "llama3": {"max_tokens": 8192, "context_window": 8192},
        "llama3.1": {"max_tokens": 8192, "context_window": 128000},
        "mistral": {"max_tokens": 8192, "context_window": 8192},
        "mixtral": {"max_tokens": 8192, "context_window": 32000},
        "codellama": {"max_tokens": 4096, "context_window": 16000},
        "phi3": {"max_tokens": 4096, "context_window": 128000},
        "gemma": {"max_tokens": 8192, "context_window": 8192},
        "gemma2": {"max_tokens": 8192, "context_window": 8192},
        "qwen2": {"max_tokens": 32768, "context_window": 32768},
    }
    
    # Local models have no cost
    PRICING = {
        "default": {"input": 0.0, "output": 0.0},
    }
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        # Ollama doesn't require an API key by default
        super().__init__(api_key=api_key, base_url=base_url or "http://localhost:11434", **kwargs)
        self._client = None
        self._async_client = None
        self._available_models = None
    
    def _get_client(self):
        """Lazy initialization of Ollama client."""
        if self._client is None:
            try:
                from ollama import Client
                self._client = Client(host=self.base_url)
                self._initialized = True
            except ImportError:
                raise ProviderConfigurationError(
                    "Ollama package not installed. Run: pip install ollama"
                )
        return self._client
    
    async def _get_async_client(self):
        """Lazy initialization of async Ollama client."""
        if self._async_client is None:
            try:
                from ollama import AsyncClient
                self._async_client = AsyncClient(host=self.base_url)
                self._initialized = True
            except ImportError:
                raise ProviderConfigurationError(
                    "Ollama package not installed. Run: pip install ollama"
                )
        return self._async_client
    
    def generate(self, request: AIRequest) -> AIResponse:
        """Generate a complete response using Ollama."""
        self._validate_request(request)
        
        start_time = time.time()
        
        try:
            client = self._get_client()
            
            params = self._build_params(request)
            
            response = client.chat(**params)
            
            execution_time = time.time() - start_time
            
            content = response["message"]["content"]
            tokens = {
                "prompt_tokens": response.get("prompt_eval_count", 0),
                "completion_tokens": response.get("eval_count", 0),
                "total_tokens": response.get("prompt_eval_count", 0) + response.get("eval_count", 0),
            }
            
            # Ollama is free (local)
            cost = 0.0
            
            return AIResponse(
                content=content,
                provider=self.PROVIDER_NAME,
                model=params.get("model", "unknown"),
                tokens=tokens,
                cost=cost,
                execution_time=execution_time,
                metadata={
                    "done": response.get("done", True),
                    "total_duration": response.get("total_duration", 0),
                }
            )
            
        except Exception as e:
            raise self._handle_error(e)
    
    def stream(self, request: AIRequest) -> Generator[str, None, None]:
        """Stream response chunks from Ollama."""
        self._validate_request(request)
        
        try:
            client = self._get_client()
            
            params = self._build_params(request)
            params["stream"] = True
            
            response = client.chat(**params)
            
            for chunk in response:
                if chunk["message"]["content"]:
                    yield chunk["message"]["content"]
                    
        except Exception as e:
            raise self._handle_error(e)
    
    async def generate_async(self, request: AIRequest) -> AIResponse:
        """Async version of generate."""
        self._validate_request(request)
        
        start_time = time.time()
        
        try:
            client = await self._get_async_client()
            
            params = self._build_params(request)
            
            response = await client.chat(**params)
            
            execution_time = time.time() - start_time
            
            content = response["message"]["content"]
            tokens = {
                "prompt_tokens": response.get("prompt_eval_count", 0),
                "completion_tokens": response.get("eval_count", 0),
                "total_tokens": response.get("prompt_eval_count", 0) + response.get("eval_count", 0),
            }
            
            cost = 0.0
            
            return AIResponse(
                content=content,
                provider=self.PROVIDER_NAME,
                model=params.get("model", "unknown"),
                tokens=tokens,
                cost=cost,
                execution_time=execution_time,
                metadata={
                    "done": response.get("done", True),
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
            params["stream"] = True
            
            response = await client.chat(**params)
            
            async for chunk in response:
                if chunk["message"]["content"]:
                    yield chunk["message"]["content"]
                    
        except Exception as e:
            raise self._handle_error(e)
    
    def validate_connection(self) -> bool:
        """Validate connection to Ollama server."""
        try:
            client = self._get_client()
            # Check if server is running by listing models
            client.list()
            return True
        except Exception:
            return False
    
    def get_model_info(self, model_id: str) -> ModelInfo:
        """Get information about a specific Ollama model."""
        model_config = self.DEFAULT_MODELS.get(model_id, {})
        
        return ModelInfo(
            provider=self.PROVIDER_NAME,
            model_id=model_id,
            name=model_id,
            max_tokens=model_config.get("max_tokens", 4096),
            supports_streaming=True,
            supports_vision="vision" in model_id.lower(),
            supports_function_calling=False,  # Most Ollama models don't support function calling
            context_window=model_config.get("context_window", 8192),
            pricing=self.PRICING["default"],
        )
    
    def list_available_models(self) -> List[str]:
        """List models available in Ollama server."""
        if self._available_models is not None:
            return self._available_models
        
        try:
            client = self._get_client()
            response = client.list()
            self._available_models = [model["name"] for model in response.get("models", [])]
            return self._available_models
        except Exception:
            # Return default models if we can't connect
            return list(self.DEFAULT_MODELS.keys())
    
    def _build_params(self, request: AIRequest) -> Dict[str, Any]:
        """Build parameters for API call."""
        params = {
            "model": request.parameters.get("model", "llama3"),
            "messages": []
        }
        
        # Add system prompt if available
        if request.context and "system_prompt" in request.context:
            params["messages"].append({
                "role": "system",
                "content": request.context["system_prompt"]
            })
        
        # Add user prompt
        params["messages"].append({
            "role": "user",
            "content": request.prompt
        })
        
        # Handle memory/conversation history
        if request.memory and isinstance(request.memory, list):
            for item in request.memory:
                if isinstance(item, dict) and "role" in item and "content" in item:
                    params["messages"].insert(len(params["messages"]) - 1, item)
        
        # Add optional parameters
        if request.parameters:
            optional_params = ["temperature", "top_p", "top_k", "num_predict"]
            for param in optional_params:
                if param in request.parameters:
                    params[param] = request.parameters[param]
        
        return params
    
    def _calculate_cost(self, model: str, tokens: Dict[str, int]) -> float:
        """Ollama is free (local execution)."""
        return 0.0
    
    def _handle_error(self, error: Exception) -> ProviderError:
        """Convert exceptions to appropriate ProviderError types."""
        error_str = str(error).lower()
        
        if "connection" in error_str or "refused" in error_str or "cannot connect" in error_str:
            return ProviderConnectionError(
                "Cannot connect to Ollama server. Is it running?",
                code="connection_error",
                original_error=error
            )
        
        if "not found" in error_str or "model not found" in error_str:
            return ProviderError(
                "Model not found. Pull it with: ollama pull <model>",
                code="model_not_found",
                original_error=error
            )
        
        return ProviderError(
            str(error),
            original_error=error
        )


# Import for error handling
from app.ai.providers.base import ProviderConfigurationError

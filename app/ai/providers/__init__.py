"""
AI Providers Package

This package provides the AI provider abstraction layer for AICF v2.
"""

from app.ai.providers.base import (
    BaseProvider,
    AIRequest,
    AIResponse,
    ModelInfo,
    ProviderError,
    ProviderConfigurationError,
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderAuthenticationError,
)

from app.ai.providers.registry import (
    ProviderRegistry,
    auto_register_providers,
)

from app.ai.providers.openai import OpenAIProvider
from app.ai.providers.anthropic import AnthropicProvider
from app.ai.providers.ollama import OllamaProvider

__all__ = [
    # Base classes
    "BaseProvider",
    "AIRequest",
    "AIResponse",
    "ModelInfo",
    # Exceptions
    "ProviderError",
    "ProviderConfigurationError",
    "ProviderConnectionError",
    "ProviderRateLimitError",
    "ProviderAuthenticationError",
    # Registry
    "ProviderRegistry",
    "auto_register_providers",
    # Concrete providers
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
]

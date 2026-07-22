"""
AI Intelligence Foundation Package

This package provides the core AI infrastructure for AICF v2:
- Provider abstraction layer
- Context system
- Memory foundation
- Prompt management
"""

from app.ai.providers import (
    # Base classes
    BaseProvider,
    AIRequest,
    AIResponse,
    ModelInfo,
    ProviderError,
    ProviderConfigurationError,
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderAuthenticationError,
    # Registry
    ProviderRegistry,
    auto_register_providers,
    # Concrete providers
    OpenAIProvider,
    AnthropicProvider,
    OllamaProvider,
)

from app.ai.context import (
    AIContext,
    ContextBuilder,
    OrganizationInfo,
    ChannelInfo,
    AudienceInfo,
    BrandRules,
    ContentReference,
    Constraints,
)

__all__ = [
    # Providers - Base
    "BaseProvider",
    "AIRequest",
    "AIResponse",
    "ModelInfo",
    "ProviderError",
    "ProviderConfigurationError",
    "ProviderConnectionError",
    "ProviderRateLimitError",
    "ProviderAuthenticationError",
    # Providers - Registry
    "ProviderRegistry",
    "auto_register_providers",
    # Providers - Concrete
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    # Context
    "AIContext",
    "ContextBuilder",
    "OrganizationInfo",
    "ChannelInfo",
    "AudienceInfo",
    "BrandRules",
    "ContentReference",
    "Constraints",
]

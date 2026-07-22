"""
AI Provider Registry

This module provides a registry for managing AI providers.
Allows dynamic provider selection without hard dependencies.
"""

from typing import Dict, Optional, Type, List
from app.ai.providers.base import BaseProvider, ProviderConfigurationError


class ProviderRegistry:
    """
    Registry for AI providers.
    
    Provides centralized management of available providers
    with lazy loading and caching.
    """
    
    _instance = None
    _providers: Dict[str, Type[BaseProvider]] = {}
    _instances: Dict[str, BaseProvider] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register(cls, name: str, provider_class: Type[BaseProvider]) -> None:
        """
        Register a provider class.
        
        Args:
            name: Provider identifier (e.g., 'openai', 'anthropic')
            provider_class: Provider class to register
        """
        cls._providers[name.lower()] = provider_class
        # Clear cached instance when re-registering
        if name.lower() in cls._instances:
            del cls._instances[name.lower()]
    
    @classmethod
    def get_provider(cls, name: str, **kwargs) -> BaseProvider:
        """
        Get or create a provider instance.
        
        Args:
            name: Provider identifier
            **kwargs: Provider initialization arguments
            
        Returns:
            Configured provider instance
            
        Raises:
            ProviderConfigurationError: If provider not found
        """
        name = name.lower()
        
        if name not in cls._providers:
            raise ProviderConfigurationError(
                f"Provider '{name}' not registered. "
                f"Available providers: {list(cls._providers.keys())}"
            )
        
        # Check for cached instance with same config
        cache_key = f"{name}_{hash(frozenset(kwargs.items()))}"
        if cache_key not in cls._instances:
            provider_class = cls._providers[name]
            cls._instances[cache_key] = provider_class(**kwargs)
        
        return cls._instances[cache_key]
    
    @classmethod
    def get_provider_class(cls, name: str) -> Type[BaseProvider]:
        """
        Get a provider class without instantiating.
        
        Args:
            name: Provider identifier
            
        Returns:
            Provider class
            
        Raises:
            ProviderConfigurationError: If provider not found
        """
        name = name.lower()
        
        if name not in cls._providers:
            raise ProviderConfigurationError(
                f"Provider '{name}' not registered"
            )
        
        return cls._providers[name]
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """List all registered provider names."""
        return list(cls._providers.keys())
    
    @classmethod
    def is_available(cls, name: str) -> bool:
        """Check if a provider is registered."""
        return name.lower() in cls._providers
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached provider instances."""
        cls._instances.clear()
    
    @classmethod
    def unregister(cls, name: str) -> None:
        """
        Unregister a provider.
        
        Args:
            name: Provider identifier
        """
        name = name.lower()
        if name in cls._providers:
            del cls._providers[name]
        if name in cls._instances:
            del cls._instances[name]


def auto_register_providers():
    """
    Auto-register all built-in providers.
    
    This function imports and registers all standard providers.
    Call this once at application startup.
    """
    from app.ai.providers.openai import OpenAIProvider
    from app.ai.providers.anthropic import AnthropicProvider
    from app.ai.providers.ollama import OllamaProvider
    
    ProviderRegistry.register("openai", OpenAIProvider)
    ProviderRegistry.register("anthropic", AnthropicProvider)
    ProviderRegistry.register("ollama", OllamaProvider)


# Auto-register on module import
auto_register_providers()

"""
Unit tests for AI Provider Abstraction Layer.

Tests cover:
- Base provider interface
- Provider registry
- Request/Response schemas
- Error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

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

from app.ai.providers.registry import ProviderRegistry


class TestAIRequest:
    """Tests for AIRequest schema."""
    
    def test_create_request(self):
        """Test creating a basic AI request."""
        request = AIRequest(
            organization_id=1,
            agent_type="content_generator",
            prompt="Generate a blog post about AI"
        )
        
        assert request.organization_id == 1
        assert request.agent_type == "content_generator"
        assert request.prompt == "Generate a blog post about AI"
        assert request.request_id is not None
        assert request.created_at is not None
    
    def test_request_to_dict(self):
        """Test converting request to dictionary."""
        request = AIRequest(
            organization_id=1,
            agent_type="test_agent",
            prompt="Test prompt",
            context={"key": "value"},
            parameters={"temperature": 0.7}
        )
        
        data = request.to_dict()
        
        assert data["organization_id"] == 1
        assert data["agent_type"] == "test_agent"
        assert data["prompt"] == "Test prompt"
        assert data["context"] == {"key": "value"}
        assert data["parameters"] == {"temperature": 0.7}
        assert "request_id" in data
        assert "created_at" in data
    
    def test_request_with_context_and_memory(self):
        """Test request with context and memory."""
        request = AIRequest(
            organization_id=1,
            agent_type="test_agent",
            prompt="Continue the conversation",
            context={"system_prompt": "You are helpful"},
            memory=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
        )
        
        assert request.context["system_prompt"] == "You are helpful"
        assert len(request.memory) == 2


class TestAIResponse:
    """Tests for AIResponse schema."""
    
    def test_create_response(self):
        """Test creating a basic AI response."""
        response = AIResponse(
            content="Generated content here",
            provider="openai",
            model="gpt-4"
        )
        
        assert response.content == "Generated content here"
        assert response.provider == "openai"
        assert response.model == "gpt-4"
        assert response.response_id is not None
    
    def test_response_to_dict(self):
        """Test converting response to dictionary."""
        response = AIResponse(
            content="Test output",
            provider="anthropic",
            model="claude-3",
            tokens={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            cost=0.001,
            execution_time=1.5
        )
        
        data = response.to_dict()
        
        assert data["content"] == "Test output"
        assert data["provider"] == "anthropic"
        assert data["model"] == "claude-3"
        assert data["tokens"]["total_tokens"] == 30
        assert data["cost"] == 0.001
        assert data["execution_time"] == 1.5


class TestModelInfo:
    """Tests for ModelInfo schema."""
    
    def test_create_model_info(self):
        """Test creating model info."""
        info = ModelInfo(
            provider="openai",
            model_id="gpt-4",
            name="GPT-4",
            max_tokens=8192,
            supports_streaming=True,
            supports_vision=False,
            supports_function_calling=True,
            context_window=8192
        )
        
        assert info.provider == "openai"
        assert info.model_id == "gpt-4"
        assert info.max_tokens == 8192
        assert info.supports_streaming is True
        assert info.supports_vision is False


class TestProviderRegistry:
    """Tests for ProviderRegistry."""
    
    def setup_method(self):
        """Clear registry before each test."""
        ProviderRegistry._providers.clear()
        ProviderRegistry._instances.clear()
    
    def test_register_provider(self):
        """Test registering a provider."""
        mock_provider = Mock(spec=BaseProvider)
        
        ProviderRegistry.register("test_provider", mock_provider)
        
        assert ProviderRegistry.is_available("test_provider")
        assert "test_provider" in ProviderRegistry.list_providers()
    
    def test_get_provider(self):
        """Test getting a provider instance."""
        mock_provider_class = Mock(spec=BaseProvider)
        mock_instance = Mock(spec=BaseProvider)
        mock_provider_class.return_value = mock_instance
        
        ProviderRegistry.register("test", mock_provider_class)
        
        provider = ProviderRegistry.get_provider("test", api_key="test-key")
        
        assert provider is mock_instance
        mock_provider_class.assert_called_once_with(api_key="test-key")
    
    def test_get_provider_not_found(self):
        """Test getting non-existent provider raises error."""
        with pytest.raises(ProviderConfigurationError):
            ProviderRegistry.get_provider("nonexistent")
    
    def test_provider_caching(self):
        """Test that providers are cached."""
        mock_provider_class = Mock(spec=BaseProvider)
        mock_instance = Mock(spec=BaseProvider)
        mock_provider_class.return_value = mock_instance
        
        ProviderRegistry.register("cached", mock_provider_class)
        
        # Get twice with same config
        provider1 = ProviderRegistry.get_provider("cached")
        provider2 = ProviderRegistry.get_provider("cached")
        
        # Should be same instance (cached)
        assert provider1 is provider2
        assert mock_provider_class.call_count == 1
    
    def test_clear_cache(self):
        """Test clearing provider cache."""
        mock_provider_class = Mock(spec=BaseProvider)
        ProviderRegistry.register("temp", mock_provider_class)
        
        ProviderRegistry.get_provider("temp")
        ProviderRegistry.clear_cache()
        
        assert len(ProviderRegistry._instances) == 0


class TestProviderErrors:
    """Tests for provider error types."""
    
    def test_provider_error_base(self):
        """Test base ProviderError."""
        error = ProviderError("Something went wrong", code="generic")
        
        assert error.message == "Something went wrong"
        assert error.code == "generic"
    
    def test_configuration_error(self):
        """Test ProviderConfigurationError."""
        error = ProviderConfigurationError("Invalid config")
        
        assert isinstance(error, ProviderError)
        assert error.message == "Invalid config"
    
    def test_connection_error(self):
        """Test ProviderConnectionError."""
        original = ConnectionError("Network failed")
        error = ProviderConnectionError("Cannot connect", original_error=original)
        
        assert error.original_error is original
    
    def test_rate_limit_error(self):
        """Test ProviderRateLimitError."""
        error = ProviderRateLimitError("Too many requests", code="rate_limit")
        
        assert error.code == "rate_limit"
    
    def test_auth_error(self):
        """Test ProviderAuthenticationError."""
        error = ProviderAuthenticationError("Invalid API key")
        
        assert "auth" in str(error).lower() or "Invalid" in str(error)


class TestBaseProviderInterface:
    """Tests for BaseProvider abstract interface."""
    
    def test_cannot_instantiate_base(self):
        """Test that BaseProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseProvider()
    
    def test_mock_provider_implementation(self):
        """Test implementing a mock provider."""
        class MockProvider(BaseProvider):
            def generate(self, request):
                return AIResponse(content="mock", provider="mock", model="mock")
            
            def stream(self, request):
                yield "chunk"
            
            async def generate_async(self, request):
                return self.generate(request)
            
            async def stream_async(self, request):
                async def gen():
                    yield "chunk"
                return gen()
            
            def validate_connection(self):
                return True
            
            def get_model_info(self, model_id):
                return ModelInfo(
                    provider="mock", model_id=model_id, name="Mock",
                    max_tokens=1000, supports_streaming=True,
                    supports_vision=False, supports_function_calling=False,
                    context_window=1000
                )
            
            def list_available_models(self):
                return ["mock-model"]
        
        provider = MockProvider()
        
        request = AIRequest(
            organization_id=1,
            agent_type="test",
            prompt="Test"
        )
        
        response = provider.generate(request)
        assert response.content == "mock"
        assert provider.validate_connection() is True

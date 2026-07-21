"""
AI Provider Abstraction

Unified interface for multiple AI providers (OpenAI, Anthropic, Ollama, etc.).
Provides consistent API for all agents to generate content.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
import json

from core.config import settings


@dataclass
class Message:
    """Chat message structure."""
    role: str  # "system", "user", or "assistant"
    content: str


@dataclass
class AIResponse:
    """Standardized AI response."""
    content: str
    model: str
    usage: Dict[str, int]  # prompt_tokens, completion_tokens, total_tokens
    raw_response: Any  # Provider-specific raw response


class BaseAIProvider(ABC):
    """Abstract base class for AI providers."""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.kwargs = kwargs
    
    @abstractmethod
    def generate(self, messages: List[Message], **kwargs) -> AIResponse:
        """Generate a response from the AI model."""
        pass
    
    @abstractmethod
    def generate_json(self, messages: List[Message], **kwargs) -> Dict[str, Any]:
        """Generate a JSON response from the AI model."""
        pass
    
    def build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build a system prompt from context."""
        parts = []
        
        if context.get("channel_name"):
            parts.append(f"You are creating content for the YouTube channel: {context['channel_name']}")
        
        if context.get("niche"):
            parts.append(f"Channel niche: {context['niche']}")
        
        if context.get("target_audience"):
            parts.append(f"Target audience: {context['target_audience']}")
        
        if context.get("visual_style"):
            parts.append(f"Visual style: {context['visual_style']}")
        
        if context.get("storytelling_rules"):
            parts.append(f"Storytelling rules: {context['storytelling_rules']}")
        
        if context.get("forbidden_elements"):
            forbidden = ", ".join(context["forbidden_elements"])
            parts.append(f"FORBIDDEN ELEMENTS - Never include: {forbidden}")
        
        if context.get("recurring_characters"):
            characters = ", ".join(context["recurring_characters"])
            parts.append(f"Recurring characters: {characters}")
        
        if context.get("music_style"):
            parts.append(f"Music style: {context['music_style']}")
        
        if context.get("video_duration"):
            parts.append(f"Video duration: {context['video_duration']}")
        
        if context.get("language"):
            parts.append(f"Language: {context['language']}")
        
        return "\n".join(parts)


class OpenAIProvider(BaseAIProvider):
    """OpenAI API provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(api_key or settings.OPENAI_API_KEY, **kwargs)
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")
    
    def generate(self, messages: List[Message], **kwargs) -> AIResponse:
        """Generate text using OpenAI."""
        model = kwargs.get("model", settings.DEFAULT_MODEL)
        temperature = kwargs.get("temperature", settings.TEMPERATURE)
        max_tokens = kwargs.get("max_tokens", settings.MAX_TOKENS)
        
        msg_dicts = [{"role": m.role, "content": m.content} for m in messages]
        
        response = self.client.chat.completions.create(
            model=model,
            messages=msg_dicts,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return AIResponse(
            content=response.choices[0].message.content,
            model=model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            raw_response=response
        )
    
    def generate_json(self, messages: List[Message], **kwargs) -> Dict[str, Any]:
        """Generate JSON using OpenAI."""
        # Add instruction for JSON output
        json_message = Message(
            role="user",
            content="Respond ONLY with valid JSON. No markdown, no explanations."
        )
        messages_with_json = messages + [json_message]
        
        response = self.generate(messages_with_json, **kwargs)
        
        try:
            # Try to extract JSON from the response
            content = response.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}. Raw content: {response.content}")


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude API provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(api_key or settings.ANTHROPIC_API_KEY, **kwargs)
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
    
    def generate(self, messages: List[Message], **kwargs) -> AIResponse:
        """Generate text using Anthropic Claude."""
        model = kwargs.get("model", "claude-sonnet-4-20250514")
        max_tokens = kwargs.get("max_tokens", settings.MAX_TOKENS)
        
        # Separate system message from conversation
        system_message = ""
        conv_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                conv_messages.append({"role": msg.role, "content": msg.content})
        
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_message,
            messages=conv_messages
        )
        
        return AIResponse(
            content=response.content[0].text,
            model=model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            raw_response=response
        )
    
    def generate_json(self, messages: List[Message], **kwargs) -> Dict[str, Any]:
        """Generate JSON using Anthropic Claude."""
        json_message = Message(
            role="user",
            content="Respond ONLY with valid JSON. No markdown, no explanations."
        )
        messages_with_json = messages + [json_message]
        
        response = self.generate(messages_with_json, **kwargs)
        
        try:
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}. Raw content: {response.content}")


class OllamaProvider(BaseAIProvider):
    """Ollama local LLM provider implementation."""
    
    def __init__(self, base_url: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        try:
            import ollama
            self.client = ollama.Client(host=self.base_url)
        except ImportError:
            raise ImportError("ollama package not installed. Run: pip install ollama")
    
    def generate(self, messages: List[Message], **kwargs) -> AIResponse:
        """Generate text using Ollama."""
        model = kwargs.get("model", "llama3.1")
        
        msg_dicts = [{"role": m.role, "content": m.content} for m in messages]
        
        response = self.client.chat(model=model, messages=msg_dicts)
        
        return AIResponse(
            content=response["message"]["content"],
            model=model,
            usage={
                "prompt_tokens": 0,  # Ollama doesn't provide token counts by default
                "completion_tokens": 0,
                "total_tokens": 0
            },
            raw_response=response
        )
    
    def generate_json(self, messages: List[Message], **kwargs) -> Dict[str, Any]:
        """Generate JSON using Ollama."""
        json_message = Message(
            role="user",
            content="Respond ONLY with valid JSON. No markdown, no explanations."
        )
        messages_with_json = messages + [json_message]
        
        response = self.generate(messages_with_json, **kwargs)
        
        try:
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}. Raw content: {response.content}")


def get_ai_provider(provider_type: Optional[str] = None) -> BaseAIProvider:
    """
    Factory function to get the appropriate AI provider.
    
    Args:
        provider_type: Type of provider ("openai", "anthropic", "ollama").
                      If None, uses settings.AI_PROVIDER.
    
    Returns:
        Configured AI provider instance.
    """
    provider = provider_type or settings.AI_PROVIDER
    
    if provider == "openai":
        return OpenAIProvider()
    elif provider == "anthropic":
        return AnthropicProvider()
    elif provider == "ollama":
        return OllamaProvider()
    else:
        raise ValueError(f"Unknown AI provider: {provider}")


# AICF v2 Agent System Documentation

## Overview

The Agent System provides specialized AI agents for each stage of the content production workflow. Each agent follows a standard interface and produces structured outputs.

---

## Agent Architecture

### Base Interface

```python
class BaseAgent(ABC):
    name: str
    description: str
    stage_type: str
    
    @abstractmethod
    def execute(self, context: AgentContext) -> AgentResult:
        pass
    
    @abstractmethod
    def validate_input(self, context: AgentContext) -> bool:
        pass
    
    @abstractmethod
    def validate_output(self, output: Dict[str, Any]) -> bool:
        pass
```

### Agent Context

```python
@dataclass
class AgentContext:
    episode: Episode
    channel_profile: ChannelProfile
    organization_id: int
    previous_outputs: Dict[str, Any] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def get_custom_instructions(self) -> Optional[str]:
        return self.settings.get("custom_instructions")
```

### Agent Result

```python
@dataclass
class AgentResult:
    success: bool
    output: Dict[str, Any]
    error_message: Optional[str] = None
    tokens_used: int = 0
    execution_time_seconds: float = 0.0
```

---

## Agent Registry

### Registration Pattern

```python
registry = AgentRegistry()
registry.register("idea", MockIdeaAgent())
registry.register("research", MockResearchAgent())
# ... register all 8 agents
```

### Lazy Instantiation

```python
registry.register_class("script", ScriptAgentClass)
# Agent instantiated on first get_agent() call
agent = registry.get_agent("script")
```

---

## Agent Details

### 1. IdeaAgent

**Purpose**: Generate video concepts based on channel profile and topic

**Input Contract:**
```python
{
    "episode": Episode,
    "channel_profile": ChannelProfile,
    "previous_outputs": {}  # First stage
}
```

**Output Contract:**
```python
{
    "idea": str,           # Core concept
    "concept": str,        # Detailed explanation
    "hook": str,           # Opening attention-grabber
    "key_points": List[str],  # Main talking points
    "target_duration": str
}
```

**Execution Lifecycle:**
1. Read channel profile for brand guidelines
2. Extract episode topic/description
3. Generate idea aligned with channel style
4. Validate output structure
5. Return formatted result

**Error Handling:**
- Missing channel profile → ValidationError
- Invalid topic → Return generic idea template
- Generation failure → Retry with simplified prompt

**Future Implementation:**
```python
class RealIdeaAgent(BaseAgent):
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
    
    def execute(self, context):
        prompt = self._build_prompt(context)
        response = await self.llm.generate(prompt)
        return self._parse_response(response)
```

---

### 2. ResearchAgent

**Purpose**: Gather information and facts about the topic

**Input Contract:**
```python
{
    "previous_outputs": {
        "idea": {...}
    }
}
```

**Output Contract:**
```python
{
    "research_summary": str,
    "sources": List[str],
    "key_facts": List[str],
    "statistics": Dict[str, str],
    "related_topics": List[str]
}
```

**Execution Lifecycle:**
1. Extract idea from previous stage
2. Search knowledge base / external sources
3. Compile relevant facts and statistics
4. Cite sources
5. Format for script agent consumption

**Error Handling:**
- No sources found → Use general knowledge
- Conflicting information → Flag for review
- Source access failed → Log and continue

---

### 3. ScriptAgent

**Purpose**: Write complete video script with timing

**Input Contract:**
```python
{
    "previous_outputs": {
        "idea": {...},
        "research": {...}
    }
}
```

**Output Contract:**
```python
{
    "script": str,              # Full narration text
    "scenes": List[Dict],       # Scene breakdown
    "word_count": int,
    "estimated_duration": int,  # Seconds
    "tone_notes": str
}
```

**Scene Structure:**
```python
{
    "scene": 1,
    "description": "Intro scene",
    "duration": 10,
    "visual_cues": ["Title card", "Host on camera"],
    "audio_cues": ["Upbeat music fades in"]
}
```

---

### 4. StoryboardAgent

**Purpose**: Create visual frame descriptions

**Input Contract:**
```python
{
    "previous_outputs": {
        "script": {...}
    }
}
```

**Output Contract:**
```python
{
    "storyboard_frames": List[Dict],
    "visual_notes": str,
    "transitions": List[str],
    "color_palette": List[str]
}
```

**Frame Structure:**
```python
{
    "frame": 1,
    "timestamp": "00:00-00:10",
    "visual": "Opening shot with title",
    "text": "Video title overlay",
    "camera_angle": "wide",
    "lighting": "bright"
}
```

---

### 5. AssetAgent

**Purpose**: Generate or source media assets

**Input Contract:**
```python
{
    "previous_outputs": {
        "storyboard": {...}
    }
}
```

**Output Contract:**
```python
{
    "generated_assets": List[Dict],
    "asset_count": int,
    "total_size_mb": float
}
```

**Asset Structure:**
```python
{
    "type": "image",  # image, audio, video, graphic
    "url": "/assets/generated/xxx.png",
    "description": "Background image for scene 1",
    "dimensions": "1920x1080",
    "format": "png"
}
```

**Future Implementation:**
- DALL-E integration for images
- ElevenLabs for voice synthesis
- FFmpeg for video clips

---

### 6. VideoAgent (VideoProductionAgent)

**Purpose**: Assemble final video from assets

**Input Contract:**
```python
{
    "previous_outputs": {
        "script": {...},
        "asset_generation": {...}
    }
}
```

**Output Contract:**
```python
{
    "video_url": str,
    "duration_seconds": int,
    "resolution": str,
    "format": str,
    "file_size_mb": float,
    "thumbnail_url": str
}
```

**Future Implementation:**
- FFmpeg integration
- Scene assembly
- Audio mixing
- Transition effects
- Color grading

---

### 7. SEOAgent

**Purpose**: Optimize content for discoverability

**Input Contract:**
```python
{
    "previous_outputs": {
        "video_production": {...}
    }
}
```

**Output Contract:**
```python
{
    "title": str,
    "description": str,
    "tags": List[str],
    "category": str,
    "seo_score": int,
    "recommendations": List[str]
}
```

**SEO Factors:**
- Keyword density
- Title length (60 chars max for YouTube)
- Description completeness
- Tag relevance
- Category match

---

### 8. PublishAgent

**Purpose**: Handle platform publishing

**Input Contract:**
```python
{
    "previous_outputs": {
        "seo": {...}
    }
}
```

**Output Contract:**
```python
{
    "published": bool,
    "platform_url": str,
    "publish_date": str,
    "platform_id": str,
    "status": str,  # public, private, scheduled
    "scheduled": bool
}
```

**Future Implementation:**
- YouTube Data API
- Instagram Graph API
- TikTok API
- Scheduling system

---

## Agent Provider System

### Provider Interface

```python
class AgentProvider(ABC):
    name: str
    
    @abstractmethod
    def execute(self, prompt: str, context: Dict) -> Dict:
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        pass
    
    def get_capabilities(self) -> Dict:
        return {
            "name": self.name,
            "supports_streaming": False,
            "max_tokens": 4096
        }
```

### Mock Provider (Current)

```python
class MockAgentProvider(AgentProvider):
    name = "mock_provider"
    
    def execute(self, prompt, context):
        return {
            "success": True,
            "data": {"mock_output": "..."},
            "tokens_used": 100
        }
```

### Future Providers

```python
class OpenAIProvider(AgentProvider):
    name = "openai"
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def execute(self, prompt, context):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return {
            "content": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens
        }

class AnthropicProvider(AgentProvider):
    name = "anthropic"
    # Similar implementation for Claude

class OllamaProvider(AgentProvider):
    name = "ollama"
    # Local model support
```

---

## Document Information

- **Version**: 2.0
- **Last Updated**: 2024
- **Author**: AICF Engineering Team
- **Status**: Active Development

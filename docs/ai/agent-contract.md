# AICF v2 Agent Contract Specification

## Overview

This document defines the standard contract for all AI agents in the AICF v2 system.

---

## Agent Interface

### Base Class

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseAgent(ABC):
    """Base class for all workflow agents."""
    
    # Class attributes (must be defined by subclasses)
    name: str = ""
    description: str = ""
    stage_type: str = ""
    
    @abstractmethod
    def execute(self, context: AgentContext) -> AgentResult:
        """Execute the agent with given context."""
        pass
    
    @abstractmethod
    def validate_input(self, context: AgentContext) -> bool:
        """Validate input before execution."""
        pass
    
    @abstractmethod
    def validate_output(self, output: Dict[str, Any]) -> bool:
        """Validate output after execution."""
        pass
```

---

## Context Contract

### AgentContext Structure

```python
@dataclass
class AgentContext:
    """Input context for agent execution."""
    
    # Core entities
    episode: Episode
    channel_profile: ChannelProfile
    organization_id: int
    
    # Previous stage outputs
    previous_outputs: Dict[str, Any] = field(default_factory=dict)
    
    # Execution settings
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def get_custom_instructions(self) -> Optional[str]:
        return self.settings.get("custom_instructions")
    
    def get_previous_output(self, stage_name: str) -> Optional[Dict]:
        return self.previous_outputs.get(stage_name)
```

---

## Result Contract

### AgentResult Structure

```python
@dataclass
class AgentResult:
    """Output result from agent execution."""
    
    success: bool
    output: Dict[str, Any]
    error_message: Optional[str] = None
    tokens_used: int = 0
    execution_time_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "output": self.output,
            "error_message": self.error_message,
            "tokens_used": self.tokens_used,
            "execution_time_seconds": self.execution_time_seconds,
            "metadata": self.metadata
        }
```

---

## Stage-Specific Contracts

### IDEA Stage Contract

**Input:**
```python
{
    "episode": {"title": "...", "topic": "..."},
    "channel_profile": {"target_audience": {...}, "brand_guidelines": {...}}
}
```

**Output:**
```python
{
    "idea": str,
    "concept": str,
    "hook": str,
    "key_points": [str],
    "target_duration": str
}
```

### RESEARCH Stage Contract

**Input:**
```python
{
    "previous_outputs": {
        "idea": {"idea": "...", "key_points": [...]}
    }
}
```

**Output:**
```python
{
    "research_summary": str,
    "sources": [str],
    "key_facts": [str],
    "statistics": {str: str},
    "related_topics": [str]
}
```

### SCRIPT Stage Contract

**Output:**
```python
{
    "script": str,
    "scenes": [{"scene": int, "description": str, "duration": int}],
    "word_count": int,
    "estimated_duration": int
}
```

### STORYBOARD Stage Contract

**Output:**
```python
{
    "storyboard_frames": [{"frame": int, "visual": str, "timestamp": str}],
    "transitions": [str],
    "color_palette": [str]
}
```

### ASSET_GENERATION Stage Contract

**Output:**
```python
{
    "generated_assets": [{"type": str, "url": str, "description": str}],
    "asset_count": int
}
```

### VIDEO_PRODUCTION Stage Contract

**Output:**
```python
{
    "video_url": str,
    "duration_seconds": int,
    "resolution": str,
    "thumbnail_url": str
}
```

### SEO Stage Contract

**Output:**
```python
{
    "title": str,
    "description": str,
    "tags": [str],
    "category": str,
    "seo_score": int
}
```

### PUBLISH Stage Contract

**Output:**
```python
{
    "published": bool,
    "platform_url": str,
    "publish_date": str,
    "platform_id": str
}
```

---

## Validation Rules

### Input Validation

```python
def validate_input(self, context: AgentContext) -> bool:
    # Required fields
    if not context.episode:
        return False
    if not context.channel_profile:
        return False
    if not context.organization_id:
        return False
    
    # Stage-specific validation
    if self.stage_type == "script":
        if "idea" not in context.previous_outputs:
            return False
        if "research" not in context.previous_outputs:
            return False
    
    return True
```

### Output Validation

```python
def validate_output(self, output: Dict[str, Any]) -> bool:
    if not output:
        return False
    
    # Check required keys based on stage
    required_keys = self._get_required_keys()
    for key in required_keys:
        if key not in output:
            return False
    
    return True
```

---

## Document Information

- **Version**: 2.0
- **Last Updated**: 2024
- **Author**: AICF Engineering Team
- **Status**: Active Development

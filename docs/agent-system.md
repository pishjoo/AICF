# AICF - Agent System Design

## Multi-Agent Architecture Specification

This document details the design of the multi-agent system that powers AICF.

---

## 1. Agent Overview

### 1.1 Agent Philosophy

Each agent in AICF is a specialized AI-powered module with:
- **Clear responsibility** - Single focused task
- **Defined interfaces** - Standardized input/output contracts
- **Autonomous execution** - Can operate independently
- **Collaborative behavior** - Works within the workflow pipeline
- **Memory awareness** - Accesses and contributes to system memory

---

## 2. Agent Specifications

### 2.1 Research Agent

**Purpose:** Gather comprehensive information for video topics.

**Responsibilities:**
- Analyze topic seeds and expand into researchable queries
- Search for credible sources (academic, news, official)
- Extract key facts, statistics, and quotes
- Identify trending angles and competitor content
- Validate information accuracy
- Compile structured research reports

**Input:**
```python
{
    "topic": str,
    "channel_profile": ChannelProfile,
    "research_depth": "shallow" | "medium" | "deep",
    "excluded_sources": List[str]
}
```

**Output:**
```python
{
    "summary": str,
    "key_facts": List[Fact],
    "sources": List[Source],
    "trending_angles": List[str],
    "competitor_videos": List[VideoReference],
    "suggested_hooks": List[str]
}
```

**Tools Used:**
- Web search API
- YouTube Data API
- News APIs
- Academic databases (if available)

**QC Checks:**
- Source credibility score > threshold
- Fact verification (cross-reference multiple sources)
- No forbidden topics included
- Proper citation format

---

### 2.2 Idea Generator Agent

**Purpose:** Create compelling video concepts from research.

**Responsibilities:**
- Generate multiple video ideas from research data
- Develop unique hooks and angles
- Score ideas based on viral potential and relevance
- Align ideas with channel identity
- Reference successful past patterns
- Avoid previously failed approaches

**Input:**
```python
{
    "research_report": ResearchReport,
    "channel_profile": ChannelProfile,
    "success_patterns": List[Pattern],
    "failed_approaches": List[Approach],
    "idea_count": int (default: 5)
}
```

**Output:**
```python
{
    "ideas": List[{
        "title": str,
        "hook": str,
        "angle": str,
        "description": str,
        "target_duration": int,
        "relevance_score": float,
        "viral_potential": float,
        "feasibility_score": float
    }]
}
```

**Prompt Strategy:**
- Few-shot examples of successful videos
- Channel style guidelines in context
- Constraints for forbidden elements
- Scoring rubric provided

**QC Checks:**
- Ideas align with channel niche
- Hooks are attention-grabbing
- No forbidden topics/words
- Duration matches channel format

---

### 2.3 Script Writer Agent

**Purpose:** Write engaging, on-brand video scripts.

**Responsibilities:**
- Transform selected idea into full narration script
- Structure content with intro, body, conclusion
- Add timing markers for each section
- Incorporate channel's tone and style
- Include calls-to-action at appropriate points
- Maintain target duration

**Input:**
```python
{
    "selected_idea": Idea,
    "research_report": ResearchReport,
    "channel_profile": ChannelProfile,
    "target_duration_seconds": int,
    "include_timestamps": bool
}
```

**Output:**
```python
{
    "full_text": str,
    "word_count": int,
    "estimated_duration": int,
    "sections": List[{
        "name": str,
        "start_time": int,
        "end_time": int,
        "text": str
    }],
    "hooks_used": List[str],
    "cta_placement": List[int]
}
```

**Prompt Strategy:**
- Provide channel tone examples
- Include hook and angle from idea
- Specify exact duration target
- Request timestamp annotations

**QC Checks:**
- Word count matches duration target (~150 wpm)
- Tone matches channel profile
- All required elements included
- No forbidden words/topics
- Hook present in first 15 seconds

---

### 2.4 Storyboard Agent

**Purpose:** Break scripts into visual scene descriptions.

**Responsibilities:**
- Parse script into logical scenes
- Create detailed visual descriptions for each scene
- Specify transitions between scenes
- Estimate scene durations
- Note special visual requirements
- Reference channel's visual identity

**Input:**
```python
{
    "script": Script,
    "channel_profile": ChannelProfile,
    "scene_granularity": "coarse" | "medium" | "fine"
}
```

**Output:**
```python
{
    "scenes": List[{
        "scene_number": int,
        "script_text": str,
        "visual_description": str,
        "duration_seconds": int,
        "transition": str,
        "image_style_notes": str,
        "special_requirements": List[str]
    }],
    "total_scenes": int,
    "total_duration": int
}
```

**Prompt Strategy:**
- Provide visual style examples
- Include color palette and aesthetic notes
- Request specific transition types
- Ask for image generation hints

**QC Checks:**
- All script content covered
- Scene count reasonable for duration
- Visual descriptions detailed enough for image generation
- Transitions match channel style

---

### 2.5 Image Prompt Agent

**Purpose:** Generate optimized prompts for AI image generation.

**Responsibilities:**
- Convert scene descriptions to image prompts
- Optimize for specific image generation models
- Include style, lighting, composition details
- Ensure consistency across scenes
- Handle character consistency (if applicable)

**Input:**
```python
{
    "storyboard": Storyboard,
    "channel_profile": ChannelProfile,
    "target_model": "dall-e-3" | "stable-diffusion" | "midjourney"
}
```

**Output:**
```python
{
    "prompts": List[{
        "scene_number": int,
        "prompt": str,
        "negative_prompt": str,
        "style_preset": str,
        "aspect_ratio": str,
        "quality_params": dict
    }]
}
```

**Prompt Engineering:**
- Subject + Action + Context + Style
- Lighting specifications
- Camera angle and composition
- Color grading notes
- Model-specific optimizations

**QC Checks:**
- Prompts are detailed and specific
- Style consistent across all scenes
- No policy-violating content
- Aspect ratio matches channel format

---

### 2.6 Video Production Agent

**Purpose:** Assemble final video from assets.

**Responsibilities:**
- Collect all generated images/assets
- Generate or source voice narration
- Select and add background music
- Apply transitions and effects
- Render final video file
- Ensure technical quality standards

**Input:**
```python
{
    "script": Script,
    "storyboard": Storyboard,
    "scene_assets": List[SceneAsset],
    "channel_profile": ChannelProfile,
    "output_format": str
}
```

**Output:**
```python
{
    "video_file_path": str,
    "duration_seconds": int,
    "resolution": str,
    "file_size_bytes": int,
    "voice_track_path": str,
    "music_track_path": str,
    "render_log": List[str]
}
```

**Tools Used:**
- MoviePy / FFmpeg for editing
- ElevenLabs / TTS API for voice
- Music libraries (Epidemic Sound, etc.)

**QC Checks:**
- Audio levels balanced
- Transitions smooth
- Duration within tolerance
- Resolution matches specification
- No rendering artifacts

---

### 2.7 SEO Agent

**Purpose:** Optimize video metadata for discovery.

**Responsibilities:**
- Generate compelling, keyword-rich titles
- Write detailed, SEO-optimized descriptions
- Research and select relevant tags
- Create thumbnail concepts
- Categorize content appropriately
- Schedule optimal publish times

**Input:**
```python
{
    "video": Video,
    "script": Script,
    "channel_profile": ChannelProfile,
    "target_keywords": List[str]
}
```

**Output:**
```python
{
    "title": str,
    "description": str,
    "tags": List[str],
    "category_id": str,
    "thumbnail_concepts": List[{
        "concept": str,
        "prompt": str,
        "text_overlay": str
    }],
    "publish_schedule": {
        "optimal_date": date,
        "optimal_time": time,
        "timezone": str
    },
    "seo_score": float
}
```

**Optimization Strategy:**
- Keyword density analysis
- Competitor tag research
- Title A/B testing concepts
- Thumbnail psychology principles

**QC Checks:**
- Title under 100 characters
- Description includes keywords naturally
- Tags relevant and varied
- Hashtags from channel profile included

---

### 2.8 Quality Control Agent

**Purpose:** Validate all outputs against standards.

**Responsibilities:**
- Check content against channel constraints
- Verify brand compliance
- Detect forbidden elements
- Assess quality thresholds
- Provide actionable feedback
- Approve or reject with reasons

**Input:**
```python
{
    "content_type": str,
    "content": Any,
    "channel_profile": ChannelProfile,
    "stage": str,
    "constraints": List[Constraint]
}
```

**Output:**
```python
{
    "status": "APPROVED" | "REJECTED" | "REVISION_REQUESTED",
    "checks_performed": List[{
        "check_name": str,
        "passed": bool,
        "details": str
    }],
    "issues_found": List[{
        "severity": "low" | "medium" | "high",
        "description": str,
        "suggestion": str
    }],
    "overall_score": float,
    "notes": str
}
```

**Check Categories:**
- **Content Compliance:** Forbidden topics, words, themes
- **Brand Alignment:** Tone, style, visual identity
- **Quality Standards:** Length, formatting, completeness
- **Technical Requirements:** File formats, resolutions, durations

**QC Gates by Stage:**
| Stage | Auto-QC | Manual Review |
|-------|---------|---------------|
| Idea | ✓ | Optional |
| Research | ✓ | Optional |
| Script | ✓ | ✓ Required |
| Storyboard | ✓ | Optional |
| Assets | ✓ | Optional |
| Video | ✓ | ✓ Required |
| SEO | ✓ | Optional |
| Publish | ✓ | Final check |

---

## 3. Agent Communication

### 3.1 Message Protocol

All inter-agent communication follows this structure:

```python
class AgentMessage(BaseModel):
    message_id: UUID
    correlation_id: UUID  # Links related messages
    project_id: UUID
    sender_agent: str
    receiver_agent: str
    stage: str
    message_type: str  # REQUEST, RESPONSE, NOTIFICATION, ERROR
    payload: dict
    timestamp: datetime
    priority: int  # 1-5, higher = more urgent
```

### 3.2 Communication Patterns

**Pipeline Pattern:** Sequential handoff between stages
```
Research → Idea → Script → Storyboard → Assets → Video → SEO
```

**Request-Response Pattern:** Agent requests data from another
```
Script Writer → Memory System → Get successful hooks
```

**Publish-Subscribe Pattern:** Agents listen for events
```
QC Agent subscribes to "*_COMPLETE" events
```

### 3.3 Error Handling

```python
class AgentError(Exception):
    agent_name: str
    error_code: str
    retryable: bool
    suggestions: List[str]

# Error categories:
# - VALIDATION_ERROR: Input doesn't meet requirements
# - EXECUTION_ERROR: Task failed during execution
# - TIMEOUT_ERROR: Operation exceeded time limit
# - EXTERNAL_ERROR: Third-party service failure
# - CONFIGURATION_ERROR: Missing or invalid config
```

---

## 4. Agent Base Class

```python
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, agent_id: str, config: dict):
        self.agent_id = agent_id
        self.config = config
        self.memory = None
        self.status = "IDLE"
    
    @abstractmethod
    async def execute(self, input_data: dict) -> dict:
        """Execute the agent's primary function."""
        pass
    
    @abstractmethod
    def validate_input(self, input_data: dict) -> bool:
        """Validate incoming data meets requirements."""
        pass
    
    @abstractmethod
    def validate_output(self, output_data: dict) -> bool:
        """Validate output meets quality standards."""
        pass
    
    async def initialize(self, context: dict):
        """Setup agent with project context."""
        self.context = context
        self.memory = context.get("memory")
    
    def get_status(self) -> dict:
        """Return current agent status."""
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "current_project": self.context.get("project_id"),
            "last_execution": self.last_execution_time
        }
    
    async def log_execution(self, input_data: dict, output_data: dict, 
                           execution_time: int, tokens_used: int):
        """Log execution for learning and auditing."""
        log_entry = {
            "agent_name": self.agent_id,
            "project_id": self.context.get("project_id"),
            "input_summary": summarize(input_data),
            "output_summary": summarize(output_data),
            "execution_time_ms": execution_time,
            "tokens_used": tokens_used,
            "status": "SUCCESS"
        }
        await self.memory.store_learning(log_entry)
```

---

## 5. Agent Configuration

### 5.1 Configuration Schema

```yaml
agents:
  research:
    enabled: true
    model: "gpt-4"
    max_tokens: 4000
    temperature: 0.7
    timeout_seconds: 120
    retries: 3
    tools:
      - web_search
      - youtube_search
    
  script_writer:
    enabled: true
    model: "gpt-4"
    max_tokens: 8000
    temperature: 0.8
    timeout_seconds: 180
    retries: 2
    prompt_template: "scripts/writer_v1.txt"
    
  qc_agent:
    enabled: true
    model: "gpt-4"
    strict_mode: true
    auto_reject_threshold: 0.6
    escalation_enabled: true
```

### 5.2 Model Selection Strategy

| Agent | Recommended Model | Rationale |
|-------|------------------|-----------|
| Research | GPT-4 | Complex reasoning, source evaluation |
| Idea Generator | GPT-4 | Creative ideation, pattern matching |
| Script Writer | GPT-4 | Long-form content, narrative flow |
| Storyboard | GPT-4 | Visual imagination, structure |
| Image Prompt | GPT-3.5-Turbo | Straightforward transformation |
| SEO | GPT-4 | Keyword optimization, marketing |
| QC | GPT-4 | Critical evaluation, rule enforcement |

---

## 6. Learning & Improvement

### 6.1 Feedback Loop

```
Agent Execution → Outcome Recorded → Analysis → Pattern Update → Future Improvement
```

### 6.2 Learning Triggers

- **User Approval:** Positive reinforcement
- **User Rejection:** Learn what to avoid
- **Performance Metrics:** High views = success pattern
- **QC Failures:** Identify common mistakes
- **A/B Test Results:** Compare variations

### 6.3 Pattern Updates

```python
async def update_success_patterns(video_metrics: dict, agent_decisions: list):
    if video_metrics["views"] > threshold:
        for decision in agent_decisions:
            pattern = await db.get_pattern(decision.type, decision.value)
            if pattern:
                pattern.success_count += 1
                pattern.update_confidence()
            else:
                await db.create_pattern({
                    "type": decision.type,
                    "value": decision.value,
                    "success_count": 1
                })
```

---

## 7. Scaling Considerations

### 7.1 Horizontal Scaling

- Agents are stateless (state in memory system)
- Multiple instances per agent type possible
- Load balancer distributes requests
- Queue-based architecture for async processing

### 7.2 Rate Limiting

```python
class RateLimiter:
    def __init__(self, agent_id: str, limits: dict):
        self.agent_id = agent_id
        self.limits = limits  # requests_per_minute, tokens_per_hour, etc.
    
    async def acquire(self, tokens: int) -> bool:
        # Check rate limits before execution
        pass
```

### 7.3 Caching Strategy

- Cache frequent memory lookups
- Cache successful prompt templates
- Cache research results (with TTL)
- Invalidate on profile changes
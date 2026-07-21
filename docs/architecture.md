# AICF - AI Content Factory

## Complete Architecture Proposal

### System Overview

AICF (AI Content Factory) is an autonomous AI-powered content production system designed to manage multiple YouTube channels simultaneously. The system orchestrates specialized AI agents through a structured workflow to transform ideas into published videos.

---

## 1. High-Level Architecture

### 1.1 Architecture Pattern

The system follows a **Multi-Agent Orchestration Architecture** with:
- **Event-driven communication** between agents
- **Centralized workflow engine** for process coordination
- **Shared memory layer** for context persistence
- **Profile-based configuration** for multi-channel support

### 1.2 Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer                                │
│                    (Streamlit UI / REST)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Workflow Engine                             │
│              (State Machine / Pipeline Orchestrator)            │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────────┐   ┌──────────────┐
│ Agent Pool   │    │  Memory System   │   │ Profile Mgr  │
│ - Research   │    │  - Channel Mem   │   │ - Identity   │
│ - Idea Gen   │    │  - Content Hist  │   │ - Style Rules│
│ - Script     │    │  - Performance   │   │ - Constraints│
│ - Storyboard │    │  - Learnings     │   │ - Visual ID  │
│ - Image Prmpt│    └──────────────────┘   └──────────────┘
│ - Video Prod │
│ - SEO        │
│ - QC         │
└──────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                            │
│    OpenAI API │ YouTube API │ Storage │ Image Generation       │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Directory Structure

```
/workspace/
├── app/                  # Application layer (UI, API endpoints)
├── core/                 # Core business logic, workflow engine
├── agents/               # Agent implementations
├── models/               # Data models, Pydantic schemas
├── projects/             # Project state and artifacts
├── storage/              # Generated assets (images, audio, video)
└── docs/                 # Documentation
```

---

## 2. Multi-Agent Architecture

### 2.1 Agent Definitions

| Agent | Responsibility | Input | Output |
|-------|---------------|-------|--------|
| **Research Agent** | Trend analysis, topic validation, source gathering | Topic seed, channel profile | Research report, sources, key facts |
| **Idea Generator Agent** | Concept creation, angle selection, hook development | Research data, channel profile | Video ideas with hooks and angles |
| **Script Writer Agent** | Full script creation, timing, pacing | Selected idea, channel profile | Complete script with timestamps |
| **Storyboard Agent** | Scene breakdown, visual planning | Script, channel visual identity | Scene-by-scene visual descriptions |
| **Image Prompt Agent** | AI image generation prompts | Storyboard scenes, visual style | Optimized prompts for each scene |
| **Video Production Agent** | Asset assembly, editing, rendering | Images, audio, script | Final video file |
| **SEO Agent** | Title, description, tags, thumbnails | Video content, channel profile | SEO metadata package |
| **Quality Control Agent** | Content validation, brand compliance | All outputs at each stage | Approval/rejection with feedback |

### 2.2 Agent Communication Protocol

Agents communicate through a **Message Bus Pattern**:

```python
# Message Structure
{
    "message_id": "uuid",
    "agent_from": "script_writer",
    "agent_to": "storyboard",
    "project_id": "uuid",
    "stage": "script_complete",
    "payload": {
        "script": "...",
        "metadata": {...}
    },
    "timestamp": "ISO8601"
}
```

### 2.3 Agent Base Interface

All agents implement a common interface:
- `initialize(context)` - Setup with project context
- `execute(input_data)` - Perform agent task
- `validate(output)` - Self-validation before passing on
- `get_status()` - Current execution status

---

## 3. Workflow Engine Design

### 3.1 Pipeline Stages

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────────┐
│  IDEA   │ →  │RESEARCH │ →  │ SCRIPT  │ →  │ STORYBOARD  │
└─────────┘    └─────────┘    └─────────┘    └─────────────┘
     │              │              │              │
     ▼              ▼              ▼              ▼
  QC Gate        QC Gate        QC Gate        QC Gate

┌─────────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ ASSETS IMG  │ →  │ VIDEO   │ →  │  SEO    │ →  │PUBLISH  │
└─────────────┘    └─────────┘    └─────────┘    └─────────┘
     │              │              │              │
     ▼              ▼              ▼              ▼
  QC Gate        QC Gate        QC Gate      Final QC
```

### 3.2 Stage Definitions

| Stage | Agent(s) | Description | Exit Criteria |
|-------|----------|-------------|---------------|
| **Idea** | Idea Generator | Generate and rank video concepts | 3+ viable ideas produced |
| **Research** | Research Agent | Gather facts, sources, context | Research report complete |
| **Script** | Script Writer | Write full narration script | Script approved by user/QC |
| **Storyboard** | Storyboard Agent | Break script into visual scenes | Scene list with descriptions |
| **Assets** | Image Prompt + External | Generate images/graphics | All scene assets ready |
| **Video** | Video Production | Assemble video with audio | Rendered video file |
| **SEO** | SEO Agent | Optimize metadata | Title, desc, tags ready |
| **Publish** | System | Upload to YouTube | Video published |

### 3.3 State Machine

Each project progresses through states:
`DRAFT → IN_RESEARCH → IN_SCRIPT → IN_STORYBOARD → IN_ASSETS → IN_VIDEO → IN_SEO → READY_PUBLISH → PUBLISHED`

Transitions require:
1. Current stage completion
2. QC approval (auto or manual)
3. User approval (at key milestones)

---

## 4. Memory System Architecture

### 4.1 Memory Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Long-Term Memory                         │
│  (Persistent DB: Channel profiles, historical performance)  │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                   Medium-Term Memory                        │
│     (Project context, recent content, active learning)      │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Short-Term Memory                        │
│        (Current session, in-progress project state)         │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Memory Categories

| Category | Content | Persistence | Usage |
|----------|---------|-------------|-------|
| **Channel Identity** | Name, niche, target audience | Permanent | All agents reference |
| **Style Rules** | Tone, format, visual guidelines | Permanent | Script, storyboard agents |
| **Forbidden Elements** | Topics, words, visuals to avoid | Permanent | QC, all creative agents |
| **Content History** | Past videos, performance metrics | Permanent | Idea generator, research |
| **Successful Patterns** | High-performing formats/hooks | Permanent (updated) | Idea generator |
| **Failed Approaches** | Low performers, rejections | Permanent (updated) | All agents (avoidance) |
| **Project Context** | Current video progress | Session-based | Workflow continuity |
| **Learning Log** | Agent decisions, user feedback | Permanent | Continuous improvement |

### 4.3 Memory Access Pattern

```python
class MemoryAccess:
    def get_channel_profile(channel_id) -> ChannelProfile
    def get_content_history(channel_id, limit=50) -> List[Video]
    def get_successful_patterns(channel_id, category) -> List[Pattern]
    def record_outcome(video_id, metrics) -> None
    def store_learning(agent, decision, outcome) -> None
```

---

## 5. Content Profile System

### 5.1 Profile Schema

Each channel profile contains:

```yaml
channel_identity:
  name: string
  niche: string
  description: string
  target_audience:
    demographics: object
    interests: list[string]
    pain_points: list[string]

style_rules:
  tone: string (documentary, casual, educational, etc.)
  pacing: string (fast, moderate, slow)
  hook_style: string
  call_to_action: string
  language: string
  reading_level: string

visual_identity:
  color_palette: list[string]
  font_styles: list[string]
  image_style: string (cinematic, illustrated, realistic)
  transition_style: string
  logo_placement: string
  watermark: string

format_rules:
  video_orientation: string (horizontal, vertical)
  duration_target: integer (seconds)
  duration_tolerance: integer
  aspect_ratio: string
  resolution: string

content_constraints:
  forbidden_topics: list[string]
  forbidden_words: list[string]
  required_elements: list[string]
  sourcing_rules: list[string]

branding:
  hashtags: list[string]
  intro_template: string
  outro_template: string
  music_style: string
  voice_characteristics: string

recurring_elements:
  characters: list[object]
  segments: list[string]
  running_gags: list[string]
  series_structure: string
```

### 5.2 Profile Examples

#### Historical Documentary Channel
```yaml
channel_identity:
  name: "History Unveiled"
  niche: "Historical documentaries"
  target_audience:
    demographics: {age: "25-54", education: "college+"}
    interests: ["history", "documentaries", "education"]

style_rules:
  tone: "documentary, authoritative, engaging"
  pacing: "moderate"
  language: "English"

visual_identity:
  image_style: "old cinematic, sepia tones"
  color_palette: ["#704214", "#8B7355", "#2C2C2C"]
  transition_style: "slow fades"

format_rules:
  video_orientation: "horizontal"
  duration_target: 600
  aspect_ratio: "16:9"

content_constraints:
  forbidden_topics: ["conspiracy theories", "unverified claims"]
  sourcing_rules: ["academic sources only", "cite primary sources"]

branding:
  hashtags: ["#history", "#documentary", "#education"]
  music_style: "orchestral, dramatic"
```

#### Cooking Reels Channel
```yaml
channel_identity:
  name: "Quick Bites"
  niche: "Quick cooking tutorials"
  target_audience:
    demographics: {age: "18-35"}
    interests: ["cooking", "food", "quick recipes"]

style_rules:
  tone: "energetic, friendly, casual"
  pacing: "fast"
  language: "English"

visual_identity:
  image_style: "bright, clean food photography"
  color_palette: ["#FF6B6B", "#FFE66D", "#4ECDC4"]

format_rules:
  video_orientation: "vertical"
  duration_target: 30
  aspect_ratio: "9:16"

branding:
  hashtags: ["#cooking", "#reels", "#quickrecipes"]
  music_style: "upbeat, trendy"
```

---

## 6. Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Streamlit | User interface, approvals |
| **Backend** | Python 3.11+ | Core application |
| **Database** | SQLite (dev) / PostgreSQL (prod) | Persistent storage |
| **ORM** | SQLAlchemy | Database operations |
| **Validation** | Pydantic | Data validation |
| **AI/LLM** | OpenAI API | Agent intelligence |
| **Image Gen** | DALL-E 3 / Stable Diffusion | Visual assets |
| **Audio** | ElevenLabs / TTS API | Voice generation |
| **Video** | MoviePy / FFmpeg | Video assembly |
| **Storage** | Local FS / S3 | Asset storage |
| **Queue** | Celery + Redis (future) | Async job processing |

---

## 7. Security & Compliance

- API keys stored in environment variables
- Rate limiting on external API calls
- Content moderation before publishing
- Copyright compliance checks
- YouTube API quota management
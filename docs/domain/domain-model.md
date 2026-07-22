# AICF v2 Domain Model

## Overview

This document describes the core domain entities, their responsibilities, and business logic in AICF v2.

---

## Core Aggregates

### Organization Aggregate

**Root Entity**: Organization

**Purpose**: Represents a tenant organization in the SaaS platform.

**Entities:**
- Organization (root)
- Team
- User
- Role
- Permission
- UserRole
- TeamMember

**Invariants:**
- Every organization must have at least one owner
- Users can only belong to one organization
- Roles must exist before assignment

### Channel Aggregate

**Root Entity**: ChannelProfile

**Purpose**: Defines brand identity and content strategy for a channel.

**Entities:**
- ChannelProfile (root)
- ContentStrategy

**Invariants:**
- Channel profile must belong to an organization
- Each channel has exactly one content strategy
- Brand guidelines are required

### Content Planning Aggregate

**Root Entity**: Playlist

**Purpose**: Organizes episodes into thematic collections.

**Entities:**
- Playlist (root)
- Episode

**Invariants:**
- Playlist must belong to organization and channel
- Episodes cannot exist without playlist
- Episode status transitions follow defined rules

### Production Aggregate

**Root Entity**: ContentJob

**Purpose**: Manages workflow execution and asset generation.

**Entities:**
- ContentJob (root)
- AgentExecution
- Asset

**Invariants:**
- ContentJob must reference an episode
- AgentExecution must reference a ContentJob
- Assets must be linked to an episode

---

## Entity Details

### Organization

```python
class Organization(Base):
    id: int
    name: str
    slug: str  # Unique identifier
    subscription_plan: str
    status: OrganizationStatus
    settings: JSON
    created_at: datetime
    
    # Relationships
    teams: List[Team]
    users: List[User]
    channel_profiles: List[ChannelProfile]
```

### ChannelProfile

```python
class ChannelProfile(Base):
    id: int
    organization_id: int
    name: str
    description: str
    target_audience: JSON
    brand_guidelines: JSON
    visual_identity: JSON
    voice_settings: JSON
    seo_defaults: JSON
    
    # Relationships
    content_strategy: ContentStrategy
    playlists: List[Playlist]
    episodes: List[Episode]
```

### Playlist

```python
class Playlist(Base):
    id: int
    organization_id: int
    channel_profile_id: int
    title: str
    description: str
    playlist_type: PlaylistType  # PLANNED or DYNAMIC
    generation_rules: JSON  # For dynamic playlists
    
    # Relationships
    episodes: List[Episode]
    channel_profile: ChannelProfile
```

### Episode

```python
class Episode(Base):
    id: int
    organization_id: int
    playlist_id: int
    channel_profile_id: int
    title: str
    description: Optional[str]
    topic: Optional[str]
    status: EpisodeStatus
    scheduled_date: Optional[datetime]
    
    # Relationships
    playlist: Playlist
    channel_profile: ChannelProfile
    content_jobs: List[ContentJob]
    agent_executions: List[AgentExecution]
    assets: List[Asset]
```

### ContentJob

```python
class ContentJob(Base):
    id: int
    organization_id: int
    episode_id: int
    job_type: JobType  # WORKFLOW or STAGE
    stage_type: Optional[WorkflowStageType]
    stage_order: Optional[int]
    status: ContentJobStatus
    metadata: JSON
    retry_count: int
    max_retries: int
    
    # Relationships
    episode: Episode
    agent_execution: AgentExecution
```

### AgentExecution

```python
class AgentExecution(Base):
    id: int
    organization_id: int
    episode_id: int
    content_job_id: int
    execution_id: str  # UUID
    agent_name: str
    agent_type: str
    status: AgentExecutionStatus
    input_data: JSON
    output_data: JSON
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    execution_time_seconds: float
    tokens_used: int
    
    # Relationships
    content_job: ContentJob
    episode: Episode
```

---

## Value Objects

### BrandGuidelines

```python
@dataclass
class BrandGuidelines:
    colors: Dict[str, str]  # Primary, secondary, accent
    fonts: Dict[str, str]   # Heading, body
    logo_url: str
    tone_of_voice: str
    do_not_use: List[str]
```

### TargetAudience

```python
@dataclass
class TargetAudience:
    age_range: Tuple[int, int]
    demographics: Dict[str, str]
    interests: List[str]
    pain_points: List[str]
```

### SEOSettings

```python
@dataclass
class SEOSettings:
    default_tags: List[str]
    category: str
    hashtag_strategy: str
    keyword_focus: List[str]
```

---

## Domain Services

### WorkflowOrchestrationService

**Responsibility**: Coordinate workflow execution across stages.

**Methods:**
- `start_workflow(episode: Episode) -> ContentJob`
- `execute_stage(episode: Episode, stage: WorkflowStageType) -> AgentResult`
- `retry_stage(episode: Episode, stage: WorkflowStageType) -> AgentResult`
- `pause_workflow(episode: Episode) -> bool`
- `resume_workflow(episode: Episode) -> bool`

### ChannelManagementService

**Responsibility**: Manage channel profiles and strategies.

**Methods:**
- `create_channel(org_id: int, config: ChannelConfig) -> ChannelProfile`
- `update_brand_guidelines(channel_id: int, guidelines: BrandGuidelines)`
- `set_content_strategy(channel_id: int, strategy: ContentStrategy)`

### ContentPlanningService

**Responsibility**: Manage playlists and episode planning.

**Methods:**
- `create_playlist(channel_id: int, title: str) -> Playlist`
- `add_episode(playlist_id: int, topic: str) -> Episode`
- `generate_dynamic_episodes(playlist: Playlist) -> List[Episode]`

---

## Domain Events

### Events Published

| Event | When Raised | Payload |
|-------|-------------|---------|
| `OrganizationCreated` | New org registered | org_id, name |
| `ChannelProfileCreated` | New channel created | channel_id, org_id |
| `EpisodePlanned` | Episode created | episode_id, playlist_id |
| `WorkflowStarted` | Workflow initiated | workflow_id, episode_id |
| `StageCompleted` | Stage finishes | stage_type, success |
| `ContentPublished` | Episode published | episode_id, platform_url |

### Event Handlers

```python
class EventHandler:
    @on_event(EpisodePlanned)
    def auto_start_workflow(self, event: EpisodePlanned):
        if event.auto_start:
            workflow_service.start_workflow(event.episode_id)
    
    @on_event(StageCompleted)
    def trigger_next_stage(self, event: StageCompleted):
        if event.success:
            next_stage = get_next_stage(event.stage_type)
            if next_stage:
                workflow_engine.execute_stage(event.episode, next_stage)
```

---

## Document Information

- **Version**: 2.0
- **Last Updated**: 2024
- **Author**: AICF Engineering Team
- **Status**: Active Development

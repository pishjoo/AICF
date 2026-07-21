# AICF v2 Domain Model

## Overview

This document defines the core domain entities for AICF v2, a multi-tenant SaaS content production platform.

---

## 1. Multi-Tenant Architecture

### 1.1 Organization

The top-level tenant entity representing a company or business.

```python
class Organization(Base):
    id: UUID
    name: str
    slug: str  # Unique identifier for URLs
    subscription_tier: str  # free, pro, enterprise
    max_channels: int
    max_users: int
    max_storage_gb: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
```

**Business Rules:**
- Each organization is completely isolated from others
- Subscription tier determines resource limits
- Slug must be unique across all organizations

### 1.2 Team

A subdivision within an organization for grouping users.

```python
class Team(Base):
    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
```

**Business Rules:**
- Teams belong to exactly one organization
- Users can be members of multiple teams within an organization
- Teams can have their own channel assignments

### 1.3 User

A system user who can access the platform.

```python
class User(Base):
    id: UUID
    email: str
    hashed_password: str
    full_name: str
    avatar_url: Optional[str]
    is_active: bool
    is_super_admin: bool  # Platform-wide admin
    created_at: datetime
    last_login_at: Optional[datetime]
```

**Business Rules:**
- Email must be unique across the platform
- Passwords are hashed using bcrypt
- Super admins can access all organizations

### 1.4 OrganizationMember

Links users to organizations with specific roles.

```python
class OrganizationMember(Base):
    id: UUID
    organization_id: UUID
    user_id: UUID
    role_id: UUID
    invited_at: datetime
    joined_at: Optional[datetime]
    invited_by: UUID
    status: str  # pending, active, suspended
```

**Business Rules:**
- Composite unique constraint on (organization_id, user_id)
- Members can only access resources in their organization
- Invitation flow required for new members

### 1.5 Role

Defines permissions within an organization.

```python
class Role(Base):
    id: UUID
    organization_id: UUID
    name: str  # owner, admin, editor, viewer
    description: Optional[str]
    is_system_role: bool  # Cannot be deleted
    created_at: datetime
    permissions: List[Permission]  # Many-to-many
```

**Built-in Roles:**
- **Owner**: Full control, can delete organization
- **Admin**: Manage members, channels, billing
- **Editor**: Create/edit content, cannot manage members
- **Viewer**: Read-only access

### 1.6 Permission

Granular access control entries.

```python
class Permission(Base):
    id: UUID
    name: str  # e.g., "channels.create", "episodes.publish"
    description: str
    resource_type: str  # channel, episode, playlist, etc.
    action: str  # create, read, update, delete, publish
```

**Permission Categories:**
- `channels.*` - Channel profile management
- `playlists.*` - Playlist operations
- `episodes.*` - Episode lifecycle
- `assets.*` - Media asset management
- `team.*` - Member management
- `billing.*` - Subscription and payments

### 1.7 AuditLog

Track all significant actions for compliance.

```python
class AuditLog(Base):
    id: UUID
    organization_id: UUID
    user_id: UUID
    action: str
    resource_type: str
    resource_id: UUID
    old_values: Optional[JSON]
    new_values: Optional[JSON]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
```

---

## 2. Channel Profile System

### 2.1 ChannelProfile

Represents a content identity for a specific platform/channel.

```python
class ChannelProfile(Base):
    id: UUID
    organization_id: UUID
    
    # Basic Identity
    name: str
    platform: str  # youtube, tiktok, instagram, linkedin
    handle: Optional[str]  # @username
    description: Optional[str]
    
    # Audience Definition
    target_audience: JSON  # {demographics, interests, pain_points}
    age_range: Optional[str]  # "18-24", "25-34", etc.
    gender_focus: Optional[str]  # all, male, female, non-binary
    
    # Content Characteristics
    interests: List[str]
    content_style: str  # documentary, tutorial, entertainment
    tone: str  # professional, casual, humorous
    language: str  # ISO 639-1 code
    reading_level: Optional[str]  # elementary, high_school, college
    
    # Visual Identity
    visual_identity: JSON  # {color_palette, fonts, logo_url}
    image_dimensions: str  # "1920x1080", "1080x1920"
    video_format: str  # mp4, mov
    aspect_ratio: str  # 16:9, 9:16, 1:1
    
    # Audio/Character
    voice_type: Optional[str]  # male_narrator, female_host
    character_avatar: Optional[JSON]  # Character descriptions
    music_style: Optional[str]
    
    # Branding Rules
    branding_rules: JSON  # Specific brand guidelines
    hashtag_strategy: JSON  # {always_include, category_tags}
    seo_rules: JSON  # Keyword strategies
    
    # Status
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: UUID
```

**Business Rules:**
- Each profile belongs to exactly one organization
- Platform determines available features
- All content generated must follow profile rules

---

## 3. Content Strategy

### 3.1 ContentStrategy

Long-term planning for a channel.

```python
class ContentStrategy(Base):
    id: UUID
    channel_profile_id: UUID
    
    # Planning
    goals: List[str]  # ["grow_subscribers", "increase_engagement"]
    content_pillars: List[str]  # Main topic categories
    publishing_schedule: JSON  # {days_of_week, times}
    frequency_per_week: int
    platforms: List[str]  # Cross-platform strategy
    
    # KPIs
    target_kpis: JSON  # {views_target, engagement_rate, subscriber_growth}
    
    # Metadata
    start_date: date
    end_date: Optional[date]
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

---

## 4. Playlist System

### 4.1 Playlist

A collection of episodes, either planned or dynamic.

```python
class Playlist(Base):
    id: UUID
    channel_profile_id: UUID
    name: str
    description: Optional[str]
    
    # Type discriminator
    playlist_type: str  # "planned" or "dynamic"
    
    # For Planned Playlists
    episode_roadmap: Optional[JSON]  # Predefined episode list
    production_template_id: Optional[UUID]
    
    # For Dynamic Playlists
    content_source: Optional[JSON]  # RSS feeds, keywords, monitors
    auto_generation_enabled: bool
    max_episodes: Optional[int]
    
    # Common
    episode_count: int  # Computed
    status: str  # draft, active, archived
    created_at: datetime
    updated_at: datetime
```

**Planned Playlist Example:**
```json
{
  "episodes": [
    {"order": 1, "topic": "Introduction to AI", "status": "published"},
    {"order": 2, "topic": "Machine Learning Basics", "status": "in_production"},
    {"order": 3, "topic": "Deep Learning Explained", "status": "planned"}
  ],
  "total_planned": 150,
  "timeline": "12_months"
}
```

**Dynamic Playlist Example:**
```json
{
  "sources": [
    {"type": "rss", "url": "https://techcrunch.com/feed"},
    {"type": "keywords", "terms": ["AI", "machine learning", "LLM"]}
  ],
  "refresh_interval_hours": 6,
  "auto_create_episodes": true
}
```

### 4.2 PlaylistEpisode

Junction table for playlist ordering.

```python
class PlaylistEpisode(Base):
    id: UUID
    playlist_id: UUID
    episode_id: UUID
    order: int
    added_at: datetime
    added_by: UUID
```

---

## 5. Episode System

### 5.1 Episode

A single content unit in any state.

```python
class Episode(Base):
    id: UUID
    channel_profile_id: UUID
    playlist_id: Optional[UUID]
    
    # Identification
    title: str
    description: Optional[str]
    episode_number: Optional[int]
    
    # Type & Source
    episode_type: str  # planned, generated, manual
    source_topic: Optional[str]  # For generated episodes
    source_url: Optional[str]  # For dynamic episodes
    
    # Lifecycle
    status: str  # draft, research, script, storyboard, production, review, approved, published, archived
    priority: int  # 1-5
    
    # Content References
    script_id: Optional[UUID]
    storyboard_id: Optional[UUID]
    video_asset_id: Optional[UUID]
    
    # Scheduling
    scheduled_publish_at: Optional[datetime]
    published_at: Optional[datetime]
    
    # Metadata
    duration_seconds: Optional[int]
    tags: List[str]
    
    created_at: datetime
    updated_at: datetime
    created_by: UUID
```

**Status Flow:**
```
draft → research → script → storyboard → production → review → approved → published
                                         ↓
                                       archived
```

---

## 6. Production Template

### 6.1 ProductionTemplate

Reusable production rules for consistent output.

```python
class ProductionTemplate(Base):
    id: UUID
    channel_profile_id: UUID
    name: str
    description: Optional[str]
    
    # Character/Voice
    narrator_character: Optional[JSON]
    voice_settings: Optional[JSON]  # {provider, voice_id, speed, pitch}
    
    # Visual Style
    visual_style: JSON  # {color_grading, filters, transitions}
    intro_template: Optional[JSON]  # Intro sequence config
    outro_template: Optional[JSON]  # Outro sequence config
    
    # Audio
    music_library: List[str]  # Allowed music tracks
    sfx_preferences: JSON
    
    # Format
    duration_target_seconds: int
    duration_tolerance_seconds: int
    aspect_ratio: str
    resolution: str  # 1080p, 4K
    
    # Branding
    watermark_position: Optional[str]
    logo_overlay: Optional[JSON]
    
    is_default: bool  # Default template for channel
    created_at: datetime
    updated_at: datetime
```

---

## 7. Content Job

### 7.1 ContentJob

Actual production execution tracking.

```python
class ContentJob(Base):
    id: UUID
    episode_id: UUID
    stage: str  # research, script, storyboard, etc.
    
    # Execution
    status: str  # pending, running, completed, failed, cancelled
    progress_percentage: int
    
    # Agent Tracking
    agents_involved: List[JSON]  # [{agent_type, started_at, completed_at}]
    
    # Retry Logic
    retry_count: int
    max_retries: int
    last_error: Optional[str]
    
    # Cost Tracking
    ai_provider_costs: JSON  # {openai: 0.50, elevenlabs: 0.30}
    total_cost_usd: Decimal
    tokens_used: JSON  # {prompt_tokens, completion_tokens}
    
    # Timing
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    
    created_at: datetime
    updated_at: datetime
```

---

## 8. Asset Management

### 8.1 Asset

Managed media files.

```python
class Asset(Base):
    id: UUID
    organization_id: UUID
    episode_id: Optional[UUID]
    
    # Identification
    name: str
    asset_type: str  # image, video, audio, subtitle, script, thumbnail
    
    # Storage
    file_path: str
    file_url: str
    file_size_bytes: int
    mime_type: str
    storage_provider: str  # local, s3, gcs
    
    # Metadata
    duration_seconds: Optional[int]  # For audio/video
    dimensions: Optional[str]  # For images/video
    format: str  # mp4, png, mp3, srt
    
    # Generation Info
    generated_by_agent: Optional[str]
    generation_prompt: Optional[str]  # For AI-generated assets
    source_asset_id: Optional[UUID]  # For derived assets
    
    # Status
    status: str  # uploading, processing, ready, failed
    checksum: str  # For integrity verification
    
    created_at: datetime
    updated_at: datetime
```

### 8.2 AssetRelationship

Track asset dependencies.

```python
class AssetRelationship(Base):
    id: UUID
    parent_asset_id: UUID
    child_asset_id: UUID
    relationship_type: str  # derived_from, part_of, alternate_version
    metadata: Optional[JSON]
```

---

## 9. Entity Relationships Summary

```
Organization (1) ──┬── (N) Team
                   ├── (N) OrganizationMember ── (1) User
                   ├── (N) Role ── (N) Permission
                   ├── (N) ChannelProfile
                   │       └── (1) ContentStrategy
                   │       ├── (N) Playlist
                   │       │     └── (N) Episode
                   │       ├── (N) Episode
                   │       │     ├── (1) ContentJob (per stage)
                   │       │     └── (N) Asset
                   │       └── (N) ProductionTemplate
                   ├── (N) AuditLog
                   └── (N) Asset
```

---

## 10. Domain Events

Key events for event-driven architecture:

| Event | Trigger | Consumers |
|-------|---------|-----------|
| `OrganizationCreated` | New org signup | Billing, Analytics |
| `ChannelProfileCreated` | Profile setup | Strategy, Templates |
| `EpisodeStatusChanged` | Workflow progression | Notifications, Jobs |
| `ContentJobCompleted` | Stage finished | Workflow Engine |
| `AssetReady` | Asset processing done | Episode, Thumbnails |
| `EpisodePublished` | Publish action | Analytics, Social |
| `MemberInvited` | Invite sent | Email Service |
| `RolePermissionsChanged` | Admin action | Cache Invalidation |

---

*Document Version: 2.0*
*Last Updated: 2024*

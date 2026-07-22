# AICF v2 Database Schema

## Overview

This document provides a complete reference for the AICF v2 database schema implemented in `database/models.py`.

---

## Schema Summary

| Table | Columns | Purpose |
|-------|---------|---------|
| organizations | 8 | Tenant organizations |
| teams | 6 | Team subdivisions |
| users | 10 | User accounts |
| roles | 4 | RBAC roles |
| permissions | 5 | Permission definitions |
| user_roles | 6 | Role assignments |
| team_members | 6 | Team membership |
| channel_profiles | 12 | Channel brand identity |
| content_strategies | 7 | Content strategy per channel |
| playlists | 9 | Content collections |
| episodes | 12 | Individual content units |
| production_templates | 8 | Production presets |
| content_jobs | 13 | Workflow jobs |
| assets | 12 | Generated media files |
| agent_executions | 18 | AI execution records |

---

## Entity Definitions

### Organizations

```sql
CREATE TABLE organizations (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    subscription_plan VARCHAR(50) DEFAULT 'free',
    status VARCHAR(20) DEFAULT 'active',
    settings JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Users

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id),
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
```

### Roles & Permissions

```sql
CREATE TABLE roles (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_built_in BOOLEAN DEFAULT FALSE
);

CREATE TABLE permissions (
    id INTEGER PRIMARY KEY,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT,
    UNIQUE(resource, action)
);

CREATE TABLE user_roles (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    role_id INTEGER REFERENCES roles(id),
    organization_id INTEGER REFERENCES organizations(id),
    granted_by INTEGER REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, role_id, organization_id)
);
```

### Channel Profiles

```sql
CREATE TABLE channel_profiles (
    id INTEGER PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    target_audience JSON DEFAULT '{}',
    brand_guidelines JSON DEFAULT '{}',
    visual_identity JSON DEFAULT '{}',
    voice_settings JSON DEFAULT '{}',
    seo_defaults JSON DEFAULT '{}',
    metadata JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
```

### Playlists

```sql
CREATE TABLE playlists (
    id INTEGER PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id),
    channel_profile_id INTEGER REFERENCES channel_profiles(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    playlist_type VARCHAR(20) DEFAULT 'planned',
    generation_rules JSON DEFAULT '{}',
    metadata JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
```

### Episodes

```sql
CREATE TABLE episodes (
    id INTEGER PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id),
    playlist_id INTEGER REFERENCES playlists(id),
    channel_profile_id INTEGER REFERENCES channel_profiles(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    topic TEXT,
    status VARCHAR(30) DEFAULT 'planned',
    scheduled_date TIMESTAMP,
    published_url VARCHAR(500),
    metadata JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
```

### Content Jobs

```sql
CREATE TABLE content_jobs (
    id INTEGER PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id),
    episode_id INTEGER REFERENCES episodes(id),
    job_type VARCHAR(20) NOT NULL,
    stage_type VARCHAR(50),
    stage_order INTEGER,
    status VARCHAR(30) DEFAULT 'pending',
    input_data JSON DEFAULT '{}',
    output_data JSON DEFAULT '{}',
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    metadata JSON DEFAULT '{}',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Agent Executions

```sql
CREATE TABLE agent_executions (
    id INTEGER PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id),
    episode_id INTEGER REFERENCES episodes(id),
    content_job_id INTEGER REFERENCES content_jobs(id),
    execution_id VARCHAR(100) UNIQUE,
    agent_name VARCHAR(100) NOT NULL,
    agent_type VARCHAR(100),
    status VARCHAR(30) DEFAULT 'pending',
    input_data JSON DEFAULT '{}',
    output_data JSON DEFAULT '{}',
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    execution_time_seconds FLOAT,
    prompt_tokens BIGINT,
    completion_tokens BIGINT,
    total_tokens BIGINT,
    cost_usd DECIMAL(10,6),
    retry_count INTEGER DEFAULT 0,
    parent_execution_id INTEGER,
    metadata JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Indexes

```sql
-- Organization scoping
CREATE INDEX idx_users_org ON users(organization_id);
CREATE INDEX idx_channels_org ON channel_profiles(organization_id);
CREATE INDEX idx_playlists_org ON playlists(organization_id);
CREATE INDEX idx_episodes_org ON episodes(organization_id);
CREATE INDEX idx_jobs_org ON content_jobs(organization_id);
CREATE INDEX idx_executions_org ON agent_executions(organization_id);

-- Foreign keys
CREATE INDEX idx_episodes_playlist ON episodes(playlist_id);
CREATE INDEX idx_episodes_channel ON episodes(channel_profile_id);
CREATE INDEX idx_jobs_episode ON content_jobs(episode_id);
CREATE INDEX idx_executions_episode ON agent_executions(episode_id);
CREATE INDEX idx_executions_job ON agent_executions(content_job_id);

-- Status queries
CREATE INDEX idx_episodes_status ON episodes(status);
CREATE INDEX idx_jobs_status ON content_jobs(status);
CREATE INDEX idx_executions_status ON agent_executions(status);

-- Composite indexes
CREATE INDEX idx_org_status ON episodes(organization_id, status);
CREATE INDEX idx_org_created ON episodes(organization_id, created_at);
```

---

## Enumerations

### EpisodeStatus

```python
class EpisodeStatus(Enum):
    PLANNED = "planned"
    RESEARCHING = "researching"
    SCRIPTING = "scripting"
    STORYBOARDING = "storyboarding"
    ASSET_GENERATING = "asset_generating"
    VIDEO_PRODUCING = "video_producing"
    SEO_OPTIMIZED = "seo_optimized"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    FAILED = "failed"
```

### ContentJobStatus

```python
class ContentJobStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
```

### AgentExecutionStatus

```python
class AgentExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
```

---

## Document Information

- **Version**: 2.0
- **Last Updated**: 2024
- **Author**: AICF Engineering Team
- **Status**: Active Development

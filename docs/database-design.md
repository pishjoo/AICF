# AICF - Database Design

## Entity Relationship Model

This document defines the database schema for the AICF system.

---

## 1. Core Entities

### 1.1 Channel

Represents a YouTube channel managed by the system.

```sql
CREATE TABLE channels (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    youtube_id      VARCHAR(100),  -- YouTube channel ID
    niche           VARCHAR(255),
    description     TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active       BOOLEAN DEFAULT TRUE
);
```

### 1.2 Channel Profile

Complete profile configuration for a channel.

```sql
CREATE TABLE channel_profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id          UUID REFERENCES channels(id) ON DELETE CASCADE,
    
    -- Identity
    target_audience     JSONB,  -- {demographics, interests, pain_points}
    
    -- Style Rules
    tone                VARCHAR(100),
    pacing              VARCHAR(50),
    hook_style          VARCHAR(255),
    call_to_action      TEXT,
    language            VARCHAR(50) DEFAULT 'English',
    reading_level       VARCHAR(50),
    
    -- Visual Identity
    color_palette       JSONB,  -- Array of hex colors
    font_styles         JSONB,  -- Array of font names
    image_style         VARCHAR(255),
    transition_style    VARCHAR(255),
    logo_placement      VARCHAR(100),
    watermark_url       VARCHAR(500),
    
    -- Format Rules
    video_orientation   VARCHAR(20) CHECK (video_orientation IN ('horizontal', 'vertical')),
    duration_target     INTEGER,  -- seconds
    duration_tolerance  INTEGER,  -- seconds
    aspect_ratio        VARCHAR(10),
    resolution          VARCHAR(20),
    
    -- Branding
    hashtags            JSONB,  -- Array of hashtags
    intro_template      TEXT,
    outro_template      TEXT,
    music_style         VARCHAR(255),
    voice_characteristics TEXT,
    
    -- Recurring Elements
    characters          JSONB,  -- Array of character objects
    segments            JSONB,  -- Array of segment names
    series_structure    TEXT,
    
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 1.3 Content Constraints

Forbidden and required elements for a channel.

```sql
CREATE TABLE content_constraints (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_profile_id  UUID REFERENCES channel_profiles(id) ON DELETE CASCADE,
    constraint_type     VARCHAR(50) CHECK (constraint_type IN ('forbidden_topic', 'forbidden_word', 'required_element', 'sourcing_rule')),
    value               TEXT NOT NULL,
    severity            VARCHAR(20) DEFAULT 'high',  -- low, medium, high
    description         TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 2. Project & Workflow Entities

### 2.1 Project

Represents a single video production project.

```sql
CREATE TABLE projects (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id          UUID REFERENCES channels(id),
    title               VARCHAR(500),
    description         TEXT,
    
    -- Workflow State
    status              VARCHAR(50) DEFAULT 'DRAFT' CHECK (status IN (
        'DRAFT', 'IN_RESEARCH', 'IN_SCRIPT', 'IN_STORYBOARD', 
        'IN_ASSETS', 'IN_VIDEO', 'IN_SEO', 'READY_PUBLISH', 
        'PUBLISHED', 'ARCHIVED', 'FAILED'
    )),
    current_stage       VARCHAR(50),
    
    -- Content References
    selected_idea_id    UUID,  -- References ideas table
    script_id           UUID,  -- References scripts table
    
    -- Timestamps
    started_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at        TIMESTAMP,
    published_at        TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 Idea

Generated video ideas/concepts.

```sql
CREATE TABLE ideas (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID REFERENCES projects(id) ON DELETE CASCADE,
    title               VARCHAR(500) NOT NULL,
    hook                TEXT,
    angle               TEXT,
    description         TEXT,
    research_notes      TEXT,
    
    -- Scoring
    relevance_score     DECIMAL(3,2),  -- 0.00 to 1.00
    viral_potential     DECIMAL(3,2),
    feasibility_score   DECIMAL(3,2),
    
    -- Status
    is_selected         BOOLEAN DEFAULT FALSE,
    rejection_reason    TEXT,
    
    generated_by        VARCHAR(100),  -- Agent identifier
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.3 Research Report

Research data gathered for a project.

```sql
CREATE TABLE research_reports (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID REFERENCES projects(id) ON DELETE CASCADE,
    
    -- Content
    summary             TEXT,
    key_facts           JSONB,  -- Array of fact objects
    sources             JSONB,  -- Array of source objects {url, title, credibility}
    trending_topics     JSONB,
    competitor_analysis TEXT,
    
    -- Metadata
    sources_count       INTEGER,
    facts_count         INTEGER,
    
    generated_by        VARCHAR(100),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.4 Script

Video narration script.

```sql
CREATE TABLE scripts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID REFERENCES projects(id) ON DELETE CASCADE,
    
    -- Content
    full_text           TEXT,
    word_count          INTEGER,
    estimated_duration  INTEGER,  -- seconds
    
    -- Structure
    sections            JSONB,  -- Array of section objects
    timestamps          JSONB,  -- Time-coded segments
    
    -- Approval
    approval_status     VARCHAR(50) DEFAULT 'PENDING',  -- PENDING, APPROVED, REJECTED
    approval_notes      TEXT,
    approved_by         VARCHAR(100),
    approved_at         TIMESTAMP,
    
    version             INTEGER DEFAULT 1,
    parent_script_id    UUID,  -- For revisions
    
    generated_by        VARCHAR(100),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.5 Storyboard

Visual scene breakdown.

```sql
CREATE TABLE storyboards (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_id           UUID REFERENCES scripts(id),
    
    -- Content
    scenes              JSONB,  -- Array of scene objects
    
    -- Scene object structure:
    -- {
    --   "scene_number": 1,
    --   "script_text": "...",
    --   "visual_description": "...",
    --   "duration_seconds": 5,
    --   "transition": "fade",
    --   "notes": "..."
    -- }
    
    total_scenes        INTEGER,
    total_duration      INTEGER,  -- seconds
    
    generated_by        VARCHAR(100),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.6 Scene Assets

Generated assets for each scene.

```sql
CREATE TABLE scene_assets (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    storyboard_id       UUID REFERENCES storyboards(id),
    scene_number        INTEGER NOT NULL,
    
    -- Asset Types
    asset_type          VARCHAR(50) CHECK (asset_type IN ('image', 'video_clip', 'audio', 'text_overlay')),
    
    -- Generation
    prompt_used         TEXT,
    generation_params   JSONB,
    
    -- Storage
    file_path           VARCHAR(500),
    file_url            VARCHAR(500),
    thumbnail_path      VARCHAR(500),
    
    -- Status
    status              VARCHAR(50) DEFAULT 'PENDING',  -- PENDING, GENERATING, READY, FAILED
    error_message       TEXT,
    
    -- External IDs
    external_job_id     VARCHAR(255),  -- DALL-E, Stable Diffusion job ID
    
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at        TIMESTAMP
);
```

### 2.7 Video

Final rendered video.

```sql
CREATE TABLE videos (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID REFERENCES projects(id),
    
    -- File Info
    file_path           VARCHAR(500),
    file_url            VARCHAR(500),
    file_size_bytes     BIGINT,
    duration_seconds    INTEGER,
    resolution          VARCHAR(20),
    format              VARCHAR(20),
    
    -- Composition
    voice_track_path    VARCHAR(500),
    music_track_path    VARCHAR(500),
    assets_used         JSONB,  -- Array of asset IDs
    
    -- Rendering
    render_params       JSONB,
    render_time_seconds INTEGER,
    
    -- Status
    status              VARCHAR(50) DEFAULT 'PENDING',
    error_message       TEXT,
    
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at        TIMESTAMP
);
```

### 2.8 SEO Metadata

SEO optimization data.

```sql
CREATE TABLE seo_metadata (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id            UUID REFERENCES videos(id),
    
    -- YouTube Fields
    title               VARCHAR(100) NOT NULL,
    description         TEXT,
    tags                JSONB,  -- Array of tags
    category_id         VARCHAR(50),
    
    -- Thumbnail
    thumbnail_prompt    TEXT,
    thumbnail_path      VARCHAR(500),
    thumbnail_variants  JSONB,  -- Array of thumbnail options
    
    -- Optimization
    keyword_density     JSONB,
    seo_score           DECIMAL(3,2),
    
    -- Schedule
    publish_date        TIMESTAMP,
    is_scheduled        BOOLEAN DEFAULT FALSE,
    
    generated_by        VARCHAR(100),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. Memory & Learning Entities

### 3.1 Content History

Historical record of published content.

```sql
CREATE TABLE content_history (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id          UUID REFERENCES channels(id),
    video_id            UUID REFERENCES videos(id),
    
    -- YouTube Data
    youtube_video_id    VARCHAR(50),
    youtube_url         VARCHAR(255),
    
    -- Performance Metrics
    views               BIGINT DEFAULT 0,
    likes               INTEGER DEFAULT 0,
    comments            INTEGER DEFAULT 0,
    shares              INTEGER DEFAULT 0,
    watch_time_seconds  BIGINT DEFAULT 0,
    average_view_duration INTEGER,
    click_through_rate  DECIMAL(5,4),
    retention_rate      DECIMAL(5,4),
    
    -- Timestamps
    published_at        TIMESTAMP,
    metrics_updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 Success Patterns

Learned successful patterns.

```sql
CREATE TABLE success_patterns (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id          UUID REFERENCES channels(id),
    
    -- Pattern Info
    pattern_type        VARCHAR(50),  -- hook_style, topic, format, duration, etc.
    pattern_value       TEXT,
    description         TEXT,
    
    -- Metrics
    success_count       INTEGER DEFAULT 1,
    avg_performance     DECIMAL(10,2),  -- Average views or engagement
    confidence_score    DECIMAL(3,2),
    
    -- Examples
    example_video_ids   JSONB,  -- Array of video IDs demonstrating pattern
    
    last_validated      TIMESTAMP,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.3 Failed Approaches

Learned failures to avoid.

```sql
CREATE TABLE failed_approaches (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id          UUID REFERENCES channels(id),
    
    -- Failure Info
    approach_type       VARCHAR(50),
    approach_value      TEXT,
    failure_reason      TEXT,
    
    -- Impact
    failure_count       INTEGER DEFAULT 1,
    avg_negative_impact DECIMAL(10,2),
    
    -- Examples
    example_video_ids   JSONB,
    
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.4 Learning Log

Agent decisions and outcomes.

```sql
CREATE TABLE learning_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Context
    agent_name          VARCHAR(100),
    project_id          UUID,
    stage               VARCHAR(50),
    
    -- Decision
    decision_type       VARCHAR(100),
    decision_data       JSONB,
    reasoning           TEXT,
    
    -- Outcome
    outcome             VARCHAR(50),  -- SUCCESS, FAILURE, PARTIAL
    user_feedback       TEXT,
    feedback_score      INTEGER,  -- 1-5 rating
    
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. System Entities

### 4.1 QC Reviews

Quality control checkpoints.

```sql
CREATE TABLE qc_reviews (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID REFERENCES projects(id),
    stage               VARCHAR(50),
    
    -- Review Result
    status              VARCHAR(50) CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'REVISION_REQUESTED')),
    
    -- Checks Performed
    checks              JSONB,  -- Array of check results
    -- {
    --   "check_name": "brand_compliance",
    --   "passed": true,
    --   "notes": "..."
    -- }
    
    issues_found        JSONB,  -- Array of issues
    reviewer_type       VARCHAR(50),  -- AUTO, MANUAL
    reviewer_id         VARCHAR(100),
    
    notes               TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at         TIMESTAMP
);
```

### 4.2 Agent Executions

Track agent execution history.

```sql
CREATE TABLE agent_executions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Execution Context
    agent_name          VARCHAR(100) NOT NULL,
    project_id          UUID,
    stage               VARCHAR(50),
    
    -- Execution Details
    input_summary       TEXT,
    output_summary      TEXT,
    execution_time_ms   INTEGER,
    tokens_used         INTEGER,
    
    -- Status
    status              VARCHAR(50) CHECK (status IN ('SUCCESS', 'FAILURE', 'TIMEOUT')),
    error_message       TEXT,
    
    -- Artifacts
    output_artifact_id  UUID,  -- Reference to specific output table
    
    started_at          TIMESTAMP,
    completed_at        TIMESTAMP
);
```

### 4.3 API Usage

Track external API usage.

```sql
CREATE TABLE api_usage (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Service
    service_name        VARCHAR(100),  -- openai, elevenlabs, youtube, etc.
    endpoint            VARCHAR(255),
    
    -- Usage
    request_count       INTEGER DEFAULT 1,
    tokens_in           INTEGER,
    tokens_out          INTEGER,
    cost_usd            DECIMAL(10,6),
    
    -- Rate Limiting
    quota_remaining     INTEGER,
    quota_reset_at      TIMESTAMP,
    
    period_start        DATE,
    period_end          DATE,
    
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. Indexes

```sql
-- Performance indexes
CREATE INDEX idx_projects_channel ON projects(channel_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_ideas_project ON ideas(project_id);
CREATE INDEX idx_scripts_project ON scripts(project_id);
CREATE INDEX idx_videos_project ON videos(project_id);
CREATE INDEX idx_content_history_channel ON content_history(channel_id);
CREATE INDEX idx_content_history_published ON content_history(published_at);
CREATE INDEX idx_success_patterns_channel ON success_patterns(channel_id);
CREATE INDEX idx_agent_executions_project ON agent_executions(project_id);
CREATE INDEX idx_qc_reviews_project ON qc_reviews(project_id);

-- Full-text search
CREATE INDEX idx_scripts_fulltext ON scripts USING gin(to_tsvector('english', full_text));
CREATE INDEX idx_research_summary_fulltext ON research_reports USING gin(to_tsvector('english', summary));
```

---

## 6. Entity Relationships Diagram

```
┌─────────────┐       ┌──────────────────┐       ┌─────────────────┐
│   CHANNEL   │───────│ CHANNEL_PROFILE  │───────│CONTENT_CONSTRAINT│
└─────────────┘       └──────────────────┘       └─────────────────┘
       │
       │ 1:N
       ▼
┌─────────────┐       ┌──────────────────┐       ┌─────────────────┐
│   PROJECT   │───────│      IDEAS       │       │  RESEARCH_RPT   │
└─────────────┘       └──────────────────┘       └─────────────────┘
       │
       │ 1:1
       ▼
┌─────────────┐       ┌──────────────────┐       ┌─────────────────┐
│   SCRIPT    │───────│   STORYBOARD     │───────│  SCENE_ASSETS   │
└─────────────┘       └──────────────────┘       └─────────────────┘
       │
       │ 1:1
       ▼
┌─────────────┐       ┌──────────────────┐       ┌─────────────────┐
│    VIDEO    │───────│   SEO_METADATA   │       │   QC_REVIEWS    │
└─────────────┘       └──────────────────┘       └─────────────────┘
       │
       │ 1:1
       ▼
┌─────────────┐
│CONTENT_HIST │
└─────────────┘

┌─────────────┐       ┌──────────────────┐       ┌─────────────────┐
│CHANNEL (FK) │───────│ SUCCESS_PATTERNS │       │FAILED_APPROACHES│
└─────────────┘       └──────────────────┘       └─────────────────┘

┌─────────────┐       ┌──────────────────┐       ┌─────────────────┐
│LEARNING_LOG │       │AGENT_EXECUTIONS  │       │   API_USAGE     │
└─────────────┘       └──────────────────┘       └─────────────────┘
```

---

## 7. Migration Strategy

### Phase 1: Core Tables
- channels
- channel_profiles
- content_constraints
- projects

### Phase 2: Workflow Tables
- ideas
- research_reports
- scripts
- storyboards
- scene_assets

### Phase 3: Output Tables
- videos
- seo_metadata
- qc_reviews

### Phase 4: Memory Tables
- content_history
- success_patterns
- failed_approaches
- learning_log

### Phase 5: System Tables
- agent_executions
- api_usage
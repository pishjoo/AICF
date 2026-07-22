# AICF v2 Product Overview

## Executive Summary

AICF (AI Content Factory) v2 is a Multi-Tenant SaaS platform that automates end-to-end AI-powered content production for digital channels. The system transforms content ideas into published videos through an intelligent 8-stage workflow powered by specialized AI agents.

## Vision

Enable content creators, marketing teams, and media companies to produce high-quality, brand-consistent video content at scale using AI automation while maintaining complete creative control.

## Core Value Proposition

1. **Automated Production Pipeline**: Transform ideas into published content through an 8-stage AI workflow
2. **Brand Consistency**: Channel profiles ensure all content adheres to brand guidelines
3. **Multi-Platform Publishing**: Support for YouTube, Instagram, TikTok, LinkedIn, and more
4. **Tenant Isolation**: Complete data separation for multi-tenant SaaS architecture
5. **Role-Based Access Control**: Granular permissions for team collaboration
6. **Cost Tracking**: Monitor AI token usage and production costs per content piece

## Target Platforms

- YouTube (long-form, shorts)
- Instagram (Reels, Stories, Posts)
- TikTok
- LinkedIn
- Twitter/X
- Facebook

---

## Key Features

### 1. Channel Profile System

Define complete channel identity including:
- Brand guidelines (colors, fonts, logos)
- Target audience demographics
- Content style and tone
- Visual identity rules
- Voice/avatar preferences
- SEO and hashtag strategies

### 2. Content Planning

**Playlists** organize content into thematic collections:
- **Planned Playlists**: Pre-defined content calendars
- **Dynamic Playlists**: AI-curated from RSS feeds, news, trends

**Episodes** represent individual content units moving through production.

### 3. AI Production Workflow

Eight automated stages:

| Stage | Agent | Output |
|-------|-------|--------|
| IDEA | IdeaAgent | Video concept, hook, key points |
| RESEARCH | ResearchAgent | Sources, facts, statistics |
| SCRIPT | ScriptAgent | Full script, scenes, timing |
| STORYBOARD | StoryboardAgent | Visual frames, transitions |
| ASSET_GENERATION | AssetAgent | Images, audio, graphics |
| VIDEO_PRODUCTION | VideoAgent | Final video assembly |
| SEO | SEOAgent | Titles, descriptions, tags |
| PUBLISH | PublishAgent | Platform publishing |

### 4. Agent System

Specialized AI agents for each workflow stage:
- Input/output validation
- Mock implementations for development
- Pluggable AI provider architecture
- Execution tracking and logging

### 5. Multi-Tenant Architecture

- **Organizations**: Top-level tenant entities
- **Teams**: Subdivisions within organizations
- **Users**: Individual accounts with role-based access
- **Complete Data Isolation**: Every query scoped by organization_id

### 6. Security & RBAC

- JWT authentication with refresh tokens
- Role-based permission system
- Custom and built-in roles (Owner, Admin, Manager, Member, Viewer)
- Audit logging for compliance

---

## Content Production Lifecycle

```
Organization
    └── Team (optional)
        └── ChannelProfile
            ├── ContentStrategy
            └── Playlist
                └── Episode
                    ├── ContentJob (workflow + 8 stages)
                    │   └── AgentExecution (per stage)
                    └── Asset (generated media)
                        └── Published Content
```

### Detailed Flow

1. **Organization Setup**
   - Create organization with subscription plan
   - Define teams and invite users
   - Assign roles and permissions

2. **Channel Definition**
   - Create ChannelProfile with brand guidelines
   - Define target audience and content style
   - Set visual identity and voice preferences

3. **Content Planning**
   - Create Playlist (planned or dynamic)
   - Define episode roadmap or auto-generation rules
   - Set production templates

4. **Episode Creation**
   - Create Episode with topic/description
   - Link to playlist and channel profile
   - Status: PLANNED

5. **Workflow Initiation**
   - Start workflow engine
   - Creates ContentJob records (1 workflow + 8 stages)
   - Creates AgentExecution records (one per stage)
   - Status: RESEARCHING

6. **Stage Execution**
   - Each stage executes its agent
   - Agent validates input, processes, validates output
   - ContentJob and AgentExecution updated with results
   - Outputs passed to next stage

7. **Asset Generation**
   - Images, audio, video clips created
   - Stored as Asset records
   - Linked to episode

8. **SEO Optimization**
   - Title, description, tags generated
   - Platform-specific optimization
   - SEO score calculated

9. **Publishing**
   - Content published to target platforms
   - Published URL stored
   - Status: PUBLISHED

---

## Technical Architecture Highlights

### Backend Stack
- **Framework**: FastAPI
- **ORM**: SQLAlchemy v2
- **Database**: PostgreSQL (SQLite for development)
- **Authentication**: JWT with refresh tokens
- **Migration**: Alembic

### Database Models

**Identity & SaaS:**
- Organization, Team, User, Role, Permission, UserRole, TeamMember

**Channel System:**
- ChannelProfile, ContentStrategy

**Content Planning:**
- Playlist, Episode

**Production:**
- ProductionTemplate, ContentJob, Asset, AgentExecution

### Workflow Engine V2

- Replaces deprecated Project/WorkflowStage/ContentProfile system
- Direct Episode → ContentJob → AgentExecution flow
- Supports pause/resume, retry, status tracking

### Agent Registry

- Centralized agent management
- Mock agents for development
- Pluggable AI provider interface

---

## Current Limitations

1. **Mock AI Agents**: All agents return mock outputs; no external AI API integration yet
2. **No Frontend**: API-only implementation; no UI dashboard
3. **Basic Retry Logic**: Simple retry count without exponential backoff
4. **Local Storage**: Assets stored locally; cloud storage (S3/GCS) not implemented
5. **No Queue System**: Synchronous execution; no Celery/RQ for background jobs
6. **Limited Analytics**: No content performance tracking or feedback loop

---

## Future Enhancements

### Phase 5: AI Integration
- Connect agents to OpenAI, Anthropic, local LLMs
- Implement real prompt engineering
- Add streaming responses

### Phase 6: Media Processing
- Integrate image generation (DALL-E, Midjourney, Stable Diffusion)
- Video assembly (FFmpeg, RunwayML)
- Voice synthesis (ElevenLabs, Azure TTS)

### Phase 7: Publishing
- YouTube API integration
- Instagram Graph API
- TikTok API
- Scheduling system

### Phase 8: Analytics & Learning
- Performance tracking (views, engagement, retention)
- Feedback collection system
- Analytics Agent for insights
- Recommendation engine
- User preference learning
- Brand memory system
- Content intelligence scoring

### Phase 9: Scalability
- Redis caching
- Message queue (RabbitMQ/SQS)
- Horizontal scaling
- CDN integration

### Phase 10: Enterprise Features
- White-label options
- Advanced reporting
- API rate limiting
- Custom integrations
- SLA monitoring

---

## Success Metrics

- **Content Velocity**: Episodes produced per week
- **Quality Score**: Human review ratings
- **Engagement Rate**: Views, likes, shares, comments
- **Cost Efficiency**: USD per episode
- **Time Savings**: Hours saved vs manual production
- **Brand Consistency**: Adherence to guidelines score

---

## Document Information

- **Version**: 2.0
- **Last Updated**: 2024
- **Author**: AICF Engineering Team
- **Status**: Active Development

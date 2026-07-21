# AICF v2 Architecture Review

## Executive Summary

This document reviews the current AICF implementation and proposes architectural changes for v2 to support multi-tenant SaaS operations, enhanced content management, and scalable production workflows.

---

## 1. Current State Analysis

### 1.1 Existing Structure

The current codebase (`/workspace/aicf/`) contains:

**Core Components:**
- `core/config.py` - Configuration management with Pydantic settings
- `core/ai_provider.py` - Multi-provider AI abstraction (OpenAI, Anthropic, Ollama)
- `core/workflow.py` - Workflow engine for pipeline orchestration
- `database/connection.py` - SQLAlchemy database setup
- `database/models.py` - Basic models (ContentProfile, Project, WorkflowStage)
- `agents/base.py` - Base agent class with execution framework
- `app/main.py` - FastAPI application entry point
- `app/api/routes.py` - REST API endpoints
- `app/api/schemas.py` - Pydantic request/response schemas
- `app/dashboard/app.py` - Streamlit dashboard

**Documentation:**
- `docs/architecture.md` - Original architecture proposal
- `docs/database-design.md` - Detailed schema design
- `docs/product-spec.md` - Product requirements
- `docs/agent-system.md` - Agent specifications
- `docs/roadmap.md` - Development roadmap

### 1.2 Identified Gaps for v2

| Area | Current State | v2 Requirement |
|------|---------------|----------------|
| **Multi-tenancy** | Single tenant only | Full organization/team/user isolation |
| **Authorization** | None | RBAC with permissions |
| **Channel Profile** | Basic fields | Complete identity system with platform support |
| **Content Planning** | Projects only | Playlists (planned/dynamic) + Episodes |
| **Production** | Simple stages | Templates + Jobs with cost tracking |
| **Assets** | JSON references | Full asset management system |
| **Audit** | None | Complete audit logging |
| **Workflow** | Sequential | Parallel, conditional, human-in-loop |

---

## 2. Target Architecture

### 2.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │
│  │ Streamlit   │  │ REST API    │  │ WebSocket (future)          │ │
│  │ Dashboard   │  │ (FastAPI)   │  │                             │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          APPLICATION LAYER                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │
│  │ Auth        │  │ Tenant      │  │ Permission                  │ │
│  │ Service     │  │ Context     │  │ Checker                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │
│  │ Channel     │  │ Playlist    │  │ Episode                     │ │
│  │ Service     │  │ Service     │  │ Service                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │
│  │ Production  │  │ Asset       │  │ Workflow                    │ │
│  │ Service     │  │ Service     │  │ Orchestrator                │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           DOMAIN LAYER                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Domain Entities                          │   │
│  │  Organization │ Team │ User │ Role │ Permission             │   │
│  │  ChannelProfile │ ContentStrategy │ Playlist │ Episode      │   │
│  │  ProductionTemplate │ ContentJob │ Asset                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Domain Services                          │   │
│  │  Tenant Isolation │ Authorization │ Validation              │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        INFRASTRUCTURE LAYER                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │
│  │ PostgreSQL  │  │ Redis       │  │ Object Storage              │ │
│  │ (Primary)   │  │ (Cache)     │  │ (S3-compatible)             │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │
│  │ AI Providers│  │ Message     │  │ Audit Log                   │ │
│  │ (OpenAI,    │  │ Queue       │  │ Store                       │ │
│  │ Anthropic)  │  │ (Redis)     │  │                             │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Directory Structure (v2)

```
/workspace/
├── agents/                 # Agent implementations
│   ├── base.py            # Base agent class [EXISTS in /aicf]
│   ├── research.py        # Research agent
│   ├── script_writer.py   # Script generation
│   ├── storyboard.py      # Visual planning
│   ├── video.py           # Video production
│   └── __init__.py
│
├── app/                   # Application layer
│   ├── main.py           # FastAPI entry [EXISTS in /aicf]
│   ├── api/
│   │   ├── routes.py     # API endpoints [EXISTS in /aicf]
│   │   ├── schemas.py    # Pydantic models [EXISTS in /aicf]
│   │   ├── deps.py       # Dependencies (auth, db)
│   │   └── v1/           # Versioned API
│   └── dashboard/
│       └── app.py        # Streamlit UI [EXISTS in /aicf]
│
├── core/                  # Core business logic
│   ├── config.py         # Settings [EXISTS in /aicf]
│   ├── ai_provider.py    # AI abstraction [EXISTS in /aicf]
│   ├── workflow.py       # Workflow engine [EXISTS in /aicf]
│   ├── security.py       # Auth & permissions
│   └── events.py         # Domain events
│
├── database/             # Data layer
│   ├── connection.py     # DB setup [EXISTS in /aicf]
│   ├── models.py         # SQLAlchemy models [EXISTS in /aicf]
│   └── repositories/     # Data access layer
│
├── models/               # Pydantic schemas
│   ├── organization.py
│   ├── channel.py
│   ├── episode.py
│   └── __init__.py
│
├── profiles/             # Profile management
│   └── channel_profile.py
│
├── projects/             # Project/Episode management
│   ├── playlist.py
│   └── episode.py
│
├── prompts/              # Prompt templates
│   ├── research/
│   ├── script/
│   └── storyboard/
│
├── services/             # Business services
│   ├── tenant_service.py
│   ├── channel_service.py
│   ├── production_service.py
│   └── asset_service.py
│
├── storage/              # File storage [EXISTS]
│   └── .gitkeep
│
├── tests/                # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── docs/                 # Documentation
    ├── aicf-v2-domain-model.md     [CREATED]
    ├── aicf-v2-architecture-review.md [THIS FILE]
    ├── architecture.md             [EXISTS]
    ├── database-design.md          [EXISTS]
    ├── agent-system.md             [EXISTS]
    ├── product-spec.md             [EXISTS]
    └── roadmap.md                  [EXISTS]
```

---

## 3. Key Architectural Decisions

### 3.1 Multi-Tenancy Strategy

**Decision:** Database-level isolation with shared schema

**Rationale:**
- Cost-effective for SaaS
- Easier maintenance than separate databases
- Row-level security via organization_id on all tables
- Application-enforced isolation through middleware

**Implementation:**
```python
# All queries automatically filtered by organization
def get_db_session(org_id: UUID) -> Session:
    session = SessionLocal()
    # Middleware injects organization filter
    return session
```

### 3.2 Authentication & Authorization

**Decision:** JWT-based auth with RBAC

**Components:**
- OAuth2 with password flow
- JWT tokens with organization context
- Permission checks at API layer
- Role hierarchy: Owner > Admin > Editor > Viewer

**Implementation:**
```python
@router.get("/channels")
def list_channels(
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    # Only returns channels in user's organization
    ...
```

### 3.3 Workflow Engine Evolution

**Current:** Linear stage progression

**v2:** DAG-based workflow with:
- Parallel execution branches
- Conditional transitions
- Human approval gates
- Retry policies per stage
- Event-driven triggers

**Example:**
```python
workflow = Workflow(
    name="video_production",
    stages=[
        Stage("research", parallel=False),
        Stage("script", requires_approval=True),
        Stage("storyboard", parallel=True),
        Stage("asset_generation", parallel=True, retry=3),
        Stage("video_assembly", requires=["storyboard", "assets"]),
        Stage("qc", requires_approval=True),
        Stage("publish", conditional="if_approved"),
    ]
)
```

### 3.4 Asset Management Strategy

**Decision:** Centralized asset service with CDN support

**Features:**
- Upload with checksum verification
- Automatic format conversion
- Thumbnail generation
- CDN URL generation
- Lifecycle policies (archive/delete)

### 3.5 Event-Driven Components

**Decision:** In-process events with Redis pub/sub for scaling

**Key Events:**
- `EpisodeCreated` → Trigger workflow
- `AssetReady` → Notify dependent jobs
- `JobCompleted` → Advance workflow
- `ApprovalRequired` → Send notification

---

## 4. Migration Strategy

### 4.1 Phase 1: Foundation (Weeks 1-2)

1. Create new domain models
2. Implement multi-tenancy infrastructure
3. Add authentication system
4. Set up migration scripts

### 4.2 Phase 2: Core Services (Weeks 3-4)

1. Migrate ContentProfile → ChannelProfile
2. Implement Playlist system
3. Create Episode model
4. Build ProductionTemplate system

### 4.3 Phase 3: Enhanced Workflow (Weeks 5-6)

1. Upgrade workflow engine to DAG
2. Add ContentJob tracking
3. Implement cost tracking
4. Build approval system

### 4.4 Phase 4: Asset Management (Weeks 7-8)

1. Create asset service
2. Implement storage abstraction
3. Add processing pipelines
4. Build CDN integration

---

## 5. Security Considerations

### 5.1 Data Isolation

- Every query includes `organization_id` filter
- Database views for complex queries
- API-level validation of resource ownership
- Audit logs for all data access

### 5.2 API Security

- Rate limiting per organization
- Input validation on all endpoints
- SQL injection prevention (ORM)
- XSS protection in dashboard

### 5.3 Secret Management

- Environment variables for sensitive data
- Encrypted database connections
- API key rotation support
- No secrets in code/repository

---

## 6. Scalability Plan

### 6.1 Horizontal Scaling

- Stateless application servers
- Session data in Redis
- Database connection pooling
- Async task queue (Celery)

### 6.2 Performance Optimization

- Query optimization with indexes
- Caching strategy (Redis)
- CDN for static assets
- Database read replicas

### 6.3 Monitoring

- Health check endpoints
- Metrics collection (Prometheus)
- Distributed tracing (OpenTelemetry)
- Alert rules for critical failures

---

## 7. Technology Stack Updates

| Component | Current | v2 Recommendation |
|-----------|---------|-------------------|
| **Database** | SQLite/PostgreSQL | PostgreSQL 15+ |
| **Cache** | None | Redis 7+ |
| **Queue** | None | Celery + Redis |
| **Auth** | None | FastAPI Users + JWT |
| **Storage** | Local FS | S3-compatible |
| **Monitoring** | Logging only | Prometheus + Grafana |

---

## 8. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Data leakage between tenants | Critical | Low | Rigorous testing, code review |
| Performance degradation | High | Medium | Load testing, caching |
| Migration data loss | Critical | Low | Backups, staged rollout |
| Auth bypass | Critical | Low | Security audit, penetration testing |

---

## 9. Success Criteria

### 9.1 Functional

- [ ] Multi-tenant isolation verified
- [ ] RBAC working for all roles
- [ ] Playlist system supports both types
- [ ] Workflow handles parallel stages
- [ ] Asset management complete

### 9.2 Non-Functional

- [ ] < 100ms API response time (P95)
- [ ] 99.9% uptime target
- [ ] Support 100 concurrent organizations
- [ ] Zero data leakage incidents

---

## 10. Next Steps

1. **Review this document** with stakeholders
2. **Finalize domain model** based on feedback
3. **Create detailed implementation plan**
4. **Set up development environment**
5. **Begin Phase 1 implementation**

---

*Document Version: 2.0*
*Last Updated: 2024*
*Author: AICF Architecture Team*

---

## Database Layer Implementation Status

### Completed ✓

#### SQLAlchemy Models
All 16 core domain entities implemented in `database/models.py`:

**Identity & SaaS (8 entities):**
- Organization - Multi-tenant isolation root
- Team - Organizational subdivisions  
- User - Platform users with org-scoped emails
- Role - Custom roles with JSON permissions
- Permission - Granular resource:action permissions
- UserRole - User-role assignments
- TeamMember - Team membership tracking
- AuditLog - Security and compliance logging

**Channel System (2 entities):**
- ChannelProfile - Complete content identity with all required fields
- ContentStrategy - Long-term planning with KPIs and pillars

**Content Planning (3 entities):**
- Playlist - Support for both PLANNED_PLAYLIST and DYNAMIC_PLAYLIST types
- PlaylistEpisode - Junction table for playlist ordering
- Episode - Full lifecycle from PLANNED to ARCHIVED

**Production (2 entities):**
- ProductionTemplate - Reusable production rules
- ContentJob - AI job tracking with cost, tokens, retries

**Media (1 entity):**
- Asset - Complete media management with versioning

**AI Operations (1 entity):**
- AgentExecution - Full agent tracking with costs, tokens, errors

#### Multi-Tenant Structure
- TenantMixin provides automatic organization_id, created_at, updated_at
- All content entities properly scoped to organizations
- Cascade delete rules configured for data integrity
- Composite unique constraints for org-scoped uniqueness

#### Migration System
- Alembic configured with PostgreSQL support
- Initial migration (001) creates complete schema
- Enum types properly handled for PostgreSQL
- All indexes and foreign keys defined

### Remaining Tasks

#### Authentication (Phase 2)
- JWT/OAuth2 integration
- Password hashing utilities
- Login/logout endpoints
- Session management

#### API Layer (Phase 3)
- REST endpoints for all entities
- Pydantic schemas for validation
- Pagination and filtering
- RBAC middleware

#### Agent Implementation (Phase 4)
- ResearchAgent
- ScriptWriterAgent
- StoryboardAgent
- VideoProductionAgent
- SEOAgent
- QualityControlAgent

---

*Last Updated: 2024*
*Document Version: 2.1*

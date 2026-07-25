# Phase 9 Architecture Analysis

## Executive Summary

This document analyzes the existing AICF v2 architecture to inform the implementation of Phase 9: Personal Control Center MVP.

**Analysis Date:** 2024
**Phase:** 9.0 - Frontend Foundation + AI Provider Management

---

## 1. Current Architecture Overview

### 1.1 Technology Stack

**Backend:**
- FastAPI (Python) - Main API framework
- SQLAlchemy ORM - Database layer
- Alembic - Database migrations
- Streamlit - Existing basic dashboard

**Frontend:**
- Streamlit-based dashboard (`/workspace/app/dashboard/app.py`)
- No React/Next.js frontend currently exists

**Database:**
- SQLite (development) / PostgreSQL (production-ready)
- Multi-tenant architecture with organization_id isolation

### 1.2 Existing Directory Structure

```
/workspace
├── aicf/                    # Alternative AICF version
├── app/                     # Main application
│   ├── api/                 # API routes
│   ├── auth/                # Authentication
│   ├── dashboard/           # Streamlit dashboard
│   ├── agents/              # Agent definitions
│   ├── ai/                  # AI provider implementations
│   ├── rendering/           # Rendering engine
│   └── main.py              # FastAPI entry point
├── core/                    # Core utilities
│   ├── workflow/            # Workflow engine
│   ├── config.py            # Configuration
│   └── ai_provider.py       # Basic AI provider abstraction
├── database/
│   ├── models.py            # SQLAlchemy models (1377 lines)
│   └── connection.py        # DB connection
├── services/                # Business logic services
│   ├── base.py              # BaseService with CRUD
│   ├── publishing/          # Publishing service layer
│   │   ├── __init__.py      # EncryptionService, Credential services
│   │   └── platforms/       # Platform adapters
│   ├── asset_service.py
│   ├── channel_service.py
│   ├── episode_service.py
│   └── workflow_service.py
├── agents/                  # Agent system
├── workflows/               # Workflow definitions
├── alembic/                 # Migration scripts
└── docs/                    # Documentation
```

---

## 2. Database Model Analysis

### 2.1 Key Existing Models

#### Identity & SaaS Models
- `Organization` - Top-level tenant
- `Team` - Subdivision within organization
- `User` - User accounts
- `Role`, `Permission`, `UserRole` - RBAC system
- `AuditLog` - Security logging

#### Channel System
- `ChannelProfile` - YouTube channel configuration
- `ContentStrategy` - Content strategy definition

#### Content Planning
- `Playlist` - Content playlists
- `Episode` - Individual episodes/videos
  - Status: planned, researching, script_ready, producing, review, approved, published, archived

#### Production
- `ProductionTemplate` - Production templates
- `ContentJob` - Job execution tracking
  - Fields: job_type, status, ai_provider, model_name, tokens, cost_usd, input_data, output_data
  - Status: pending, queued, running, completed, failed, cancelled, retrying

#### Media
- `Asset` - Media file management
  - Types: image, video, audio, subtitle, script, thumbnail, document
  - Storage tracking with provider, bucket, path, URL

#### AI Operations
- `AgentExecution` - Agent execution tracking
  - Status: pending, running, success, failed, timeout

#### Publishing (Existing)
- `PublishingCredential` - Encrypted platform credentials
- `PublishingState` - Publishing state machine
- `PlatformWebhook` - Webhook configurations
- `PlatformRateLimit` - Rate limit tracking
- `AnalyticsJob` - Analytics collection jobs

### 2.2 Models Required for Phase 9

**New models needed:**

1. **AIProvider** - External AI service configuration
   - provider_type: text, image, video, voice, research
   - provider_name: deepseek, openai, elevenlabs, runway, etc.
   - encrypted_api_key
   - configuration JSON
   - is_active

2. **AIProfile** - AI provider profile grouping
   - Links multiple AI providers for a workflow
   - text_provider_id, image_provider_id, video_provider_id, voice_provider_id, research_provider_id
   - is_default flag

3. **AIUsageRecord** - Usage tracking
   - organization_id, profile_id, provider_id
   - operation_type, tokens_used, cost, execution_time

---

## 3. Existing Services Analysis

### 3.1 Service Layer Pattern

All services inherit from `BaseService` which provides:
- `get(resource_id, organization_id)` - Get by ID with tenant isolation
- `list(skip, limit, organization_id, filters)` - List with pagination
- `count(organization_id, filters)` - Count records
- `create(data, organization_id)` - Create new resource
- `update(resource_id, data, organization_id)` - Update resource
- `delete(resource_id, organization_id)` - Delete resource

### 3.2 Existing Services

| Service | Purpose |
|---------|---------|
| `OrganizationService` | Organization management |
| `UserService` | User management |
| `ChannelService` | Channel profiles |
| `EpisodeService` | Episode management |
| `PlaylistService` | Playlist management |
| `AssetService` | Asset lifecycle |
| `WorkflowService` | Workflow orchestration |
| `PublishingService` | Platform publishing |

### 3.3 Encryption Service

Located in `services/publishing/__init__.py`:

```python
class EncryptionService:
    """Fernet symmetric encryption for credential storage."""
    
    def encrypt_dict(self, data: Dict) -> str
    def decrypt_dict(self, encrypted_data: str) -> Dict
    def encrypt_string(self, value: str) -> str
    def decrypt_string(self, encrypted_value: str) -> str
```

**This can be reused for AI provider API key encryption.**

---

## 4. AI Provider Abstraction Analysis

### 4.1 Existing AI Provider Implementation

Location: `/workspace/core/ai_provider.py` and `/workspace/app/ai/providers/`

Current structure:
- `core/ai_provider.py` - Basic provider interface
- `app/ai/providers/base.py` - Base provider class
- `app/ai/providers/openai.py` - OpenAI implementation
- `app/ai/providers/anthropic.py` - Anthropic implementation
- `app/ai/providers/ollama.py` - Ollama implementation
- `app/ai/providers/registry.py` - Provider registry

### 4.2 Gap Analysis for Phase 9

The current provider system is code-centric. Phase 9 requires:
1. **Dynamic provider configuration** - Users configure via UI, not code
2. **Provider profiles** - Group multiple providers for different media types
3. **Runtime routing** - Workflows request "generate script" not "use DeepSeek"
4. **Usage tracking** - Track costs per provider/profile

---

## 5. Frontend Analysis

### 5.1 Current State

The existing dashboard (`app/dashboard/app.py`) is a Streamlit application with:
- Dashboard home with basic metrics
- Content Profiles management
- Projects management
- Workflow Status viewer
- Settings page

**Limitations:**
- No AI Provider management
- No AI Profile management
- Basic UI without modern component library
- Not suitable for complex control center operations

### 5.2 Recommended Approach for Phase 9

**Option A: Extend Streamlit** (Recommended for MVP)
- Pros: Already integrated, Python-only, quick development
- Cons: Limited customization, not ideal for complex UIs

**Option B: Build Next.js Frontend**
- Pros: Modern UI, better UX, scalable
- Cons: Requires TypeScript/React setup, more complex deployment

**Decision:** For Phase 9 MVP, extend Streamlit with new pages for:
1. AI Providers management
2. AI Profiles management
3. Enhanced Dashboard
4. Content Studio foundation
5. Workflow Monitor

Future phases can migrate to Next.js if needed.

---

## 6. API Routes Analysis

### 6.1 Current API Structure

Location: `/workspace/app/api/routes.py`

Existing endpoints follow pattern:
- `GET /api/v1/{resource}` - List resources
- `POST /api/v1/{resource}` - Create resource
- `GET /api/v1/{resource}/{id}` - Get resource
- `PUT /api/v1/{resource}/{id}` - Update resource
- `DELETE /api/v1/{resource}/{id}` - Delete resource

### 6.2 New Endpoints Required

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/ai-providers` | GET, POST | List/Create AI providers |
| `/ai-providers/{id}` | GET, PUT, DELETE | Manage single provider |
| `/ai-providers/{id}/test` | POST | Test provider connection |
| `/ai-profiles` | GET, POST | List/Create AI profiles |
| `/ai-profiles/{id}` | GET, PUT, DELETE | Manage single profile |
| `/ai-profiles/{id}/activate` | POST | Activate profile |
| `/ai-usage` | GET | Get usage records |
| `/dashboard/stats` | GET | Dashboard statistics |
| `/content-studio/generate` | POST | Generate content (foundation) |
| `/workflow-monitor` | GET | Monitor workflow states |

---

## 7. Security Considerations

### 7.1 API Key Security Requirements

From Phase 9 specification:
- API keys must never be stored as plain text
- Encrypt credentials before storage
- Decrypt only during execution
- Never expose keys in API responses

### 7.2 Implementation Strategy

Reuse existing `EncryptionService` from publishing module:
1. Move or copy `EncryptionService` to shared location
2. Use Fernet encryption with key from environment variable
3. Store encrypted keys in `encrypted_api_key` field
4. Return masked keys in API responses (e.g., `sk-****1234`)

---

## 8. Multi-Tenant Compatibility

### 8.1 Existing Pattern

All models use `TenantMixin`:
```python
class TenantMixin:
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

### 8.2 Phase 9 Compliance

New models MUST:
- Inherit from `TenantMixin`
- Include `organization_id` field
- Filter queries by organization_id
- Maintain tenant isolation in all services

---

## 9. Integration Points

### 9.1 Workflow Engine Integration

The AI Execution Router must integrate with:
- Existing workflow engine (`core/workflow/engine.py`)
- ContentJob model (for tracking AI usage)
- Agent execution system

### 9.2 Rendering Engine Compatibility

No changes required to rendering engine.
AI Profile selection happens before rendering stage.

### 9.3 Agent Runtime Compatibility

Agents should request AI services through the router, not directly.
Example change:
```python
# Before
result = openai_provider.generate(prompt)

# After
result = ai_router.get_text_provider().generate(prompt)
```

---

## 10. Implementation Plan

### Phase 9.1: Database Layer
1. Add AIProvider, AIProfile, AIUsageRecord models
2. Create Alembic migration
3. Add relationships to existing models

### Phase 9.2: Services Layer
1. Create `AIProviderService`
2. Create `AIProfileService`
3. Create `AIExecutionRouter`
4. Create `AIUsageService`

### Phase 9.3: API Layer
1. Add API routes for providers
2. Add API routes for profiles
3. Add dashboard stats endpoint
4. Add content studio endpoint

### Phase 9.4: Frontend Layer
1. Extend Streamlit dashboard
2. Add AI Providers page
3. Add AI Profiles page
4. Add Content Studio page
5. Add Workflow Monitor page

### Phase 9.5: Testing
1. Unit tests for services
2. Integration tests for API
3. Frontend testing

### Phase 9.6: Documentation
1. Create phase9-control-center.md
2. Update API documentation

---

## 11. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing functionality | High | Comprehensive testing, backward compatibility |
| Security vulnerabilities with API keys | High | Use proven encryption, audit code |
| Performance degradation | Medium | Index new tables, optimize queries |
| Scope creep | Medium | Stick to MVP requirements |

---

## 12. Conclusion

The existing architecture provides a solid foundation for Phase 9:
- Multi-tenant infrastructure is complete
- Encryption service exists for secure credential storage
- Service layer pattern is established
- Streamlit dashboard provides starting point for UI

Key additions for Phase 9:
- AI Provider and Profile models
- Dynamic provider routing
- Enhanced dashboard UI
- Content Studio foundation

The implementation will maintain backward compatibility while adding the personal control center capabilities.

---

## Appendix A: File Inventory

### Files to Create
- `database/models.py` - Add new models (modify existing)
- `alembic/versions/[new_migration].py` - Database migration
- `services/ai_provider_service.py` - Provider management
- `services/ai_profile_service.py` - Profile management
- `services/ai_execution_router.py` - Runtime routing
- `services/ai_usage_service.py` - Usage tracking
- `app/api/routes_ai.py` - AI provider API routes
- `app/dashboard/pages/ai_providers.py` - Providers UI
- `app/dashboard/pages/ai_profiles.py` - Profiles UI
- `app/dashboard/pages/content_studio.py` - Content creation UI
- `docs/phase9-architecture-analysis.md` - This document
- `docs/phase9-control-center.md` - Phase 9 documentation

### Files to Modify
- `database/models.py` - Add new models
- `app/main.py` - Include new routers
- `app/dashboard/app.py` - Extend navigation

---

*End of Architecture Analysis*

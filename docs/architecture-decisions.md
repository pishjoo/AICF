# AICF v2 Architecture Decisions Record (ADR)

**Last Updated:** December 2024  
**Phase:** 4 - Production Infrastructure Foundation

---

## Overview

This document records key architectural decisions made during the development of AICF v2, including the rationale, alternatives considered, and consequences.

---

## Decision Log

### ADR-001: Multi-Tenant Architecture with Organization Isolation

**Date:** Phase 2  
**Status:** Accepted  
**Impact:** High

#### Context

AICF v2 requires support for multiple organizations (tenants) with complete data isolation for SaaS deployment.

#### Decision

Implement tenant isolation using:
- `TenantMixin` with `organization_id` foreign key on all business entities
- Database-level filtering on all queries
- Organization-scoped unique constraints

#### Alternatives Considered

1. **Separate databases per tenant**
   - Pro: Complete isolation
   - Con: Operational complexity, cost
   
2. **Schema-per-tenant**
   - Pro: Logical separation
   - Con: Migration complexity, limited scalability

3. **Row-level security (PostgreSQL)**
   - Pro: Database-enforced isolation
   - Con: Vendor lock-in, complex setup

#### Consequences

- ✅ All models include `organization_id` field
- ✅ Queries must explicitly filter by organization
- ⚠️ Requires developer discipline to prevent data leaks
- ⚠️ No automatic enforcement at ORM level

---

### ADR-002: Job Queue Abstraction Over Direct Redis

**Date:** Phase 4  
**Status:** Accepted  
**Impact:** High

#### Context

Workflow execution requires asynchronous job processing. Need to support development/testing without Redis while preparing for production Redis/Celery deployment.

#### Decision

Create abstract `JobQueue` interface with multiple implementations:
- `InMemoryJobQueue` for development/testing
- `RedisJobQueue` for production
- Future: `CeleryJobQueue` for advanced features

#### Alternatives Considered

1. **Direct Celery from start**
   - Pro: Mature ecosystem
   - Con: Heavy dependency, Redis required for all environments

2. **Redis-only implementation**
   - Pro: Simpler codebase
   - Con: Testing requires Redis, no fallback

3. **RabbitMQ/Kafka directly**
   - Pro: More robust
   - Con: Overkill for initial deployment, operational complexity

#### Consequences

- ✅ Testable without external dependencies
- ✅ Gradual migration path to Celery
- ✅ Environment-specific configuration
- ⚠️ Additional abstraction layer
- ⚠️ Must maintain multiple implementations

---

### ADR-003: Agent Runtime with Standardized Result Schema

**Date:** Phase 4  
**Status:** Accepted  
**Impact:** High

#### Context

AI agents need consistent execution interface across different workflow stages and AI providers.

#### Decision

Implement `AgentRuntime` with:
- Standardized `AgentResult` schema (status, output, metadata, execution_time, token_usage, error)
- Input/output validation hooks
- Timeout enforcement
- Metrics collection

#### Alternatives Considered

1. **Direct agent invocation**
   - Pro: Simpler
   - Con: No standardization, hard to track metrics

2. **Async execution from start**
   - Pro: Better performance
   - Con: Complexity, debugging difficulty

3. **Provider-specific runtimes**
   - Pro: Optimized per provider
   - Con: Code duplication, maintenance burden

#### Consequences

- ✅ Uniform error handling across all agents
- ✅ Easy integration with job system
- ✅ Metrics collection for cost attribution
- ⚠️ Synchronous execution limits throughput
- ⚠️ Unix-only timeout handling (signal.alarm)

---

### ADR-004: Storage Provider Abstraction

**Date:** Phase 4  
**Status:** Accepted  
**Impact:** High

#### Context

Asset storage needs to support multiple backends (local, S3, R2, MinIO) without changing business logic.

#### Decision

Create abstract `StorageProvider` interface with:
- `upload()`, `download()`, `delete()`, `get_url()`, `exists()` methods
- `LocalStorageProvider` fully implemented
- `S3StorageProvider`, `CloudflareR2Provider`, `MinIOProvider` prepared (not implemented)

#### Alternatives Considered

1. **Direct S3/boto3 usage**
   - Pro: Simpler initially
   - Con: Vendor lock-in, can't support local dev

2. **Django Storage API adaptation**
   - Pro: Battle-tested
   - Con: Django dependency, over-engineering

3. **Cloud-native storage services**
   - Pro: Managed service
   - Con: Cost, vendor lock-in

#### Consequences

- ✅ Business logic independent of storage backend
- ✅ Local development without cloud costs
- ✅ Easy provider switching
- ⚠️ Only LocalStorage fully implemented
- ⚠️ Cloud providers require additional work before production

---

### ADR-005: ContentJob + AgentExecution Tracking

**Date:** Phase 3/4  
**Status:** Accepted  
**Impact:** High

#### Context

Need to track workflow execution progress, costs, and results for observability and billing.

#### Decision

Implement dual-tracking model:
- `ContentJob`: Tracks production work units (workflow or stage)
- `AgentExecution`: Tracks individual AI agent invocations
- Hierarchical relationship: Workflow Job → Stage Jobs → Agent Executions

#### Alternatives Considered

1. **Single Job model**
   - Pro: Simpler schema
   - Con: Can't track agent-level details separately

2. **Event sourcing**
   - Pro: Complete audit trail
   - Con: Complexity, query performance

3. **Workflow state machine tables**
   - Pro: Explicit state tracking
   - Con: Rigidity, migration complexity

#### Consequences

- ✅ Granular cost tracking per agent execution
- ✅ Retry tracking at both job and execution levels
- ✅ Clear separation of concerns
- ⚠️ Multiple tables to query for full workflow status
- ⚠️ Column aliases create confusion (`finished_at` vs `completed_at`)

---

### ADR-006: Workflow Engine V2 Orchestration

**Date:** Phase 3  
**Status:** Accepted  
**Impact:** High

#### Context

Content production requires orchestrated workflow through 8 stages with proper sequencing and error handling.

#### Decision

Implement `WorkflowEngineV2` with:
- `start_episode_workflow()`: Initialize workflow
- `execute_stage()`: Run specific stage
- `retry_stage()`: Handle failures
- `pause_workflow()`, `resume_workflow()`: Manual control
- Agent registry integration

#### Alternatives Considered

1. **State machine library (python-statemachine)**
   - Pro: Formal state management
   - Con: Learning curve, rigidity

2. **Workflow engine (Airflow, Prefect)**
   - Pro: Mature orchestration
   - Con: Overkill, operational overhead

3. **Event-driven architecture**
   - Pro: Loose coupling
   - Con: Complexity, eventual consistency

#### Consequences

- ✅ Simple, understandable orchestration
- ✅ Direct database updates for status
- ✅ Easy to add new stages
- ⚠️ Sequential execution only (no parallel stages)
- ⚠️ No explicit state machine enforcement

---

### ADR-007: RBAC with Custom Roles

**Date:** Phase 2  
**Status:** Accepted  
**Impact:** Medium

#### Context

Multi-tenant SaaS requires flexible permission system supporting both built-in and custom roles.

#### Decision

Implement RBAC with:
- Built-in roles: owner, admin, manager, member, viewer
- Custom roles per organization
- Permission slugs: `resource:action` format
- Many-to-many Role-Permission relationship

#### Alternatives Considered

1. **Simple role enum**
   - Pro: Simplicity
   - Con: Inflexible, can't customize

2. **Policy-based (OPA, Cedar)**
   - Pro: Very flexible
   - Con: Complexity, learning curve

3. **ACL per resource**
   - Pro: Fine-grained
   - Con: Performance, management overhead

#### Consequences

- ✅ Flexible permission system
- ✅ Organization-specific customization
- ✅ Support for enterprise requirements
- ⚠️ Permission checks not enforced at ORM level
- ⚠️ Requires middleware implementation

---

### ADR-008: JSON Columns for Flexible Data

**Date:** Phase 3  
**Status:** Accepted  
**Impact:** Medium

#### Context

Workflow stages produce varied output structures; rigid schemas would limit flexibility.

#### Decision

Use JSON columns for:
- `ContentJob.input_data`, `output_data`
- `AgentExecution.input_data`, `output_data`, `extra_data`
- `Episode.research_data`, `storyboard`, `seo_data`
- `Asset.metadata`

#### Alternatives Considered

1. **EAV (Entity-Attribute-Value)**
   - Pro: Structured
   - Con: Query complexity, performance

2. **JSONB with schema validation**
   - Pro: PostgreSQL validation
   - Con: Vendor lock-in

3. **Separate tables per data type**
   - Pro: Type safety
   - Con: Schema proliferation

#### Consequences

- ✅ Flexible data structures
- ✅ Easy to add new fields
- ✅ Good query support in modern ORMs
- ⚠️ No schema validation at database level
- ⚠️ Type safety relies on application logic

---

### ADR-009: Soft Delete Support

**Date:** Phase 2  
**Status:** Partially Implemented  
**Impact:** Low

#### Context

Data recovery and compliance require ability to "delete" records without permanent removal.

#### Decision

Add `deleted_at` timestamp column to soft-delete capable models. Queries should filter out deleted records.

#### Alternatives Considered

1. **Hard delete only**
   - Pro: Simplicity
   - Con: No recovery, compliance issues

2. **Separate archive tables**
   - Pro: Clean active tables
   - Con: Complexity, restore difficulty

3. **Audit log only**
   - Pro: Complete history
   - Con: Can't restore state

#### Consequences

- ✅ Data recovery possible
- ✅ Compliance with data retention policies
- ⚠️ Only `Organization` has `deleted_at` currently
- ⚠️ Queries don't automatically filter deleted records
- ⚠️ Requires manual enforcement

---

### ADR-010: SQLAlchemy ORM Over Raw SQL

**Date:** Phase 1  
**Status:** Accepted  
**Impact:** High

#### Context

Database access layer needs to balance productivity, type safety, and performance.

#### Decision

Use SQLAlchemy ORM for:
- All database models
- Query construction
- Relationship management

Raw SQL only for:
- Complex analytics queries
- Bulk operations
- Migrations

#### Alternatives Considered

1. **Raw SQL / psycopg2**
   - Pro: Full control, performance
   - Con: Verbosity, SQL injection risk

2. **SQLAlchemy Core**
   - Pro: More control than ORM
   - Con: More verbose than ORM

3. **Tortoise ORM / asyncpg**
   - Pro: Async support
   - Con: Smaller community, less mature

#### Consequences

- ✅ Productive development
- ✅ Type hints and IDE support
- ✅ Relationship management
- ⚠️ N+1 query risks
- ⚠️ Learning curve for complex queries
- ⚠️ No native async support

---

## Tradeoffs Summary

| Decision | Benefit | Cost |
|----------|---------|------|
| TenantMixin | Simple isolation | Manual filtering |
| JobQueue abstraction | Testability | Extra layer |
| AgentRuntime | Standardization | Sync execution |
| StorageProvider | Backend flexibility | Incomplete impl |
| ContentJob+AgentExecution | Granular tracking | Multiple tables |
| WorkflowEngineV2 | Simple orchestration | Sequential only |
| RBAC | Flexibility | Enforcement needed |
| JSON columns | Flexibility | No validation |
| Soft delete | Recovery | Manual filtering |
| SQLAlchemy ORM | Productivity | N+1 queries |

---

## Future Decisions Pending

1. **Async Runtime**: Migrate AgentRuntime to async/await
2. **Connection Pooling**: Implement SQLAlchemy pool configuration
3. **Dead Letter Queue**: Design DLQ for poison messages
4. **Delayed Jobs**: Implement scheduled execution
5. **Provider Implementation**: Complete S3/R2/MinIO providers
6. **State Machine**: Add formal workflow state enforcement
7. **Audit Enforcement**: Implement automatic audit logging
8. **Query Validation**: Add soft-delete filtering mixin

---

*This is a living document. Update when making significant architectural decisions.*

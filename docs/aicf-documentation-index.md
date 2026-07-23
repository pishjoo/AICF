# AICF v2 Documentation Index

## Overview

This document provides a comprehensive index of all AICF v2 architecture and design documentation, organized by category with purpose, last update phase, and relationships between documents.

---

## Architecture Documents

### Core Architecture

| Document | Purpose | Last Updated | Related Documents |
|----------|---------|--------------|-------------------|
| `architecture.md` | High-level system architecture overview | Phase 5 | All architecture docs |
| `architecture/system-architecture.md` | Detailed system architecture with component diagrams | Phase 5 | backend-architecture, storage-architecture |
| `architecture/backend-architecture.md` | Backend service architecture | Phase 5 | system-architecture, api-design |
| `architecture/storage-architecture.md` | Storage and media handling architecture | Phase 5 | system-architecture |
| `architecture/security-architecture.md` | Security model and tenant isolation | Phase 7.8 | multi-tenant-design |
| `architecture/multi-tenant-design.md` | Multi-tenancy implementation details | Phase 7.8 | security-architecture |
| `aicf-current-architecture.md` | **Current state architecture** (source of truth) | **Phase 7.99** | All documents |

### Agent Architecture

| Document | Purpose | Last Updated | Related Documents |
|----------|---------|--------------|-------------------|
| `agent-system.md` | Complete agent system documentation | Phase 7.5 | agent-runtime, agent-lifecycle |
| `architecture/agent-system.md` | Agent architecture overview | Phase 7.5 | agent-system |
| `architecture/agent-runtime.md` | Agent runtime execution environment | Phase 7.5 | agent-system, job-processing |
| `ai/agent-lifecycle.md` | Agent lifecycle management | Phase 7.5 | agent-system |
| `ai/agent-contract.md` | Agent interface contracts | Phase 7.5 | agent-runtime |
| `ai/memory-system-design.md` | Memory system for agents | Phase 7.5 | ai-intelligence-foundation |

### Workflow Architecture

| Document | Purpose | Last Updated | Related Documents |
|----------|---------|--------------|-------------------|
| `architecture/workflow-engine.md` | Workflow engine orchestration | Phase 7.5 | job-processing, agent-system |
| `architecture/job-processing.md` | Job processing and queue management | Phase 7.5 | workflow-engine |

---

## Database Documents

| Document | Purpose | Last Updated | Related Documents |
|----------|---------|--------------|-------------------|
| `database-design.md` | Overall database design principles | Phase 5 | database-schema |
| `development/database-schema.md` | Complete database schema reference | Phase 7.99 | All models |
| `development/cost-tracking.md` | Cost tracking system schema and logic | **Phase 7.99** | database-schema |
| `development/asset-lifecycle.md` | Asset lifecycle management | **Phase 7.99** | database-schema, media-quality-system |
| `domain/entity-relationships.md` | Entity relationship diagrams | Phase 5 | database-schema |
| `domain/domain-model.md` | Domain model definitions | Phase 5 | entity-relationships |

---

## AI Intelligence Documents

| Document | Purpose | Last Updated | Related Documents |
|----------|---------|--------------|-------------------|
| `ai-intelligence-foundation.md` | AI intelligence layer foundation | Phase 7.5 | memory-system, agent-system |
| `ai/future-ai-evolution.md` | Future AI evolution roadmap | Phase 7.5 | ai-intelligence-foundation |

---

## Media Pipeline Documents

| Document | Purpose | Last Updated | Related Documents |
|----------|---------|--------------|-------------------|
| `media-quality-system.md` | Media quality evaluation system | Phase 7.5 | approval-workflow, asset-lifecycle |
| `approval-workflow.md` | Human approval workflow | Phase 7.5 | media-quality-system, workflow-engine |
| `media-cost-management.md` | Media production cost management | Phase 7.5 | cost-tracking |
| `development/asset-lifecycle.md` | Asset lifecycle states and transitions | **Phase 7.99** | media-quality-system |
| `development/cost-tracking.md` | Cost tracking implementation | **Phase 7.99** | media-cost-management |

---

## Domain Documents

| Document | Purpose | Last Updated | Related Documents |
|----------|---------|--------------|-------------------|
| `domain/domain-model.md` | Domain model definitions | Phase 5 | entity-relationships |
| `domain/entity-relationships.md` | Entity relationships | Phase 5 | domain-model, database-schema |
| `domain/business-rules.md` | Business rules and constraints | Phase 5 | domain-model |

---

## Product Documents

| Document | Purpose | Last Updated | Related Documents |
|----------|---------|--------------|-------------------|
| `product/product-overview.md` | Product overview and vision | Phase 5 | product-spec |
| `product/product-spec.md` | Product specifications | Phase 5 | product-overview |
| `product/user-personas.md` | User personas and use cases | Phase 5 | product-overview |
| `product/feature-roadmap.md` | Feature roadmap | Phase 7.8 | roadmap |
| `roadmap.md` | Development roadmap | Phase 7.8 | feature-roadmap |

---

## Development Documents

| Document | Purpose | Last Updated | Related Documents |
|----------|---------|--------------|-------------------|
| `development/project-structure.md` | Project folder structure | Phase 5 | development-guide |
| `development/development-guide.md` | Development guidelines | Phase 5 | project-structure |
| `development/api-design.md` | API design patterns | Phase 5 | backend-architecture |
| `development/database-schema.md` | Database schema reference | Phase 7.99 | database-design |
| `development/cost-tracking.md` | Cost tracking system | **Phase 7.99** | database-schema |
| `development/asset-lifecycle.md` | Asset lifecycle system | **Phase 7.99** | database-schema |

---

## Audit & Review Documents

| Document | Purpose | Last Updated | Related Documents |
|----------|---------|--------------|-------------------|
| `aicf-architecture-audit-phase5.md` | Phase 5 architecture audit | Phase 5 | All docs |
| `aicf-phase7.8-architecture-audit.md` | Phase 7.8 full architecture audit | Phase 7.8 | aicf-current-architecture |
| `aicf-v2-architecture-review.md` | V2 architecture review | Phase 5 | aicf-architecture-audit-phase5 |
| `aicf-v2-domain-model.md` | V2 domain model review | Phase 5 | domain-model |
| `phase5.5-architecture-stabilization.md` | Phase 5.5 stabilization report | Phase 5.5 | aicf-phase7.8-architecture-audit |
| `agent-readiness-report.md` | Agent system readiness assessment | Phase 7.5 | agent-system |

---

## Document Status Legend

| Status | Meaning |
|--------|---------|
| 🟢 Current | Updated in Phase 7.99 or later |
| 🟡 Recent | Updated in Phase 7.x |
| 🟠 Stable | Accurate but may need updates |
| 🔴 Outdated | Needs review and update |

---

## Quick Reference by Topic

### Getting Started
1. `architecture.md` - System overview
2. `product/product-overview.md` - What we're building
3. `development/project-structure.md` - Where things are

### Architecture Deep Dive
1. `aicf-current-architecture.md` - Current architecture (START HERE)
2. `architecture/system-architecture.md` - System components
3. `architecture/security-architecture.md` - Security model
4. `development/database-schema.md` - Database design

### Agent System
1. `agent-system.md` - Complete agent documentation
2. `architecture/agent-runtime.md` - Runtime execution
3. `ai/agent-contract.md` - Interface contracts

### Workflow System
1. `architecture/workflow-engine.md` - Workflow orchestration
2. `architecture/job-processing.md` - Job processing

### Media Pipeline
1. `development/asset-lifecycle.md` - Asset states and transitions
2. `media-quality-system.md` - Quality evaluation
3. `approval-workflow.md` - Approval flows
4. `development/cost-tracking.md` - Cost management

### AI Intelligence
1. `ai-intelligence-foundation.md` - AI foundation
2. `ai/memory-system-design.md` - Memory system

---

## Documentation Maintenance

### Update Guidelines

1. **When to Update**: 
   - After each phase completion
   - When architecture changes
   - When new models are added
   - When APIs change

2. **Update Process**:
   - Update relevant section in this index
   - Update "Last Updated" field
   - Add related document references
   - Update `aicf-current-architecture.md` if structural changes

3. **Review Schedule**:
   - Full review: Every phase
   - Quick review: Monthly
   - Critical docs: Before each release

---

## Document Information

- **Version**: 1.0
- **Created**: Phase 7.99
- **Last Updated**: Phase 7.99
- **Author**: AICF Engineering Team
- **Status**: Active
- **Owner**: Architecture Team

---

## Related Documents

- `aicf-current-architecture.md` - Current architecture reference
- `aicf-phase7.8-architecture-audit.md` - Latest architecture audit
- `roadmap.md` - Development roadmap

# AICF v2 Project Structure

## Directory Layout

```
/workspace
├── alembic/                    # Database migrations
│   ├── versions/              # Migration scripts
│   │   └── f76fc6eccc76_initial_complete_schema.py
│   ├── env.py                 # Alembic environment config
│   └── script.py.mako         # Migration template
│
├── agents/                     # AI Agent system
│   ├── __init__.py
│   ├── base.py                # BaseAgent abstract class
│   ├── provider.py            # AI provider abstraction
│   └── registry.py            # AgentRegistry implementation
│
├── app/                        # FastAPI application
│   ├── __init__.py
│   ├── main.py                # Application entry point
│   ├── api/                   # API routes (planned)
│   ├── auth/                  # Authentication module
│   │   ├── jwt.py             # JWT token handling
│   │   ├── password.py        # Password hashing
│   │   ├── routes.py          # Auth endpoints
│   │   ├── dependencies.py    # Auth dependencies
│   │   └── schemas.py         # Auth Pydantic models
│   └── middleware/            # Custom middleware
│       └── tenant_isolation.py
│
├── core/                       # Core modules
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── logging_config.py      # Logging setup
│   └── workflow/              # Workflow engine V2
│       ├── __init__.py
│       ├── engine.py          # WorkflowEngineV2
│       ├── stages.py          # WorkflowStageType enum
│       └── exceptions.py      # Workflow exceptions
│
├── database/                   # Database layer
│   ├── __init__.py
│   ├── connection.py          # DB connection factory
│   └── models.py              # SQLAlchemy models (983 lines)
│
├── docs/                       # Documentation
│   ├── product/               # Product documentation
│   ├── architecture/          # Architecture docs
│   ├── domain/                # Domain model docs
│   ├── ai/                    # AI system docs
│   └── development/           # Developer guides
│
├── services/                   # Business logic layer
│   ├── __init__.py
│   ├── workflow_service.py    # Workflow orchestration
│   └── ...                    # Other services (planned)
│
├── storage/                    # Storage abstraction (planned)
│
├── tests/                      # Test suites
│   ├── __init__.py
│   ├── integration/           # Integration tests
│   │   ├── test_auth.py
│   │   └── test_workflow_engine.py
│   └── unit/                  # Unit tests (planned)
│
├── requirements.txt            # Python dependencies
└── README.md                   # Project overview
```

## Module Responsibilities

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `alembic/` | Database migrations | Migration scripts |
| `agents/` | AI agent system | base.py, registry.py |
| `app/` | FastAPI application | main.py, auth/ |
| `core/` | Core business logic | workflow/engine.py |
| `database/` | Data access layer | models.py, connection.py |
| `services/` | Service layer | workflow_service.py |
| `tests/` | Test coverage | Integration tests |

## File Size Reference

| File | Lines | Purpose |
|------|-------|---------|
| database/models.py | 983 | All SQLAlchemy models |
| core/workflow/engine.py | 610 | Workflow engine V2 |
| agents/registry.py | 400+ | Agent registration |
| alembic migration | ~500 | Initial schema |

## Import Paths

```python
# Database models
from database.models import Organization, User, Episode, ContentJob

# Workflow engine
from core.workflow.engine import WorkflowEngineV2
from core.workflow.stages import WorkflowStageType
from core.workflow.exceptions import WorkflowError

# Agents
from agents.base import BaseAgent, AgentContext, AgentResult
from agents.registry import AgentRegistry

# Services
from services.workflow_service import WorkflowService

# Auth
from app.auth.jwt import create_access_token, verify_token
from app.auth.dependencies import get_current_user
```

## Document Information

- **Version**: 2.0
- **Last Updated**: 2024
- **Author**: AICF Engineering Team
- **Status**: Active Development

# AICF v2 Development Guide

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL (or SQLite for development)
- pip or poetry

### Installation

```bash
# Clone repository
cd /workspace

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="sqlite:///./aicf_dev.db"
export SECRET_KEY="your-secret-key-here"
export JWT_ALGORITHM="HS256"
export ACCESS_TOKEN_EXPIRE_MINUTES=15

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Running Tests

```bash
# Run all tests
pytest

# Run integration tests only
pytest tests/integration/

# Run with coverage
pytest --cov=. --cov-report=html
```

---

## Database Operations

### Create Migration

```bash
alembic revision --autogenerate -m "Add new column to episodes"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migration

```bash
alembic downgrade -1
```

---

## Code Style

### Formatting

```bash
# Format code
black .

# Sort imports
isort .

# Type checking
mypy .
```

### Linting

```bash
flake8 .
pylint database/ core/ agents/ services/
```

---

## Common Tasks

### Add New Agent

1. Create agent class in `agents/`:
```python
class MyNewAgent(BaseAgent):
    name = "my_new_agent"
    stage_type = "custom_stage"
    
    def execute(self, context):
        # Implementation
        pass
```

2. Register in `agents/registry.py`:
```python
registry.register("custom_stage", MyNewAgent())
```

### Add New Workflow Stage

1. Add to `WorkflowStageType` enum in `core/workflow/stages.py`
2. Add to `STAGE_ORDER` list in `WorkflowEngineV2`
3. Create corresponding agent
4. Update business rules if needed

### Create Service

```python
# services/my_service.py
class MyService:
    def __init__(self, db: Session, organization_id: int):
        self.db = db
        self.organization_id = organization_id
    
    def do_something(self, param: str) -> Dict:
        # Business logic here
        pass
```

---

## Debugging

### Enable Debug Logging

```python
# In core/logging_config.py
logging.basicConfig(level=logging.DEBUG)
```

### SQL Query Logging

```python
# Enable SQLAlchemy echo
engine = create_engine(DATABASE_URL, echo=True)
```

### Interactive Debugging

```python
import pdb; pdb.set_trace()
```

---

## API Testing

### Using curl

```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Get channels (with token)
curl http://localhost:8000/channels \
  -H "Authorization: Bearer <access_token>"
```

### Using Swagger UI

Visit `http://localhost:8000/docs` for interactive API documentation.

---

## Document Information

- **Version**: 2.0
- **Last Updated**: 2024
- **Author**: AICF Engineering Team
- **Status**: Active Development

# Contributing to AICF v2

Thank you for your interest in contributing to AICF v2! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Welcome newcomers and help them learn

## How to Contribute

### Reporting Bugs

1. Check existing issues first
2. Use the bug report template
3. Include:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (Python version, OS, etc.)

### Suggesting Features

1. Check existing feature requests
2. Use the feature request template
3. Explain the use case and benefits

### Pull Requests

1. **Fork** the repository
2. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-123
   ```

3. **Make changes** following our coding standards
4. **Write tests** for new functionality
5. **Run tests**:
   ```bash
   pytest tests/
   ```

6. **Commit** with clear messages:
   ```bash
   git commit -m "feat: add user invitation endpoint"
   git commit -m "fix: resolve tenant isolation bug in playlist service"
   ```

7. **Push** and create a Pull Request

## Coding Standards

### Python Style

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use docstrings for public APIs

### Example

```python
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.connection import get_db
from app.schemas.user import UserCreate, UserResponse


router = APIRouter()


@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    """
    Create a new user in the organization.
    
    Args:
        user: User creation data
        db: Database session
        
    Returns:
        Created user object
        
    Raises:
        HTTPException: If email already exists
    """
    # Implementation here
    pass
```

### Testing Requirements

- Unit tests for all services
- Integration tests for API endpoints
- Minimum 80% code coverage
- Test both success and failure cases

## Development Setup

1. **Clone and setup**:
   ```bash
   git clone https://github.com/your-org/aicf-v2.git
   cd aicf-v2
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

4. **Start server**:
   ```bash
   uvicorn app.main:app --reload
   ```

## Architecture Overview

### Layers

- **API Layer** (`app/api/`): FastAPI routers and endpoints
- **Service Layer** (`services/`): Business logic
- **Database Layer** (`database/`): SQLAlchemy models and connections
- **Core** (`core/`): Configuration and utilities

### Key Concepts

- **Multi-tenancy**: All content scoped to organizations
- **RBAC**: Role-based access control with granular permissions
- **Tenant Isolation**: Middleware ensures cross-org access prevention

## Release Process

1. Version bump in `core/config.py`
2. Update CHANGELOG.md
3. Create release tag
4. Publish to PyPI (future)

## Questions?

Open an issue for any questions or concerns.

---

Thank you for contributing to AICF v2! 🚀

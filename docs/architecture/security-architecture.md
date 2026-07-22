# AICF v2 Security Architecture

## Overview

This document details the security architecture of AICF v2, covering authentication, authorization, tenant isolation, and data protection.

---

## Authentication System

### JWT-Based Authentication

**Token Types:**
1. **Access Token**: Short-lived (15 minutes), used for API requests
2. **Refresh Token**: Long-lived (7 days), used to obtain new access tokens

### Token Structure

```python
# Access Token Claims
{
    "sub": "user_123",
    "email": "user@example.com",
    "organization_id": 1,
    "roles": ["member"],
    "permissions": ["channel:read", "episode:create"],
    "exp": 1704067200,
    "iat": 1704066300,
    "type": "access"
}

# Refresh Token Claims
{
    "sub": "user_123",
    "type": "refresh",
    "exp": 1704671100,
    "iat": 1704066300
}
```

### Token Generation

```python
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

### Password Hashing

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

---

## RBAC (Role-Based Access Control)

### Role Hierarchy

```
Owner
  └── Admin
      └── Manager
          └── Member
              └── Viewer
```

### Built-in Roles

| Role | Description |
|------|-------------|
| owner | Full organization control |
| admin | Manage users, channels, content |
| manager | Manage content, view analytics |
| member | Create and edit content |
| viewer | Read-only access |

### Permission Model

```python
PERMISSIONS = {
    "organization": ["create", "read", "update", "delete"],
    "team": ["create", "read", "update", "delete"],
    "channel": ["create", "read", "update", "delete", "publish"],
    "playlist": ["create", "read", "update", "delete"],
    "episode": ["create", "read", "update", "delete", "publish"],
    "workflow": ["create", "read", "update", "retry"],
    "user": ["create", "read", "update", "delete"]
}

ROLE_PERMISSIONS = {
    "owner": "*",  # All permissions
    "admin": [
        "organization:read", "organization:update",
        "team:*", "channel:*", "playlist:*", "episode:*",
        "workflow:*", "user:*"
    ],
    "manager": [
        "channel:*", "playlist:*", "episode:*", "workflow:*"
    ],
    "member": [
        "channel:read", "playlist:create", "playlist:read",
        "episode:create", "episode:read", "episode:update",
        "workflow:create", "workflow:read"
    ],
    "viewer": [
        "channel:read", "playlist:read", "episode:read",
        "workflow:read"
    ]
}
```

### Permission Check Implementation

```python
def has_permission(user: User, permission: str) -> bool:
    user_roles = db.query(UserRole).filter(
        UserRole.user_id == user.id
    ).all()
    
    for user_role in user_roles:
        role_permissions = ROLE_PERMISSIONS.get(user_role.role.name, [])
        
        # Check for wildcard
        if "*" in role_permissions:
            return True
        
        # Check specific permission
        resource, action = permission.split(":")
        for rp in role_permissions:
            rp_resource, rp_action = rp.split(":")
            if rp_resource == resource and (rp_action == "*" or rp_action == action):
                return True
    
    return False

# Decorator usage
@app.delete("/channels/{channel_id}")
@require_permission("channel:delete")
async def delete_channel(channel_id: int, current_user: User):
    ...
```

---

## Tenant Isolation

### Database-Level Isolation

Every query includes organization_id filter:

```python
class TenantMixin(Base):
    __abstract__ = True
    
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    
    @classmethod
    def scoped_query(cls, db: Session, organization_id: int):
        return db.query(cls).filter(cls.organization_id == organization_id)

# Usage in services
class ChannelService:
    def get_channels(self, organization_id: int) -> List[ChannelProfile]:
        return ChannelProfile.scoped_query(self.db, organization_id).all()
```

### Middleware Enforcement

```python
class TenantIsolationMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        request = Request(scope)
        
        # Extract user from JWT
        token = request.headers.get("Authorization").replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        organization_id = payload.get("organization_id")
        
        # Attach to request state
        request.state.organization_id = organization_id
        request.state.user_id = payload.get("sub")
        
        # Continue processing
        await self.app(scope, receive, send)
```

### Query Scoping Examples

```python
# Episode queries always scoped
episodes = db.query(Episode).filter(
    Episode.organization_id == current_user.organization_id,
    Episode.id == episode_id
).first()

# Workflow queries scoped
jobs = db.query(ContentJob).filter(
    ContentJob.organization_id == org_id,
    ContentJob.episode_id == episode_id
).all()

# Agent executions scoped
executions = db.query(AgentExecution).filter(
    AgentExecution.organization_id == org_id
).order_by(AgentExecution.created_at).all()
```

---

## Data Protection

### Encryption at Rest

```python
# Sensitive fields encrypted before storage
from cryptography.fernet import Fernet

cipher = Fernet(ENCRYPTION_KEY)

def encrypt_field(value: str) -> str:
    return cipher.encrypt(value.encode()).decode()

def decrypt_field(encrypted: str) -> str:
    return cipher.decrypt(encrypted.encode()).decode()

# Usage in model
class Organization(Base):
    api_key_encrypted = Column(String(255))
    
    @property
    def api_key(self):
        return decrypt_field(self.api_key_encrypted)
    
    @api_key.setter
    def api_key(self, value):
        self.api_key_encrypted = encrypt_field(value)
```

### Secure Token Storage

```python
# Refresh tokens stored as hashes
import hashlib

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

# Store hash, not raw token
refresh_token_record = RefreshToken(
    user_id=user.id,
    token_hash=hash_token(refresh_token),
    expires_at=expiry
)
db.add(refresh_token_record)
```

---

## API Security

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: OAuth2PasswordRequestForm):
    ...

@app.post("/episodes")
@limiter.limit("100/hour")
async def create_episode(request: Request, episode: EpisodeCreate):
    ...
```

### Input Validation

```python
from pydantic import BaseModel, validator, Field

class EpisodeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    playlist_id: int = Field(..., gt=0)
    
    @validator('title')
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError("Title cannot be empty")
        if '<' in v or '>' in v:
            raise ValueError("Invalid characters in title")
        return v.strip()
```

### SQL Injection Prevention

All queries use SQLAlchemy ORM with parameterized queries:

```python
# SAFE - Uses parameterized query
user = db.query(User).filter(
    User.email == email,
    User.organization_id == org_id
).first()

# UNSAFE - Never do this
user = db.execute(f"SELECT * FROM users WHERE email = '{email}'").first()
```

---

## Audit Logging

### Log Structure

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=True)
    action = Column(String(50), nullable=False)  # CREATE, READ, UPDATE, DELETE
    resource_type = Column(String(50), nullable=False)  # episode, channel, etc.
    resource_id = Column(Integer, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    timestamp = Column(DateTime, server_default=func.now())
    details = Column(JSON, default=dict)
```

### Audit Events

| Event | Resource | Trigger |
|-------|----------|---------|
| USER_LOGIN | User | Successful login |
| CHANNEL_CREATED | ChannelProfile | New channel |
| EPISODE_PUBLISHED | Episode | Publish action |
| WORKFLOW_STARTED | ContentJob | Workflow initiation |
| PERMISSION_CHANGED | UserRole | Role assignment |

---

## Security Headers

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

---

## Document Information

- **Version**: 2.0
- **Last Updated**: 2024
- **Author**: AICF Engineering Team
- **Status**: Active Development

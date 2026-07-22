# AICF v2 Technical Debt Register

**Last Updated:** December 2024  
**Phase:** 4 - Production Infrastructure Foundation

---

## Overview

This document tracks technical debt accumulated during AICF v2 development. Each item includes impact, effort to fix, and priority.

### Summary

| Priority | Count | Estimated Effort |
|----------|-------|-----------------|
| Critical | 3 | 6-8 days |
| High | 3 | 5-7 days |
| Medium | 3 | 5-7 days |
| Low | 2 | 1-2 days |
| **Total** | **11** | **17-24 days** |

---

## Critical Technical Debt (Must Fix Before Production)

### TD-001: Incomplete Storage Providers

**Category:** Architecture  
**Introduced:** Phase 4  
**Effort:** 6-9 days  
**Risk:** High

#### Description

Only `LocalStorageProvider` is fully implemented. The following providers raise `NotImplementedError`:
- `S3StorageProvider`
- `CloudflareR2Provider`
- `MinIOProvider`

#### Impact

- ❌ Cannot deploy to production cloud environments
- ❌ No object storage for scalable deployments
- ❌ Forces use of local filesystem in production

#### Code Locations

```
app/storage/providers.py:
  - S3StorageProvider (lines 334-377)
  - CloudflareR2Provider (lines 379-422)
  - MinIOProvider (lines 424-468)
```

#### Fix Required

Implement all abstract methods for each provider:
- `upload()`
- `download()`
- `delete()`
- `get_url()` (with signed URL support)
- `exists()`

#### Dependencies

- boto3 library for S3/R2
- minio library for MinIO (or boto3 with endpoint override)

#### Recommendation

**Priority:** Critical  
**Timeline:** Week 1 of Phase 5

---

### TD-002: Unix-Only Timeout Handling

**Category:** Portability  
**Introduced:** Phase 4  
**Effort:** 1 day  
**Risk:** Medium

#### Description

`AgentRuntime.execute()` uses `signal.alarm()` for timeout enforcement, which only works on Unix systems. Windows falls back to no timeout.

#### Impact

- ⚠️ Development on Windows has no timeout protection
- ⚠️ Runaway agent executions possible on Windows
- ⚠️ Inconsistent behavior across platforms

#### Code Location

```python
# app/agents/runtime/__init__.py:296-313
try:
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Agent execution exceeded {timeout}s timeout")
    
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(int(timeout))
    
    try:
        result = agent.execute(agent_context)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        
except (ImportError, AttributeError):
    # Windows or signal not available, execute without timeout
    result = agent.execute(agent_context)
```

#### Fix Required

Implement cross-platform timeout using threading:

```python
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

def execute_with_timeout(func, args, timeout):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            raise TimeoutError(f"Execution exceeded {timeout}s timeout")
```

#### Recommendation

**Priority:** Critical  
**Timeline:** Week 1 of Phase 5

---

### TD-003: No Dead Letter Queue

**Category:** Reliability  
**Introduced:** Phase 4  
**Effort:** 2-3 days  
**Risk:** High

#### Description

Jobs that fail after max retries are lost. There's no mechanism to capture, analyze, or reprocess poison messages.

#### Impact

- ❌ Operations cannot analyze failure patterns
- ❌ Customer data may be lost on permanent failures
- ❌ No way to manually reprocess failed jobs
- ❌ Debugging production issues difficult

#### Current Behavior

```python
# app/jobs/worker.py:87-91
if message.retry_count >= message.max_retries:
    self.logger.warning(
        f"Job {message.job_id} exceeded max retries ({message.max_retries})"
    )
    return False  # Job is simply dropped
```

#### Fix Required

1. Create `DeadLetterQueue` class
2. Move failed messages to DLQ instead of dropping
3. Add DLQ inspection API
4. Implement manual reprocessing capability
5. Set up alerting for DLQ growth

#### Recommendation

**Priority:** Critical  
**Timeline:** Week 2 of Phase 5

---

## High Priority Technical Debt

### TD-004: No Database Connection Pooling

**Category:** Performance  
**Introduced:** Phase 4  
**Effort:** 1-2 days  
**Risk:** High

#### Description

Database sessions are created per task without connection pooling. This can lead to connection exhaustion under load.

#### Impact

- ⚠️ Connection exhaustion under moderate load
- ⚠️ Slow database connection times
- ⚠️ Potential application crashes

#### Code Locations

```python
# app/jobs/tasks.py:52
db = db_session_factory()  # New session every task

# core/workflow/engine.py:104
def __init__(self, db: Session):  # Session passed in
    self.db = db
```

#### Fix Required

Configure SQLAlchemy connection pooling:

```python
# database/connection.py
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

#### Recommendation

**Priority:** High  
**Timeline:** Week 1 of Phase 5

---

### TD-005: Blocking Retry Implementation

**Category:** Performance  
**Introduced:** Phase 4  
**Effort:** 2-3 days  
**Risk:** Medium

#### Description

Retry logic uses `time.sleep()` which blocks the worker thread. No support for delayed execution.

#### Impact

- ⚠️ Worker inefficiency during retry delays
- ⚠️ No scheduled job support
- ⚠️ Cannot implement exponential backoff properly

#### Code Location

```python
# app/jobs/worker.py:94-104
delay = min(2 ** message.retry_count, 60)  # Max 60 seconds
self.logger.info(
    f"Retrying job {message.job_id} in {delay}s (attempt {message.retry_count + 1}/{message.max_retries})"
)

# Re-enqueue with incremented retry count
message.mark_retrying()
time.sleep(delay)  # Simple blocking delay; use delayed queue in production
self.queue.enqueue(message)
```

#### Fix Required

1. Implement delayed queue with Redis sorted sets
2. Use score as execution timestamp
3. Worker polls for due jobs only
4. Remove `time.sleep()` blocking

#### Recommendation

**Priority:** High  
**Timeline:** Week 2 of Phase 5

---

### TD-006: Soft Delete Not Enforced

**Category:** Data Integrity  
**Introduced:** Phase 2  
**Effort:** 1 day  
**Risk:** Medium

#### Description

`deleted_at` column exists on `Organization` but queries don't automatically filter soft-deleted records.

#### Impact

- ⚠️ Deleted organizations may appear in queries
- ⚠️ Data leakage risk
- ⚠️ Compliance issues

#### Code Location

```python
# database/models.py:153
class Organization(Base):
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
```

#### Fix Required

1. Create `SoftDeleteMixin` with query helper
2. Apply mixin to all soft-delete capable models
3. Update all queries to filter `deleted_at IS NULL`
4. Or use SQLAlchemy event listeners for automatic filtering

#### Recommendation

**Priority:** High  
**Timeline:** Week 2 of Phase 5

---

## Medium Priority Technical Debt

### TD-007: Column Aliases Confusion

**Category:** Maintainability  
**Introduced:** Phase 4  
**Effort:** 0.5 days  
**Risk:** Low

#### Description

Multiple aliases for same concept create developer confusion:
- `finished_at` vs `completed_at`
- `execution_time` vs `duration_seconds`
- `token_usage` vs `total_tokens`

#### Impact

- ⚠️ Developer confusion
- ⚠️ Potential bugs from using wrong column
- ⚠️ Inconsistent API responses

#### Code Locations

```python
# database/models.py: AgentExecution
finished_at = Column(DateTime(timezone=True), nullable=True)  # Alias for completed_at
completed_at = Column(DateTime(timezone=True), nullable=True)

execution_time = Column(Float, nullable=True)  # Alias for duration_seconds
duration_seconds = Column(Float, nullable=True)

token_usage = Column(BigInteger, default=0)  # Alias for total_tokens
total_tokens = Column(BigInteger, default=0)
```

#### Fix Required

Option 1: Document canonical names and deprecate aliases  
Option 2: Use SQLAlchemy hybrid properties for true aliases  
Option 3: Remove duplicates entirely

#### Recommendation

**Priority:** Medium  
**Timeline:** Week 1 of Phase 5 (documentation only)

---

### TD-008: No JSON Schema Validation

**Category:** Data Integrity  
**Introduced:** Phase 3  
**Effort:** 2-3 days  
**Risk:** Medium

#### Description

JSON columns (`input_data`, `output_data`, `metadata`, etc.) have no schema validation at database or application level.

#### Impact

- ⚠️ Data integrity risks
- ⚠️ Hard to catch schema changes
- ⚠️ Debugging difficult with inconsistent structures

#### Affected Columns

```python
# ContentJob
input_data = Column(JSON, nullable=True)
output_data = Column(JSON, nullable=True)
extra_data = Column(JSON, default=dict)

# AgentExecution
input_data = Column(JSON, nullable=True)
output_data = Column(JSON, nullable=True)
extra_data = Column(JSON, default=dict)

# Episode
research_data = Column(JSON, default=dict)
storyboard = Column(JSON, default=list)
seo_data = Column(JSON, default=dict)
```

#### Fix Required

1. Define JSON schemas for critical data structures
2. Add validation layer before database writes
3. Use Pydantic models for serialization/deserialization
4. Consider PostgreSQL JSONB with check constraints

#### Recommendation

**Priority:** Medium  
**Timeline:** Week 3 of Phase 5

---

### TD-009: No Health Check Endpoints

**Category:** Operations  
**Introduced:** Phase 4  
**Effort:** 1 day  
**Risk:** Medium

#### Description

No health check endpoints for monitoring worker and service status.

#### Impact

- ⚠️ Cannot monitor service health
- ⚠️ Load balancers cannot route traffic properly
- ⚠️ Kubernetes readiness/liveness probes impossible

#### Fix Required

Implement health check endpoints:

```python
# GET /health
# GET /health/ready
# GET /health/live
```

#### Recommendation

**Priority:** Medium  
**Timeline:** Week 1 of Phase 5

---

## Low Priority Technical Debt

### TD-010: No Centralized Logging Configuration

**Category:** Maintainability  
**Introduced:** Phase 1  
**Effort:** 0.5 days  
**Risk:** Low

#### Description

No centralized logging configuration leads to inconsistent log formats across modules.

#### Impact

- ⚠️ Inconsistent log parsing
- ⚠️ Hard to aggregate logs
- ⚠️ Debugging more difficult

#### Fix Required

Create centralized logging configuration:

```python
# config/logging.py
LOGGING_CONFIG = {
    'version': 1,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'level': 'INFO'
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO'
    }
}
```

#### Recommendation

**Priority:** Low  
**Timeline:** Week 1 of Phase 5

---

### TD-011: Missing Unit Tests

**Category:** Testing  
**Introduced:** Phase 4  
**Effort:** Ongoing  
**Risk:** Medium

#### Description

Integration tests exist but unit test coverage is sparse. Key components lack isolated testing.

#### Impact

- ⚠️ Regression risk during refactoring
- ⚠️ Harder to validate individual components
- ⚠️ Slower CI/CD feedback loop

#### Missing Test Coverage

| Component | Current Tests | Needed |
|-----------|--------------|--------|
| `RedisJobQueue` | None | Integration + mock tests |
| `WorkflowEngineV2` | None | Unit tests for each method |
| `AgentRuntime` validation | None | Input/output validation tests |
| Storage failover | None | Redis fallback tests |
| Retry logic | Partial | Exponential backoff tests |

#### Recommendation

**Priority:** Medium  
**Timeline:** Ongoing throughout Phase 5

---

## Technical Debt Metrics

### Debt Distribution by Category

| Category | Count | Total Effort |
|----------|-------|--------------|
| Architecture | 1 | 6-9 days |
| Performance | 2 | 3-5 days |
| Reliability | 1 | 2-3 days |
| Data Integrity | 2 | 2.5-3.5 days |
| Operations | 1 | 1 day |
| Portability | 1 | 1 day |
| Maintainability | 2 | 1-1.5 days |
| Testing | 1 | Ongoing |

### Interest Accumulation

Technical debt "interest" is paid through:
- Extra debugging time
- Workarounds in new code
- Increased cognitive load
- Production incidents

**Estimated Weekly Interest:** 4-8 hours of engineering time

**Projected Monthly Cost:** 16-32 hours if left unpaid

---

## Debt Repayment Plan

### Phase 5 Sprint 1 (Week 1-2)
- [ ] TD-001: Complete storage providers
- [ ] TD-002: Cross-platform timeout
- [ ] TD-004: Connection pooling
- [ ] TD-009: Health checks
- [ ] TD-010: Logging configuration

### Phase 5 Sprint 2 (Week 3-4)
- [ ] TD-003: Dead letter queue
- [ ] TD-005: Non-blocking retries
- [ ] TD-006: Soft delete enforcement
- [ ] TD-007: Column alias documentation

### Phase 5 Sprint 3 (Week 5-6)
- [ ] TD-008: JSON schema validation
- [ ] TD-011: Unit test coverage (ongoing)

---

## Prevention Strategies

To prevent future technical debt accumulation:

1. **Code Review Checklist**
   - [ ] Error handling complete
   - [ ] Tests written
   - [ ] Documentation updated
   - [ ] No TODOs in production code

2. **Definition of Done**
   - Feature complete
   - Tests passing
   - Documentation updated
   - No known critical bugs
   - Security review (if applicable)

3. **Regular Debt Audits**
   - Quarterly technical debt review
   - Track new debt introduced
   - Allocate 20% sprint capacity to debt repayment

---

*This is a living document. Update when new debt is identified or existing debt is repaid.*

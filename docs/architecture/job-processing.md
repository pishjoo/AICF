# Job Processing Architecture

## Overview

AICF v2 implements an asynchronous job processing architecture to handle long-running workflow executions without blocking API requests. This document describes the current implementation and future scaling approach.

## Current Implementation

### Architecture Components

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  API Layer  │────▶│  Job Queue   │────▶│   Worker    │
│             │     │  (Redis/In-Mem)│     │  Process    │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                    │
                           ▼                    ▼
                    ┌──────────────┐     ┌─────────────┐
                    │ Status Store │     │  Database   │
                    │  (Redis Hash)│     │  (Updates)  │
                    └──────────────┘     └─────────────┘
```

### Module Structure

```
app/jobs/
├── __init__.py      # Module exports
├── queue.py         # JobQueue abstraction, RedisJobQueue, InMemoryJobQueue
├── worker.py        # JobWorker for consuming jobs
└── tasks.py         # Task definitions (WorkflowTask, StageExecutionTask)
```

### Key Classes

#### JobMessage

Represents a unit of work in the queue:

```python
{
    "job_id": "uuid",
    "task_type": "workflow.create",
    "payload": {...},
    "priority": 0,
    "max_retries": 3,
    "retry_count": 0,
    "status": "pending|queued|running|completed|failed|retrying"
}
```

#### JobQueue (Abstract)

Interface for queue implementations:

- `enqueue(message)` - Add job to queue
- `dequeue(timeout)` - Get next job (blocking)
- `peek()` - View next job without removing
- `get_status(job_id)` - Get job status
- `update_status(job_id, status)` - Update status
- `get_queue_size()` - Queue depth
- `clear()` - Clear all jobs

#### Implementations

1. **InMemoryJobQueue**: Development/testing use
   - Thread-safe list-based queue
   - Priority ordering
   - No persistence

2. **RedisJobQueue**: Production use
   - Redis sorted sets for priority queue
   - Redis hashes for status tracking
   - Automatic fallback to in-memory if Redis unavailable
   - Prepared for Celery integration

#### JobWorker

Consumes and processes jobs:

```python
worker = JobWorker(queue=redis_queue)
worker.register_task(TaskDefinition(
    name="workflow.create",
    handler=WorkflowTask.create_workflow_task(db_factory),
    max_retries=3,
    timeout=300.0
))
worker.run()
```

### Task Types

#### WorkflowTask

- `create_workflow_task`: Create and start workflow for episode
- `execute_stage_task`: Execute specific workflow stage
- `retry_stage_task`: Retry failed stage

### ContentJob Status Flow

```
PENDING → QUEUED → RUNNING → COMPLETED
                      ↓
                   FAILED → RETRYING → RUNNING
                      ↓
                 CANCELLED
```

## Design Decisions

### 1. Abstraction Over Direct Redis

**Decision**: Use abstract `JobQueue` interface with multiple implementations.

**Rationale**:
- Enables testing without Redis dependency
- Allows gradual migration to Celery
- Supports different environments (dev, staging, prod)

### 2. Priority Queue Support

**Decision**: Use Redis sorted sets with negative scores for priority.

**Rationale**:
- Higher priority jobs processed first
- Simple O(log N) operations
- Native Redis support

### 3. Status Separation

**Decision**: Store status separately from job data.

**Rationale**:
- Fast status lookups without deserializing full job
- Enables efficient monitoring dashboards
- Reduces memory usage for common queries

### 4. Retry with Exponential Backoff (Prepared)

**Decision**: Include retry count and max_retries in message structure.

**Rationale**:
- Handles transient failures gracefully
- Prevents infinite retry loops
- Backoff strategy ready for implementation

## Future Scaling Approach

### Phase 1: Current (In-Memory / Basic Redis)

- Single worker process
- Simple retry logic
- No delayed execution

### Phase 2: Enhanced Redis + Multiple Workers

```
┌─────────────┐
│   Redis     │
│   Cluster   │
└──────┬──────┘
       │
   ┌───┴───┐
   ▼       ▼
┌─────┐ ┌─────┐
│ W1  │ │ W2  │ ...
└─────┘ └─────┘
```

- Multiple worker processes
- Redis Sentinel/Cluster for HA
- Graceful shutdown handling

### Phase 3: Celery Integration

```python
# celery_app.py
from celery import Celery

celery = Celery(
    'aicf',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

@celery.task(bind=True, max_retries=3)
def execute_workflow_stage(self, episode_id, stage_type):
    # Task implementation
    pass
```

**Benefits**:
- Mature ecosystem
- Built-in retry with backoff
- Flower monitoring
- Task routing
- Rate limiting

### Phase 4: Distributed Queue (RabbitMQ/Kafka)

For high-scale deployments:

- **RabbitMQ**: Reliable delivery, complex routing
- **Kafka**: High throughput, event sourcing

### Phase 5: Serverless Execution

- AWS Lambda with SQS
- Google Cloud Functions with Pub/Sub
- Azure Functions with Service Bus

## Monitoring & Observability

### Metrics to Track

1. **Queue Health**
   - Queue depth
   - Average wait time
   - Oldest job age

2. **Worker Performance**
   - Jobs processed per minute
   - Success/failure rate
   - Average execution time

3. **Retry Analysis**
   - Retry rate by task type
   - Max retry exhaustion count
   - Common failure patterns

### Logging Strategy

```python
logger.info(f"Enqueued job {job_id} ({task_type})")
logger.debug(f"Dequeued job {job_id}")
logger.error(f"Job {job_id} failed: {error}")
```

## Error Handling

### Failure Scenarios

1. **Transient Errors** (network, timeout)
   - Automatic retry with backoff
   
2. **Permanent Errors** (validation, not found)
   - Fail immediately, no retry
   
3. **Worker Crash**
   - Job re-queued (visibility timeout)
   
4. **Poison Messages**
   - Move to dead letter queue after max retries

### Dead Letter Queue (Future)

```python
class DeadLetterQueue:
    def add(self, message: JobMessage, reason: str):
        # Store for analysis
        # Alert operations team
        pass
```

## Usage Example

```python
from app.jobs import RedisJobQueue, JobWorker, WorkflowTask
from sqlalchemy.orm import sessionmaker

# Setup
queue = RedisJobQueue(redis_url="redis://localhost:6379/0")
db_factory = sessionmaker(bind=engine)

# Create worker
worker = JobWorker(queue=queue)

# Register tasks
worker.register_task(TaskDefinition(
    name="workflow.create",
    handler=WorkflowTask.create_workflow_task(db_factory),
    max_retries=3
))

worker.register_task(TaskDefinition(
    name="stage.execute",
    handler=WorkflowTask.execute_stage_task(db_factory),
    max_retries=2
))

# Start processing
worker.run()
```

## Migration Path from Synchronous

Current synchronous workflow execution:

```python
# Before (blocking)
result = engine.execute_stage(episode, stage_type)
return result
```

After async migration:

```python
# After (non-blocking)
job_id = queue.enqueue(JobMessage(
    task_type="stage.execute",
    payload={"episode_id": episode.id, "stage_type": stage_type.value}
))
return {"job_id": job_id, "status": "queued"}
```

Client polls for completion or uses webhooks.

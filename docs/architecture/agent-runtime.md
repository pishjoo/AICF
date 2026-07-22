# Agent Runtime Architecture

## Overview

The Agent Runtime is the execution environment for AI agents in AICF v2. It provides standardized interfaces for loading, validating, executing, and tracking agent executions across all workflow stages.

## Current Implementation

### Module Structure

```
app/agents/runtime/
└── __init__.py      # AgentRuntime, AgentResult, RuntimeContext, ExecutionMetrics
```

### Core Components

#### AgentResult Schema

Standardized result format for all agent executions:

```python
{
    "status": "success|failed|timeout",
    "output": {...},           # Agent-specific output data
    "metadata": {...},         # Additional context
    "execution_time": 0.0,     # Seconds
    "token_usage": 0,          # LLM tokens consumed
    "error": null              # Error message if failed
}
```

#### RuntimeContext

Execution context passed to agents:

```python
@dataclass
class RuntimeContext:
    episode: Episode                    # Episode being processed
    channel_profile: ChannelProfile     # Brand guidelines
    organization_id: int                # Tenant isolation
    previous_outputs: Dict[str, Any]    # Results from prior stages
    settings: Dict[str, Any]            # Configuration options
    content_job_id: Optional[int]       # Job reference
    agent_execution_id: Optional[int]   # Execution record ID
```

#### ExecutionMetrics

Tracking metrics for observability:

```python
@dataclass
class ExecutionMetrics:
    start_time: datetime
    end_time: datetime
    execution_time_seconds: float
    tokens_used: int
    cost_usd: float
    memory_usage_mb: float
    success: bool
    error_message: Optional[str]
```

#### AgentRuntime Class

Main runtime orchestrator:

```python
class AgentRuntime:
    def __init__(self, db_session, agent_registry=None, default_timeout=300.0):
        pass
    
    def load_agent(self, agent_name: str) -> BaseAgent:
        """Load agent from registry."""
        pass
    
    def validate_input(self, agent: BaseAgent, context: RuntimeContext) -> bool:
        """Validate input before execution."""
        pass
    
    def execute(self, agent_name: str, context: RuntimeContext, timeout: float = None) -> AgentResult:
        """Execute agent with full runtime support."""
        pass
    
    def execute_and_store(self, agent_name: str, context: RuntimeContext, 
                         agent_execution_id: int, timeout: float = None) -> AgentResult:
        """Execute agent and persist results to database."""
        pass
```

### Execution Flow

```
┌─────────────────┐
│  Load Agent     │
│  from Registry  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Validate Input  │
│ (validate_input)│
└────────┬────────┘
         │ Valid?
    ┌────┴────┐
    │ Yes     │ No
    ▼         ▼
┌───────┐  ┌──────────┐
│Execute│  │ Fail Fast│
│Agent  │  │ Return   │
└───┬───┘  └──────────┘
    │
    ▼
┌─────────────────┐
│ Validate Output │
│ (validate_output)│
└────────┬────────┘
         │ Valid?
    ┌────┴────┐
    │ Yes     │ No
    ▼         ▼
┌──────────┐  ┌──────────┐
│Measure   │  │ Mark     │
│Metrics   │  │ Failed   │
└────┬─────┘  └──────────┘
     │
     ▼
┌─────────────────┐
│ Store Result    │
│ (DB + Metrics)  │
└─────────────────┘
```

## Design Decisions

### 1. Standardized Result Schema

**Decision**: All agents return `AgentResult` with consistent fields.

**Rationale**:
- Uniform error handling
- Simplified monitoring
- Easy integration with job system
- Clear contract for API responses

### 2. Input/Output Validation

**Decision**: Separate validation methods on agents.

**Rationale**:
- Fail fast on invalid inputs
- Ensure output quality
- Catch agent bugs early
- Type safety without strict typing

### 3. Timeout Support

**Decision**: Configurable timeout per execution with signal-based enforcement.

**Rationale**:
- Prevent runaway executions
- Resource protection
- Predictable SLAs
- Graceful degradation

### 4. Metrics Collection

**Decision**: Track execution time, tokens, and costs at runtime.

**Rationale**:
- Cost attribution per episode
- Performance optimization
- Billing accuracy
- Usage analytics

### 5. Database Integration

**Decision**: `execute_and_store()` method for atomic updates.

**Rationale**:
- Single responsibility
- Transactional consistency
- Audit trail
- Real-time status updates

## Agent Lifecycle

### States

```
PENDING → VALIDATING → RUNNING → VALIDATING_OUTPUT → COMPLETED
                                      ↓
                                   FAILED
                                      ↓
                                   TIMEOUT
```

### State Transitions

| From | To | Trigger |
|------|-----|---------|
| PENDING | VALIDATING | Runtime starts execution |
| VALIDATING | RUNNING | Input validation passed |
| VALIDATING | FAILED | Input validation failed |
| RUNNING | VALIDATING_OUTPUT | Agent execution completed |
| RUNNING | FAILED | Exception during execution |
| RUNNING | TIMEOUT | Timeout exceeded |
| VALIDATING_OUTPUT | COMPLETED | Output validation passed |
| VALIDATING_OUTPUT | FAILED | Output validation failed |

## Error Handling

### Exception Types

1. **ValidationError**: Input/output validation failure
2. **TimeoutError**: Execution exceeded timeout
3. **AgentNotFoundError**: Agent not in registry
4. **ExecutionContextError**: Missing context data

### Error Response Format

```python
{
    "status": "failed",
    "output": {},
    "metadata": {},
    "execution_time": 0.5,
    "token_usage": 0,
    "error": "Input validation failed: missing required field 'topic'"
}
```

### Retry Integration

Runtime integrates with job retry system:

```python
if result.status == "failed":
    if retry_count < max_retries:
        # Re-enqueue job
        queue.enqueue(retry_message)
    else:
        # Mark as permanently failed
        update_db_status(FAILED)
```

## Database Schema Updates

### AgentExecution Additions

```sql
ALTER TABLE agent_executions ADD COLUMN finished_at TIMESTAMP;
ALTER TABLE agent_executions ADD COLUMN execution_time FLOAT;
ALTER TABLE agent_executions ADD COLUMN token_usage BIGINT DEFAULT 0;
ALTER TABLE agent_executions ADD COLUMN cost_usd FLOAT DEFAULT 0.0;
```

### Asset Additions

```sql
ALTER TABLE assets ADD COLUMN storage_key VARCHAR(255);
ALTER TABLE assets ADD COLUMN metadata JSON DEFAULT '{}';
CREATE INDEX idx_asset_storage_key ON assets(storage_key);
```

## Future Scaling Approach

### Phase 1: Current (Single Runtime)

- Synchronous execution
- Local state tracking
- Basic metrics

### Phase 2: Distributed Runtime

```
┌─────────────────┐
│  Agent Runtime  │
│  Service        │
└────────┬────────┘
         │
   ┌─────┴─────┐
   ▼           ▼
┌─────┐     ┌─────┐
│Redis│     │ DB  │
│Cache│     │Store│
└─────┘     └─────┘
```

- Stateless runtime instances
- Centralized state store
- Horizontal scaling

### Phase 3: Specialized Runtimes

Different runtimes for different agent types:

- **LLM Runtime**: Optimized for large language models
- **Vision Runtime**: GPU-accelerated image processing
- **Audio Runtime**: Speech synthesis/recognition
- **Video Runtime**: Video encoding/composition

### Phase 4: Edge Execution

- Run lightweight agents on edge devices
- Reduce latency for real-time operations
- Offline capability

## Monitoring & Observability

### Key Metrics

1. **Performance**
   - Average execution time per agent type
   - P95/P99 latency
   - Timeout rate

2. **Reliability**
   - Success/failure rate
   - Retry rate
   - Validation failure rate

3. **Cost**
   - Token usage per episode
   - Cost per agent execution
   - Monthly burn rate

### Logging Strategy

```python
# Execution start
logger.info(f"Executing agent {agent_name} for episode {episode_id}")

# Validation
logger.debug(f"Input validation {'passed' if valid else 'failed'}")

# Completion
logger.info(f"Agent {agent_name} completed in {execution_time:.2f}s, tokens={tokens}")

# Errors
logger.error(f"Agent {agent_name} failed: {error_message}", exc_info=True)
```

### Tracing

Future distributed tracing integration:

```python
from opentelemetry import trace

tracer = trace.get_tracer("agent_runtime")

with tracer.start_as_current_span("agent.execute") as span:
    span.set_attribute("agent.name", agent_name)
    span.set_attribute("episode.id", episode_id)
    result = execute(...)
```

## Usage Example

```python
from app.agents.runtime import AgentRuntime, RuntimeContext, AgentResult
from sqlalchemy.orm import Session

# Initialize runtime
runtime = AgentRuntime(db_session=db, default_timeout=300.0)

# Build context
context = RuntimeContext(
    episode=episode,
    channel_profile=channel_profile,
    organization_id=org_id,
    previous_outputs={"idea": {...}},
    settings={"custom_instructions": "Make it engaging"},
    agent_execution_id=execution_record.id
)

# Execute with storage
result = runtime.execute_and_store(
    agent_name="script_agent",
    context=context,
    agent_execution_id=execution_record.id,
    timeout=120.0
)

# Check result
if result.status == "success":
    print(f"Script generated: {result.output['script']}")
    print(f"Tokens used: {result.token_usage}")
    print(f"Execution time: {result.execution_time:.2f}s")
else:
    print(f"Execution failed: {result.error}")
```

## Integration Points

### With Workflow Engine

```python
# In WorkflowEngineV2.execute_stage()
runtime = AgentRuntime(self.db)
context = RuntimeContext(...)
result = runtime.execute_and_store(
    agent_name=agent.name,
    context=context,
    agent_execution_id=agent_execution.id
)

# Update records based on result
if result.status == "success":
    stage_job.status = ContentJobStatus.COMPLETED
    agent_execution.status = AgentExecutionStatus.SUCCESS
```

### With Job System

```python
# In tasks.py
def handler(payload):
    runtime = AgentRuntime(db)
    context = RuntimeContext(...)
    result = runtime.execute(agent_name, context)
    
    if result.status == "success":
        return TaskResult.success(result.to_dict())
    else:
        return TaskResult.failure(result.error)
```

### With Storage Provider

```python
# When agent generates assets
storage_result = storage_provider.upload(
    file=generated_file,
    key=f"org_{org_id}/episode_{ep_id}/asset.mp4",
    metadata=result.metadata
)

# Update asset record
asset.storage_key = storage_result.storage_key
asset.storage_url = storage_result.storage_url
asset.metadata = storage_result.metadata.to_dict()
```

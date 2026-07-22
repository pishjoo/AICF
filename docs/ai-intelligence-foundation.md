# AICF v2 - AI Intelligence Foundation (Phase 5A)

## Overview

This document describes the AI Intelligence Foundation implemented in Phase 5A of AICF v2. This foundation provides the infrastructure that future AI agents will use for content generation, without implementing the actual content generation agents themselves.

## 1. AI Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Future AI Agents Layer                       │
│    (Content Generator, Script Writer, Thumbnail Creator, etc.)   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AI Intelligence Foundation                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Context    │  │    Memory    │  │    Prompts   │          │
│  │    System    │  │   Foundation │  │  Management  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Provider Abstraction Layer                      │  │
│  │  ┌─────────┐ ┌───────────┐ ┌─────────┐ ┌─────────────┐  │  │
│  │  │ OpenAI  │ │ Anthropic │ │ Ollama  │ │ Future...   │  │  │
│  │  └─────────┘ └───────────┘ └─────────┘ └─────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Database / Vector Store                        │
└─────────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Provider Agnosticism**: Agents never directly depend on specific AI providers
2. **Tenant Isolation**: All data is scoped to organizations
3. **Standardized Contracts**: Request/Response schemas are consistent across providers
4. **Extensibility**: New providers can be added without modifying agent code

---

## 2. Provider Design

### Base Interface (`app/ai/providers/base.py`)

All AI providers implement the `BaseProvider` abstract class:

```python
class BaseProvider(ABC):
    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse: ...
    
    @abstractmethod
    def stream(self, request: AIRequest) -> Generator[str, None, None]: ...
    
    @abstractmethod
    async def generate_async(self, request: AIRequest) -> AIResponse: ...
    
    @abstractmethod
    async def stream_async(self, request: AIRequest) -> AsyncGenerator[str, None]: ...
    
    @abstractmethod
    def validate_connection(self) -> bool: ...
    
    @abstractmethod
    def get_model_info(self, model_id: str) -> ModelInfo: ...
    
    @abstractmethod
    def list_available_models(self) -> list: ...
```

### Standardized Schemas

**AIRequest:**
- `organization_id`: Tenant identifier
- `agent_type`: Type of agent making request
- `prompt`: Main instruction
- `context`: AIContext dictionary
- `memory`: Historical data
- `parameters`: Model-specific settings

**AIResponse:**
- `content`: Generated output
- `provider`: Provider name
- `model`: Model identifier
- `tokens`: Usage statistics
- `cost`: USD cost
- `execution_time`: Seconds
- `metadata`: Additional data

### Implemented Providers

| Provider | File | Models Supported |
|----------|------|------------------|
| OpenAI | `openai.py` | GPT-4, GPT-4-turbo, GPT-4o, GPT-3.5-turbo |
| Anthropic | `anthropic.py` | Claude 3 Opus/Sonnet/Haiku |
| Ollama | `ollama.py` | Local models (Llama3, Mistral, etc.) |

### Provider Registry

The `ProviderRegistry` enables dynamic provider selection:

```python
from app.ai.providers import ProviderRegistry

# Get configured provider instance
provider = ProviderRegistry.get_provider("openai", api_key="sk-...")

# List available providers
providers = ProviderRegistry.list_providers()  # ['openai', 'anthropic', 'ollama']
```

---

## 3. Context System

### AIContext Object (`app/ai/context/context.py`)

The `AIContext` aggregates all contextual information needed for AI operations:

```python
@dataclass
class AIContext:
    organization: OrganizationInfo
    channel: Optional[ChannelInfo]
    audience: AudienceInfo
    brand_rules: BrandRules
    content_references: List[ContentReference]
    constraints: Constraints
    custom_data: Dict[str, Any]
```

### Components

| Component | Purpose |
|-----------|---------|
| `OrganizationInfo` | Tenant identification and settings |
| `ChannelInfo` | Platform-specific channel details |
| `AudienceInfo` | Demographics, interests, preferences |
| `BrandRules` | Voice, prohibited words, compliance |
| `ContentReference` | Links to previous content |
| `Constraints` | Length, format, language limits |

### Context Builder Pattern

```python
from app.ai.context import ContextBuilder, OrganizationInfo

context = (ContextBuilder()
    .with_organization(OrganizationInfo(id=1, name="Acme", slug="acme"))
    .with_channel(ChannelInfo(id=1, name="YouTube", platform="youtube"))
    .with_brand_rules(BrandRules(brand_voice="Professional"))
    .add_content_reference(ContentReference(id=100, type="episode", title="Previous"))
    .build())

# Generate system prompt from context
system_prompt = context.get_system_prompt()
```

---

## 4. Memory Design

### Memory Models (`app/memory/models.py`)

Five memory types provide historical context for AI agents:

| Model | Scope | Purpose |
|-------|-------|---------|
| `OrganizationMemory` | Org-wide | Campaigns, preferences, strategies |
| `ChannelMemory` | Per channel | Performance history, engagement patterns |
| `AudienceMemory` | Per segment | Demographics, behavior, sentiment |
| `ContentMemory` | Per content | Generation params, performance metrics |
| `AgentMemory` | Per agent | Execution outcomes, optimizations |

### Service Layer (`app/memory/service.py`)

Each memory type has a dedicated service with CRUD operations:

```python
from app.memory import create_memory_service

# Create organization memory service
org_service = create_memory_service(db, organization_id=1, service_type="organization")

# Store preference
org_service.store_preference("default_tone", "professional")

# Create channel memory service
channel_service = create_memory_service(db, organization_id=1, service_type="channel", channel_id=5)

# Store learning
channel_service.store_learning("best_posting_time", {"hour": 9, "engagement": 0.15})
```

### Tenant Isolation

All memory services enforce organization-level isolation:

```python
def _ensure_tenant_isolation(self, query):
    return query.filter(self.model.organization_id == self.organization_id)
```

### Vector Database Migration Path

Current implementation uses PostgreSQL JSON columns. Migration to vector database:

1. Keep relational models for metadata
2. Add vector embeddings column
3. Implement hybrid search (keyword + semantic)
4. Use pgvector or external vector store (Pinecone, Weaviate)

---

## 5. Prompt Management

### PromptTemplate Model (`app/prompts/models.py`)

```python
class PromptTemplate(Base):
    name: str              # Human-readable name
    slug: str              # URL-friendly identifier
    agent_type: str        # Associated agent
    version: str           # Semantic versioning
    is_active: bool        # Current active version
    system_prompt: str     # Main prompt text
    user_prompt_template: str  # Optional user template
    variables: List[str]   # Substitutable variables
    default_values: Dict   # Variable defaults
```

### Versioning Strategy

- Each agent type can have multiple template versions
- Only one version is active at a time
- Updates can optionally bump version numbers
- Full history tracked in `PromptVersionHistory`

### PromptService Operations

```python
from app.prompts import PromptService

service = PromptService(db, organization_id=1)

# Create template
template = service.create_template(
    name="Script Writer",
    slug="script-writer-v1",
    agent_type="script_writer",
    system_prompt="You are a script writer for {{channel}}...",
    variables=["channel", "topic"],
    default_values={"channel": "YouTube"}
)

# Get active template
active = service.get_active_template("script_writer")

# Render with variables
rendered = active.render(topic="AI Safety", channel="Tech Channel")

# Update with version bump
service.update_template(template.id, system_prompt="New prompt...", bump_version=True)
```

### Organization Scoping

Templates can be:
- **Global** (`organization_id=None`): Available to all organizations
- **Org-specific**: Only available within that organization

Org-specific templates take precedence over global templates.

---

## 6. Future Agent Architecture

When implementing content generation agents in future phases, they will:

1. **Receive standardized input** via `AIRequest`
2. **Build context** using `AIContext` and `ContextBuilder`
3. **Retrieve relevant memory** via Memory Services
4. **Load prompt template** from PromptService
5. **Select provider** via ProviderRegistry
6. **Execute generation** with proper error handling
7. **Store results** in ContentMemory for future learning

### Example Agent Skeleton (Future)

```python
class ContentGenerationAgent:
    def __init__(self, db: Session, organization_id: int):
        self.db = db
        self.org_id = organization_id
        self.prompt_service = PromptService(db, organization_id)
        self.memory_service = create_memory_service(db, organization_id, "content")
    
    def generate(self, episode_id: int) -> str:
        # 1. Build context
        context = self._build_context(episode_id)
        
        # 2. Load prompt template
        template = self.prompt_service.get_active_template("content_generator")
        
        # 3. Get provider
        provider = ProviderRegistry.get_provider("openai")
        
        # 4. Create request
        request = AIRequest(
            organization_id=self.org_id,
            agent_type="content_generator",
            prompt=template.render(**context_vars),
            context=context.to_dict(),
            memory=self._get_relevant_memory()
        )
        
        # 5. Execute
        response = provider.generate(request)
        
        # 6. Store memory
        self.memory_service.store_performance(...)
        
        return response.content
```

---

## 7. Migration Path to RAG/Vector Database

### Current State (Phase 5A)

- Memory stored in PostgreSQL with JSON columns
- Basic keyword search via `ilike` queries
- No semantic understanding

### Phase 5B+ Roadmap

1. **Add Embedding Generation**
   - Generate embeddings for memory values
   - Store in new `embedding` column (pgvector) or external store

2. **Hybrid Search Implementation**
   ```python
   def semantic_search(self, query: str, k: int = 5):
       query_embedding = self.embedder.encode(query)
       results = self.db.query(Memory).order_by(
           Memory.embedding.cosine_distance(query_embedding)
       ).limit(k).all()
       return results
   ```

3. **Chunking Strategy**
   - Break large memories into searchable chunks
   - Maintain parent-child relationships

4. **Retrieval-Augmented Generation**
   - Retrieve relevant memories before generation
   - Inject into AI context automatically

### Recommended Vector Stores

| Option | Pros | Cons |
|--------|------|------|
| **pgvector** | Same DB, ACID transactions | Limited scale |
| **Pinecone** | Managed, high performance | Additional cost |
| **Weaviate** | Open source, hybrid search | Self-hosted complexity |
| **Chroma** | Simple, Python-native | Limited production use |

---

## Files Created

### Provider Layer
```
app/ai/providers/
├── __init__.py
├── base.py          # Abstract interface, AIRequest, AIResponse
├── openai.py        # OpenAI implementation
├── anthropic.py     # Anthropic implementation
├── ollama.py        # Ollama/local implementation
└── registry.py      # Provider registry
```

### Context System
```
app/ai/context/
├── __init__.py
└── context.py       # AIContext, builders, data classes
```

### Memory Foundation
```
app/memory/
├── __init__.py
├── models.py        # 5 memory models
└── service.py       # CRUD services with tenant isolation
```

### Prompt Management
```
app/prompts/
├── __init__.py
└── models.py        # PromptTemplate, PromptService
```

### Tests
```
tests/unit/ai/
├── test_providers.py   # Provider abstraction tests
├── test_context.py     # Context system tests
├── test_memory.py      # Memory isolation tests
└── test_prompts.py     # Prompt versioning tests
```

---

## Database Changes Required

Run migrations to add these tables:

1. **organization_memory** - Org-level historical data
2. **channel_memory** - Channel-specific learnings
3. **audience_memory** - Audience insights
4. **content_memory** - Content generation history
5. **agent_memory** - Agent execution learnings
6. **prompt_templates** - Prompt template storage
7. **prompt_version_history** - Template change audit

---

## Limitations

1. **No Vector Search**: Current memory search is keyword-based only
2. **No Caching**: Provider responses not cached (add Redis layer later)
3. **No Rate Limiting**: Rate limits handled per-provider, not globally
4. **No Streaming Persistence**: Streaming responses not persisted incrementally
5. **Mock Tests**: Tests use mocks; integration tests need real API keys

---

## Next Recommended Phase: Phase 5B

**Title**: AI Agent Implementation Foundation

**Goals**:
1. Implement base agent class with provider integration
2. Create first content generation agent (pilot)
3. Add RAG/vector search capability
4. Implement response caching layer
5. Add comprehensive logging/observability

**Deliverables**:
- `app/agents/base.py` - Base agent class
- `app/agents/content_generator.py` - First generation agent
- Vector database integration
- Redis caching layer
- Agent execution monitoring dashboard

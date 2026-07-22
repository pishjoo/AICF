# AICF v2 Memory System Design

## Overview

This document describes the memory system architecture for storing and retrieving brand, user, and content intelligence data.

---

## Memory Types

### 1. Brand Memory

**Purpose**: Store channel-specific brand guidelines and preferences.

**Storage**: Vector database (planned: Pinecone, Weaviate)

**Schema:**
```python
class BrandMemory:
    channel_id: int
    embedding: List[float]  # 1536 dimensions
    content_type: str       # "guideline", "style", "preference"
    text: str               # Original text
    metadata: Dict          # Additional context
    created_at: datetime
    updated_at: datetime
```

**Usage:**
- Retrieve brand guidelines during content generation
- Ensure visual consistency
- Maintain tone of voice

### 2. User Preference Memory

**Purpose**: Learn from user feedback and behavior.

**Storage**: Relational + Vector hybrid

**Schema:**
```python
class UserPreference:
    user_id: int
    preference_type: str    # "style", "topic", "format"
    preference_data: JSON
    confidence_score: float
    source: str             # "explicit", "implicit"
    last_updated: datetime
```

### 3. Content Intelligence Memory

**Purpose**: Store performance data and insights.

**Storage**: Analytics database (TimescaleDB planned)

**Schema:**
```python
class ContentPerformance:
    episode_id: int
    platform: str
    views: int
    engagement_rate: float
    retention_rate: float
    published_at: datetime
    metrics_snapshot: JSON
```

---

## Retrieval Patterns

### Semantic Search

```python
def retrieve_brand_guidelines(channel_id: int, query: str, top_k: int = 5):
    query_embedding = embedder.encode(query)
    
    results = vector_db.search(
        index=f"brand_memory_{channel_id}",
        vector=query_embedding,
        top_k=top_k,
        filter={"content_type": "guideline"}
    )
    
    return [r.text for r in results]
```

### Preference Aggregation

```python
def get_user_preferences(user_id: str) -> Dict:
    prefs = db.query(UserPreference).filter(
        UserPreference.user_id == user_id
    ).order_by(UserPreference.confidence_score.desc()).all()
    
    aggregated = {}
    for p in prefs:
        if p.preference_type not in aggregated:
            aggregated[p.preference_type] = []
        aggregated[p.preference_type].append({
            "data": p.preference_data,
            "confidence": p.confidence_score
        })
    
    return aggregated
```

---

## Document Information

- **Version**: 2.0
- **Last Updated**: 2024
- **Author**: AICF Engineering Team
- **Status**: Planned (Phase 9)
